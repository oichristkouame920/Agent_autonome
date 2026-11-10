$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    $portable = Join-Path $PSScriptRoot "runtime\python\python.exe"
    if (Test-Path $portable) {
        $py = $portable
    } else {
        throw "Python AgentLocal introuvable (.venv ou runtime portable)."
    }
}

Write-Host ""
Write-Host "=== 1. COMPILATION PYTHON ==="
$compileTargets = @("app", "backends", "agent_tools", "tests") | ForEach-Object { Join-Path $PSScriptRoot $_ } | Where-Object { Test-Path $_ }
& $py -m compileall -q -f @compileTargets
if ($LASTEXITCODE -ne 0) { throw "Compilation Python echouee." }
Write-Host "Python : OK"

Write-Host ""
Write-Host "=== 2. VALIDATION JSON AGENTLOCAL ==="
$jsonFiles = @()
$configDir = Join-Path $PSScriptRoot "config"
if (Test-Path $configDir) { $jsonFiles += Get-ChildItem $configDir -Filter *.json -File }
$manifest = Join-Path $PSScriptRoot "browser_extension\manifest.json"
if (Test-Path $manifest) { $jsonFiles += Get-Item $manifest }
foreach ($file in $jsonFiles) {
    & $py -m json.tool $file.FullName *> $null
    if ($LASTEXITCODE -ne 0) { throw "JSON invalide : $($file.FullName)" }
    Write-Host "OK :" $file.Name
}

Write-Host ""
Write-Host "=== 3. VERIFICATEURS AGENTLOCAL ==="
$verifiers = Get-ChildItem $PSScriptRoot -Filter "verifier_*.py" -File | Sort-Object Name
foreach ($file in $verifiers) {
    Write-Host ""
    Write-Host "TEST :" $file.Name
    & $py $file.FullName
    if ($LASTEXITCODE -ne 0) { throw "Echec du verificateur : $($file.Name)" }
}

Write-Host ""
Write-Host "=== 4. PYTEST COMPLET ==="
& $py -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Certains tests Pytest ont echoue." }

Write-Host ""
Write-Host "============================================="
Write-Host "TOUS LES TESTS AGENTLOCAL SONT PASSES"
Write-Host "============================================="
