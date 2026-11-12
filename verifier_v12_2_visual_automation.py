from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.gui import AgentLocalGUI, MORNING_CHECK_MS
from project_version import AGENTLOCAL_BUILD, AGENTLOCAL_VERSION

assert AGENTLOCAL_VERSION == "12.5"
assert "visual-alerts" in AGENTLOCAL_BUILD
assert MORNING_CHECK_MS >= 5000
for rel in ("app/alerts.py", "app/system_monitor.py", "app/morning_automation.py", "config/automation.json"):
    assert (ROOT / rel).is_file(), rel

cfg = json.loads((ROOT / "config/automation.json").read_text(encoding="utf-8"))
morning = cfg.get("morning_automation", {})
health = cfg.get("health_monitor", {})
assert morning.get("enabled") is True
assert morning.get("start_time") == "07:00"
assert morning.get("end_time") == "09:30"
assert morning.get("trigger") == "first_unlock_seen"
assert health.get("ram_warning_percent") == 80
assert health.get("ram_critical_percent") == 92
assert health.get("disk_warning_free_gb") == 15
assert health.get("disk_critical_free_gb") == 5
permissions = json.loads((ROOT / "config/permissions.json").read_text(encoding="utf-8"))
policy = permissions.get("morning_automation_policy", {})
assert policy.get("enabled") is True
assert policy.get("trigger") == "first_unlock_seen"
assert policy.get("allow_destructive_actions") is False
assert policy.get("allow_process_termination") is False
assert policy.get("allow_file_deletion") is False
assert policy.get("allow_shell") is False

nav = [key for _, key in AgentLocalGUI.NAV_ITEMS]
assert nav[:8] == ["home", "briefing", "assistant", "pc", "alerts", "files", "web", "routines"]
assert nav[-1] == "settings"
source = (ROOT / "app/gui.py").read_text(encoding="utf-8")
for token in (
    "def _build_alerts_page",
    "def _health_monitor_loop",
    "def _morning_automation_loop",
    "def _show_morning_routine_popup",
    "raise_alert",
    "is_session_unlocked",
):
    assert token in source, token
for forbidden in ("subprocess.Popen", "os.system("):
    assert forbidden not in source

print("V12.2 interface clean + alertes + routine premier deverrouillage : OK")
