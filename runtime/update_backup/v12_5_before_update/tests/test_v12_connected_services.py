from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from backends.deterministic_backend import interpret
from project_version import AGENTLOCAL_VERSION, AGENTLOCAL_BUILD
import connected_services as cs


class ConnectedServicesV12Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(AGENTLOCAL_VERSION, "12.4")
        self.assertIn("connected-services", AGENTLOCAL_BUILD)

    def test_weather_news_briefing_and_updates_are_deterministic(self):
        cases = {
            "quelle est la météo d'aujourd'hui ?": ("read_weather", "today"),
            "donne-moi les actualités du jour": ("read_news", "today"),
            "briefing du jour": ("read_daily_briefing", "today"),
            "verifi mes mises à jours": ("check_online_updates", "agentlocal"),
        }
        for text, expected in cases.items():
            result = interpret(text)
            self.assertTrue(result.get("understood"), text)
            action = result.get("actions", [])[0]
            self.assertEqual((action.get("action"), action.get("target")), expected)

    def test_weather_never_becomes_file_search(self):
        action = interpret("quelle est la météo d'aujourd'hui ?")["actions"][0]
        self.assertNotIn("file", action["action"])

    def test_fetch_rejects_unlisted_domain_before_network(self):
        with self.assertRaises(RuntimeError):
            cs._fetch("https://example.com/test")

    def test_weather_parser_with_mocked_https_payloads(self):
        geo = json.dumps({"results": [{"name": "Abidjan", "country": "Côte d'Ivoire", "latitude": 5.32, "longitude": -4.03}]}).encode()
        weather = json.dumps({
            "current": {
                "temperature_2m": 29.1,
                "apparent_temperature": 33.0,
                "relative_humidity_2m": 76,
                "precipitation": 0.0,
                "weather_code": 2,
                "wind_speed_10m": 11.0,
            },
            "daily": {
                "temperature_2m_max": [31.0],
                "temperature_2m_min": [24.0],
                "precipitation_probability_max": [40],
            },
        }).encode()
        with patch.object(cs, "_fetch", side_effect=[geo, weather]):
            ok, data = cs.get_weather(force=True)
        self.assertTrue(ok)
        self.assertEqual(data["city"], "Abidjan")
        self.assertEqual(data["temperature_c"], 29.1)
        self.assertIn("Partiellement", data["condition"])

    def test_news_parser_with_mocked_rss(self):
        rss = b'''<?xml version="1.0"?><rss><channel>
        <item><title>Titre 1 - Source A</title><link>https://news.google.com/x</link><pubDate>Tue, 10 Nov 2026 12:00:00 GMT</pubDate><source>Source A</source></item>
        <item><title>Titre 2 - Source B</title><link>https://news.google.com/y</link><pubDate>Tue, 10 Nov 2026 11:00:00 GMT</pubDate><source>Source B</source></item>
        </channel></rss>'''
        with patch.object(cs, "_fetch", return_value=rss):
            ok, items = cs.get_news(force=True)
        self.assertTrue(ok)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["source"], "Source A")
        self.assertIn("Titre 1", cs.format_news(items))

    def test_briefing_can_be_partial_without_failure(self):
        with patch.object(cs, "get_weather", return_value=(False, "Meteo indisponible")), patch.object(
            cs, "get_news", return_value=(True, [{"title": "Info", "source": "Test", "published": "", "link": ""}])
        ):
            data = cs.build_daily_briefing(force=True)
        text = cs.format_daily_briefing(data)
        self.assertIn("Meteo indisponible", text)
        self.assertIn("Info", text)

    def test_morning_briefing_once_per_day(self):
        with tempfile.TemporaryDirectory() as td:
            original = cs.STATE_PATH
            try:
                cs.STATE_PATH = Path(td) / "state.json"
                now = dt.datetime(2026, 11, 10, 7, 0, 0)
                self.assertTrue(cs.should_show_morning_briefing(now))
                cs.mark_morning_briefing_shown(now)
                self.assertFalse(cs.should_show_morning_briefing(now))
            finally:
                cs.STATE_PATH = original

    def test_security_policy_is_read_only_and_no_post(self):
        policy = json.loads((ROOT / "config/permissions.json").read_text(encoding="utf-8"))["connected_services_policy"]
        self.assertTrue(policy["read_only"])
        self.assertTrue(policy["https_only"])
        self.assertFalse(policy["allow_http_post"])
        self.assertFalse(policy["allow_automatic_actions_from_content"])
        self.assertIn("api.open-meteo.com", policy["allowed_hosts"])
        self.assertIn("news.google.com", policy["allowed_hosts"])


if __name__ == "__main__":
    unittest.main()
