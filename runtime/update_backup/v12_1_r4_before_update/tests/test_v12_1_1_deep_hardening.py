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

import connected_services as cs
import scheduler


class SchedulerDeepHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.config_file = root / "memory" / "schedules.json"
        self.claim_dir = root / "runtime" / "schedule_claims"
        self.patch_config = mock.patch.object(scheduler, "CONFIG_FILE", self.config_file)
        self.patch_claim = mock.patch.object(scheduler, "CLAIM_DIR", self.claim_dir)
        self.patch_config.start()
        self.patch_claim.start()

    def tearDown(self):
        self.patch_claim.stop()
        self.patch_config.stop()
        self.tmp.cleanup()

    def test_corrupt_file_is_backed_up_and_recovered(self):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text("{not-json", encoding="utf-8")
        data = scheduler.load_config()
        self.assertEqual(data["schedules"], {})
        self.assertTrue(list(self.config_file.parent.glob("schedules.corrupt-*.json")))
        reparsed = json.loads(self.config_file.read_text(encoding="utf-8"))
        self.assertEqual(reparsed["schema_version"], 1)

    def test_manual_enable_without_confirmation_is_neutralized(self):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps({
            "schema_version": 1,
            "enabled": True,
            "poll_seconds": 1,
            "catch_up_minutes": 99999,
            "schedules": {
                "p-1234abcd": {
                    "id": "p-1234abcd", "name": "X", "kind": "briefing", "target": "today",
                    "trigger": {"type": "weekly", "time": "07:00", "days": list(range(7))},
                    "confirmed": False, "enabled": True,
                }
            },
        }), encoding="utf-8")
        data = scheduler.load_config()
        self.assertFalse(data["schedules"]["p-1234abcd"]["enabled"])
        self.assertEqual(data["poll_seconds"], 10)
        self.assertEqual(data["catch_up_minutes"], 1440)

    def test_unauthorized_manual_kind_is_removed(self):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps({
            "schema_version": 1, "enabled": True, "schedules": {
                "p-1234abcd": {
                    "id": "p-1234abcd", "name": "Shell", "kind": "shell", "target": "cmd",
                    "trigger": {"type": "weekly", "time": "07:00", "days": [0]},
                    "confirmed": True, "enabled": True,
                }
            }
        }), encoding="utf-8")
        self.assertEqual(scheduler.load_config()["schedules"], {})

    def test_exact_duplicate_draft_is_not_created_twice(self):
        trigger = scheduler.build_trigger(7, 0)
        first = scheduler.create_draft("briefing", "today", trigger)
        second = scheduler.create_draft("briefing", "today", trigger)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(scheduler.list_schedules()), 1)

    def test_claim_prevents_double_execution_same_day(self):
        item = scheduler.create_draft("briefing", "today", scheduler.build_trigger(7, 0))
        scheduler.confirm_schedule(item["id"])
        now = datetime(2026, 11, 10, 7, 10).astimezone()
        self.assertEqual(len(scheduler.get_due_schedules(now)), 1)
        self.assertTrue(scheduler.claim_schedule(item["id"], now))
        self.assertFalse(scheduler.claim_schedule(item["id"], now))
        self.assertEqual(scheduler.get_due_schedules(now), [])

    def test_claim_is_day_scoped(self):
        item = scheduler.create_draft("briefing", "today", scheduler.build_trigger(7, 0))
        day1 = datetime(2026, 11, 10, 7, 10).astimezone()
        day2 = datetime(2026, 11, 11, 7, 10).astimezone()
        self.assertTrue(scheduler.claim_schedule(item["id"], day1))
        self.assertTrue(scheduler.claim_schedule(item["id"], day2))

    def test_invalid_persisted_trigger_is_removed(self):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps({
            "schema_version": 1, "schedules": {
                "p-1234abcd": {
                    "id": "p-1234abcd", "kind": "briefing", "target": "today",
                    "trigger": {"type": "weekly", "time": "99:99", "days": [0]},
                    "confirmed": True, "enabled": True,
                }
            }
        }), encoding="utf-8")
        self.assertEqual(scheduler.load_config()["schedules"], {})


class ConnectedServicesDeepHardeningTests(unittest.TestCase):
    def setUp(self):
        cs._CACHE.clear()

    def test_fetch_rejects_credentials_before_network(self):
        with self.assertRaises(RuntimeError):
            cs._fetch("https://user:pass@api.open-meteo.com/v1/forecast")

    def test_fetch_rejects_non_https_port_before_network(self):
        with self.assertRaises(RuntimeError):
            cs._fetch("https://api.open-meteo.com:444/v1/forecast")

    def test_cache_returns_copy_not_mutable_internal_object(self):
        original = {"items": [1]}
        cs._cache_put("x", original)
        first = cs._cache_get("x", 900)
        first["items"].append(2)
        second = cs._cache_get("x", 900)
        self.assertEqual(second, {"items": [1]})

    def test_format_weather_tolerates_partial_data(self):
        text = cs.format_weather({"city": "Abidjan", "condition": "--"})
        self.assertIn("Abidjan", text)
        self.assertIn("--", text)

    def test_news_rejects_doctype_payload(self):
        payload = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e "bad">]><rss><channel/></rss>'
        with mock.patch.object(cs, "_fetch", return_value=payload):
            ok, message = cs.get_news(force=True)
        self.assertFalse(ok)
        self.assertIn("indisponibles", str(message).lower())

    def test_update_rejects_invalid_remote_sha(self):
        with mock.patch.object(cs, "_fetch", return_value=json.dumps({"sha": "not-a-sha"}).encode("utf-8")):
            ok, message = cs.check_agentlocal_update(force=True)
        self.assertFalse(ok)
        self.assertIn("invalide", str(message).lower())

    def test_morning_briefing_bad_hours_fall_back_safely(self):
        now = datetime(2026, 11, 10, 7, 0)
        with mock.patch.object(cs, "_service_config", return_value={
            "enabled": True, "start_hour": "oops", "end_hour": -4, "show_once_per_day": False,
        }):
            self.assertTrue(cs.should_show_morning_briefing(now))


if __name__ == "__main__":
    unittest.main()
