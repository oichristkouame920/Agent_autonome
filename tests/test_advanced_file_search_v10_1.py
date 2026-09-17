import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

import agent
import recursive_file_tools
from backends import backend_manager
from backends.deterministic_backend import interpret


class AdvancedSearchParserTests(unittest.TestCase):
    def one_action(self, text):
        result = interpret(text)
        self.assertTrue(result.get("understood"), msg=(text, result))
        actions = result.get("actions", [])
        self.assertEqual(len(actions), 1, msg=(text, result))
        self.assertEqual(actions[0].get("action"), "advanced_file_search", msg=(text, result))
        return actions[0]

    def test_pdf_downloaded_today(self):
        item = self.one_action("montre-moi les PDF téléchargés aujourd'hui")
        self.assertEqual(item["target"], "downloads")
        self.assertEqual(item["params"]["file_kind"], "pdf")
        self.assertEqual(item["params"]["date_filter"], "today")
        self.assertFalse(item["params"]["count_only"])

    def test_word_modified_this_week(self):
        item = self.one_action("retrouve les fichiers Word modifiés cette semaine")
        self.assertEqual(item["target"], "auto")
        self.assertEqual(item["params"]["file_kind"], "word")
        self.assertEqual(item["params"]["date_filter"], "this_week")
        self.assertEqual(item["params"]["date_field"], "modified")

    def test_recent_files_limit(self):
        item = self.one_action("montre-moi les 5 fichiers les plus récents")
        self.assertEqual(item["params"]["limit"], 5)
        self.assertEqual(item["params"]["sort"], "modified_desc")

    def test_size_filter(self):
        item = self.one_action("montre les fichiers de plus de 100 Mo dans Téléchargements")
        self.assertEqual(item["target"], "downloads")
        self.assertEqual(item["params"]["size_operator"], "gt")
        self.assertEqual(item["params"]["size_bytes"], 100 * 1024**2)

    def test_count_pdf_documents(self):
        item = self.one_action("j'ai combien de PDF dans Documents ?")
        self.assertEqual(item["target"], "documents")
        self.assertEqual(item["params"]["file_kind"], "pdf")
        self.assertTrue(item["params"]["count_only"])

    def test_created_images_yesterday(self):
        item = self.one_action("retrouve les images créées hier")
        self.assertEqual(item["params"]["file_kind"], "image")
        self.assertEqual(item["params"]["date_filter"], "yesterday")
        self.assertEqual(item["params"]["date_field"], "created")
        self.assertEqual(item["params"]["sort"], "created_desc")

    def test_excel_in_documents(self):
        item = self.one_action("cherche les fichiers Excel dans Documents et ses sous-dossiers")
        self.assertEqual(item["target"], "documents")
        self.assertEqual(item["params"]["file_kind"], "excel")

    def test_downloaded_today_natural_question(self):
        item = self.one_action("qu'est-ce que j'ai téléchargé aujourd'hui ?")
        self.assertEqual(item["target"], "downloads")
        self.assertEqual(item["params"]["date_filter"], "today")

    def test_largest_files(self):
        item = self.one_action("montre les 5 fichiers les plus gros dans Téléchargements")
        self.assertEqual(item["params"]["limit"], 5)
        self.assertEqual(item["params"]["sort"], "size_desc")

    def test_negation_does_not_search(self):
        result = interpret("montre pas les PDF téléchargés aujourd'hui")
        self.assertTrue(result.get("understood"), msg=result)
        self.assertEqual(result.get("actions"), [], msg=result)

    def test_regular_named_file_search_is_not_hijacked(self):
        result = interpret("cherche rapport.pdf")
        actions = result.get("actions", [])
        self.assertEqual(actions[0].get("action"), "find_filesystem_item", msg=result)


