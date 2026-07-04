@echo off
cd /d "%~dp0"

echo ============================================
echo  Indian Datacenter News Automation - Setup
echo ============================================

REM ---- Python virtual environment ----
if not exist "venv\Scripts\python.exe" (
    echo [1/4] Creating Python virtual environment...
    python -m venv venv
) else (
    echo [1/4] Python virtual environment found.
)

echo [2/4] Installing Python packages...
call venv\Scripts\pip.exe install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo ERROR: Python package install failed.
    pause
    exit /b 1
)

echo [3/4] Installing Node.js packages...
call npm install --silent
if %errorlevel% neq 0 (
    echo ERROR: Node.js package install failed.
    pause
    exit /b 1
)

echo [4/4] Running daily news automation...
call venv\Scripts\python.exe run_daily.py

echo ============================================
echo  Done.
echo ============================================
pause
