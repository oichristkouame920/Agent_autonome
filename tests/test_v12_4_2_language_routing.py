from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from backends.backend_manager import interpret
from backends import deterministic_backend
from action_suggestions import build_suggestions
from agent import format_habit_summary
from project_version import AGENTLOCAL_BUILD


class NaturalRoutingV1242Tests(unittest.TestCase):
    def test_habit_queries_bypass_llm(self):
        for text in (
            "Quelles sont mes habitudes ?",
            "quelle sont mes habitudes ?",
            "liste mes habitudes",
            "quelles sont mes habittudes ?",
        ):
            result = interpret(text)
            self.assertEqual(result.get("routing"), "deterministic_preflight", text)
            actions = result.get("actions", [])
            self.assertEqual(actions[0].get("action"), "list_habits", text)


    def test_briefing_queries_bypass_llm(self):
        for text in (
            "Briefing du jour",
            "mon briefing du jour",
            "affiche le briefing",
            "donne-moi le briefing du jour",
            "fais le briefing du matin",
        ):
            result = interpret(text)
            self.assertEqual(result.get("routing"), "deterministic_preflight", text)
            actions = result.get("actions", [])
            self.assertTrue(actions, text)
            self.assertEqual(actions[0].get("action"), "read_daily_briefing", text)

    def test_habit_parser_tolerates_punctuation_directly(self):
        actions = deterministic_backend.parse_habit_command("Quelles sont mes habitudes ?")
        self.assertTrue(actions)
        self.assertEqual(actions[0]["action"], "list_habits")

    def test_empty_habit_summary_is_human_readable(self):
        # La base de test de reference peut etre vide. La sortie ne doit jamais
        # etre une question LLM ou une simple reformulation de la demande.
        text = format_habit_summary()
        self.assertIsInstance(text, str)
        self.assertTrue(text.strip())
        self.assertNotIn("quelle est la liste", text.lower())

    def test_closed_desktop_app_can_offer_web_variant(self):
        suggestions = build_suggestions(
            "ferme teams",
            [{"action": "close_application", "target": "teams"}],
            ["Microsoft Teams est déjà fermé."],
        )
        labels = [x.label for x in suggestions]
        commands = [x.command for x in suggestions]
        self.assertIn("Fermer Teams dans Edge", labels)
        self.assertIn("ferme le site teams", commands)

    def test_build_marker(self):
        self.assertIn("v12.4.2-language-routing", AGENTLOCAL_BUILD)


if __name__ == "__main__":
    unittest.main()
