#!/bin/bash

# 设置控制台编码和标题
echo -e "\033]0;启动开发环境\007"
chcp 65001 > /dev/null 2>&1  # Windows兼容，Linux/macOS忽略

echo "========================================"
echo "    正在启动开发环境，请稍候..."
echo "========================================"
echo ""

# 获取当前目录
CURRENT_DIR=$(cd "$(dirname "$0")" && pwd)
echo "当前目录: $CURRENT_DIR"
echo ""

# 设置虚拟环境路径 - 请根据你的实际情况修改
VENV_PATH="$CURRENT_DIR/.venv"
# 如果你的虚拟环境在其他位置，请修改这一行，例如：
# VENV_PATH="/path/to/your/venv"

# ========== 环境准备阶段 ==========
# 检查 Python 是否可用并验证版本 (需要 Python 3.10 或更高)
echo "检查系统 Python 版本..."
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3，请确保 Python 已安装并添加到 PATH 中。"
    read -p "请按 Enter 键退出..."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if ! python3 -c "import sys; exit(0 if sys.version_info[:2] >= (3,10) else 1)" 2>/dev/null; then
    echo "[错误] Python 版本过低，需要 3.10 或更高版本。"
    echo "当前版本: $PYTHON_VERSION"
    echo "请升级 Python 后重试。"
    read -p "请按 Enter 键退出..."
    exit 1
fi
echo "[成功] 系统 Python 版本符合要求 ($PYTHON_VERSION)"
echo ""

# 检查虚拟环境是否存在，不存在则创建
if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "[信息] 未找到虚拟环境，正在创建..."
    python3 -m venv "$VENV_PATH"
    if [ $? -ne 0 ]; then
        echo "[错误] 创建虚拟环境失败，请检查权限或磁盘空间。"
        read -p "请按 Enter 键退出..."
        exit 1
    fi
    echo "[成功] 虚拟环境创建完成。"
else
    echo "[信息] 虚拟环境已存在，跳过创建步骤。"
fi
echo ""

# 激活虚拟环境
echo "正在激活虚拟环境..."
source "$VENV_PATH/bin/activate"
if [ $? -ne 0 ]; then
    echo "[错误] 激活虚拟环境失败。"
    read -p "请按 Enter 键退出..."
    exit 1
fi
echo "[成功] 虚拟环境已激活。"
echo ""

# 如果虚拟环境是新创建的，则安装依赖
if [ ! -f "$VENV_PATH/bin/pip" ]; then
    echo "[信息] 检测到新的虚拟环境，正在安装依赖..."
    if [ -f "$CURRENT_DIR/requirements_py3.10.txt" ]; then
        pip install -r "$CURRENT_DIR/requirements_py3.10.txt"
        if [ $? -ne 0 ]; then
            echo "[错误] 依赖安装失败，请检查网络或 requirements 文件。"
            read -p "请按 Enter 键退出..."
            exit 1
        fi
        echo "[成功] 依赖安装完成。"
    else
        echo "[警告] 未找到 requirements_py3.10.txt 文件，跳过依赖安装。"
    fi
else
    echo "[信息] 虚拟环境已包含 pip，跳过依赖安装（如需更新请手动执行 pip install -r requirements_py3.10.txt）"
fi
echo ""

# ========== 数据库配置阶段 ==========
cd "$CURRENT_DIR"

echo "执行数据库迁移..."
python manage.py makemigrations
if [ $? -ne 0 ]; then
    echo "[错误] makemigrations 失败，请检查模型定义。"
    read -p "请按 Enter 键退出..."
    exit 1
fi

python manage.py migrate
if [ $? -ne 0 ]; then
    echo "[错误] migrate 失败，请检查数据库配置。"
    read -p "请按 Enter 键退出..."
    exit 1
fi
echo "[成功] 数据库迁移完成。"
echo ""

# 询问是否创建管理员账号
read -p "是否创建超级管理员账号？(y/n): " CREATE_SUPERUSER
if [[ "$CREATE_SUPERUSER" == "y" || "$CREATE_SUPERUSER" == "Y" ]]; then
    echo "开始创建超级管理员..."
    python manage.py createsuperuser
    if [ $? -ne 0 ]; then
        echo "[警告] 创建管理员失败，可能是输入错误或已存在。"
    else
        echo "[成功] 超级管理员创建完成。"
    fi
else
    echo "跳过创建管理员。"
fi
echo ""

# ========== 启动服务阶段 ==========
# 注意：以下服务将在新终端窗口中运行，每个窗口都会独立激活虚拟环境
# 需要根据你的终端模拟器调整启动命令（这里使用常见的 gnome-terminal, xterm, 或 macOS 的 Terminal）

# 检测可用的终端模拟器
if command -v gnome-terminal &> /dev/null; then
    TERM_CMD="gnome-terminal --"
elif command -v xterm &> /dev/null; then
    TERM_CMD="xterm -e"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS 使用 open 命令打开 Terminal.app
    TERM_CMD="open -a Terminal.app"
else
    echo "[警告] 未找到支持的终端模拟器，将后台运行服务（可能无法看到输出）"
    TERM_CMD=""
fi

# 启动 Redis (端口 6380)
echo "[1/3] 启动 Redis 服务器 (端口:6380)..."
if command -v redis-server &> /dev/null; then
    if [[ -n "$TERM_CMD" ]]; then
        if [[ "$TERM_CMD" == "open -a Terminal.app" ]]; then
            osascript -e 'tell application "Terminal" to do script "redis-server --port 6380"'
        else
            $TERM_CMD redis-server --port 6380
        fi
    else
        redis-server --port 6380 &
    fi
else
    echo "[警告] 未找到 redis-server 命令，请确保 Redis 已安装。"
fi

# 等待2秒让Redis启动
sleep 2

# 启动 Celery Worker
echo "[2/3] 启动 Celery Worker..."
CELERY_CMD="cd '$CURRENT_DIR' && source '$VENV_PATH/bin/activate' && echo 'Celery环境已激活' && celery -A IntelligentHomeworkGradingSystem worker -l info --pool=solo"
if [[ -n "$TERM_CMD" ]]; then
    if [[ "$TERM_CMD" == "open -a Terminal.app" ]]; then
        osascript -e 'tell application "Terminal" to do script "'"$CELERY_CMD"'"'
    else
        $TERM_CMD bash -c "$CELERY_CMD"
    fi
else
    bash -c "$CELERY_CMD" &
fi

# 启动 Django Server
echo "[3/3] 启动 Django 开发服务器..."
DJANGO_CMD="cd '$CURRENT_DIR' && source '$VENV_PATH/bin/activate' && echo 'Django环境已激活' && python manage.py runserver"
if [[ -n "$TERM_CMD" ]]; then
    if [[ "$TERM_CMD" == "open -a Terminal.app" ]]; then
        osascript -e 'tell application "Terminal" to do script "'"$DJANGO_CMD"'"'
    else
        $TERM_CMD bash -c "$DJANGO_CMD"
    fi
else
    bash -c "$DJANGO_CMD" &
fi

echo ""
echo "========================================"
echo "    所有服务启动命令已执行！"
echo "    请查看各个窗口的输出确认服务正常启动。"
echo "========================================"
echo ""
read -p "按 Enter 键关闭此窗口..."
exit 0