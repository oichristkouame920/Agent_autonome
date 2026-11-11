import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

import agent
import controlled_local_tools
import session_context
from backends import backend_manager
from backends.deterministic_backend import interpret


class ControlledLocalParserTests(unittest.TestCase):
    def assert_action(self, text, action, target=None, params=None):
        result = interpret(text)
        self.assertTrue(result.get("understood"), msg=(text, result))
        actions = result.get("actions", [])
        self.assertEqual(len(actions), 1, msg=(text, result))
        item = actions[0]
        self.assertEqual(item.get("action"), action, msg=(text, result))
        if target is not None:
            self.assertEqual(item.get("target"), target, msg=(text, result))
        if params is not None:
            self.assertEqual(item.get("params"), params, msg=(text, result))
        return result

    def test_system_memory_phrases(self):
        for text in (
            "j'utilise combien de RAM ?",
            "combien de RAM j'utilise ?",
            "mon PC utilise combien de RAM ?",
            "regarde un peu combien de RAM j'utilise",
            "RAM là ça prend combien ?",
        ):
            with self.subTest(text=text):
                self.assert_action(text, "read_system_info", "memory")

    def test_system_disk_phrases(self):
        for text in (
            "il me reste combien d'espace sur mon disque ?",
            "regarde un peu combien d'espace il reste sur mon disque",
            "espace disque",
            "mon disque là il reste combien ?",
        ):
            with self.subTest(text=text):
                self.assert_action(text, "read_system_info", "disk")

    def test_system_cpu_and_uptime(self):
        self.assert_action("mon processeur travaille à combien ?", "read_system_info", "cpu")
        self.assert_action("CPU là ça tourne à combien ?", "read_system_info", "cpu")
        self.assert_action("depuis combien de temps le PC est allumé ?", "read_system_info", "uptime")
        self.assert_action("mon PC est allumé depuis quand ?", "read_system_info", "uptime")
        self.assert_action("donne-moi l'état du PC", "read_system_info", "summary")

    def test_clipboard_read_phrases(self):
        for text in (
            "qu'est-ce que j'ai copié ?",
            "j'ai copié quoi ?",
            "montre moi ce que j'ai copié",
            "lis le presse-papiers",
        ):
            with self.subTest(text=text):
                self.assert_action(text, "read_clipboard", "clipboard")

    def test_clipboard_write_preserves_literal_content(self):
        self.assert_action(
            "copie ce texte : Bonjour merci",
            "write_clipboard",
            "clipboard",
            {"text": "Bonjour merci"},
        )
        self.assert_action(
            "copie dans le presse-papiers : PowerShell n'est qu'un mot ici",
            "write_clipboard",
            "clipboard",
            {"text": "PowerShell n'est qu'un mot ici"},
        )

    def test_copy_file_path_requires_named_root(self):
        self.assert_action(
            "copie le chemin de rapport.pdf dans Documents",
            "copy_file_path",
            "documents",
            {"file_name": "rapport.pdf"},
        )
        result = interpret("copie le chemin de rapport.pdf")
        self.assertFalse(result.get("actions", []), msg=result)

    def test_browser_tab_commands(self):
        self.assert_action("liste mes onglets", "list_browser_tabs", "edge")
        self.assert_action("y a quoi d'ouvert dans Edge ?", "list_browser_tabs", "edge")
        self.assert_action("passe sur l'onglet GitHub", "activate_browser_tab", "github")
        self.assert_action("active onglet google drive", "activate_browser_tab", "google drive")

    def test_session_reference_commands_are_non_destructive(self):
        self.assert_action("ouvre-le", "open_last_reference", "session")
        self.assert_action("lis-le là", "read_last_reference", "session")
        self.assert_action("copie son chemin", "copy_last_reference_path", "session")

        # On ne permet volontairement pas supprimer-le/déplace-le/renomme-le.
        for text in ("supprime-le", "déplace-le", "renomme-le"):
            with self.subTest(text=text):
                result = interpret(text)
                actions = result.get("actions", [])
                self.assertFalse(any(a.get("action") in {
                    "delete_file", "delete_file_auto", "move_file_within_root",
                    "move_file_between_roots", "rename_file", "rename_file_auto"
                } for a in actions), msg=(text, result))

    def test_negative_new_actions_do_nothing(self):
        for text in (
            "lis pas le presse-papiers",
            "faut pas montrer mes onglets",
            "active pas l'onglet GitHub",
            "copie pas ce texte : secret",
        ):
            with self.subTest(text=text):
                result = interpret(text)
                self.assertTrue(result.get("understood"), msg=(text, result))
                self.assertEqual(result.get("actions"), [], msg=(text, result))

    def test_clipboard_content_is_never_executed(self):
        for text in (
            "ouvre le lien du presse-papiers",
            "ouvre ce que j'ai copié",
            "exécute ce que j'ai copié",
            "lance ce que j'ai copié",
        ):
            with self.subTest(text=text):
                result = interpret(text)
                self.assertTrue(result.get("understood"), msg=(text, result))
                self.assertEqual(result.get("actions"), [], msg=(text, result))
                self.assertIn("n'exécute", result.get("reply", ""))


