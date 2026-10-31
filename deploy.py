#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键部署 / 启动脚本（跨平台，Windows / Linux / macOS 通用）。

用法：
    python deploy.py check            # 环境自检，只检查不启动
    python deploy.py dev              # 开发模式：Redis + Celery + runserver
    python deploy.py prod             # 生产模式：collectstatic + Celery + gunicorn
    python deploy.py migrate          # 只执行数据库迁移
    python deploy.py dev --no-celery  # 不起 Celery（只调页面/接口时够用）
    python deploy.py prod --workers 4 --port 8000

设计要点：
1. 一律用「当前解释器」sys.executable 启动子进程，不写死 .venv 路径。
   所以用 conda / venv / 系统 Python 都能跑，只要那个环境里装了依赖。
2. 启动前做自检：依赖、config.py、MySQL、Redis、迁移是否齐全，缺什么直接说清楚。
3. 所有子进程由本脚本托管，Ctrl+C 会一起退出，不会留下孤儿进程。
"""
import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PY = sys.executable
REDIS_PORT = 6380

IS_WINDOWS = os.name == 'nt'

# 启动 Django 所需的最小依赖集合（import 名 -> pip 包名）
REQUIRED_MODULES = [
    ('django', 'Django'),
    ('rest_framework', 'djangorestframework'),
    ('rest_framework_simplejwt', 'djangorestframework-simplejwt'),
    ('pymysql', 'PyMySQL'),
    ('celery', 'celery'),
    ('redis', 'redis'),
    ('openai', 'openai'),
    ('PIL', 'Pillow'),
    ('numpy', 'numpy'),
    ('torch', 'torch'),
    ('pybloom_live', 'pybloom-live'),
]

C_RESET = '\033[0m'
C_RED = '\033[31m'
C_GREEN = '\033[32m'
C_YELLOW = '\033[33m'
C_CYAN = '\033[36m'


def _enable_ansi():
    """Windows 10+ 控制台开启 ANSI 颜色。"""
    if IS_WINDOWS:
        os.system('')


def info(msg):
    print(f'{C_CYAN}[信息]{C_RESET} {msg}', flush=True)


def ok(msg):
    print(f'{C_GREEN}[成功]{C_RESET} {msg}', flush=True)


def warn(msg):
    print(f'{C_YELLOW}[警告]{C_RESET} {msg}', flush=True)


def fail(msg):
    print(f'{C_RED}[失败]{C_RESET} {msg}', flush=True)


def header(title):
    print()
    print(f'{C_CYAN}{"=" * 56}{C_RESET}')
    print(f'{C_CYAN}  {title}{C_RESET}')
    print(f'{C_CYAN}{"=" * 56}{C_RESET}')


# --------------------------------------------------------------------------
# 基础探测
# --------------------------------------------------------------------------
def check_python():
    v = sys.version_info
    if v < (3, 10):
        fail(f'Python {v.major}.{v.minor} 过低，本项目需要 3.10+（当前代码还依赖 distutils/audioop，3.12+ 也不可用）')
        return False
    if v >= (3, 12):
        fail(f'Python {v.major}.{v.minor} 不可用：settings.py 仍导入 distutils，3.12 起已被移除')
        return False
    ok(f'Python {v.major}.{v.minor}.{v.micro}  {PY}')
    return True


def check_dependencies():
    missing = []
    for module, package in REQUIRED_MODULES:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    if missing:
        fail('缺少依赖：' + ' '.join(missing))
        print(f'       安装命令：{PY} -m pip install ' + ' '.join(f'"{p}"' for p in missing), flush=True)
        return False
    ok(f'依赖齐全（{len(REQUIRED_MODULES)} 个核心包）')
    return True


def check_config():
    """config.py 承载密钥，被 .gitignore 排除，新环境必须手工准备。"""
    config = BASE_DIR / 'config.py'
    example = BASE_DIR / 'config.example.py'
    if config.exists():
        ok('config.py 已存在')
        return True

    fail('缺少 config.py（数据库密码、大模型 Key、微信凭证都在里面）')
    if example.exists():
        print(f'       模板已就绪：{example.name}', flush=True)
        print('       请执行：cp config.example.py config.py 后填写真实值', flush=True)
    else:
        print('       请参考 README 手工创建', flush=True)
    return False


def port_open(host, port, timeout=0.4):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_port(host, port, seconds=10):
    for _ in range(seconds * 10):
        if port_open(host, port):
            return True
        time.sleep(0.1)
    return False


def check_mysql():
    """通过 Django 的连接层探测，能同时验证 config 与库名。"""
    try:
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IntelligentHomeworkGradingSystem.settings')
        django.setup()
        from django.db import connection
        connection.ensure_connection()
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
        db = connection.settings_dict
        ok(f"MySQL 连通：{db['USER']}@{db['HOST']}:{db['PORT']}/{db['NAME']}")
        return True
    except Exception as e:
        fail(f'MySQL 连接失败：{type(e).__name__}: {e}')
        print('       检查：MySQL 是否启动、config.py 中的 DATABASES_PASSWORD 是否正确、库 ihgs 是否已创建', flush=True)
        return False


def check_redis():
    if port_open('127.0.0.1', REDIS_PORT):
        ok(f'Redis 已在 {REDIS_PORT} 端口运行')
        return True
    warn(f'Redis 未在 {REDIS_PORT} 端口运行（启动时会尝试拉起）')
    return True


def check_migrations():
    """
    只检查、不写文件。仓库 `.gitignore` 里有 */migrations/，新增迁移极易漏提交，
    这里用 --check --dry-run 提前暴露「模型改了但没迁移」的情况。
    """
    r = subprocess.run(
        [PY, 'manage.py', 'makemigrations', '--check', '--dry-run'],
        cwd=BASE_DIR, capture_output=True, text=True,
    )
    if r.returncode == 0:
        ok('模型与迁移文件一致')
        return True
    warn('存在未生成的迁移（模型已改但缺少 migration 文件）：')
    for line in (r.stdout or r.stderr).strip().splitlines()[:8]:
        print('       ' + line, flush=True)
    print('       修复：python manage.py makemigrations && git add -f <新迁移文件>', flush=True)
    return True  # 仅警告，不阻断启动


# --------------------------------------------------------------------------
# 服务管理
# --------------------------------------------------------------------------
class Supervisor:
    """托管子进程，任一退出则全部停止，Ctrl+C 也能干净退出。"""

    def __init__(self):
        self.procs = []

    def spawn(self, name, cmd, env=None):
        info(f'启动 {name}：{" ".join(cmd)}')
        p = subprocess.Popen(cmd, cwd=str(BASE_DIR), env=env)
        self.procs.append((name, p))
        return p

    def shutdown(self):
        for name, p in self.procs:
            if p.poll() is None:
                info(f'停止 {name}')
                try:
                    p.terminate()
                except Exception:
                    pass
        deadline = time.time() + 8
        for name, p in self.procs:
            while p.poll() is None and time.time() < deadline:
                time.sleep(0.1)
            if p.poll() is None:
                try:
                    p.kill()
                except Exception:
                    pass

    def wait(self):
        """阻塞直到某个子进程退出。"""
        while True:
            for name, p in self.procs:
                code = p.poll()
                if code is not None:
                    warn(f'{name} 已退出（code={code}），停止其余服务')
                    return
            time.sleep(0.5)


def start_redis(sup):
    if port_open('127.0.0.1', REDIS_PORT):
        ok(f'Redis 已在 {REDIS_PORT} 端口运行，跳过启动')
        return True

    exe = shutil.which('redis-server')
    if not exe:
        fail('未找到 redis-server 命令，请先安装 Redis 或手动启动到 6380 端口')
        return False

    cmd = [exe, '--port', str(REDIS_PORT), '--save', '', '--appendonly', 'no']
    sup.spawn('Redis', cmd)
    if not wait_port('127.0.0.1', REDIS_PORT, 8):
        fail('Redis 启动超时')
        return False
    ok(f'Redis 就绪（{REDIS_PORT}）')
    return True


def start_celery(sup):
    cmd = [PY, '-m', 'celery', '-A', 'IntelligentHomeworkGradingSystem', 'worker',
           '-l', 'info']
    if IS_WINDOWS:
        # Windows 上 prefork 不可用，必须 solo
        cmd += ['--pool=solo']
    sup.spawn('Celery', cmd)
    return True


def run_migrate():
    info('执行数据库迁移')
    r = subprocess.run([PY, 'manage.py', 'migrate', '--noinput'], cwd=BASE_DIR)
    if r.returncode != 0:
        fail('迁移失败')
        return False
    ok('迁移完成')
    return True


def run_collectstatic():
    info('收集静态文件')
    r = subprocess.run([PY, 'manage.py', 'collectstatic', '--noinput'], cwd=BASE_DIR)
    if r.returncode != 0:
        warn('collectstatic 失败（开发模式可忽略，生产环境必须处理）')
        return False
    ok('静态文件已收集到 staticfiles/')
    return True


# --------------------------------------------------------------------------
# 命令实现
# --------------------------------------------------------------------------
def cmd_check(args):
    header('环境自检')
    results = [check_python(), check_dependencies(), check_config()]
    if not all(results):
        print()
        fail('自检未通过，请先解决上面的问题')
        return 1
    results.append(check_mysql())
    results.append(check_redis())
    results.append(check_migrations())

    header('Django 系统检查')
    r = subprocess.run([PY, 'manage.py', 'check'], cwd=BASE_DIR)
    results.append(r.returncode == 0)

    print()
    if all(results):
        ok('全部检查通过，可以启动')
        return 0
    fail('存在未通过项')
    return 1


def cmd_migrate(args):
    header('数据库迁移')
    if not (check_python() and check_dependencies() and check_config() and check_mysql()):
        return 1
    return 0 if run_migrate() else 1


def cmd_dev(args):
    header('开发模式启动')
    if not (check_python() and check_dependencies() and check_config() and check_mysql()):
        fail('自检未通过，已中止启动')
        return 1

    sup = Supervisor()
    try:
        if not start_redis(sup):
            return 1
        if not args.skip_migrate:
            if not run_migrate():
                return 1
        if args.with_celery:
            start_celery(sup)

        print()
        ok(f'服务启动中：http://{args.host}:{args.port}/    （Ctrl+C 全部停止）')
        print(f'       管理后台：http://{args.host}:{args.port}/admin/', flush=True)
        print(f'       接口前缀：http://{args.host}:{args.port}/api/v1/', flush=True)
        if not args.reload:
            print('       代码自动重载已关闭（--reload 可开启，但可能残留子进程）', flush=True)
        print()

        run_cmd = [PY, 'manage.py', 'runserver', f'{args.host}:{args.port}']
        if not args.reload:
            # runserver 的自动重载会 fork 子进程，父进程被停掉后子进程容易变孤儿，
            # 与「由本脚本统一托管」的模型冲突，所以默认关闭。
            run_cmd.append('--noreload')
        sup.spawn('Django', run_cmd)
        sup.wait()
    except KeyboardInterrupt:
        print()
        info('收到中断信号')
    finally:
        sup.shutdown()
    return 0


def cmd_prod(args):
    header('生产模式启动')
    if not (check_python() and check_dependencies() and check_config() and check_mysql()):
        fail('自检未通过，已中止启动')
        return 1

    try:
        import gunicorn  # noqa: F401
    except ImportError:
        fail('未安装 gunicorn，生产模式需要它：')
        print(f'       {PY} -m pip install gunicorn', flush=True)
        return 1

    sup = Supervisor()
    try:
        if not start_redis(sup):
            return 1
        if not args.skip_migrate:
            if not run_migrate():
                return 1
        run_collectstatic()
        start_celery(sup)

        print()
        ok(f'gunicorn 监听 0.0.0.0:{args.port}（{args.workers} workers）')
        print('       注意：静态文件需由 Nginx 转发 /static/ 与 /media/', flush=True)
        print()

        sup.spawn('gunicorn', [
            PY, '-m', 'gunicorn', 'IntelligentHomeworkGradingSystem.wsgi:application',
            '-b', f'0.0.0.0:{args.port}',
            '-w', str(args.workers),
            '--timeout', '120',
        ])
        sup.wait()
    except KeyboardInterrupt:
        print()
        info('收到中断信号')
    finally:
        sup.shutdown()
    return 0


def main():
    _enable_ansi()
    parser = argparse.ArgumentParser(
        description='智能作业批改系统 一键部署/启动',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='示例：\n'
               '  python deploy.py check\n'
               '  python deploy.py dev\n'
               '  python deploy.py prod --workers 4\n',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    p_check = sub.add_parser('check', help='仅做环境自检')
    p_check.set_defaults(func=cmd_check)

    p_migrate = sub.add_parser('migrate', help='仅执行数据库迁移')
    p_migrate.set_defaults(func=cmd_migrate)

    p_dev = sub.add_parser('dev', help='开发模式：Redis + Celery + runserver')
    p_dev.add_argument('--host', default='127.0.0.1')
    p_dev.add_argument('--port', type=int, default=8000)
    p_dev.add_argument('--no-celery', dest='with_celery', action='store_false',
                       help='不启动 Celery Worker')
    p_dev.add_argument('--skip-migrate', action='store_true', help='跳过迁移')
    p_dev.add_argument('--reload', action='store_true',
                       help='开启 runserver 自动重载（会 fork 子进程，退出时可能残留）')
    p_dev.set_defaults(func=cmd_dev, with_celery=True)

    p_prod = sub.add_parser('prod', help='生产模式：collectstatic + Celery + gunicorn')
    p_prod.add_argument('--port', type=int, default=8000)
    p_prod.add_argument('--workers', type=int, default=3)
    p_prod.add_argument('--skip-migrate', action='store_true', help='跳过迁移')
    p_prod.set_defaults(func=cmd_prod)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == '__main__':
    main()
