@echo off
setlocal enabledelayedexpansion
title IHGS - one click launcher

rem ---------------------------------------------------------------
rem Finds a Python interpreter that can "import django".
rem Windows may alias "python" to the Microsoft Store stub, so plain
rem "python deploy.py" can fail with "Python was not found".
rem This launcher probes several candidates and uses the first one
rem that has the project dependencies installed.
rem NOTE: keep this file ASCII-only. Chinese text in .bat breaks the
rem       cmd parser when the file is UTF-8 encoded.
rem ---------------------------------------------------------------

set "DIR=%~dp0"
set "PY="
set "PYARGS="

rem 1) explicit override
if defined IHGS_PYTHON call :probe "%IHGS_PYTHON%"
if defined PY goto run

rem 2) project virtualenv
if exist "%DIR%.venv\Scripts\python.exe" call :probe "%DIR%.venv\Scripts\python.exe"
if defined PY goto run

rem 3) activated conda env
if defined CONDA_PREFIX if exist "%CONDA_PREFIX%\python.exe" call :probe "%CONDA_PREFIX%\python.exe"
if defined PY goto run

rem 4) named conda env (no activate needed)
where conda >nul 2>&1
if not errorlevel 1 call :probe_conda
if defined PY goto run

rem 5) py launcher
py -3.10 -c "import django" >nul 2>&1
if not errorlevel 1 (
    set "PY=py"
    set "PYARGS=-3.10"
)
if defined PY goto run

rem 6) python on PATH
python -c "import django" >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto run

goto no_python

:probe
"%~1" -c "import django" >nul 2>&1
if not errorlevel 1 set "PY=%~1"
exit /b 0

:probe_conda
rem Resolve the env's real interpreter path instead of using "conda run",
rem because conda run buffers stdout and hides live server logs.
set "CAND="
for /f "usebackq delims=" %%i in (`conda run -n IntelligentHomeworkGradingSystem python -c "import sys;print(sys.executable)" 2^>nul`) do set "CAND=%%i"
if defined CAND call :probe "%CAND%"
exit /b 0

:no_python
echo.
echo [FAIL] No Python interpreter with project dependencies was found.
echo.
echo   Fix it with one of:
echo     1) conda activate IntelligentHomeworkGradingSystem
echo        start.bat check
echo     2) "D:\miniconda\envs\IntelligentHomeworkGradingSystem\python.exe" deploy.py check
echo     3) set IHGS_PYTHON=D:\path\to\python.exe
echo.
pause
exit /b 1

:run
"%PY%" %PYARGS% "%DIR%deploy.py" %*
set "CODE=%ERRORLEVEL%"

rem keep the window open when launched by double click (no args)
if "%~1"=="" pause
exit /b %CODE%
