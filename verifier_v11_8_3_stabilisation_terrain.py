from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from backends.deterministic_backend import interpret
from project_version import AGENTLOCAL_VERSION, AGENTLOCAL_BUILD

parts = tuple(int(x) for x in AGENTLOCAL_VERSION.split(".")[:2])
assert parts >= (11, 8)
assert AGENTLOCAL_BUILD

samples = {
    "quel est l'etat de ma connexion ?": ("read_network_info", "status"),
    "quelle est ta performance ?": ("read_system_info", "agent"),
    "quelle sont les fenetre active sur ce PC": ("read_system_info", "windows"),
}
for text, expected in samples.items():
    result = interpret(text)
    actions = result.get("actions", [])
    assert actions, text
    assert (actions[0].get("action"), actions[0].get("target")) == expected, (text, actions)

connected = {
    "quelle est la météo d'aujourd'hui ?": ("read_weather", "today"),
    "verifi mes mises à jours": ("check_online_updates", "agentlocal"),
}
for text, expected in connected.items():
    result = interpret(text)
    actions = result.get("actions", [])
    assert actions and (actions[0].get("action"), actions[0].get("target")) == expected, (text, result)

text = "Enregistre mes habitudes chaque matin à 7H"
result = interpret(text)
assert result.get("understood") is True, text
actions = result.get("actions", [])
assert actions and actions[0].get("action") == "create_schedule_draft", (text, result)
assert actions[0].get("target") == "habit_summary", (text, result)

print("V11.8.3 stabilisation terrain : OK")
