from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from backends.deterministic_backend import interpret
from app.response_style import choose_emoji, decorate_response


def first_action(text: str):
    result = interpret(text)
    actions = result.get("actions", [])
    return actions[0] if actions else None, result


class NaturalInteractionsV1241Tests(unittest.TestCase):
    def assert_windows(self, text: str):
        action, result = first_action(text)
        self.assertTrue(result.get("understood"), text)
        self.assertIsNotNone(action, text)
        self.assertEqual(action.get("action"), "read_system_info", text)
        self.assertEqual(action.get("target"), "windows", text)

    def assert_tabs(self, text: str):
        action, result = first_action(text)
        self.assertTrue(result.get("understood"), text)
        self.assertIsNotNone(action, text)
        self.assertEqual(action.get("action"), "list_browser_tabs", text)
        self.assertEqual(action.get("target"), "edge", text)

    def test_exact_user_window_variants(self):
        for phrase in (
            "quelles sont les fenêtre actives ?",
            "quelles sont les fenêtres qui sont ouverte ?",
            "vérifi les fenêtres ouverte",
            "combien de fenêtre ssont ouverte ?",
        ):
            with self.subTest(phrase=phrase):
                self.assert_windows(phrase)

    def test_more_window_variants(self):
        for phrase in (
            "quelles fenêtres sont ouvertes",
            "verifie les fenetres ouvertes sur ce pc",
            "combien de fenetres sont ouvertes sur mon pc",
            "fenetres visibles",
        ):
            with self.subTest(phrase=phrase):
                self.assert_windows(phrase)

    def test_exact_user_tab_variant(self):
        self.assert_tabs("quels sont les onglets actifs ?")

    def test_more_tab_variants(self):
        for phrase in (
            "quels onglets sont ouverts",
            "quels sont les onglets visibles dans edge",
            "verifi les onglets ouverts",
            "combien d onglets sont ouverts",
            "onglets actifs",
        ):
            with self.subTest(phrase=phrase):
                self.assert_tabs(phrase)

    def test_comment_tu_vas_is_local_conversation(self):
        action, result = first_action("comment tu vas ?")
        self.assertIsNone(action)
        self.assertTrue(result.get("conversation"))
        self.assertIn("Ça va bien", result.get("reply", ""))
        self.assertNotIn("Comment puis-tu", result.get("reply", ""))

    def test_sont_does_not_trigger_audio_emoji(self):
        self.assertEqual(choose_emoji("Quelles sont les fenêtres ouvertes ?"), "🪟")
        self.assertNotEqual(choose_emoji("Combien de fenêtres sont ouvertes ?"), "🔊")
        self.assertEqual(choose_emoji("Quel est le son actuel ?"), "🔊")

    def test_window_response_decoration_is_window_specific(self):
        decorated = decorate_response("Fenêtres visibles sur ce PC (3) :")
        self.assertTrue(decorated.startswith("🪟 "))


if __name__ == "__main__":
    unittest.main()
