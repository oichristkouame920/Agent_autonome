import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import language_profile, notification_policy, theme_manager, user_profile


class V125PersonalizationTests(unittest.TestCase):
    def test_new_preference_blocks_are_sanitized(self):
        prefs = user_profile.sanitize_preferences({
            "appearance": {"theme": "dark", "accent_color": "#123ABC", "density": "compact"},
            "notifications": {"mode": "periodic", "summary_minutes": 120, "repeat_cooldown_minutes": 20},
            "understanding": {"typo_tolerance": 3, "context_turns": 6},
            "assistant": {"response_detail": "detailed"},
        })
        self.assertEqual(prefs["appearance"]["theme"], "dark")
        self.assertEqual(prefs["appearance"]["accent_color"], "#123ABC")
        self.assertEqual(prefs["notifications"]["mode"], "periodic")
        self.assertEqual(prefs["notifications"]["summary_minutes"], 120)
        self.assertEqual(prefs["understanding"]["typo_tolerance"], 3)
        self.assertEqual(prefs["assistant"]["response_detail"], "detailed")

    def test_bad_values_fall_back_safely(self):
        prefs = user_profile.sanitize_preferences({
            "appearance": {"theme": "unknown", "accent_color": "red"},
            "notifications": {"mode": "spam", "summary_minutes": 17},
            "understanding": {"typo_tolerance": 99, "context_turns": 99},
        })
        self.assertEqual(prefs["appearance"]["theme"], "agentlocal")
        self.assertEqual(prefs["appearance"]["accent_color"], "#356AE6")
        self.assertEqual(prefs["notifications"]["mode"], "balanced")
        self.assertEqual(prefs["notifications"]["summary_minutes"], 60)
        self.assertEqual(prefs["understanding"]["typo_tolerance"], 3)
        self.assertEqual(prefs["understanding"]["context_turns"], 8)

    def test_privacy_guarantees_still_fail_closed(self):
        prefs = user_profile.sanitize_preferences({"privacy": {"observe_private_content": True, "capture_keystrokes": True, "automatic_sensitive_actions": True}})
        self.assertFalse(prefs["privacy"]["observe_private_content"])
        self.assertFalse(prefs["privacy"]["capture_keystrokes"])
        self.assertFalse(prefs["privacy"]["automatic_sensitive_actions"])


    def test_language_profile_learns_only_explicit_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(language_profile, "FILE", Path(tmp) / "language_profile.json"):
                self.assertIsNone(language_profile.resolve_expression("fais le point"))
                self.assertTrue(language_profile.remember_expression("fais le point", "quel est l'état de mon PC"))
                self.assertEqual(language_profile.resolve_expression("FAIS   LE POINT"), "quel est l'état de mon PC")

    def test_theme_custom_colors_are_applied(self):
        palette = theme_manager.build_palette({"theme": "dark", "accent_color": "#112233", "sidebar_color": "#010203", "card_color": "#222222"})
        self.assertEqual(palette["accent"], "#112233")
        self.assertEqual(palette["sidebar"], "#010203")
        self.assertEqual(palette["card"], "#222222")
        self.assertIn("text", palette)


class V125NotificationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state_file = Path(self.tmp.name) / "notification_state.json"
        self.state_patch = mock.patch.object(notification_policy, "STATE_FILE", self.state_file)
        self.state_patch.start(); self.addCleanup(self.state_patch.stop)

    def _prefs(self, **changes):
        base = user_profile.sanitize_preferences({})
        base["notifications"].update(changes)
        return base

    def test_silent_mode_never_pops(self):
        with mock.patch.object(notification_policy, "load_preferences", return_value=self._prefs(mode="silent")):
            self.assertFalse(notification_policy.popup_allowed({"code": "health.ram", "level": "critical", "source": "system_monitor"}))

    def test_balanced_mode_pops_warning_but_not_info(self):
        with mock.patch.object(notification_policy, "load_preferences", return_value=self._prefs(mode="balanced")):
            self.assertTrue(notification_policy.popup_allowed({"code": "health.ram", "level": "warning", "source": "system_monitor"}))
            self.assertFalse(notification_policy.popup_allowed({"code": "morning.note", "level": "info", "source": "morning_automation"}))

    def test_cooldown_prevents_spam(self):
        now = dt.datetime(2026, 11, 12, 9, 0, tzinfo=dt.timezone.utc)
        prefs = self._prefs(mode="realtime", repeat_cooldown_minutes=60)
        item = {"code": "health.ram", "level": "warning", "source": "system_monitor"}
        with mock.patch.object(notification_policy, "load_preferences", return_value=prefs):
            self.assertTrue(notification_policy.popup_allowed(item, now))
            notification_policy.mark_popup(item, now)
            self.assertFalse(notification_policy.popup_allowed(item, now + dt.timedelta(minutes=10)))
            self.assertTrue(notification_policy.popup_allowed(item, now + dt.timedelta(minutes=61)))

    def test_periodic_digest_uses_selected_frequency(self):
        now = dt.datetime(2026, 11, 12, 9, 0, tzinfo=dt.timezone.utc)
        prefs = self._prefs(mode="periodic", summary_minutes=30)
        alerts = [{"code": "health.ram", "level": "warning"}]
        with mock.patch.object(notification_policy, "load_preferences", return_value=prefs):
            self.assertTrue(notification_policy.digest_due(alerts, now))
            notification_policy.mark_digest(now)
            self.assertFalse(notification_policy.digest_due(alerts, now + dt.timedelta(minutes=20)))
            self.assertTrue(notification_policy.digest_due(alerts, now + dt.timedelta(minutes=31)))

    def test_quiet_hours_suppress_warning_but_allow_critical(self):
        prefs = self._prefs(mode="realtime", quiet_hours={"enabled": True, "start": "18:30", "end": "07:00", "allow_critical": True})
        now = dt.datetime(2026, 11, 12, 22, 0).astimezone()
        with mock.patch.object(notification_policy, "load_preferences", return_value=prefs):
            self.assertFalse(notification_policy.popup_allowed({"code": "health.ram", "level": "warning", "source": "system_monitor"}, now))
            self.assertTrue(notification_policy.popup_allowed({"code": "health.disk", "level": "critical", "source": "system_monitor"}, now))


if __name__ == "__main__":
    unittest.main()
