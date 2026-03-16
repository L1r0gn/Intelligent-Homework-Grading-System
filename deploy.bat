@echo off
chcp 65001 >nul
title 启动开发环境

echo ========================================
echo     正在启动开发环境，请稍候...
echo ========================================
echo.

:: 获取当前目录
set "CURRENT_DIR=%~dp0"
set "CURRENT_DIR=%CURRENT_DIR:~0,-1%"
echo 当前目录: %CURRENT_DIR%
echo.

:: 设置虚拟环境路径 - 请根据你的实际情况修改
:: 假设虚拟环境在当前目录下的 .venv 文件夹
set "VENV_PATH=%CURRENT_DIR%\.venv"
:: 如果你的虚拟环境在其他位置，请修改这一行，例如：
:: set "VENV_PATH=D:\myproject\venv"

:: ========== 环境准备阶段 ==========
:: 检查 Python 是否可用并验证版本 (需要 Python 3.10 或更高)
echo 检查系统 Python 版本...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请确保 Python 已安装并添加到 PATH 中。
    echo 请按任意键退出...
    pause >nul
    exit /b 1
)

python -c "import sys; exit(0 if sys.version_info[:2] >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [错误] Python 版本过低，需要 3.10 或更高版本。
    python --version
    echo 请升级 Python 后重试。
    echo 请按任意键退出...
    pause >nul
    exit /b 1
)
echo [成功] 系统 Python 版本符合要求。
echo.

:: 检查虚拟环境是否存在，不存在则创建
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo [信息] 未找到虚拟环境，正在创建...
    python -m venv "%VENV_PATH%"
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败，请检查权限或磁盘空间。
        pause >nul
        exit /b 1
    )
    echo [成功] 虚拟环境创建完成。
) else (
    echo [信息] 虚拟环境已存在，跳过创建步骤。
)
echo.

:: 激活虚拟环境（无论新建还是已存在，都需激活以便后续命令）
echo 正在激活虚拟环境...
call "%VENV_PATH%\Scripts\activate.bat"
if errorlevel 1 (
    echo [错误] 激活虚拟环境失败。
    pause >nul
    exit /b 1
)
echo [成功] 虚拟环境已激活。
echo.

:: 如果虚拟环境是新创建的，则安装依赖
if not exist "%VENV_PATH%\Scripts\pip.exe" (
    echo [信息] 检测到新的虚拟环境，正在安装依赖...
    if exist "%CURRENT_DIR%\requirements_py3.10.txt" (
        pip install -r "%CURRENT_DIR%\requirements_py3.10.txt"
        if errorlevel 1 (
            echo [错误] 依赖安装失败，请检查网络或 requirements 文件。
            pause >nul
            exit /b 1
        )
        echo [成功] 依赖安装完成。
    ) else (
        echo [警告] 未找到 requirements_py3.10.txt 文件，跳过依赖安装。
    )
) else (
    echo [信息] 虚拟环境已包含 pip，跳过依赖安装（如需更新请手动执行 pip install -r requirements_py3.10.txt）
)
echo.

:: ========== 数据库配置阶段 ==========
cd /d "%CURRENT_DIR%"

echo 执行数据库迁移...
python manage.py makemigrations
if errorlevel 1 (
    echo [错误] makemigrations 失败，请检查模型定义。
    pause >nul
    exit /b 1
)

python manage.py migrate
if errorlevel 1 (
    echo [错误] migrate 失败，请检查数据库配置。
    pause >nul
    exit /b 1
)
echo [成功] 数据库迁移完成。
echo.

:: 询问是否创建管理员账号
set /p CREATE_SUPERUSER="是否创建超级管理员账号？(y/n): "
if /i "%CREATE_SUPERUSER%"=="y" (
    echo 开始创建超级管理员...
    python manage.py createsuperuser
    if errorlevel 1 (
        echo [警告] 创建管理员失败，可能是输入错误或已存在。
    ) else (
        echo [成功] 超级管理员创建完成。
    )
) else (
    echo 跳过创建管理员。
)
echo.

:: ========== 启动服务阶段 ==========
:: 注意：以下服务将在新窗口中运行，每个窗口都会独立激活虚拟环境

:: 启动 Redis (端口 6380)
echo [1/3] 启动 Redis 服务器 (端口:6380)...
start "Redis Server" cmd /k "redis-server --port 6380"

:: 等待2秒让Redis启动
timeout /t 2 /nobreak >nul

:: 启动 Celery Worker
echo [2/3] 启动 Celery Worker...
start "Celery Worker" cmd /k "cd /d "%CURRENT_DIR%" && call "%VENV_PATH%\Scripts\activate.bat" && echo Celery环境已激活 && celery -A IntelligentHomeworkGradingSystem worker -l info --pool=solo"

:: 启动 Django Server
echo [3/3] 启动 Django 开发服务器...
start "Django Server" cmd /k "cd /d "%CURRENT_DIR%" && call "%VENV_PATH%\Scripts\activate.bat" && echo Django环境已激活 && python manage.py runserver"

echo.
echo ========================================
echo     所有服务启动命令已执行！
echo     请查看各个窗口的输出确认服务正常启动。
echo ========================================
echo.
echo 按任意键关闭此窗口...
pause >nul
exit