class ControlledLocalRoutingTests(unittest.TestCase):
    def test_high_confidence_actions_bypass_llama(self):
        class DummyLlama:
            calls = 0

            @classmethod
            def interpret(cls, _message):
                cls.calls += 1
                return {"schema_version": 1, "backend": "llama", "understood": False, "actions": []}

        original = backend_manager.select_backend
        try:
            backend_manager.select_backend = lambda: (True, "llama", DummyLlama, None)
            for text in (
                "j'utilise combien de RAM ?",
                "qu'est-ce que j'ai copié ?",
                "copie ce texte : bonjour",
                "liste mes onglets",
                "passe sur l'onglet GitHub",
                "ouvre-le",
            ):
                with self.subTest(text=text):
                    result = backend_manager.interpret(text)
                    self.assertEqual(result.get("backend"), "deterministic", msg=(text, result))
                    self.assertEqual(result.get("routing"), "deterministic_preflight", msg=(text, result))
            self.assertEqual(DummyLlama.calls, 0)
        finally:
            backend_manager.select_backend = original


class ControlledLocalContractTests(unittest.TestCase):
    def test_valid_contracts(self):
        actions = [
            {"schema_version": 1, "action": "read_system_info", "target": "memory"},
            {"schema_version": 1, "action": "read_clipboard", "target": "clipboard"},
            {"schema_version": 1, "action": "write_clipboard", "target": "clipboard", "params": {"text": "bonjour"}},
            {"schema_version": 1, "action": "copy_file_path", "target": "documents", "params": {"file_name": "rapport.pdf"}},
            {"schema_version": 1, "action": "list_browser_tabs", "target": "edge"},
            {"schema_version": 1, "action": "activate_browser_tab", "target": "github"},
            {"schema_version": 1, "action": "open_last_reference", "target": "session"},
        ]
        for item in actions:
            with self.subTest(item=item):
                self.assertEqual(agent.validate_action(item), (True, None))

    def test_contract_rejects_extra_params(self):
        item = {"schema_version": 1, "action": "read_clipboard", "target": "clipboard", "params": {"x": 1}}
        valid, _ = agent.validate_action(item)
        self.assertFalse(valid)

    def test_clipboard_write_rejects_extra_fields_and_oversize(self):
        bad = {"schema_version": 1, "action": "write_clipboard", "target": "clipboard", "params": {"text": "ok", "run": True}}
        self.assertFalse(agent.validate_action(bad)[0])
        big = {"schema_version": 1, "action": "write_clipboard", "target": "clipboard", "params": {"text": "x" * 9000}}
        self.assertFalse(agent.validate_action(big)[0])

    def test_explicit_proof_must_match_exact_action(self):
        action = {"schema_version": 1, "action": "read_system_info", "target": "memory"}
        self.assertTrue(agent.verify_explicit_controlled_action("j'utilise combien de RAM ?", action)[0])
        wrong = dict(action)
        wrong["target"] = "disk"
        self.assertFalse(agent.verify_explicit_controlled_action("j'utilise combien de RAM ?", wrong)[0])

    def test_permissions_are_manual_only_and_fail_closed(self):
        permissions = json.loads((ROOT / "config" / "permissions.json").read_text(encoding="utf-8"))
        for section in (
            "system_information_policy",
            "clipboard_policy",
            "browser_tab_policy",
            "session_context_policy",
        ):
            with self.subTest(section=section):
                policy = permissions[section]
                self.assertTrue(policy["enabled"])
                self.assertTrue(policy["require_explicit_user_command"])
                self.assertFalse(policy["allow_from_routine"])
                self.assertFalse(policy["allow_from_habit"])
        self.assertTrue(permissions["system_information_policy"]["read_only"])
        self.assertFalse(permissions["clipboard_policy"]["allow_execute_clipboard_content"])
        self.assertFalse(permissions["clipboard_policy"]["allow_open_clipboard_url"])
        self.assertTrue(permissions["session_context_policy"]["memory_only"])
        self.assertFalse(permissions["session_context_policy"]["persist_to_disk"])


