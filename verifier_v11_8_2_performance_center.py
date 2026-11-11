from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.action_suggestions import build_suggestions
from backends import backend_manager
from backends.deterministic_backend import interpret
from project_version import AGENTLOCAL_BUILD, AGENTLOCAL_VERSION

assert tuple(map(int, AGENTLOCAL_VERSION.split("."))) >= (11, 8, 2)
assert tuple(int(x) for x in AGENTLOCAL_VERSION.split(".")[:2]) >= (11, 8)

for text, target in {
    "affiche le tableau de performances du PC": "performance",
    "montre les processus les plus gourmands": "top",
    "montre les processus qui consomment le plus de CPU": "top_cpu",
    "montre les processus qui consomment le plus de RAM": "top_memory",
}.items():
    result = interpret(text)
    assert result.get("understood"), (text, result)
    action = result.get("actions", [])[0]
    if target == "performance":
        assert action.get("action") == "read_system_info" and action.get("target") == target
    else:
        assert action.get("action") == "read_process_info" and action.get("target") == target

suggestions = build_suggestions(
    "donne-moi l'état du PC",
    [{"schema_version": 1, "action": "read_system_info", "target": "summary", "params": None}],
    ["État du PC"],
)
assert [s.label for s in suggestions] == [
    "Voir les processus les plus gourmands",
    "Chercher les fichiers les plus lourds",
    "Ouvrir le tableau de performances",
]
for suggestion in suggestions:
    assert interpret(suggestion.command).get("understood"), suggestion.command

preflight = backend_manager._deterministic_preflight("montre les processus les plus gourmands")
assert preflight is not None and preflight.get("routing") == "deterministic_preflight"

permissions = json.loads((ROOT / "config/permissions.json").read_text(encoding="utf-8-sig"))
policy = permissions.get("process_information_policy", {})
assert policy.get("read_only") is True
assert policy.get("allow_process_termination") is False
assert policy.get("allow_from_routine") is False
assert policy.get("allow_from_habit") is False

print("V11.8.2 centre de performances : OK")
