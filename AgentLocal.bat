@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title AgentLocal - Lanceur unique

rem AgentLocal V12.1 R4 - point d'entree utilisateur unique.
rem Les anciens .bat sont archives automatiquement au premier lancement.
call :ARCHIVE_LEGACY >nul 2>&1

if not "%~1"=="" goto DISPATCH
goto MENU

:MENU
cls
echo ============================================================
echo                  AGENTLOCAL - LANCEUR UNIQUE
echo ============================================================
echo.
echo [1] Lancer AgentLocal
echo [2] Diagnostic / etat technique
echo [3] Tester tout AgentLocal
echo [4] Verifier / finaliser l'installation
echo [5] Preparer AgentLocal sur un nouveau PC
echo [6] Preparer les dependances hors connexion
echo [7] Construire / mettre a jour le runtime Python portable
echo [8] Afficher la version
echo [0] Quitter
echo.
set /p "CHOIX=Choix : "

if "%CHOIX%"=="1" goto LAUNCH
if "%CHOIX%"=="2" goto DIAG
if "%CHOIX%"=="3" goto TEST
if "%CHOIX%"=="4" goto VERIFY
if "%CHOIX%"=="5" goto SETUP
if "%CHOIX%"=="6" goto OFFLINE
if "%CHOIX%"=="7" goto RUNTIME
if "%CHOIX%"=="8" goto VERSION
if "%CHOIX%"=="0" goto END

echo.
echo Choix invalide.
pause
goto MENU

:DISPATCH
set "CMD=%~1"
shift
if /I "%CMD%"=="start" goto LAUNCH
if /I "%CMD%"=="launch" goto LAUNCH
if /I "%CMD%"=="gui" goto LAUNCH
if /I "%CMD%"=="diag" goto DIAG
if /I "%CMD%"=="diagnostic" goto DIAG
if /I "%CMD%"=="status" goto DIAG
if /I "%CMD%"=="test" goto TEST
if /I "%CMD%"=="tests" goto TEST
if /I "%CMD%"=="verify" goto VERIFY
if /I "%CMD%"=="finalize" goto VERIFY
if /I "%CMD%"=="finaliser" goto VERIFY
if /I "%CMD%"=="setup" goto SETUP
if /I "%CMD%"=="install" goto SETUP
if /I "%CMD%"=="offline" goto OFFLINE
if /I "%CMD%"=="runtime" goto RUNTIME
if /I "%CMD%"=="version" goto VERSION
if /I "%CMD%"=="menu" goto MENU
if /I "%CMD%"=="help" goto HELP
if /I "%CMD%"=="--help" goto HELP
if /I "%CMD%"=="-h" goto HELP

echo Commande inconnue : %CMD%
echo.
goto HELP

:LAUNCH
call :FIND_PYTHON
if not defined PY_MODE goto NO_PYTHON
call :RUN_PY "verifier_resilience_v11_3.py" --startup --quiet
set "RC=%ERRORLEVEL%"
if %RC% GEQ 2 goto DIAGFAIL
call :START_GUI
exit /b %ERRORLEVEL%

:DIAG
call :FIND_PYTHON
if not defined PY_MODE goto NO_PYTHON
call :RUN_PY "verifier_resilience_v11_3.py" --startup
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
    echo Diagnostic AgentLocal termine.
) else (
    echo Diagnostic termine avec le code %RC%.
)
pause
exit /b %RC%

:TEST
where powershell.exe >nul 2>&1
if errorlevel 1 (
    echo PowerShell Windows est introuvable. Impossible de lancer la suite globale.
    pause
    exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tester_agentlocal.ps1"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
    echo Tous les tests AgentLocal sont passes.
) else (
    echo Des tests AgentLocal ont echoue. Code : %RC%
)
pause
exit /b %RC%

:VERIFY
call :CLEAN_OBSOLETE
echo.
echo === Verification / finalisation AgentLocal ===
where powershell.exe >nul 2>&1
if errorlevel 1 (
    echo PowerShell Windows est introuvable. Verification impossible.
    pause
    exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tester_agentlocal.ps1"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
    echo AgentLocal est conforme et pret.
) else (
    echo Verification echouee. Code : %RC%
)
pause
exit /b %RC%

:SETUP
cd /d "%~dp0"
if exist "runtime\python\python.exe" (
    echo Runtime Python portable detecte. Aucune creation de venv necessaire.
    "runtime\python\python.exe" "verifier_runtime_v11_2.py"
    set "RC=%ERRORLEVEL%"
    pause
    exit /b %RC%
)

