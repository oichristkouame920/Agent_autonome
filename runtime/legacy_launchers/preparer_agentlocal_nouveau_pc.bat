@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if exist "runtime\python\python.exe" (
    echo Runtime Python portable detecte. Aucune creation de venv necessaire.
    "runtime\python\python.exe" "verifier_runtime_v11_2.py"
    exit /b %errorlevel%
)

if exist ".venv\Scripts\python.exe" goto INSTALL

where py.exe >nul 2>&1
if %errorlevel%==0 (
    py -3 -m venv ".venv"
    if errorlevel 1 goto FAIL
    goto INSTALL
)

where python.exe >nul 2>&1
if %errorlevel%==0 (
    python.exe -m venv ".venv"
    if errorlevel 1 goto FAIL
    goto INSTALL
)

echo Aucun Python utilisable n'a ete trouve.
echo Installe Python 64 bits avec Tcl/Tk ou embarque runtime\python.
goto FAIL

:INSTALL
if not exist ".venv\Scripts\python.exe" goto FAIL

set "WHEELS="
for %%F in ("vendor\wheels\*.whl") do set "WHEELS=1"
if defined WHEELS (
    echo Installation hors connexion depuis vendor\wheels ...
    ".venv\Scripts\python.exe" -m pip install --no-index --find-links "vendor\wheels" -r "requirements.txt"
) else (
    echo Aucun cache offline trouve. Installation standard via pip ...
    ".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
)
if errorlevel 1 goto FAIL

".venv\Scripts\python.exe" "verifier_runtime_v11_2.py"
exit /b %errorlevel%

:FAIL
echo.
echo Preparation AgentLocal echouee.
pause
exit /b 1
