@echo off
chcp 65001 >nul
title COA Parser Auto Launcher

:: Fast path: if virtual environment already exists and is configured, run directly!
if exist ".venv\Scripts\python.exe" (
    if exist ".venv\dependencies_installed.txt" (
        echo [SYSTEM] Fast-launching AI COA Parser...
        .venv\Scripts\python.exe -m app.main
        if errorlevel 1 (
            echo [WARNING] Application closed with exit code %errorlevel%.
            pause
        )
        exit /b
    )
)

echo ==============================================================
echo [SYSTEM] Starting AI COA Parser ^& Verification Hub...
echo ==============================================================

:: Find python executable
set "PYTHON_CMD="

:: Try 'py -3.12' first (recommended stable version)
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.12"
    goto python_found
)

:: Try 'py -3.11' second
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.11"
    goto python_found
)

:: Try standard 'py' launcher
py --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py"
    goto python_found
)

:: Try 'python'
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto python_found
)

:python_error
echo [ERROR] No compatible Python installation found.
echo Please install Python 3.11 or 3.12 (highly recommended).
echo.
pause
exit /b

:python_found
echo [SYSTEM] Using Python executor: %PYTHON_CMD%

:: Create virtual environment if it does not exist
if not exist ".venv" (
    echo [SYSTEM] Creating a secure Python virtual environment venv...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create Python virtual environment.
        pause
        exit /b
    )
    echo [SYSTEM] Virtual environment created successfully.
)

:: Activate virtual environment
echo [SYSTEM] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b
)

:: Install/update dependencies only if not already done
if not exist ".venv\dependencies_installed.txt" (
    echo [SYSTEM] Checking and updating required software libraries...
    echo Please note: This may take a minute on the first run.
    python -m pip install --upgrade pip >nul 2>&1
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies. Please check your internet connection.
        pause
        exit /b
    )
    echo Done > ".venv\dependencies_installed.txt"
) else (
    echo [SYSTEM] Dependencies already verified. Skipping update check to launch faster.
)

:: Start the application
echo [SYSTEM] Launching GUI dashboard...
python -m app.main
if errorlevel 1 (
    echo [WARNING] Application closed with exit code %errorlevel%.
    pause
)

:: Deactivate virtual env
call deactivate
echo [SYSTEM] Application closed.
pause
