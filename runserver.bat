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

:: 检查虚拟环境是否存在
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo [错误] 未找到虚拟环境激活脚本: %VENV_PATH%\Scripts\activate.bat
    echo 请检查虚拟环境路径是否正确
    echo 当前设置的虚拟环境路径: %VENV_PATH%
    echo.
    echo 请按任意键退出...
    pause >nul
    exit /b 1
)

echo [成功] 找到虚拟环境: %VENV_PATH%
echo.

:: 在新的CMD窗口中激活虚拟环境并执行命令

:: 启动 Redis (端口 6380)
echo [1/3] 启动 Redis 服务器 (端口:6380)...
start "Redis Server" cmd /k "redis-server --port 6380"

:: 等待2秒让Redis启动
timeout /t 2 /nobreak >nul

:: 启动 Celery Worker - 先激活虚拟环境
echo [2/3] 启动 Celery Worker...
start "Celery Worker" cmd /k "cd /d "%CURRENT_DIR%" && call "%VENV_PATH%\Scripts\activate.bat" && echo Celery环境已激活 && celery -A IntelligentHomeworkGradingSystem worker -l info --pool=solo"

:: 启动 Django Server - 先激活虚拟环境
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