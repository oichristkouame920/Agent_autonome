from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from project_version import AGENTLOCAL_VERSION, AGENTLOCAL_BUILD
from app import gui

assert AGENTLOCAL_VERSION == "12.5"
assert "connected-services" in AGENTLOCAL_BUILD
assert gui.MAX_COMMAND_LENGTH == 2000
assert gui.DASHBOARD_REFRESH_MS >= 2000
assert gui.COLORS.get("sidebar") and gui.COLORS.get("accent")

nav_keys = [key for _, key in gui.AgentLocalGUI.NAV_ITEMS]
assert nav_keys[:8] == ["home", "briefing", "assistant", "pc", "alerts", "files", "web", "routines"]
assert nav_keys[-1] == "settings"

source = (ROOT / "app/gui.py").read_text(encoding="utf-8")
for token in (
    "def _build_home_page",
    "def _build_briefing_page",
    "def _build_assistant_page",
    "def _build_pc_page",
    "def _build_files_page",
    "def _build_web_page",
    "def _build_routines_page",
    "def _build_settings_page",
    "def _update_dashboard_metrics",
    "def run_shortcut",
    "response_time_var",
    "get_pending_action_suggestions",
):
    assert token in source, token

# Aucun framework graphique lourd ajoute.
for forbidden in ("PyQt", "PySide", "customtkinter", "electron"):
    assert forbidden.lower() not in source.lower(), forbidden

print("V11.9 interface professionnelle preservee dans V12 : OK")
