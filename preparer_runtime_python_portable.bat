@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "preparer_runtime_python_portable.py" %*
    exit /b %errorlevel%
)

where py.exe >nul 2>&1
if %errorlevel%==0 (
    py -3 "preparer_runtime_python_portable.py" %*
    exit /b %errorlevel%
)

where python.exe >nul 2>&1
if %errorlevel%==0 (
    python.exe "preparer_runtime_python_portable.py" %*
    exit /b %errorlevel%
)

echo Python est introuvable. Installe Python 64 bits avec Tcl/Tk, puis relance ce script.
pause
exit /b 1
