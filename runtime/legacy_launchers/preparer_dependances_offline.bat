@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "vendor\wheels" mkdir "vendor\wheels"

if exist ".venv\Scripts\python.exe" goto VENV
where py.exe >nul 2>&1
if %errorlevel%==0 goto PYLAUNCHER
where python.exe >nul 2>&1
if %errorlevel%==0 goto SYSTEMPY

echo Python est introuvable.
pause
exit /b 1

:VENV
".venv\Scripts\python.exe" -m pip download --only-binary=:all: --dest "vendor\wheels" -r "requirements.txt"
exit /b %errorlevel%

:PYLAUNCHER
py -3 -m pip download --only-binary=:all: --dest "vendor\wheels" -r "requirements.txt"
exit /b %errorlevel%

:SYSTEMPY
python.exe -m pip download --only-binary=:all: --dest "vendor\wheels" -r "requirements.txt"
exit /b %errorlevel%
