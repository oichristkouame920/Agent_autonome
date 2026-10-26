@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem 1) Runtime Python portable embarque : priorite maximale.
if exist "runtime\python\python.exe" goto PORTABLE

rem 2) Environnement virtuel local recreable sur chaque machine.
if exist ".venv\Scripts\python.exe" goto VENV
if exist "venv\Scripts\python.exe" goto OLDVENV

rem 3) Python installe sur Windows, en dernier recours.
where py.exe >nul 2>&1
if %errorlevel%==0 goto PYLAUNCHER
where python.exe >nul 2>&1
if %errorlevel%==0 goto SYSTEMPY

echo AgentLocal ne trouve aucun runtime Python utilisable.
echo Lance preparer_agentlocal_nouveau_pc.bat ou construis runtime\python.
pause
exit /b 1

:PORTABLE
"runtime\python\python.exe" "verifier_runtime_v11_2.py" --startup --quiet
if errorlevel 2 goto DIAGFAIL
if exist "runtime\python\pythonw.exe" (
    start "" "runtime\python\pythonw.exe" "app\gui.py"
) else (
    start "" "runtime\python\python.exe" "app\gui.py"
)
exit /b 0

:VENV
".venv\Scripts\python.exe" "verifier_runtime_v11_2.py" --startup --quiet
if errorlevel 2 goto DIAGFAIL
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "app\gui.py"
) else (
    start "" ".venv\Scripts\python.exe" "app\gui.py"
)
exit /b 0

:OLDVENV
"venv\Scripts\python.exe" "verifier_runtime_v11_2.py" --startup --quiet
if errorlevel 2 goto DIAGFAIL
if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" "app\gui.py"
) else (
    start "" "venv\Scripts\python.exe" "app\gui.py"
)
exit /b 0

:PYLAUNCHER
py -3 "verifier_runtime_v11_2.py" --startup --quiet
if errorlevel 2 goto DIAGFAIL
start "" pyw -3 "app\gui.py"
exit /b 0

:SYSTEMPY
python.exe "verifier_runtime_v11_2.py" --startup --quiet
if errorlevel 2 goto DIAGFAIL
where pythonw.exe >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw.exe "app\gui.py"
) else (
    start "" python.exe "app\gui.py"
)
exit /b 0

:DIAGFAIL
echo.
echo Le diagnostic AgentLocal a detecte une erreur structurelle.
echo Lance : python verifier_runtime_v11_2.py
pause
exit /b 2
