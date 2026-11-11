from pathlib import Path

ROOT = Path(__file__).resolve().parent
launcher = ROOT / "AgentLocal.bat"
assert launcher.is_file(), "AgentLocal.bat manquant"
text = launcher.read_text(encoding="utf-8", errors="replace").casefold()

required = [
    ":launch",
    ":diag",
    ":test",
    ":verify",
    ":setup",
    ":offline",
    ":runtime",
    ":version",
    "tester_agentlocal.ps1",
    "verifier_resilience_v11_3.py",
    "preparer_runtime_python_portable.py",
    "runtime\\legacy_launchers",
]
for token in required:
    assert token in text, f"Fonction du lanceur unique absente : {token}"

# Le lanceur unique ne doit pas deleguer son fonctionnement aux anciens .bat.
for old in [
    "call \"%~dp0lancer_agentlocal_gui.bat\"",
    "call \"%~dp0tester_agentlocal.bat\"",
    "call \"%~dp0preparer_agentlocal_nouveau_pc.bat\"",
    "call \"%~dp0preparer_dependances_offline.bat\"",
    "call \"%~dp0preparer_runtime_python_portable.bat\"",
]:
    assert old not in text, f"Delegation legacy encore active : {old}"

assert "runtime\\python\\python.exe" in text
assert ".venv\\scripts\\python.exe" in text
assert "powershell.exe -noprofile -executionpolicy bypass" in text


# Fichiers structurels indispensables au lanceur et au backend.
for rel in [
    "project_version.py",
    "tester_agentlocal.ps1",
    "backends/deterministic_backend.py",
]:
    assert (ROOT / rel).is_file(), f"Fichier structurel AgentLocal manquant : {rel}"

print("Lanceur unique AgentLocal : OK")


# La suite globale doit rester autonome et hors connexion : unittest est inclus dans Python.
tester = (ROOT / "tester_agentlocal.ps1").read_text(encoding="utf-8-sig", errors="replace").casefold()
assert "-m unittest discover" in tester, "Le lanceur de tests doit utiliser unittest standard."
assert "-m pytest" not in tester, "Pytest ne doit plus etre une dependance obligatoire du lanceur global."

# Les anciens verificateurs de conformite, quelle que soit leur version, ne doivent jamais bloquer la version courante.
launcher_raw = launcher.read_text(encoding="utf-8-sig", errors="replace").casefold()
assert "verifier_conformite_pack_*.py" in launcher_raw, "Archivage generique des anciens verificateurs absent."
assert "verifier_conformite_pack_v12.py" in launcher_raw, "Le lanceur doit conserver le verificateur V12 courant."
assert "^verifier_conformite_pack_" in tester, "Le runner global doit ignorer les anciens verificateurs de conformite residuels."
assert "verifier_conformite_pack_v12.py" in tester, "Le runner doit conserver explicitement le verificateur V12 courant."
