from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from backends.deterministic_backend import interpret
from project_version import AGENTLOCAL_BUILD, AGENTLOCAL_VERSION
import scheduler


class SchedulerV121Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config_file = Path(self.tmp.name) / "schedules.json"
        self.patch = mock.patch.object(scheduler, "CONFIG_FILE", self.config_file)
        self.patch.start()
        scheduler.save_config({
            "schema_version": 1,
            "enabled": True,
            "poll_seconds": 20,
            "catch_up_minutes": 60,
            "schedules": {},
        })

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_version(self):
        self.assertEqual(AGENTLOCAL_VERSION, "12.3")
        self.assertIn("scheduler", AGENTLOCAL_BUILD)

    def test_parser_creates_disabled_draft_contract(self):
        result = interpret("programme mon briefing chaque matin à 7h")
        action = result["actions"][0]
        self.assertEqual(action["action"], "create_schedule_draft")
        self.assertEqual(action["target"], "briefing")
        self.assertEqual(action["params"]["trigger"]["time"], "07:00")
        self.assertEqual(action["params"]["trigger"]["days"], list(range(7)))

    def test_weekday_parser(self):
        result = interpret("programme ma routine tous les lundis à 8h30")
        action = result["actions"][0]
        self.assertEqual(action["target"], "routine")
        self.assertEqual(action["params"]["trigger"]["days"], [0])
        self.assertEqual(action["params"]["trigger"]["time"], "08:30")

    def test_habit_summary_parser(self):
        result = interpret("enregistre mes habitudes chaque matin à 7H")
        action = result["actions"][0]
        self.assertEqual(action["target"], "habit_summary")

    def test_draft_never_runs_before_confirmation(self):
        item = scheduler.create_draft(
            "briefing", "today", scheduler.build_trigger(7, 0),
        )
        now = datetime(2026, 11, 10, 7, 10).astimezone()
        self.assertEqual(scheduler.get_due_schedules(now), [])
        ok, _ = scheduler.confirm_schedule(item["id"])
        self.assertTrue(ok)
        due = scheduler.get_due_schedules(now)
        self.assertEqual([x["id"] for x in due], [item["id"]])

    def test_run_mark_prevents_duplicate_same_day(self):
        item = scheduler.create_draft(
            "habit_summary", "today", scheduler.build_trigger(7, 0),
        )
        scheduler.confirm_schedule(item["id"])
        now = datetime(2026, 11, 10, 7, 10).astimezone()
        self.assertEqual(len(scheduler.get_due_schedules(now)), 1)
        scheduler.mark_run(item["id"], True, "OK", now=now)
        self.assertEqual(scheduler.get_due_schedules(now), [])

    def test_reference_by_list_number(self):
        first = scheduler.create_draft("briefing", "today", scheduler.build_trigger(7, 0))
        resolved = scheduler.resolve_schedule_ref("1")
        self.assertEqual(resolved, first["id"])


    def test_schedule_suggestions_offer_confirmation(self):
        from action_suggestions import build_suggestions
        action = interpret("programme mon briefing chaque matin à 7h")["actions"][0]
        suggestions = build_suggestions(
            "programme mon briefing chaque matin à 7h",
            [action],
            ["Brouillon p-1234abcd créé"],
        )
        commands = [item.command for item in suggestions]
        self.assertIn("confirme la planification p-1234abcd", commands)

    def test_only_safe_kinds_are_allowed(self):
        with self.assertRaises(ValueError):
            scheduler.create_draft("shell", "cmd", scheduler.build_trigger(7, 0))


if __name__ == "__main__":
    unittest.main()
