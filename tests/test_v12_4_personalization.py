from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import connected_services
import gui
import learning_profile
import morning_automation
import response_style
import user_profile
from project_version import AGENTLOCAL_BUILD, AGENTLOCAL_VERSION


class PersonalizationV124Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.old_paths = {
            "PROFILE_FILE": user_profile.PROFILE_FILE,
            "PREFERENCES_FILE": user_profile.PREFERENCES_FILE,
            "ONBOARDING_FILE": user_profile.ONBOARDING_FILE,
            "DECLARED_HABITS_FILE": user_profile.DECLARED_HABITS_FILE,
            "MORNING_PREFS": morning_automation.PREFERENCES_FILE,
            "NEWS_PREFS": connected_services.USER_PREFERENCES_PATH,
        }
        user_profile.PROFILE_FILE = base / "user_profile.json"
        user_profile.PREFERENCES_FILE = base / "user_preferences.json"
        user_profile.ONBOARDING_FILE = base / "onboarding_state.json"
        user_profile.DECLARED_HABITS_FILE = base / "declared_habits.json"
        morning_automation.PREFERENCES_FILE = user_profile.PREFERENCES_FILE
        connected_services.USER_PREFERENCES_PATH = user_profile.PREFERENCES_FILE

    def tearDown(self):
        user_profile.PROFILE_FILE = self.old_paths["PROFILE_FILE"]
        user_profile.PREFERENCES_FILE = self.old_paths["PREFERENCES_FILE"]
        user_profile.ONBOARDING_FILE = self.old_paths["ONBOARDING_FILE"]
        user_profile.DECLARED_HABITS_FILE = self.old_paths["DECLARED_HABITS_FILE"]
        morning_automation.PREFERENCES_FILE = self.old_paths["MORNING_PREFS"]
        connected_services.USER_PREFERENCES_PATH = self.old_paths["NEWS_PREFS"]
        self.tmp.cleanup()

    def test_version_and_build(self):
        self.assertEqual(AGENTLOCAL_VERSION, "12.5")
        self.assertIn("v12.4-host-personalization", AGENTLOCAL_BUILD)

    def test_profile_is_machine_local_and_sanitized(self):
        saved = user_profile.save_profile({"display_name": "  Alice  ", "machine_name": "PC-TEST", "usage_mode": "work"})
        self.assertEqual(saved["display_name"], "Alice")
        self.assertEqual(saved["machine_name"], "PC-TEST")
        self.assertTrue(user_profile.PROFILE_FILE.exists())

    def test_privacy_guarantees_fail_closed(self):
        prefs = user_profile.load_preferences()
        prefs["privacy"].update({"observe_private_content": True, "capture_keystrokes": True, "automatic_sensitive_actions": True})
        saved = user_profile.save_preferences(prefs)
        self.assertFalse(saved["privacy"]["observe_private_content"])
        self.assertFalse(saved["privacy"]["capture_keystrokes"])
        self.assertFalse(saved["privacy"]["automatic_sensitive_actions"])

    def test_onboarding_completion_creates_profile_without_automation(self):
        profile = user_profile.load_profile(); profile["display_name"] = "Alice"
        prefs = user_profile.load_preferences(); prefs["learning"]["onboarding_mode"] = "hybrid"
        declared = user_profile.load_declared_habits(); declared["frequent_apps"] = ["edge", "teams"]
        user_profile.complete_onboarding(profile=profile, preferences=prefs, declared_habits=declared)
        self.assertTrue(user_profile.is_onboarding_complete())
        state = user_profile.load_onboarding()
        self.assertTrue(state["initial_learning_started_at"])
        self.assertFalse((Path(self.tmp.name) / "schedules.json").exists())

    def test_response_emoji_can_be_disabled(self):
        prefs = user_profile.load_preferences(); prefs["assistant"]["emoji_level"] = "none"; user_profile.save_preferences(prefs)
        self.assertEqual(response_style.decorate_response("CPU : 12 %"), "CPU : 12 %")
        prefs["assistant"]["emoji_level"] = "light"; user_profile.save_preferences(prefs)
        self.assertTrue(response_style.decorate_response("CPU : 12 %").startswith("🖥️"))

    def test_morning_window_uses_host_preferences(self):
        prefs = user_profile.load_preferences(); prefs["morning"].update({"enabled": True, "start_time": "08:00", "end_time": "10:00"}); user_profile.save_preferences(prefs)
        cfg = morning_automation.load_config()
        self.assertEqual(cfg["start_time"], "08:00")
        self.assertEqual(cfg["end_time"], "10:00")
        self.assertEqual(cfg["trigger"], "first_unlock_seen")

    def test_news_topics_follow_host_selection(self):
        prefs = user_profile.load_preferences(); prefs["briefing"]["topics"]["ukraine"] = False; prefs["briefing"]["topics"]["technology"] = True; user_profile.save_preferences(prefs)
        fake_cfg = {
            "enabled": True, "language": "fr", "country_code": "CI", "limit": 10, "per_topic_limit": 2, "cache_seconds": 0,
            "topics": [
                {"id": "ukraine", "label": "Ukraine", "query": "Ukraine"},
                {"id": "technology", "label": "Technologie", "query": "IA"},
            ],
            "exclude_keywords": [], "preferred_sources": [],
        }
        seen = []
        def fake_read(**kwargs):
            seen.append(kwargs["category_id"])
            return [{"title": kwargs["category_label"], "source": "Test", "published": "", "link": "", "category": kwargs["category_id"], "category_label": kwargs["category_label"]}]
        with mock.patch.object(connected_services, "_service_config", return_value=fake_cfg), mock.patch.object(connected_services, "_read_google_news_topic", side_effect=fake_read):
            ok, rows = connected_services.get_news(force=True)
        self.assertTrue(ok)
        self.assertEqual(seen, ["technology"])
        self.assertEqual(rows[0]["category"], "technology")

    def test_initial_learning_progress_is_two_days(self):
        profile = user_profile.load_profile(); profile["configured"] = True
        prefs = user_profile.load_preferences(); prefs["learning"].update({"enabled": True, "initial_days": 2}); user_profile.save_preferences(prefs)
        state = user_profile.load_onboarding(); state.update({"completed": True, "initial_learning_started_at": "2026-11-10T08:00:00+00:00"}); user_profile.save_onboarding(state)
        status = learning_profile.initial_learning_status(dt.datetime(2026, 11, 11, 8, 0, tzinfo=dt.timezone.utc))
        self.assertEqual(status["days"], 2)
        self.assertEqual(status["day"], 2)
        self.assertEqual(status["progress"], 50)

    def test_navigation_contains_habits_and_configuration(self):
        keys = [key for _, key in gui.AgentLocalGUI.NAV_ITEMS]
        self.assertIn("habits", keys)
        self.assertIn("configuration", keys)
        self.assertEqual(keys[-1], "settings")

    def test_onboarding_and_config_ui_are_clean_tkinter_only(self):
        gui_source = (ROOT / "app/gui.py").read_text(encoding="utf-8")
        onboarding_source = (ROOT / "app/onboarding.py").read_text(encoding="utf-8")
        for token in ("Profil de l’hôte", "Comportement", "Apprentissage", "Routine matinale", "Briefing", "Confidentialité"):
            self.assertIn(token, gui_source)
        self.assertIn("Les deux — recommandé", onboarding_source)
        self.assertIn("2 jours", onboarding_source)
        self.assertNotIn("customtkinter", (gui_source + onboarding_source).lower())

    def test_distribution_manifest_excludes_host_profile(self):
        names = ("user_profile.json", "user_preferences.json", "onboarding_state.json", "declared_habits.json")
        manifest = (ROOT / "MANIFEST_COMPLET_V12_4.sha256.txt").read_text(encoding="utf-8", errors="replace").replace("\\", "/")
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8", errors="replace").replace("\\", "/")
        for name in names:
            self.assertNotIn(f"memory/{name}", manifest, name)
            self.assertIn(f"memory/{name}", gitignore, name)

    def test_existing_host_profile_is_allowed_on_live_install(self):
        # Une installation réellement utilisée peut déjà avoir créé ces fichiers.
        profile = user_profile.load_profile()
        profile["display_name"] = "Alice"
        user_profile.save_profile(profile)
        self.assertTrue(user_profile.PROFILE_FILE.exists())
        data = json.loads(user_profile.PROFILE_FILE.read_text(encoding="utf-8"))
        self.assertIsInstance(data, dict)


if __name__ == "__main__":
    unittest.main()
