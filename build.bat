@echo off
title COA Parser Installer Builder
echo ==============================================================
echo [SYSTEM] Starting PyInstaller Compilation Pipeline...
echo ==============================================================

:: Check if virtual environment exists
if not exist ".venv" (
    echo [SYSTEM] Virtual environment not found. Please run run.bat once first to set up the environment.
    pause
    exit /b
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Make sure PyInstaller is installed
echo [SYSTEM] Verifying PyInstaller installation...
pip install pyinstaller

:: Clean previous build artifacts
echo [SYSTEM] Cleaning old build directories...
if exist "build" rd /s /q build
if exist "dist" rd /s /q dist

:: Compile Python app and static assets
echo [SYSTEM] Compiling Python backend and bundling static HTML/CSS assets...
pyinstaller --noconsole --name="COA_Parser" --add-data "frontend;frontend" app/main.py

if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller compilation failed.
    pause
    exit /b
)

echo.
echo ==============================================================
echo [SUCCESS] PyInstaller compilation completed successfully.
echo Output directory: dist\COA_Parser\
echo ==============================================================
echo.
echo [SYSTEM] Next Step: Compile installer using Inno Setup
echo.
echo 1. Install Inno Setup (free) from https://jrsoftware.org/isdl.php
echo 2. Open Inno Setup Compiler.
echo 3. Open the script file: installer_setup.iss
echo 4. Click "Compile" (or press Ctrl+F9).
echo 5. Your standalone wizard installer "COA_Parser_Setup.exe" will be 
echo    generated in the "dist_installer" directory.
echo.
pause
