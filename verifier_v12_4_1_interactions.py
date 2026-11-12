from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from backends.deterministic_backend import interpret
from app.response_style import choose_emoji


def action_of(text: str):
    result = interpret(text)
    actions = result.get("actions", [])
    return actions[0] if actions else None, result


window_cases = (
    "quelles sont les fenêtre actives ?",
    "quelles sont les fenêtres qui sont ouverte ?",
    "vérifi les fenêtres ouverte",
    "combien de fenêtre ssont ouverte ?",
)
for phrase in window_cases:
    action, result = action_of(phrase)
    assert result.get("understood") is True, phrase
    assert action and action.get("action") == "read_system_info", phrase
    assert action.get("target") == "windows", phrase
    print(f"OK - {phrase} -> fenetres visibles")

tab_cases = (
    "quels sont les onglets actifs ?",
    "combien d onglets sont ouverts ?",
    "verifi les onglets ouverts",
)
for phrase in tab_cases:
    action, result = action_of(phrase)
    assert result.get("understood") is True, phrase
    assert action and action.get("action") == "list_browser_tabs", phrase
    print(f"OK - {phrase} -> onglets Edge")

_, conversation = action_of("comment tu vas ?")
assert conversation.get("conversation") is True
assert "Ça va bien" in conversation.get("reply", "")
print("OK - comment tu vas ? -> conversation locale")

assert choose_emoji("Quelles sont les fenêtres ouvertes ?") == "🪟"
assert choose_emoji("Quel est le son actuel ?") == "🔊"
print("OK - mot 'sont' ne déclenche plus l'emoji audio")

print("V12.4.1 INTERACTIONS NATURELLES : OK")
