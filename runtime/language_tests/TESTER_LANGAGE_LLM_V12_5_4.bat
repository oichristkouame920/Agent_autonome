@echo off
setlocal EnableExtensions
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
if not exist "%ROOT%\verifier_conformite_pack_v12.py" (
  echo ERREUR : Le dossier AgentLocal est introuvable.
  pause
  exit /b 1
)
set "PYEXE="
if exist "%ROOT%\.venv\Scripts\python.exe" set "PYEXE=%ROOT%\.venv\Scripts\python.exe"
if not defined PYEXE if exist "%ROOT%\runtime\python\python.exe" set "PYEXE=%ROOT%\runtime\python\python.exe"
if not defined PYEXE if exist "%ROOT%\venv\Scripts\python.exe" set "PYEXE=%ROOT%\venv\Scripts\python.exe"
if not defined PYEXE (
  where py >nul 2>nul
  if not errorlevel 1 set "PYEXE=py"
)
if not defined PYEXE (
  where python >nul 2>nul
  if not errorlevel 1 set "PYEXE=python"
)
if not defined PYEXE (
  echo ERREUR : Aucun Python utilisable.
  pause
  exit /b 1
)
cd /d "%ROOT%"
echo AgentLocal - test manuel de comprehension LLM ^(sans execution d'actions^)
if /I "%PYEXE%"=="py" (
  py -3 "%ROOT%\runtime\language_tests\verifier_v12_5_4_llm_live.py"
) else (
  "%PYEXE%" "%ROOT%\runtime\language_tests\verifier_v12_5_4_llm_live.py"
)
set "RESULT=%errorlevel%"
echo.
echo Fin des tests LLM. Code : %RESULT%
pause
exit /b %RESULT%
