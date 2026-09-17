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
from backends import backend_manager
from backends.deterministic_backend import interpret


class AudioParserV104Tests(unittest.TestCase):
    def assert_action(self, text, action, params=None):
        result = interpret(text)
        self.assertTrue(result.get("understood"), msg=(text, result))
        actions = result.get("actions", [])
        self.assertEqual(len(actions), 1, msg=(text, result))
        self.assertEqual(actions[0]["action"], action, msg=(text, result))
        self.assertEqual(actions[0]["target"], "master", msg=(text, result))
        if params is not None:
            self.assertEqual(actions[0].get("params"), params, msg=(text, result))

    def test_read_volume_language(self):
        for text in (
            "quel est le volume ?",
            "le son est à combien ?",
            "donne moi le niveau du son",
            "état du volume",
        ):
            with self.subTest(text=text):
                self.assert_action(text, "read_audio_state")

    def test_set_exact_volume(self):
        self.assert_action("mets le volume à 30%", "set_audio_volume", {"percent": 30})
        self.assert_action("règle le son sur 55", "set_audio_volume", {"percent": 55})
        self.assert_action("baisse le volume à 20%", "set_audio_volume", {"percent": 20})

    def test_relative_volume(self):
        self.assert_action("monte le son", "change_audio_volume", {"delta": 5})
        self.assert_action("augmente un peu le volume", "change_audio_volume", {"delta": 5})
        self.assert_action("monte le son de 10%", "change_audio_volume", {"delta": 10})
        self.assert_action("baisse le volume", "change_audio_volume", {"delta": -5})
        self.assert_action("diminue le son de 15%", "change_audio_volume", {"delta": -15})

    def test_mute_and_unmute(self):
        self.assert_action("coupe le son", "set_audio_mute", {"muted": True})
        self.assert_action("mets le son en sourdine", "set_audio_mute", {"muted": True})
        self.assert_action("remets le son", "set_audio_mute", {"muted": False})
        self.assert_action("enlève le mode muet", "set_audio_mute", {"muted": False})

    def test_negative_audio_commands_do_nothing(self):
        for text in (
            "monte pas le son",
            "baisse pas le volume",
            "coupe pas le son",
            "faut pas couper le son",
            "règle pas le volume à 40%",
        ):
            with self.subTest(text=text):
                result = interpret(text)
                self.assertTrue(result.get("understood"), msg=(text, result))
                self.assertEqual(result.get("actions"), [], msg=(text, result))

    def test_out_of_range_or_large_relative_change_is_not_parsed(self):
        self.assertFalse(interpret("mets le volume à 150%").get("actions", []))
        self.assertFalse(interpret("monte le son de 40%").get("actions", []))


class AudioContractV104Tests(unittest.TestCase):
    def test_valid_contracts(self):
        for action in (
            {"schema_version": 1, "action": "read_audio_state", "target": "master"},
            {"schema_version": 1, "action": "set_audio_volume", "target": "master", "params": {"percent": 50}},
            {"schema_version": 1, "action": "change_audio_volume", "target": "master", "params": {"delta": -5}},
            {"schema_version": 1, "action": "set_audio_mute", "target": "master", "params": {"muted": True}},
        ):
            with self.subTest(action=action):
                self.assertEqual(agent.validate_action(action), (True, None))

    def test_invalid_contracts(self):
        invalid = (
            {"schema_version": 1, "action": "read_audio_state", "target": "microphone"},
            {"schema_version": 1, "action": "set_audio_volume", "target": "master", "params": {"percent": 101}},
            {"schema_version": 1, "action": "change_audio_volume", "target": "master", "params": {"delta": 30}},
            {"schema_version": 1, "action": "set_audio_mute", "target": "master", "params": {"muted": "yes"}},
        )
        for action in invalid:
            with self.subTest(action=action):
                self.assertFalse(agent.validate_action(action)[0])

    def test_manual_only_policy(self):
        permissions = json.loads((ROOT / "config" / "permissions.json").read_text(encoding="utf-8"))
        policy = permissions["audio_control_policy"]
        self.assertTrue(policy["enabled"])
        self.assertTrue(policy["require_explicit_user_command"])
        self.assertFalse(policy["allow_from_routine"])
        self.assertFalse(policy["allow_from_habit"])
        self.assertFalse(policy["allow_automatic_change"])
        self.assertEqual(policy["maximum_relative_change_percent"], 25)


class AudioRoutingExecutionV104Tests(unittest.TestCase):
    def test_audio_bypasses_llama(self):
        class DummyLlama:
            calls = 0
            @classmethod
            def interpret(cls, _message):
                cls.calls += 1
                return {"schema_version": 1, "backend": "llama", "understood": False, "actions": []}

        original = backend_manager.select_backend
        try:
            backend_manager.select_backend = lambda: (True, "llama", DummyLlama, None)
            result = backend_manager.interpret("mets le volume à 30%")
            self.assertEqual(result.get("backend"), "deterministic")
            self.assertEqual(result.get("routing"), "deterministic_preflight")
            self.assertEqual(result["actions"][0]["action"], "set_audio_volume")
            self.assertEqual(DummyLlama.calls, 0)
        finally:
            backend_manager.select_backend = original

    @patch("agent.controlled_set_audio_volume", return_value=(True, "ok"))
    def test_exact_proof_required(self, tool):
        action = {"schema_version": 1, "action": "set_audio_volume", "target": "master", "params": {"percent": 30}}
        self.assertEqual(agent.execute_action(action, user_message="mets le volume à 30%"), (True, "ok"))
        tool.assert_called_once_with(30, explicit_user_command=True, source="manual")

    @patch("agent.controlled_set_audio_volume", return_value=(True, "ok"))
    def test_contract_swap_is_rejected(self, tool):
        action = {"schema_version": 1, "action": "set_audio_volume", "target": "master", "params": {"percent": 80}}
        ok, _ = agent.execute_action(action, user_message="mets le volume à 30%")
        self.assertFalse(ok)
        tool.assert_not_called()

    def test_tool_rejects_routine_before_windows_audio(self):
        with patch("controlled_local_tools._with_default_audio_endpoint") as endpoint:
            ok, _ = controlled_local_tools.set_audio_volume(
                30, explicit_user_command=True, source="routine"
            )
            self.assertFalse(ok)
            endpoint.assert_not_called()

    def test_tool_policy_limits_relative_changes(self):
        with patch("controlled_local_tools._with_default_audio_endpoint") as endpoint:
            ok, message = controlled_local_tools.change_audio_volume(
                30, explicit_user_command=True, source="manual"
            )
            self.assertFalse(ok)
            self.assertIn("25%", message)
            endpoint.assert_not_called()

    def test_tool_formats_state_without_windows_dependency(self):
        with patch("controlled_local_tools._with_default_audio_endpoint", return_value=(True, {"percent": 42, "muted": False})):
            self.assertEqual(
                controlled_local_tools.read_audio_state(explicit_user_command=True, source="manual"),
                (True, "Volume principal : 42% — son actif."),
            )


if __name__ == "__main__":
    unittest.main()
