from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from backends.deterministic_backend import interpret
from project_version import AGENTLOCAL_VERSION, AGENTLOCAL_BUILD

assert AGENTLOCAL_VERSION == "12.1"
assert "scheduler" in AGENTLOCAL_BUILD
assert (ROOT / "app/scheduler.py").is_file()

permissions = json.loads((ROOT / "config/permissions.json").read_text(encoding="utf-8-sig"))
policy = permissions.get("scheduler_policy", {})
assert policy.get("enabled") is True
assert policy.get("require_explicit_confirmation") is True
assert policy.get("allow_arbitrary_commands") is False
assert policy.get("allow_destructive_actions") is False
assert policy.get("allow_shell_actions") is False
assert set(policy.get("allowed_kinds", [])) == {"routine", "briefing", "habit_summary"}

samples = {
    "programme mon briefing chaque matin à 7h": "create_schedule_draft",
    "lance ma routine chaque matin à 7h": "create_schedule_draft",
    "enregistre mes habitudes chaque matin à 7h": "create_schedule_draft",
    "liste mes planifications": "list_schedules",
    "confirme la planification 1": "confirm_schedule",
}
for text, expected in samples.items():
    result = interpret(text)
    actions = result.get("actions", [])
    assert actions and actions[0].get("action") == expected, (text, result)

print("V12.1 planification locale contrôlée : OK")