class AdvancedSearchRoutingAndContractTests(unittest.TestCase):
    def test_deterministic_preflight_avoids_llama(self):
        class DummyLlama:
            calls = 0

            @classmethod
            def interpret(cls, _message):
                cls.calls += 1
                return {"schema_version": 1, "backend": "llama", "understood": False, "actions": []}

        original = backend_manager.select_backend
        try:
            backend_manager.select_backend = lambda: (True, "llama", DummyLlama, None)
            result = backend_manager.interpret("montre-moi les 5 fichiers les plus récents")
            self.assertEqual(result.get("backend"), "deterministic")
            self.assertEqual(result.get("routing"), "deterministic_preflight")
            self.assertEqual(DummyLlama.calls, 0)
        finally:
            backend_manager.select_backend = original

    def test_contract_is_strict(self):
        action = interpret("combien j'ai de PDF dans Documents ?")["actions"][0]
        self.assertEqual(agent.validate_action(action), (True, None))

        tampered = json.loads(json.dumps(action))
        tampered["params"]["limit"] = 500
        self.assertFalse(agent.validate_action(tampered)[0])

        extra = json.loads(json.dumps(action))
        extra["params"]["path"] = "C:\\Windows"
        self.assertFalse(agent.validate_action(extra)[0])

    @patch("agent.recursive_advanced_search_files", return_value=(True, "recherche ok"))
    def test_execution_requires_exact_explicit_proof(self, tool):
        action = interpret("combien j'ai de PDF dans Documents ?")["actions"][0]
        self.assertEqual(
            agent.execute_action(action, user_message="combien j'ai de PDF dans Documents ?"),
            (True, "recherche ok"),
        )
        tool.assert_called_once()

        tool.reset_mock()
        wrong = json.loads(json.dumps(action))
        wrong["params"]["file_kind"] = "word"
        ok, _ = agent.execute_action(wrong, user_message="combien j'ai de PDF dans Documents ?")
        self.assertFalse(ok)
        tool.assert_not_called()

    def test_permissions_are_read_only_manual_only(self):
        permissions = json.loads((ROOT / "config" / "permissions.json").read_text(encoding="utf-8"))
        policy = permissions["filesystem"]["advanced_search_policy"]
        self.assertTrue(policy["enabled"])
        self.assertTrue(policy["read_only"])
        self.assertTrue(policy["metadata_only"])
        self.assertTrue(policy["require_explicit_user_command"])
        self.assertFalse(policy["allow_from_routine"])
        self.assertFalse(policy["allow_from_habit"])
        self.assertFalse(policy["allow_automatic_search"])
        self.assertLessEqual(policy["maximum_results"], 20)
        self.assertLessEqual(policy["maximum_search_entries"], 6000)


class AdvancedSearchToolTests(unittest.TestCase):
    def _make_file(self, root, relative, size=32, age_days=0):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as handle:
            handle.truncate(size)
        if age_days:
            timestamp = max(1, int(os.path.getmtime(path) - age_days * 86400))
            os.utime(path, (timestamp, timestamp))
        return path

    def test_metadata_search_filters_type_date_and_size(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._make_file(root, "cours/recent.pdf", size=2048)
            self._make_file(root, "cours/ancien.pdf", size=2048, age_days=2)
            self._make_file(root, "cours/tableau.xlsx", size=4096)
            self._make_file(root, "gros.bin", size=2 * 1024 * 1024)

            with patch("recursive_file_tools._root_path", return_value=(root, None)), \
                 patch("recursive_file_tools.base.is_hard_protected_path", return_value=False), \
                 patch("recursive_file_tools.base.is_reparse_point", return_value=False), \
                 patch("recursive_file_tools.base.is_hidden_or_system", return_value=False):
                ok, message = recursive_file_tools.advanced_search_files(
                    root_name="documents",
                    file_kind="pdf",
                    date_filter="today",
                    date_field="modified",
                    size_operator="any",
                    size_bytes=0,
                    sort="modified_desc",
                    limit=10,
                    count_only=False,
                    explicit_user_command=True,
                    source="manual",
                )
                self.assertTrue(ok, msg=message)
                self.assertIn("recent.pdf", message)
                self.assertNotIn("ancien.pdf", message)
                self.assertNotIn("tableau.xlsx", message)

                ok, message = recursive_file_tools.advanced_search_files(
                    root_name="documents",
                    file_kind="any",
                    size_operator="gt",
                    size_bytes=1024 * 1024,
                    limit=10,
                    count_only=False,
                    explicit_user_command=True,
                    source="manual",
                )
                self.assertTrue(ok, msg=message)
                self.assertIn("gros.bin", message)
                self.assertNotIn("recent.pdf", message)

    def test_tool_refuses_non_manual_or_implicit_search(self):
        ok, _ = recursive_file_tools.advanced_search_files(
            root_name="documents", explicit_user_command=False, source="manual"
        )
        self.assertFalse(ok)
        ok, _ = recursive_file_tools.advanced_search_files(
            root_name="documents", explicit_user_command=True, source="routine"
        )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
