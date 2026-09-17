@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No esta instalado todavia. Ejecuta primero setup.bat
    pause
    exit /b 1
)

".venv\Scripts\python.exe" server.py
pause
