import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for item in (ROOT, ROOT / "app", ROOT / "backends"):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

import controlled_local_tools
import web_tools
from deterministic_backend import interpret


class V114TerrainTests(unittest.TestCase):
    def test_whatsapp_uses_web_application_url(self):
        ok, url, error = web_tools.resolve_site("whatsapp")
        self.assertTrue(ok, msg=error)
        self.assertEqual(url, "https://web.whatsapp.com/")

    def test_whatsapp_open_detection_accepts_web_host(self):
        policy = {
            "enabled": True,
            "require_explicit_user_command": True,
            "allow_check_site_open": True,
            "allow_subdomains": False,
        }
        with patch.object(controlled_local_tools, "_load_permissions", return_value={"browser_tab_policy": policy}), \
             patch.object(controlled_local_tools, "resolve_site", return_value=(True, "https://web.whatsapp.com/", None)), \
             patch.object(controlled_local_tools, "list_tabs_via_bridge", return_value=(True, [{"url": "https://web.whatsapp.com/", "title": "WhatsApp", "active": False}], "ok")):
            ok, message = controlled_local_tools.check_browser_site_open(
                "whatsapp", explicit_user_command=True, source="manual"
            )
        self.assertTrue(ok, msg=message)
        self.assertIn("est ouvert", message)

    def test_browser_check_retries_once_after_bridge_timeout(self):
        policy = {
            "enabled": True,
            "require_explicit_user_command": True,
            "allow_check_site_open": True,
            "allow_subdomains": False,
        }
        results = [
            (False, [], "timeout"),
            (True, [{"url": "https://web.whatsapp.com/", "title": "WhatsApp", "active": True}], "ok"),
        ]
        with patch.object(controlled_local_tools, "_load_permissions", return_value={"browser_tab_policy": policy}), \
             patch.object(controlled_local_tools, "resolve_site", return_value=(True, "https://web.whatsapp.com/", None)), \
             patch.object(controlled_local_tools, "list_tabs_via_bridge", side_effect=results) as bridge, \
             patch.object(controlled_local_tools.time, "sleep"):
            ok, message = controlled_local_tools.check_browser_site_open(
                "whatsapp", explicit_user_command=True, source="manual"
            )
        self.assertTrue(ok, msg=message)
        self.assertEqual(bridge.call_count, 2)


    def test_routine_multiple_sites_share_one_edge_window(self):
        edge_path = Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe")
        window_calls = [[], [{"hwnd": 501}]]
        with patch.object(web_tools, "get_application_permission", return_value=True), \
             patch.object(web_tools, "find_edge", return_value=edge_path), \
             patch.object(web_tools, "get_application_window_records", side_effect=window_calls), \
             patch.object(web_tools, "launch_edge_new_window") as new_window, \
             patch.object(web_tools, "wait_for_new_edge_windows", return_value=[{"hwnd": 501}]), \
             patch.object(web_tools, "remember_web_windows"), \
             patch.object(web_tools, "open_site_via_bridge", return_value=(True, "ok")) as bridge:
            ok, results = web_tools.open_websites(["github", "chatgpt"])
        self.assertTrue(ok, msg=results)
        self.assertEqual(new_window.call_count, 1)
        bridge.assert_called_once_with("https://chatgpt.com/")

    def test_terrain_language_examples(self):
        expectations = {
            "quelle sont mes habitude": "list_habits",
            "donne l'etat du pc": "read_system_info",
            "le volume ?": "read_audio_state",
            "liste tout lew fichier en .txt": "advanced_file_search",
            "combien de mémoire il me reste": "read_system_info",
            "quelle sont les caracteristique de ma machine": "read_system_info",
            "verifie que whatsapp est ouvert": "check_browser_site",
        }
        for phrase, action_name in expectations.items():
            with self.subTest(phrase=phrase):
                result = interpret(phrase)
                self.assertTrue(result.get("understood"), msg=result)
                actions = result.get("actions", [])
                self.assertTrue(actions, msg=result)
                self.assertEqual(actions[0].get("action"), action_name)

    def test_identity_and_role_are_conversational(self):
        for phrase in ("qui est tu", "quel est ton rôle"):
            with self.subTest(phrase=phrase):
                result = interpret(phrase)
                self.assertTrue(result.get("understood"), msg=result)
                self.assertTrue(result.get("conversation"), msg=result)
                self.assertIn("AgentLocal", result.get("reply", ""))

    def test_create_empty_text_file_requests_content(self):
        result = interpret("crée document.txt dans document")
        self.assertTrue(result.get("understood"), msg=result)
        self.assertTrue(result.get("conversation"), msg=result)
        self.assertIn("contenu", result.get("reply", "").lower())


if __name__ == "__main__":
    unittest.main()