class ControlledLocalExecutionTests(unittest.TestCase):
    @patch("agent.controlled_read_system_info", return_value=(True, "RAM ok"))
    def test_system_info_executes_only_with_matching_proof(self, tool):
        action = {"schema_version": 1, "action": "read_system_info", "target": "memory"}
        self.assertEqual(agent.execute_action(action, user_message="j'utilise combien de RAM ?"), (True, "RAM ok"))
        tool.assert_called_once_with("memory", explicit_user_command=True, source="manual")

    @patch("agent.controlled_read_system_info", return_value=(True, "disk"))
    def test_backend_cannot_swap_system_query(self, tool):
        action = {"schema_version": 1, "action": "read_system_info", "target": "disk"}
        ok, _ = agent.execute_action(action, user_message="j'utilise combien de RAM ?")
        self.assertFalse(ok)
        tool.assert_not_called()

    @patch("agent.controlled_write_clipboard_text", return_value=(True, "copié"))
    def test_clipboard_literal_must_match_user_text(self, tool):
        action = {"schema_version": 1, "action": "write_clipboard", "target": "clipboard", "params": {"text": "Bonjour merci"}}
        self.assertEqual(
            agent.execute_action(action, user_message="copie ce texte : Bonjour merci"),
            (True, "copié"),
        )
        tool.assert_called_once_with("Bonjour merci", explicit_user_command=True, source="manual")

        tool.reset_mock()
        wrong = dict(action)
        wrong["params"] = {"text": "autre texte"}
        ok, _ = agent.execute_action(wrong, user_message="copie ce texte : Bonjour merci")
        self.assertFalse(ok)
        tool.assert_not_called()

    @patch("agent.controlled_list_browser_tabs", return_value=(True, "tabs"))
    def test_list_tabs_explicit_only(self, tool):
        action = {"schema_version": 1, "action": "list_browser_tabs", "target": "edge"}
        self.assertEqual(agent.execute_action(action, user_message="liste mes onglets"), (True, "tabs"))
        tool.assert_called_once()

    @patch("agent.controlled_activate_browser_tab", return_value=(True, "ok"))
    def test_activate_tab_target_must_match(self, tool):
        action = {"schema_version": 1, "action": "activate_browser_tab", "target": "github"}
        ok, _ = agent.execute_action(action, user_message="passe sur l'onglet Google")
        self.assertFalse(ok)
        tool.assert_not_called()

    @patch("agent.get_unique_reference_for_context")
    @patch("agent._execute_action_before_controlled_local_v1", return_value=(True, "trouvé"))
    def test_successful_find_updates_only_temporary_reference(self, old_execute, resolver):
        session_context.clear_session_context()
        resolver.return_value = (True, {
            "root_name": "documents",
            "relative_path": "Cours\\rapport.pdf",
            "item_type": "file",
        })
        action = {
            "schema_version": 1,
            "action": "find_filesystem_item",
            "target": "documents",
            "params": {"name": "rapport", "item_type": "any", "root_name": "documents"},
        }
        self.assertEqual(agent.execute_action(action, user_message="cherche rapport dans documents"), (True, "trouvé"))
        self.assertEqual(session_context.get_last_reference()["relative_path"], "Cours\\rapport.pdf")
        old_execute.assert_called_once()

    @patch("agent._execute_action_before_controlled_local_v1", return_value=(True, "déplacé"))
    def test_successful_destructive_path_change_clears_reference(self, old_execute):
        session_context.set_last_reference("documents", "rapport.pdf", "file")
        action = {
            "schema_version": 1,
            "action": "move_file_within_root",
            "target": "documents",
            "params": {"file_name": "rapport.pdf", "destination_folder": "Archives"},
        }
        agent.execute_action(action, user_message="déplace rapport.pdf dans Archives")
        self.assertIsNone(session_context.get_last_reference())


