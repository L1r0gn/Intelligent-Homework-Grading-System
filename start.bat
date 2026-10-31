@echo off
chcp 65001 >nul
setlocal
title 智能作业批改系统 - 一键启动

set "DIR=%~dp0"
set "PY=%DIR%.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" "%DIR%deploy.py" dev %*

rem 双击运行（没带参数）时停一下，方便看输出；命令行调用则直接退出
if "%~1"=="" pause