if not exist ".venv\Scripts\python.exe" (
    where py.exe >nul 2>&1
    if not errorlevel 1 (
        py -3 -m venv ".venv"
        if errorlevel 1 goto SETUP_FAIL
    ) else (
        where python.exe >nul 2>&1
        if errorlevel 1 goto SETUP_FAIL
        python.exe -m venv ".venv"
        if errorlevel 1 goto SETUP_FAIL
    )
)

if not exist ".venv\Scripts\python.exe" goto SETUP_FAIL
set "WHEELS="
for %%F in ("vendor\wheels\*.whl") do set "WHEELS=1"
if defined WHEELS (
    echo Installation hors connexion depuis vendor\wheels ...
    ".venv\Scripts\python.exe" -m pip install --no-index --find-links "vendor\wheels" -r "requirements.txt"
) else (
    echo Aucun cache offline trouve. Installation standard via pip ...
    ".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
)
if errorlevel 1 goto SETUP_FAIL
".venv\Scripts\python.exe" "verifier_runtime_v11_2.py"
set "RC=%ERRORLEVEL%"
pause
exit /b %RC%

:SETUP_FAIL
echo.
echo Preparation AgentLocal echouee.
echo Verifie qu'un Python 64 bits avec Tcl/Tk est disponible.
pause
exit /b 1

:OFFLINE
if not exist "vendor\wheels" mkdir "vendor\wheels"
call :FIND_PIP_PYTHON
if not defined PIP_MODE (
    echo Python avec pip est introuvable.
    pause
    exit /b 1
)
call :RUN_PIP_PY -m pip download --only-binary=:all: --dest "vendor\wheels" -r "requirements.txt"
set "RC=%ERRORLEVEL%"
pause
exit /b %RC%

:RUNTIME
call :FIND_PIP_PYTHON
if not defined PIP_MODE (
    echo Python est introuvable. Installe Python 64 bits avec Tcl/Tk.
    pause
    exit /b 1
)
call :RUN_PIP_PY "preparer_runtime_python_portable.py" %*
set "RC=%ERRORLEVEL%"
pause
exit /b %RC%

:VERSION
if exist "project_version.py" (
    findstr /B /C:"AGENTLOCAL_VERSION" /C:"AGENTLOCAL_BUILD" /C:"AGENTLOCAL_CHANNEL" "project_version.py"
) else (
    echo project_version.py introuvable.
)
echo.
pause
exit /b 0

:FIND_PYTHON
set "PY_MODE="
set "PY_EXE="
if exist "%~dp0runtime\python\python.exe" (
    set "PY_MODE=portable"
    set "PY_EXE=%~dp0runtime\python\python.exe"
    goto :eof
)
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_MODE=venv"
    set "PY_EXE=%~dp0.venv\Scripts\python.exe"
    goto :eof
)
if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_MODE=oldvenv"
    set "PY_EXE=%~dp0venv\Scripts\python.exe"
    goto :eof
)
where py.exe >nul 2>&1
if not errorlevel 1 (
    set "PY_MODE=launcher"
    goto :eof
)
where python.exe >nul 2>&1
if not errorlevel 1 (
    set "PY_MODE=system"
    set "PY_EXE=python.exe"
)
goto :eof

:FIND_PIP_PYTHON
set "PIP_MODE="
set "PIP_EXE="
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PIP_MODE=venv"
    set "PIP_EXE=%~dp0.venv\Scripts\python.exe"
    goto :eof
)
where py.exe >nul 2>&1
if not errorlevel 1 (
    set "PIP_MODE=launcher"
    goto :eof
)
where python.exe >nul 2>&1
if not errorlevel 1 (
    set "PIP_MODE=system"
    set "PIP_EXE=python.exe"
)
goto :eof

:RUN_PY
if /I "%PY_MODE%"=="launcher" (
    py -3 %*
) else (
    "%PY_EXE%" %*
)
exit /b %ERRORLEVEL%

:RUN_PIP_PY
if /I "%PIP_MODE%"=="launcher" (
    py -3 %*
) else (
    "%PIP_EXE%" %*
)
exit /b %ERRORLEVEL%