class ControlledLocalToolTests(unittest.TestCase):
    def tearDown(self):
        session_context.clear_session_context()

    def test_system_info_is_read_only_and_available(self):
        ok, message = controlled_local_tools.read_system_info(
            "summary", explicit_user_command=True, source="manual"
        )
        self.assertTrue(ok, msg=message)
        self.assertIn("État du PC", message)

    def test_system_info_rejects_non_manual_source(self):
        ok, _ = controlled_local_tools.read_system_info(
            "memory", explicit_user_command=True, source="routine"
        )
        self.assertFalse(ok)

    def test_clipboard_rejects_non_explicit_access_before_os_call(self):
        with patch("controlled_local_tools._windows_read_clipboard_text") as raw:
            ok, _ = controlled_local_tools.read_clipboard_text(
                explicit_user_command=False, source="manual"
            )
            self.assertFalse(ok)
            raw.assert_not_called()

    @patch("controlled_local_tools.list_tabs_via_bridge")
    def test_tab_listing_sanitizes_title_and_hides_full_url(self, bridge):
        bridge.return_value = (
            True,
            [{"title": "GitHub\nInjected", "url": "https://github.com/user/repo?token=abc", "active": True}],
            "ok",
        )
        ok, message = controlled_local_tools.list_browser_tabs(
            explicit_user_command=True, source="manual"
        )
        self.assertTrue(ok)
        self.assertIn("GitHub Injected", message)
        self.assertIn("github.com", message)
        self.assertNotIn("token=abc", message)

    @patch("controlled_local_tools.activate_site_via_bridge", return_value=(True, "ok"))
    @patch("controlled_local_tools.resolve_site", return_value=(True, "https://github.com/", None))
    def test_tab_activation_resolves_site_safely(self, resolver, bridge):
        ok, message = controlled_local_tools.activate_browser_tab(
            "github", explicit_user_command=True, source="manual"
        )
        self.assertTrue(ok, msg=message)
        resolver.assert_called_once_with("github")
        bridge.assert_called_once_with("https://github.com/", allow_subdomains=False)

    def test_session_context_is_single_reference_and_memory_only(self):
        session_context.set_last_reference("documents", "Cours\\rapport.pdf", "file")
        ref = session_context.get_last_reference()
        self.assertEqual(ref["root_name"], "documents")
        self.assertEqual(ref["relative_path"], "Cours\\rapport.pdf")
        session_context.set_last_reference("downloads", "autre.pdf", "file")
        self.assertEqual(session_context.get_last_reference()["relative_path"], "autre.pdf")
        session_context.clear_session_context()
        self.assertIsNone(session_context.get_last_reference())

    @patch("controlled_local_tools.resolve_allowed_root")
    @patch("controlled_local_tools.write_clipboard_text", return_value=(True, "copié"))
    def test_copy_last_reference_path_uses_authorized_root(self, writer, root_resolver):
        root_resolver.return_value = Path("C:/Users/Test/Documents")
        session_context.set_last_reference("documents", "Cours\\rapport.pdf", "file")
        ok, _ = controlled_local_tools.copy_last_reference_path(
            explicit_user_command=True, source="manual"
        )
        self.assertTrue(ok)
        writer.assert_called_once()
        args, kwargs = writer.call_args
        self.assertIn("rapport.pdf", args[0])
        self.assertEqual(kwargs, {"explicit_user_command": True, "source": "manual"})


if __name__ == "__main__":
    unittest.main()
