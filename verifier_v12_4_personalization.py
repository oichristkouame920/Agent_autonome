from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path: sys.path.insert(0, str(path))
from project_version import AGENTLOCAL_BUILD, AGENTLOCAL_VERSION
from user_profile import DEFAULT_PREFERENCES

assert AGENTLOCAL_VERSION == "12.5"
assert "v12.4-host-personalization" in AGENTLOCAL_BUILD
for rel in (
    "app/user_profile.py", "app/learning_profile.py", "app/onboarding.py",
    "config/defaults.json", "tests/test_v12_4_personalization.py",
):
    assert (ROOT / rel).is_file(), rel
src = (ROOT / "app/gui.py").read_text(encoding="utf-8")
for token in ("Habitudes", "Configuration", "Personnaliser", "_maybe_show_onboarding", "_open_behavior_editor", "_show_privacy_dialog"):
    assert token in src, token
onboarding = (ROOT / "app/onboarding.py").read_text(encoding="utf-8")
assert "Les deux — recommandé" in onboarding
assert "2 jours" in onboarding
assert DEFAULT_PREFERENCES["privacy"]["capture_keystrokes"] is False
assert DEFAULT_PREFERENCES["privacy"]["observe_private_content"] is False
assert DEFAULT_PREFERENCES["privacy"]["automatic_sensitive_actions"] is False
PERSONAL_FILES = ("user_profile.json", "user_preferences.json", "onboarding_state.json", "declared_habits.json")

# Sur un poste déjà configuré, ces fichiers DOIVENT pouvoir exister.
# La bonne garantie de distribution est qu'ils ne figurent jamais dans le manifeste du pack.
manifest_path = ROOT / "MANIFEST_COMPLET_V12_4.sha256.txt"
if manifest_path.is_file():
    manifest_text = manifest_path.read_text(encoding="utf-8", errors="replace")
    for personal in PERSONAL_FILES:
        assert f"memory/{personal}" not in manifest_text.replace("\\", "/"), f"Donnée hôte embarquée dans le manifeste : {personal}"

# Si les fichiers existent sur l'hôte, ils doivent au minimum rester des JSON valides.
import json
for personal in PERSONAL_FILES:
    live_path = ROOT / "memory" / personal
    if live_path.is_file():
        data = json.loads(live_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"Donnée hôte invalide : {personal}"

# Ils doivent également rester exclus de Git pour éviter une publication accidentelle.
gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8", errors="replace") if (ROOT / ".gitignore").is_file() else ""
normalized_gitignore = gitignore.replace("\\", "/")
for personal in PERSONAL_FILES:
    assert f"memory/{personal}" in normalized_gitignore, f"Exclusion Git manquante : {personal}"

print("V12.4 personnalisation hôte / onboarding / configuration / apprentissage 2 jours : OK")
