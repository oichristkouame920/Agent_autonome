from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import windows_startup
from project_version import AGENTLOCAL_BUILD, AGENTLOCAL_VERSION


class WindowsAutostartV1222Tests(unittest.TestCase):
    def test_version_build_marker(self):
        self.assertEqual(AGENTLOCAL_VERSION, "12.3")
        self.assertIn("v12.2.2-windows-autostart", AGENTLOCAL_BUILD)

    def test_startup_is_current_user_and_non_admin(self):
        source = (ROOT / "app/windows_startup.py").read_text(encoding="utf-8")
        self.assertIn("HKEY_CURRENT_USER", source)
        self.assertIn(r"Software\Microsoft\Windows\CurrentVersion\Run", source)
        self.assertNotIn("HKEY_LOCAL_MACHINE", source)
        self.assertNotIn("runas", source.lower())

    def test_hidden_launcher_path_is_defined(self):
        launcher = (ROOT / "AgentLocal.bat").read_text(encoding="utf-8-sig")
        self.assertIn('"autostart" goto AUTOSTART', launcher)
        self.assertIn("START_GUI_BACKGROUND", launcher)
        self.assertIn("--background", launcher)
        vbs = windows_startup._vbs_text()
        self.assertIn("AgentLocal.bat", vbs)
        self.assertIn(" autostart", vbs)
        self.assertIn(", 0, False", vbs)

    def test_single_instance_guard_exists(self):
        source = (ROOT / "app/single_instance.py").read_text(encoding="utf-8")
        self.assertIn("CreateMutexW", source)
        self.assertIn("ERROR_ALREADY_EXISTS", source)
        self.assertIn("SetForegroundWindow", source)

    def test_gui_can_start_hidden_and_reveal_existing(self):
        source = (ROOT / "app/gui.py").read_text(encoding="utf-8")
        self.assertIn("start_hidden", source)
        self.assertIn("InstanceGuard", source)
        self.assertIn("focus_existing_window", source)
        self.assertIn("def reveal_main", source)
        self.assertIn("def _show_background_alert_popup", source)

    def test_automation_config_keeps_first_unlock_and_startup(self):
        cfg = json.loads((ROOT / "config/automation.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["morning_automation"]["trigger"], "first_unlock_seen")
        self.assertEqual(cfg["morning_automation"]["start_time"], "07:00")
        self.assertEqual(cfg["morning_automation"]["end_time"], "09:30")
        self.assertTrue(cfg["windows_startup"]["enabled_by_default"])
        self.assertTrue(cfg["windows_startup"]["single_instance"])
        self.assertTrue(cfg["windows_startup"]["notify_background_alerts"])

    def test_startup_preference_is_persistent(self):
        source = (ROOT / "app/windows_startup.py").read_text(encoding="utf-8")
        self.assertIn("windows_startup_preference.json", source)
        self.assertIn("apply_default_if_unset", source)


if __name__ == "__main__":
    unittest.main()
