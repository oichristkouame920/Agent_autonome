from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from project_version import AGENTLOCAL_BUILD, AGENTLOCAL_VERSION
import scheduler
import connected_services as cs

assert AGENTLOCAL_VERSION == "12.3"
assert "deep-hardening" in AGENTLOCAL_BUILD
assert scheduler.MAX_SCHEDULES <= 64
assert scheduler.ALLOWED_KINDS == {"routine", "briefing", "habit_summary"}
assert callable(scheduler.claim_schedule)
assert callable(scheduler._sanitize_schedule)
assert callable(cs._cache_ttl)
assert callable(cs._finite_float)

# Contrôles statiques ciblés sur les garde-fous R2.
scheduler_source = (ROOT / "app/scheduler.py").read_text(encoding="utf-8")
connected_source = (ROOT / "app/connected_services.py").read_text(encoding="utf-8")
gui_source = (ROOT / "app/gui.py").read_text(encoding="utf-8")

for token in (
    "schedules.corrupt-",
    "os.O_CREAT | os.O_EXCL",
    "MAX_SCHEDULES",
    "_sanitize_schedule",
):
    assert token in scheduler_source, token

for token in (
    "Identifiants dans URL interdits",
    "Reponse Internet trop volumineuse",
    "<!DOCTYPE",
    "AGENTLOCAL_VERSION",
):
    assert token in connected_source, token

assert "claim_scheduled_execution" in gui_source
print("V12.1 R2 durcissement erreurs / planifications / Internet : OK")
