@echo off
setlocal
cd /d "%~dp0"

echo.
echo === AgentLocal V11.8 - Finalisation du patch ===

if exist "agent_tail.txt" (
    del /q "agent_tail.txt"
    echo Nettoye : agent_tail.txt
)

if exist "tests\test_natural_language_v2.py.tmp" (
    del /q "tests\test_natural_language_v2.py.tmp"
    echo Nettoye : tests\test_natural_language_v2.py.tmp
)

echo.
echo Lancement de la verification complete...
call "%~dp0tester_agentlocal.bat"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo.
    echo ECHEC : la verification AgentLocal a retourne le code %RC%.
    exit /b %RC%
)

echo.
echo AgentLocal V11.8 est conforme et pret.
exit /b 0
