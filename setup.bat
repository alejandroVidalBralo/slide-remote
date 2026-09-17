@echo off
setlocal
cd /d "%~dp0"

echo ==============================================================
echo  Instalando el mando de diapositivas (solo hace falta una vez)
echo ==============================================================

py -3.11 -m venv .venv
if errorlevel 1 (
    echo.
    echo No se encontro Python 3.11. Instalalo con:
    echo    winget install --id Python.Python.3.11 -e
    echo y vuelve a ejecutar este setup.bat
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
".venv\Scripts\python.exe" patch_bless.py

echo.
echo ==============================================================
echo  Instalacion completa. A partir de ahora usa start.bat
echo ==============================================================
pause
