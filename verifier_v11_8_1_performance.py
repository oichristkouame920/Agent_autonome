from pathlib import Path
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

assert tuple(int(x) for x in AGENTLOCAL_VERSION.split(".")[:2]) >= (11, 8)
assert tuple(map(int, AGENTLOCAL_VERSION.split("."))) >= (11, 8, 1)

for text in ("quelle l'etat de mon PC", "quel est l'etat de mon PC"):
    result = interpret(text)
    assert result.get("understood"), (text, result)
    assert result.get("actions", [])[0].get("action") == "read_system_info"

sleep_result = interpret("met mon PC en veille")
assert sleep_result.get("understood") and not sleep_result.get("actions")

items = build_suggestions(
    "liste les fichiers word",
    [{"action": "advanced_file_search", "target": "auto", "params": {
        "file_kind": "word", "date_filter": "any", "date_field": "modified",
        "size_operator": "any", "size_bytes": 0, "sort": "modified_desc",
        "limit": 10, "count_only": False,
    }}],
    ["83 fichiers Word"],
)
commands = [item.command.lower() for item in items]
assert any("word" in command and "plus gros" in command for command in commands)
assert any("word" in command and "cette semaine" in command for command in commands)

# Preuve structurelle : le preflight déterministe est placé avant select_backend.
source = (ROOT / "backends/backend_manager.py").read_text(encoding="utf-8")
preflight_pos = source.index("preflight = _deterministic_preflight(user_message)", source.index("def interpret("))
select_pos = source.index("select_backend()", source.index("def interpret("))
assert preflight_pos < select_pos

print("V11.8.1 performance fast-path : OK")
