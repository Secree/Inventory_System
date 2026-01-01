@echo off
echo ====================================
echo Water Gallon Inventory System
echo ====================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    echo.
)

REM Activate virtual environment and install/update dependencies
echo Checking dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
.venv\Scripts\python.exe -m pip install --only-binary :all: -r requirements.txt --quiet

if %errorlevel% neq 0 (
    echo.
    echo Error installing dependencies. Press any key to exit...
    pause > nul
    exit /b 1
)

echo.
echo Starting application...
echo.

REM Run the application
.venv\Scripts\python.exe main.py

if %errorlevel% neq 0 (
    echo.
    echo Application closed with an error.
    echo Press any key to exit...
    pause > nul
)
