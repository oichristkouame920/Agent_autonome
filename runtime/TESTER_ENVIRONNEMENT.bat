@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
rem Cet outil n'est pas un second lanceur principal AgentLocal.
if exist "runtime\python\python.exe" (
  "runtime\python\python.exe" --version >nul 2>&1
  if not errorlevel 1 goto PORTABLE
)
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" --version >nul 2>&1
  if not errorlevel 1 goto VENV
)
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" --version >nul 2>&1
  if not errorlevel 1 goto OLDVENV
)
where python.exe >nul 2>&1
if not errorlevel 1 goto SYSTEM
where py.exe >nul 2>&1
if not errorlevel 1 goto PY_LAUNCHER
echo ERREUR: Python introuvable. Utilise AgentLocal.bat, choix 5, pour preparer le PC.
exit /b 3
:PORTABLE
"runtime\python\python.exe" "runtime\agentlocal_test_manager.py" %*
exit /b %ERRORLEVEL%
:VENV
".venv\Scripts\python.exe" "runtime\agentlocal_test_manager.py" %*
exit /b %ERRORLEVEL%
:OLDVENV
"venv\Scripts\python.exe" "runtime\agentlocal_test_manager.py" %*
exit /b %ERRORLEVEL%
:SYSTEM
python.exe "runtime\agentlocal_test_manager.py" %*
exit /b %ERRORLEVEL%
:PY_LAUNCHER
py -3 "runtime\agentlocal_test_manager.py" %*
exit /b %ERRORLEVEL%
