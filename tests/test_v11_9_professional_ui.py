from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import gui
from project_version import AGENTLOCAL_VERSION, AGENTLOCAL_BUILD


class ProfessionalUiV119Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(AGENTLOCAL_VERSION, "12.3")
        self.assertIn("connected-services", AGENTLOCAL_BUILD)

    def test_navigation_is_complete_and_small(self):
        self.assertEqual(
            [key for _, key in gui.AgentLocalGUI.NAV_ITEMS],
            ["home", "briefing", "assistant", "pc", "alerts", "files", "web", "routines", "settings"],
        )

    def test_dashboard_refresh_is_lightweight(self):
        self.assertGreaterEqual(gui.DASHBOARD_REFRESH_MS, 2000)

    def test_command_limit_is_preserved(self):
        self.assertEqual(gui.MAX_COMMAND_LENGTH, 2000)

    def test_user_text_is_not_rewritten(self):
        self.assertEqual(gui.normalize_user_command("  Ouvre Rapport Final.PDF  "), "Ouvre Rapport Final.PDF")

    @patch("gui.agent.get_agent_config")
    def test_runtime_summary_still_does_not_load_llm(self, config):
        config.return_value = {"backend": {"mode": "auto"}, "learning": {"enabled": True}}
        backend, learning = gui.get_runtime_summary()
        self.assertIn("chargé à la demande", backend)
        self.assertIn("activé", learning)

    def test_interface_has_no_heavy_ui_dependency(self):
        source = (ROOT / "app/gui.py").read_text(encoding="utf-8")
        for forbidden in ("PyQt", "PySide", "customtkinter", "electron"):
            self.assertNotIn(forbidden.lower(), source.lower())

    def test_quick_actions_still_route_through_agent(self):
        source = (ROOT / "app/gui.py").read_text(encoding="utf-8")
        self.assertIn("agent.process_instruction(command)", source)
        self.assertNotIn("subprocess.Popen", source)
        self.assertNotIn("os.system(", source)


if __name__ == "__main__":
    unittest.main()
