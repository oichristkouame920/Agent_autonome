from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from backends.backend_manager import interpret
from app.agent import verify_explicit_list_directory
from app.response_style import decorate_response
import app.habit_tools as habit_tools
import app.windows_startup as windows_startup


class CoreIntentRoutingV1243Tests(unittest.TestCase):
    def _assert_action(self, text: str, action: str, target: str | None = None):
        result = interpret(text)
        self.assertEqual(result.get("routing"), "deterministic_preflight", text)
        actions = result.get("actions", [])
        self.assertTrue(actions, text)
        self.assertEqual(actions[0].get("action"), action, text)
        if target is not None:
            self.assertEqual(actions[0].get("target"), target, text)

    def test_downloads_are_core_read_only_intents(self):
        for text in (
            "liste mes telechargment",
            "montre mes téléchargement",
            "montre moi mes téléchargements",
            "affiche mes téléchargements",
        ):
            self._assert_action(text, "list_directory", "downloads")

    def test_downloads_explicit_proof_accepts_natural_and_typo_forms(self):
        self.assertTrue(verify_explicit_list_directory("liste mes telechargment", "downloads"))
        self.assertTrue(verify_explicit_list_directory("montre moi mes téléchargements", "downloads"))

    def test_process_shortcuts_are_deterministic(self):
        for text in ("Processus", "les processus", "montre moi les processus", "liste les processus"):
            self._assert_action(text, "read_process_info", "summary")

    def test_agent_state_is_deterministic(self):
        for text in ("quel est ton etat", "quel est ton statut", "montre moi ton état"):
            self._assert_action(text, "read_system_info", "agent")

    def test_identity_response_has_agent_emoji_not_file_emoji(self):
        result = interpret("qui est tu")
        self.assertEqual(result.get("routing"), "deterministic_preflight")
        rendered = decorate_response(result.get("reply", ""))
        self.assertTrue(rendered.startswith("🤖 "), rendered)

    def test_habit_tools_exports_status_reader(self):
        self.assertTrue(callable(getattr(habit_tools, "get_habits_by_status", None)))

    def test_windows_startup_vbs_has_no_bom(self):
        old_runtime = windows_startup.RUNTIME_DIR
        old_file = windows_startup.VBS_FILE
        with tempfile.TemporaryDirectory() as tmp:
            try:
                windows_startup.RUNTIME_DIR = Path(tmp)
                windows_startup.VBS_FILE = Path(tmp) / "start_agentlocal_background.vbs"
                path = windows_startup.ensure_startup_script()
                data = path.read_bytes()
                self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
                data.decode("ascii")
            finally:
                windows_startup.RUNTIME_DIR = old_runtime
                windows_startup.VBS_FILE = old_file


if __name__ == "__main__":
    unittest.main()
