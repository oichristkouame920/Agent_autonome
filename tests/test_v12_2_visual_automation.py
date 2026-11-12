from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import alerts
import gui
import morning_automation
import system_monitor
from project_version import AGENTLOCAL_BUILD, AGENTLOCAL_VERSION


class VisualAutomationV122Tests(unittest.TestCase):
    def test_version_and_navigation(self):
        self.assertEqual(AGENTLOCAL_VERSION, "12.5")
        self.assertIn("visual-alerts", AGENTLOCAL_BUILD)
        self.assertIn("alerts", [key for _, key in gui.AgentLocalGUI.NAV_ITEMS])

    def test_automation_config_window(self):
        cfg = json.loads((ROOT / "config/automation.json").read_text(encoding="utf-8"))
        morning = cfg["morning_automation"]
        self.assertEqual(morning["start_time"], "07:00")
        self.assertEqual(morning["end_time"], "09:30")
        self.assertEqual(morning["trigger"], "first_unlock_seen")

    def test_morning_security_policy_is_non_destructive(self):
        permissions = json.loads((ROOT / "config/permissions.json").read_text(encoding="utf-8"))
        policy = permissions["morning_automation_policy"]
        self.assertTrue(policy["enabled"])
        self.assertEqual(policy["trigger"], "first_unlock_seen")
        self.assertFalse(policy["allow_destructive_actions"])
        self.assertFalse(policy["allow_process_termination"])
        self.assertFalse(policy["allow_file_deletion"])
        self.assertFalse(policy["allow_shell"])

    def test_morning_triggers_on_first_observed_unlock_inside_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            cfg = Path(tmp) / "automation.json"
            cfg.write_text(json.dumps({"morning_automation": {"enabled": True, "start_time": "07:00", "end_time": "09:30", "once_per_day": True}}), encoding="utf-8")
            with patch.object(morning_automation, "STATE_FILE", state), patch.object(morning_automation, "CONFIG_FILE", cfg):
                at_745 = datetime(2026, 11, 11, 7, 45)
                self.assertFalse(morning_automation.should_trigger(at_745, unlocked=False))
                self.assertTrue(morning_automation.should_trigger(at_745, unlocked=True))
                morning_automation.mark_completed(True, at_745, "ok")
                self.assertFalse(morning_automation.should_trigger(datetime(2026, 11, 11, 8, 0), unlocked=True))

    def test_late_window_is_not_automatically_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            cfg = Path(tmp) / "automation.json"
            cfg.write_text(json.dumps({"morning_automation": {"enabled": True, "start_time": "07:00", "end_time": "09:30", "late_prompt_after_window": True}}), encoding="utf-8")
            with patch.object(morning_automation, "STATE_FILE", state), patch.object(morning_automation, "CONFIG_FILE", cfg):
                at_1100 = datetime(2026, 11, 11, 11, 0)
                self.assertFalse(morning_automation.should_trigger(at_1100, unlocked=True))
                self.assertTrue(morning_automation.should_prompt_late(at_1100, unlocked=True))

    def test_alert_store_deduplicates_and_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "alerts.json"
            with patch.object(alerts, "ALERTS_FILE", target):
                first = alerts.raise_alert("health.ram", "warning", "RAM", "82 %")
                second = alerts.raise_alert("health.ram", "critical", "RAM", "94 %")
                self.assertEqual(first["id"], second["id"])
                self.assertEqual(alerts.get_alert_summary()["active"], 1)
                self.assertEqual(alerts.get_alert_summary()["critical"], 1)
                alerts.resolve_missing(("health.",), set())
                self.assertEqual(alerts.get_alert_summary()["active"], 0)

    def test_health_monitor_generates_ram_and_disk_alerts(self):
        monitor = system_monitor.SystemHealthMonitor()
        snap = {
            "timestamp": 1000.0,
            "cpu_percent": 10,
            "ram_percent": 95,
            "disk_free_bytes": 2 * 1024**3,
            "network_interface_up": True,
            "hung_windows": [],
            "suspended_processes": [],
        }
        generated = monitor.evaluate(snap)
        by_code = {x["code"]: x for x in generated}
        self.assertEqual(by_code["health.ram"]["level"], "critical")
        self.assertEqual(by_code["health.disk"]["level"], "critical")

    def test_gui_contains_visual_alert_and_morning_components(self):
        source = (ROOT / "app/gui.py").read_text(encoding="utf-8")
        for token in (
            "def _build_alerts_page",
            "def _health_monitor_loop",
            "def _morning_automation_loop",
            "def _show_morning_routine_popup",
            "Voir les alertes",
        ):
            self.assertIn(token, source)
        self.assertNotIn("subprocess.Popen", source)
        self.assertNotIn("os.system(", source)


if __name__ == "__main__":
    unittest.main()
