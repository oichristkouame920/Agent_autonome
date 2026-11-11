@echo off
setlocal
cd /d "%~dp0"

echo.
echo === AgentLocal V11.8.1 - Correctif performance ===
echo.
echo Ce patch ne modifie pas llama.cpp.
echo Verification de la coherence et des tests...

call "%~dp0tester_agentlocal.bat"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo.
    echo ECHEC : la verification AgentLocal a retourne le code %RC%.
    exit /b %RC%
)

echo.
echo AgentLocal V11.8.1 est conforme et pret.
exit /b 0
