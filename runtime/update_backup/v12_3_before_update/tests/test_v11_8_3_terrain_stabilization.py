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
from app.controlled_local_tools import _process_rows, read_system_info
from app.agent import _register_browser_tab_number_choices
from session_context import clear_pending_choice, resolve_pending_choice
from project_version import AGENTLOCAL_VERSION, AGENTLOCAL_BUILD


def _first_action(text):
    result = interpret(text)
    actions = result.get("actions", [])
    return actions[0] if actions else None, result


class TerrainStabilizationV1183Tests(unittest.TestCase):
    def test_version_v1183(self):
        parts = tuple(int(x) for x in AGENTLOCAL_VERSION.split(".")[:2])
        self.assertGreaterEqual(parts, (11, 8))
        self.assertTrue(AGENTLOCAL_BUILD)

    def test_network_state_natural_phrase(self):
        action, _ = _first_action("quel est l'etat de ma connexion ?")
        self.assertEqual(action["action"], "read_network_info")
        self.assertEqual(action["target"], "status")

    def test_agent_performance_phrase(self):
        action, _ = _first_action("quelle est ta performance ?")
        self.assertEqual(action["action"], "read_system_info")
        self.assertEqual(action["target"], "agent")

    def test_visible_windows_phrase(self):
        action, _ = _first_action("quelle sont les fenetre active sur ce PC")
        self.assertEqual(action["action"], "read_system_info")
        self.assertEqual(action["target"], "windows")

    def test_weather_never_becomes_file_search(self):
        action, _ = _first_action("quelle est la météo d'aujourd'hui ?")
        self.assertEqual(action["action"], "read_weather")
        self.assertEqual(action["target"], "today")

    def test_updates_are_recognized_without_automatic_install(self):
        action, _ = _first_action("verifi mes mises à jours")
        self.assertEqual(action["action"], "check_online_updates")
        self.assertEqual(action["target"], "agentlocal")

    def test_habit_schedule_creates_only_a_disabled_draft(self):
        action, _ = _first_action("Enregistre mes habitudes chaque matin à 7H")
        self.assertEqual(action["action"], "create_schedule_draft")
        self.assertEqual(action["target"], "habit_summary")
        self.assertEqual(action["params"]["trigger"]["time"], "07:00")

    def test_process_cpu_is_bounded_and_idle_hidden(self):
        rows = _process_rows("top_cpu", 10)
        if rows is None:
            self.skipTest("psutil indisponible")
        self.assertTrue(all(0.0 <= row["cpu"] <= 100.0 for row in rows))
        self.assertTrue(all(row["name"].strip().lower() != "system idle process" for row in rows))

    def test_agent_performance_tool_is_read_only_and_available(self):
        ok, message = read_system_info("agent", explicit_user_command=True, source="manual")
        self.assertTrue(ok)
        self.assertIn("AgentLocal", message)

    def test_tab_number_five_can_refer_to_fifth_known_tab(self):
        clear_pending_choice()
        _register_browser_tab_number_choices(
            [{"action": "list_browser_tabs", "target": "edge", "params": {}}],
            [
                "Onglets Edge visibles par le pont local (6) :\n"
                "1. ChatGPT — chatgpt.com\n"
                "2. UDMCI — foad.udmci-enligne.ci\n"
                "3. Campus — localhost\n"
                "4. WhatsApp — web.whatsapp.com [actif]\n"
                "5. Musique — www.youtube.com\n"
                "6. Accueil — foad.udmci-enligne.ci"
            ],
        )
        self.assertEqual(resolve_pending_choice("5"), "passe sur youtube")

    def test_web_user_message_no_longer_contains_targeted_close_warning(self):
        source = (ROOT / "app/web_tools.py").read_text(encoding="utf-8")
        self.assertNotIn("La fenêtre n'a pas pu être enregistrée pour une fermeture ciblée.", source)

    def test_sticky_notes_has_title_based_fallback(self):
        source = (ROOT / "app/windows_tools.py").read_text(encoding="utf-8")
        self.assertIn('app_name == "sticky_notes"', source)
        self.assertIn("pense-bêtes", source)


if __name__ == "__main__":
    unittest.main()
