@echo off
setlocal
cd /d "%~dp0"

if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" "app\gui.py"
    exit /b 0
)

where pythonw.exe >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw.exe "app\gui.py"
    exit /b 0
)

echo Python avec Tkinter est introuvable.
echo Activez votre environnement virtuel ou reinstallez Python avec Tcl/Tk.
pause
exit /b 1