:START_GUI
if /I "%PY_MODE%"=="portable" (
    if exist "%~dp0runtime\python\pythonw.exe" (
        start "" "%~dp0runtime\python\pythonw.exe" "%~dp0app\gui.py"
    ) else (
        start "" "%~dp0runtime\python\python.exe" "%~dp0app\gui.py"
    )
    exit /b 0
)
if /I "%PY_MODE%"=="venv" (
    if exist "%~dp0.venv\Scripts\pythonw.exe" (
        start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0app\gui.py"
    ) else (
        start "" "%~dp0.venv\Scripts\python.exe" "%~dp0app\gui.py"
    )
    exit /b 0
)
if /I "%PY_MODE%"=="oldvenv" (
    if exist "%~dp0venv\Scripts\pythonw.exe" (
        start "" "%~dp0venv\Scripts\pythonw.exe" "%~dp0app\gui.py"
    ) else (
        start "" "%~dp0venv\Scripts\python.exe" "%~dp0app\gui.py"
    )
    exit /b 0
)
if /I "%PY_MODE%"=="launcher" (
    start "" pyw -3 "%~dp0app\gui.py"
    exit /b 0
)
where pythonw.exe >nul 2>&1
if not errorlevel 1 (
    start "" pythonw.exe "%~dp0app\gui.py"
) else (
    start "" python.exe "%~dp0app\gui.py"
)
exit /b 0

:CLEAN_OBSOLETE
if exist "agent_tail.txt" del /q "agent_tail.txt" >nul 2>&1
if exist "tests\test_natural_language_v2.py.tmp" del /q "tests\test_natural_language_v2.py.tmp" >nul 2>&1
call :ARCHIVE_LEGACY
call :ARCHIVE_LEGACY_DOCS
exit /b 0

:ARCHIVE_LEGACY
set "LEGACY_DIR=%~dp0runtime\legacy_launchers"
if not exist "%LEGACY_DIR%" mkdir "%LEGACY_DIR%" >nul 2>&1
for %%F in (
    "lancer_agentlocal_gui.bat"
    "tester_agentlocal.bat"
    "finaliser_patch_v11_8.bat"
    "finaliser_patch_v11_8_1.bat"
    "finaliser_patch_v11_8_2.bat"
    "preparer_agentlocal_nouveau_pc.bat"
    "preparer_dependances_offline.bat"
    "preparer_runtime_python_portable.bat"
) do (
    if exist "%~dp0%%~F" move /Y "%~dp0%%~F" "%LEGACY_DIR%\%%~F" >nul 2>&1
)
exit /b 0

:ARCHIVE_LEGACY_DOCS
set "LEGACY_DOCS=%~dp0runtime\legacy_docs"
set "LEGACY_VERIFIERS=%~dp0runtime\legacy_verifiers"
if not exist "%LEGACY_DOCS%" mkdir "%LEGACY_DOCS%" >nul 2>&1
if not exist "%LEGACY_VERIFIERS%" mkdir "%LEGACY_VERIFIERS%" >nul 2>&1
for %%F in (
    "README_AGENTLOCAL_V11_8_3.txt"
    "README_V11_8_2_PERFORMANCE_CENTER.txt"
    "README_V11_8_3_STABILISATION_TERRAIN.txt"
    "MANIFEST_COMPLET_V11_8_3.sha256.txt"
    "README_AGENTLOCAL_V12_1_R2.txt"
    "MANIFEST_COMPLET_V12_1_R2.sha256.txt"
) do (
    if exist "%~dp0%%~F" move /Y "%~dp0%%~F" "%LEGACY_DOCS%\%%~F" >nul 2>&1
)
for %%F in ("%~dp0verifier_conformite_pack_*.py") do (
    if exist "%%~fF" if /I not "%%~nxF"=="verifier_conformite_pack_v12.py" move /Y "%%~fF" "%LEGACY_VERIFIERS%\%%~nxF" >nul 2>&1
)
exit /b 0

:NO_PYTHON
echo AgentLocal ne trouve aucun runtime Python utilisable.
echo Lance : AgentLocal.bat setup
echo Ou construis le runtime portable avec : AgentLocal.bat runtime
pause
exit /b 1

:DIAGFAIL
echo.
echo Le diagnostic AgentLocal a detecte une erreur structurelle.
echo Lance : AgentLocal.bat diag
pause
exit /b 2

:HELP
echo AgentLocal.bat - unique point d'entree utilisateur
echo.
echo Double-clic : ouvre le menu principal.
echo.
echo Commandes directes :
echo   AgentLocal.bat start      Lance l'interface AgentLocal
echo   AgentLocal.bat diag       Lance le diagnostic technique
echo   AgentLocal.bat test       Lance tous les tests
echo   AgentLocal.bat verify     Nettoie et verifie l'installation
echo   AgentLocal.bat setup      Prepare AgentLocal sur un nouveau PC
echo   AgentLocal.bat offline    Prepare les dependances hors connexion
echo   AgentLocal.bat runtime    Construit le runtime Python portable
echo   AgentLocal.bat version    Affiche la version courante
echo   AgentLocal.bat menu       Affiche le menu
echo.
echo Les anciens .bat sont archives automatiquement dans :
echo   runtime\legacy_launchers\
echo.
pause
exit /b 0

:END
exit /b 0
