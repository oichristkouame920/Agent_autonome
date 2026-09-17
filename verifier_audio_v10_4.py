from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

import agent
from backends.deterministic_backend import interpret

checks = [
    ("quel est le volume", "read_audio_state", "master", None),
    ("mets le volume à 30%", "set_audio_volume", "master", {"percent": 30}),
    ("monte le son", "change_audio_volume", "master", {"delta": 5}),
    ("baisse le volume de 10%", "change_audio_volume", "master", {"delta": -10}),
    ("coupe le son", "set_audio_mute", "master", {"muted": True}),
    ("remets le son", "set_audio_mute", "master", {"muted": False}),
]

for text, expected_action, target, params in checks:
    result = interpret(text)
    actions = result.get("actions", [])
    assert len(actions) == 1, (text, result)
    action = actions[0]
    assert action.get("action") == expected_action, (text, result)
    assert action.get("target") == target, (text, result)
    if params is not None:
        assert action.get("params") == params, (text, result)
    assert agent.validate_action(action) == (True, None), (text, action, agent.validate_action(action))
    print(f"OK - {text}")

for text in ("monte pas le son", "coupe pas le son", "faut pas couper le son"):
    result = interpret(text)
    assert result.get("understood") is True and result.get("actions") == [], (text, result)
    print(f"OK - négation : {text}")

permissions = json.loads((ROOT / "config" / "permissions.json").read_text(encoding="utf-8"))
policy = permissions["audio_control_policy"]
assert policy["enabled"] is True
assert policy["require_explicit_user_command"] is True
assert policy["allow_from_routine"] is False
assert policy["allow_from_habit"] is False
assert policy["allow_automatic_change"] is False
assert policy["maximum_relative_change_percent"] == 25
print("OK - politique audio manuelle et bornée")

print("\nAUDIO V10.4 ACTIF - vérification non destructive OK")
print("Cette vérification ne modifie pas le volume du PC.")
