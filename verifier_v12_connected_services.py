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
from app.gui import AgentLocalGUI

assert AGENTLOCAL_VERSION == "12.5"
assert "connected-services" in AGENTLOCAL_BUILD
assert (ROOT / "app/connected_services.py").is_file()
assert (ROOT / "config/connected_services.json").is_file()

permissions = json.loads((ROOT / "config/permissions.json").read_text(encoding="utf-8"))
policy = permissions.get("connected_services_policy", {})
assert policy.get("enabled") is True
assert policy.get("read_only") is True
assert policy.get("https_only") is True
assert policy.get("allow_http_post") is False
assert policy.get("allow_authentication") is False
assert policy.get("allow_automatic_actions_from_content") is False
assert set(policy.get("allowed_hosts", [])) >= {
    "geocoding-api.open-meteo.com", "api.open-meteo.com", "news.google.com", "api.github.com"
}

cases = {
    "quelle est la météo d'aujourd'hui ?": "read_weather",
    "donne-moi les actualités du jour": "read_news",
    "briefing du jour": "read_daily_briefing",
    "verifi mes mises à jours": "check_online_updates",
}
for phrase, expected in cases.items():
    result = interpret(phrase)
    actions = result.get("actions", [])
    assert actions and actions[0].get("action") == expected, phrase

nav = [key for _, key in AgentLocalGUI.NAV_ITEMS]
assert "briefing" in nav
source = (ROOT / "app/gui.py").read_text(encoding="utf-8")
for token in ("def _build_briefing_page", "def _maybe_start_morning_briefing", "def _show_morning_popup"):
    assert token in source, token

print("V12 services connectes optionnels : OK")
