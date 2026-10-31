# 智能作业批改系统

一个基于 Django 的智能作业批改系统，支持用户管理、题目管理、作业批改和知识追踪等功能。

## 技术栈

- **后端框架**: Django 4.2 + Django REST Framework
- **数据库**: MySQL
- **任务队列**: Celery + Redis
- **认证**: JWT (djangorestframework-simplejwt)
- **AI集成**: OpenAI API

## 项目结构

```
├── userManageModule/       # 用户管理模块
├── questionManageModule/   # 题目管理模块
├── gradingModule/          # 批改模块
├── assignmentAndClassModule/ # 作业与班级模块
├── BKTModule/              # 贝叶斯知识追踪模块
├── dkt_app/                # 深度知识追踪模块
└── IntelligentHomeworkGradingSystem/  # 项目配置
```

## 运行方法

### 一键启动（推荐）

环境准备好之后，一条命令即可拉起 Redis、Celery 和 Django：

```bash
python deploy.py dev
```

Windows 下也可以直接双击 `start.bat`，Linux/macOS 用 `./start.sh`。

脚本会自动完成：环境自检 → 检查/拉起 Redis(6380) → 数据库迁移 → 启动 Celery → 启动 Django。
按 `Ctrl+C` 会连同子进程一起退出。

其他常用命令：

```bash
python deploy.py check                      # 只做环境自检，不启动任何服务
python deploy.py dev --no-celery            # 不起 Celery（只调页面/接口时够用）
python deploy.py dev --port 8080            # 换端口
python deploy.py migrate                    # 只执行数据库迁移
python deploy.py prod --workers 4           # 生产模式：collectstatic + Celery + gunicorn
```

> `deploy.py` 使用「当前解释器」启动所有子进程，不写死 `.venv` 路径。
> 因此 conda 环境、venv、系统 Python 都可以，只要该环境里装好了依赖。

### 首次准备

1. **Python 3.10 / 3.11**（3.12 起 `settings.py` 里的 distutils 导入会失败）
2. **安装依赖**

   ```bash
   pip install -r requirements.txt
   # 依赖清单目前缺 torch / numpy，DKT 与推荐模块需要手动补：
   pip install torch numpy
   ```

3. **创建数据库**（库名固定 `ihgs`）

   ```bash
   mysql -uroot -p -e "CREATE DATABASE ihgs CHARACTER SET utf8mb4;"
   ```

4. **准备配置文件**

   ```bash
   cp config.example.py config.py   # 然后填入 MySQL 密码、大模型 Key、微信凭证
   ```

   配置齐全后运行 `python deploy.py check` 自检，全绿再启动。

### 手动启动（不用脚本时）

```bash
redis-server --port 6380                    # Redis 必须跑在 6380
python manage.py migrate
celery -A IntelligentHomeworkGradingSystem worker -l info --pool=solo   # Windows 需要 --pool=solo
python manage.py runserver
```

访问 http://127.0.0.1:8000 使用系统；接口统一在 `/api/v1/` 下。

