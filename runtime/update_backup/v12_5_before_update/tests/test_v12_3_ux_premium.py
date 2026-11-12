from __future__ import annotations

import datetime as dt
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import daily_quotes
import gui
import response_style
from project_version import AGENTLOCAL_BUILD, AGENTLOCAL_VERSION


class UxPremiumV123Tests(unittest.TestCase):
    def test_version_and_build(self):
        self.assertEqual(AGENTLOCAL_VERSION, "12.4")
        self.assertIn("v12.3-ux-premium", AGENTLOCAL_BUILD)

    def test_quote_is_stable_for_day(self):
        day = dt.date(2026, 11, 11)
        a = daily_quotes.quote_of_day(day)
        b = daily_quotes.quote_of_day(day)
        self.assertEqual(a, b)
        self.assertTrue(a["text"])
        self.assertEqual(a["author"], "AgentLocal")

    def test_quotes_are_local_and_numerous(self):
        cfg = json.loads((ROOT / "config/quotes.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(cfg["quotes"]), 28)
        source = (ROOT / "app/daily_quotes.py").read_text(encoding="utf-8")
        self.assertNotIn("urllib", source)
        self.assertNotIn("requests", source)

    def test_response_style_is_presentation_only(self):
        value = response_style.decorate_response("CPU : 12 %")
        self.assertIn("CPU : 12 %", value)
        self.assertTrue(value.startswith("🖥️"))
        self.assertEqual(response_style.decorate_response("✅ C'est fait"), "✅ C'est fait")

    def test_gui_uses_cards_icons_quote_and_decorated_responses(self):
        source = (ROOT / "app/gui.py").read_text(encoding="utf-8")
        for token in ("CARD_META", "NAV_ICONS", "quote_of_day", "Citation du jour", "decorate_response", "soft_lavender", "quote_bg"):
            self.assertIn(token, source)
        self.assertNotIn("customtkinter", source.lower())
        self.assertNotIn("subprocess.Popen", source)

    def test_navigation_contract_is_preserved(self):
        keys = [k for _, k in gui.AgentLocalGUI.NAV_ITEMS]
        self.assertEqual(keys[:8], ["home", "briefing", "assistant", "pc", "alerts", "files", "web", "routines"])
        self.assertEqual(keys[-1], "settings")

    def test_launcher_verify_and_background_labels_are_not_corrupted(self):
        source = (ROOT / "AgentLocal.bat").read_text(encoding="utf-8-sig")
        labels = [line.strip().casefold() for line in source.splitlines() if line.strip().startswith(":")]
        self.assertEqual(len(labels), len(set(labels)))
        verify = source[source.index(":VERIFY"):source.index(":SETUP")]
        self.assertIn("call :CLEAN_OBSOLETE", verify)
        self.assertIn("tester_agentlocal.ps1", verify)
        self.assertIn(":START_GUI_BACKGROUND", source)


if __name__ == "__main__":
    unittest.main()
