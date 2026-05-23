@echo off
title GPLinks Affiliate Forwarder Controller
cls
echo =========================================================================
echo             ⚡ GPLINKS AFFILIATE FORWARDER - ONE CLICK LAUNCHER ⚡
echo =========================================================================
echo  Operating System: Windows - Engine: Python FastAPI Dashboard + Poller
echo =========================================================================
echo.

:: Try global python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto check_venv
)

:: Try py launcher
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto check_venv
)

:: Try standard local AppData installations
if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" (
    set PYTHON_CMD="%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
    goto check_venv
)
if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" (
    set PYTHON_CMD="%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
    goto check_venv
)
if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe" (
    set PYTHON_CMD="%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe"
    goto check_venv
)
if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python39\python.exe" (
    set PYTHON_CMD="%USERPROFILE%\AppData\Local\Programs\Python\Python39\python.exe"
    goto check_venv
)

echo [ERROR] Python is not detected in your system path or AppData!
echo Please install Python 3.9+ from python.org and check "Add Python to PATH".
pause
exit /b

:check_venv
:: Validate virtual environment existence
if exist .venv goto activate_venv

echo [INFO] Creating Python Virtual Environment (.venv)...
%PYTHON_CMD% -m venv .venv
if %errorlevel% neq 0 (
    echo [WARNING] Failed to create virtual environment. Running globally.
    goto global_run
)

:activate_venv
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate

echo [INFO] Auditing/installing pip package dependencies...
pip install -r requirements.txt --upgrade
if %errorlevel% neq 0 (
    echo [ERROR] Dependency installation failed! Check internet connection.
    pause
    exit /b
)

:: Start Server
echo [SUCCESS] Subsystems verified. Launching FastAPI Control Center...
python web_dashboard.py
goto end

:global_run
echo [INFO] Auditing/installing dependencies globally...
pip install -r requirements.txt --upgrade
%PYTHON_CMD% web_dashboard.py

:end
pause
