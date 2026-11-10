from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from action_suggestions import build_suggestions, clear_pending_suggestion, resolve_suggestion_message
from backends.deterministic_backend import FIELD_LANGUAGE_PATCH_VERSION, interpret
from project_version import AGENTLOCAL_BUILD, AGENTLOCAL_VERSION


def action(text):
    result = interpret(text)
    assert result.get("understood"), (text, result)
    actions = result.get("actions", [])
    assert actions, (text, result)
    return actions[0]


assert AGENTLOCAL_VERSION == "11.8"
assert FIELD_LANGUAGE_PATCH_VERSION == AGENTLOCAL_BUILD
assert action("ouvrre bloc note")["target"] == "notepad"
assert action("donne moi letat du pc")["target"] == "summary"
assert action("passe sur whatsapp")["action"] == "activate_browser_tab"
assert action("lance fire fox")["target"] == "firefox"
assert action("liste mes captures d'écran")["target"] == "pictures"

clear_pending_suggestion()
items = build_suggestions(
    "liste mes documents",
    [{"action": "list_directory", "target": "documents", "params": {}}],
    ["Contenu de Documents :"],
)
assert len(items) == 3
assert resolve_suggestion_message("oui") == items[0].command
assert resolve_suggestion_message("2") == items[1].command

for item in items:
    result = interpret(item.command)
    assert result.get("understood"), (item.command, result)

print("V11.8 contexte + suggestions actionnables : OK")
