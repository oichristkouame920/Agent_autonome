import json
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
import controlled_local_tools
from backends import backend_manager
from backends.deterministic_backend import interpret


class ScreenshotParserV103Tests(unittest.TestCase):
    def assert_capture(self, text, target):
        result = interpret(text)
        self.assertTrue(result.get("understood"), msg=(text, result))
        actions = result.get("actions", [])
        self.assertEqual(len(actions), 1, msg=(text, result))
        self.assertEqual(actions[0]["action"], "take_screenshot", msg=(text, result))
        self.assertEqual(actions[0]["target"], target, msg=(text, result))

    def test_full_screen_phrases(self):
        for text in (
            "fais une capture d'écran",
            "fais moi une capture de l'écran",
            "capture tout l'écran",
            "capture mon écran",
            "prends une capture de tout l'écran",
            "fais moi un screenshot",
        ):
            with self.subTest(text=text):
                self.assert_capture(text, "full_screen")

    def test_active_window_phrases(self):
        for text in (
            "capture la fenêtre active",
            "fais une capture de la fenêtre active",
            "capture cette fenêtre",
            "screenshot de la fenêtre active",
        ):
            with self.subTest(text=text):
                self.assert_capture(text, "active_window")

    def test_negative_capture_does_nothing(self):
        for text in (
            "fais pas de capture d'écran",
            "capture pas mon écran",
            "faut pas faire de capture d'écran",
        ):
            with self.subTest(text=text):
                result = interpret(text)
                self.assertTrue(result.get("understood"), msg=(text, result))
                self.assertEqual(result.get("actions"), [], msg=(text, result))


class ScreenshotContractV103Tests(unittest.TestCase):
    def test_contract_allows_only_two_modes(self):
        for target in ("full_screen", "active_window"):
            action = {"schema_version": 1, "action": "take_screenshot", "target": target}
            self.assertEqual(agent.validate_action(action), (True, None))

        action = {"schema_version": 1, "action": "take_screenshot", "target": "all_windows"}
        self.assertFalse(agent.validate_action(action)[0])

    def test_extra_params_are_rejected(self):
        action = {
            "schema_version": 1,
            "action": "take_screenshot",
            "target": "full_screen",
            "params": {"upload": True},
        }
        self.assertFalse(agent.validate_action(action)[0])

    def test_explicit_proof_cannot_swap_mode(self):
        full = {"schema_version": 1, "action": "take_screenshot", "target": "full_screen"}
        active = {"schema_version": 1, "action": "take_screenshot", "target": "active_window"}
        self.assertTrue(agent.verify_explicit_controlled_action("capture tout l'écran", full)[0])
        self.assertFalse(agent.verify_explicit_controlled_action("capture tout l'écran", active)[0])

    def test_policy_is_manual_only(self):
        permissions = json.loads((ROOT / "config" / "permissions.json").read_text(encoding="utf-8"))
        policy = permissions["screenshot_policy"]
        self.assertTrue(policy["enabled"])
        self.assertTrue(policy["require_explicit_user_command"])
        self.assertFalse(policy["allow_from_routine"])
        self.assertFalse(policy["allow_from_habit"])
        self.assertFalse(policy["allow_automatic_capture"])
        self.assertEqual(policy["format"], "png")
        self.assertEqual(policy["save_root"], "pictures")


class ScreenshotRoutingV103Tests(unittest.TestCase):
    def test_capture_uses_deterministic_preflight(self):
        class DummyLlama:
            calls = 0

            @classmethod
            def interpret(cls, _message):
                cls.calls += 1
                return {"schema_version": 1, "backend": "llama", "understood": False, "actions": []}

        original = backend_manager.select_backend
        try:
            backend_manager.select_backend = lambda: (True, "llama", DummyLlama, None)
            result = backend_manager.interpret("capture tout l'écran")
            self.assertEqual(result.get("backend"), "deterministic")
            self.assertEqual(result.get("routing"), "deterministic_preflight")
            self.assertEqual(result["actions"][0]["action"], "take_screenshot")
            self.assertEqual(DummyLlama.calls, 0)
        finally:
            backend_manager.select_backend = original


class ScreenshotExecutionV103Tests(unittest.TestCase):
    @patch("agent.controlled_take_screenshot", return_value=(True, "capture ok"))
    def test_agent_executes_only_matching_manual_capture(self, tool):
        action = {"schema_version": 1, "action": "take_screenshot", "target": "full_screen"}
        self.assertEqual(
            agent.execute_action(action, user_message="capture tout l'écran"),
            (True, "capture ok"),
        )
        tool.assert_called_once_with("full_screen", explicit_user_command=True, source="manual")

    @patch("agent.controlled_take_screenshot", return_value=(True, "capture ok"))
    def test_agent_rejects_mode_swap(self, tool):
        action = {"schema_version": 1, "action": "take_screenshot", "target": "active_window"}
        ok, _ = agent.execute_action(action, user_message="capture tout l'écran")
        self.assertFalse(ok)
        tool.assert_not_called()

    def test_tool_rejects_routine_before_os_capture(self):
        with patch("controlled_local_tools._screenshot_rect") as rect:
            ok, _ = controlled_local_tools.take_screenshot(
                "full_screen", explicit_user_command=True, source="routine"
            )
            self.assertFalse(ok)
            rect.assert_not_called()


    def test_png_writer_uses_standard_png_without_dependency(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "test.png"
            # 2x1 pixels en BGRA : rouge puis vert.
            controlled_local_tools._write_bgra_png(
                output, 2, 1, bytes([0, 0, 255, 0, 0, 255, 0, 0])
            )
            data = output.read_bytes()
            self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertIn(b"IHDR", data)
            self.assertIn(b"IDAT", data)
            self.assertTrue(data.endswith(b"IEND\xaeB`\x82"))

    def test_tool_saves_only_under_authorized_pictures_root(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch("controlled_local_tools._screenshot_rect", return_value=((0, 0, 800, 600), None)), \
                 patch("controlled_local_tools.resolve_allowed_root", return_value=root), \
                 patch("controlled_local_tools._capture_windows_rect_to_png", return_value=(True, None)) as capture:
                ok, message = controlled_local_tools.take_screenshot(
                    "full_screen", explicit_user_command=True, source="manual"
                )
                self.assertTrue(ok, msg=message)
                args = capture.call_args.args
                destination = args[4]
                self.assertEqual(destination.suffix.lower(), ".png")
                self.assertTrue(str(destination).startswith(str(root)))
                self.assertIn("Captures AgentLocal", str(destination))


if __name__ == "__main__":
    unittest.main()
