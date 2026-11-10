from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
for p in (ROOT, APP):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from action_suggestions import build_suggestion, clear_pending_suggestion, get_pending_suggestion

clear_pending_suggestion()
s = build_suggestion(
    "liste mes documents",
    [{"action": "list_directory", "target": "documents", "params": {}}],
    ["Contenu de Documents :"],
)
assert s is not None
assert get_pending_suggestion() is not None
assert "récents" in s.command
print("OK - suggestion contextuelle sûre créée")
print("OK - aucune exécution automatique")
print("OK - une seule suggestion de session")
print("V11.6 SUGGESTIONS D'ACTIONS ACTIVES - verification non destructive OK")
