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
Write-Host "=== 0. CONTROLE STRUCTUREL ==="
$requiredFiles = @(
    "project_version.py",
    "backends\deterministic_backend.py",
    "backends\llama_backend.py",
    "config\permissions.json",
    "config\connected_services.json",
    "config\automation.json",
    "app\connected_services.py",
    "app\scheduler.py",
    "app\alerts.py",
    "app\system_monitor.py",
    "app\morning_automation.py",
    "app\gui.py",
    "upgrade_llm_config_v12_2_1.py",
    "app\windows_startup.py",
    "app\single_instance.py",
    "app\daily_quotes.py",
    "app\response_style.py",
    "config\quotes.json",
    "app\user_profile.py",
    "app\learning_profile.py",
    "app\onboarding.py",
    "app\theme_manager.py",
    "app\notification_policy.py",
    "app\language_profile.py",
    "config\defaults.json",
    "verifier_v12_3_ux_premium.py",
    "verifier_v12_4_personalization.py",
    "verifier_v12_5_personalisation_notifications.py",
    "configure_windows_startup_v12_2_2.py",
    "upgrade_automation_config_v12_2_2.py"
)
foreach ($rel in $requiredFiles) {
    $target = Join-Path $PSScriptRoot $rel
    if (-not (Test-Path $target)) {
        throw "Fichier AgentLocal requis manquant : $rel"
    }
    Write-Host "OK :" $rel
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
$verifiers = Get-ChildItem $PSScriptRoot -Filter "verifier_*.py" -File |
    Where-Object { $_.Name -notmatch "^verifier_conformite_pack_" -or $_.Name -eq "verifier_conformite_pack_v12.py" } |
    Sort-Object Name
foreach ($file in $verifiers) {
    Write-Host ""
    Write-Host "TEST :" $file.Name

    # Les diagnostics runtime/résilience peuvent signaler un composant optionnel
    # absent (modèle, llama.cpp, cache offline) tout en laissant AgentLocal
    # parfaitement opérationnel en mode déterministe. Dans le test global,
    # ces avertissements ne doivent donc pas être traités comme des échecs.
    $verifierArgs = @()
    if ($file.Name -in @("verifier_runtime_v11_2.py", "verifier_resilience_v11_3.py")) {
        $verifierArgs += "--startup"
    }

    & $py $file.FullName @verifierArgs
    if ($LASTEXITCODE -ne 0) { throw "Echec du verificateur : $($file.Name)" }
}

Write-Host ""
Write-Host "=== 4. TESTS PYTHON COMPLETS (UNITTEST) ==="
& $py -m unittest discover -s tests -p "test_*.py" -v
if ($LASTEXITCODE -ne 0) { throw "Certains tests Python AgentLocal ont echoue." }

Write-Host ""
Write-Host "============================================="
Write-Host "TOUS LES TESTS AGENTLOCAL SONT PASSES"
Write-Host "============================================="
