@echo off
cd /d "%~dp0"

set MAX_ARTICLES=15
set MAX_SEND_MESSAGES=0

echo ============================================
echo  Indian Datacenter News Automation
echo ============================================

if not exist "venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    python -m venv venv
)

echo Installing Python packages...
call venv\Scripts\pip.exe install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo ERROR: Python package install failed.
    pause
    exit /b 1
)

echo Installing Node.js packages...
call npm install --silent
if %errorlevel% neq 0 (
    echo ERROR: Node.js package install failed.
    pause
    exit /b 1
)

echo Running daily news automation...
call venv\Scripts\python.exe run_daily.py

echo ============================================
echo  Done.
echo ============================================
pause
