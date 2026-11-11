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

from backends.deterministic_backend import interpret
import windows_tools
import agent


class WindowManagementParserTests(unittest.TestCase):
    def assert_window_action(self, message, target, operation, count=1):
        result = interpret(message)
        self.assertTrue(result.get("understood"), msg=(message, result))
        actions = result.get("actions", [])
        self.assertEqual(len(actions), count, msg=(message, result))
        self.assertEqual(actions[0].get("action"), "manage_window", msg=result)
        self.assertEqual(actions[0].get("target"), target, msg=result)
        self.assertEqual(actions[0].get("params", {}).get("operation"), operation, msg=result)
        return actions

    def test_snap_left(self):
        self.assert_window_action("Mets VS Code à gauche", "vscode", "snap_left")

    def test_snap_right(self):
        self.assert_window_action("Place Edge à droite", "edge", "snap_right")

    def test_polite_snap_left(self):
        self.assert_window_action("Peux-tu mettre VS Code à gauche ?", "vscode", "snap_left")

    def test_maximize(self):
        self.assert_window_action("Agrandis Word", "word", "maximize")

    def test_minimize(self):
        self.assert_window_action("Réduis Excel", "excel", "minimize")

    def test_restore(self):
        self.assert_window_action("Restaure PowerPoint", "powerpoint", "restore")

    def test_focus(self):
        self.assert_window_action("Mets Outlook au premier plan", "outlook", "focus")

    def test_focus_natural(self):
        self.assert_window_action("Passe sur VS Code", "vscode", "focus")

    def test_two_explicit_windows(self):
        actions = self.assert_window_action(
            "Mets VS Code à gauche et Edge à droite",
            "vscode",
            "snap_left",
            count=2,
        )
        self.assertEqual(actions[1]["action"], "manage_window")
        self.assertEqual(actions[1]["target"], "edge")
        self.assertEqual(actions[1]["params"]["operation"], "snap_right")

    def test_no_global_window_action(self):
        result = interpret("Réduis toutes les fenêtres sauf VS Code")
        self.assertFalse(result.get("understood"), msg=result)
        self.assertEqual(result.get("actions"), [])

    def test_no_automatic_side_choice(self):
        result = interpret("Mets VS Code et Edge côte à côte")
        self.assertFalse(result.get("understood"), msg=result)
        self.assertEqual(result.get("actions"), [])

    def test_file_move_is_not_window_management(self):
        result = interpret("Mets rapport.pdf dans Archives")
        self.assertTrue(result.get("understood"), msg=result)
        self.assertEqual(result["actions"][0]["action"], "move_file_within_root")

    def test_unknown_target_is_not_managed(self):
        result = interpret("Agrandis PowerShell")
        self.assertFalse(result.get("understood"), msg=result)


class WindowManagementContractTests(unittest.TestCase):
    def setUp(self):
        self.action = {
            "schema_version": 1,
            "action": "manage_window",
            "target": "vscode",
            "params": {"operation": "snap_left"},
        }

    def test_contract_is_valid(self):
        self.assertEqual(agent.validate_action(self.action), (True, None))

    def test_unknown_operation_is_rejected(self):
        bad = dict(self.action)
        bad["params"] = {"operation": "move_anywhere"}
        valid, _ = agent.validate_action(bad)
        self.assertFalse(valid)

    def test_extra_parameters_are_rejected(self):
        bad = dict(self.action)
        bad["params"] = {"operation": "snap_left", "x": 10}
        valid, _ = agent.validate_action(bad)
        self.assertFalse(valid)

    def test_explicit_proof_checks_operation(self):
        ok, _ = agent.verify_explicit_interactive_action(
            "Mets VS Code à gauche",
            "manage_window",
            "vscode",
            params={"operation": "snap_left"},
        )
        self.assertTrue(ok)

        ok, _ = agent.verify_explicit_interactive_action(
            "Mets VS Code à gauche",
            "manage_window",
            "vscode",
            params={"operation": "snap_right"},
        )
        self.assertFalse(ok)

    def test_permissions_are_manual_only(self):
        policy = windows_tools.get_window_management_policy()
        self.assertTrue(policy["enabled"])
        self.assertTrue(policy["require_explicit_user_command"])
        self.assertFalse(policy["allow_from_routine"])
        self.assertFalse(policy["allow_from_habit"])
        self.assertFalse(policy["auto_launch_missing_application"])
        self.assertTrue(policy["require_single_visible_window"])

    def test_manual_without_explicit_command_is_rejected(self):
        ok, _ = windows_tools.is_window_management_allowed(
            "vscode", "snap_left", source="manual", explicit_user_command=False
        )
        self.assertFalse(ok)

    def test_routine_window_management_is_rejected(self):
        ok, _ = windows_tools.is_window_management_allowed(
            "vscode", "snap_left", source="routine", explicit_user_command=True
        )
        self.assertFalse(ok)

    def test_habit_window_management_is_rejected(self):
        ok, _ = windows_tools.is_window_management_allowed(
            "vscode", "snap_left", source="habit", explicit_user_command=True
        )
        self.assertFalse(ok)

    @patch("agent.manage_application_window", return_value=(True, "ok"))
    def test_agent_executes_only_explicit_matching_operation(self, manage):
        result = agent.execute_action(
            self.action,
            user_message="Mets VS Code à gauche",
        )
        self.assertEqual(result, (True, "ok"))
        manage.assert_called_once_with(
            "vscode",
            "snap_left",
            source="manual",
            explicit_user_command=True,
        )

    @patch("agent.manage_application_window", return_value=(True, "should not run"))
    def test_agent_rejects_backend_invented_side(self, manage):
        wrong = dict(self.action)
        wrong["params"] = {"operation": "snap_right"}
        ok, _ = agent.execute_action(
            wrong,
            user_message="Mets VS Code à gauche",
        )
        self.assertFalse(ok)
        manage.assert_not_called()

    @patch("windows_tools.get_windows_info", return_value={"supported": True})
    @patch("windows_tools.get_application_window_records", return_value=[])
    def test_missing_app_is_not_auto_launched(self, _records, _windows):
        ok, message = windows_tools.manage_application_window(
            "vscode", "snap_left", source="manual", explicit_user_command=True
        )
        self.assertFalse(ok)
        self.assertIn("Aucune fenêtre visible", message)

    @patch("windows_tools.get_windows_info", return_value={"supported": True})
    @patch("windows_tools.get_application_window_records")
    def test_multiple_windows_are_not_chosen_automatically(self, records, _windows):
        records.return_value = [
            {"hwnd": 1, "window_pid": 10, "window_process_create_time": 1.0},
            {"hwnd": 2, "window_pid": 11, "window_process_create_time": 2.0},
        ]
        ok, message = windows_tools.manage_application_window(
            "vscode", "maximize", source="manual", explicit_user_command=True
        )
        self.assertFalse(ok)
        self.assertIn("Plusieurs fenêtres", message)

    @patch("windows_tools.get_windows_info", return_value={"supported": True})
    @patch("windows_tools._apply_window_operation", return_value=(True, "Fenêtre agrandie."))
    @patch("windows_tools.is_expected_application_window", return_value=True)
    @patch("windows_tools.get_application_window_records")
    def test_single_window_can_be_managed(self, records, expected, apply_operation, _windows):
        records.return_value = [
            {"hwnd": 100, "window_pid": 10, "window_process_create_time": 1.0},
        ]
        ok, message = windows_tools.manage_application_window(
            "vscode", "maximize", source="manual", explicit_user_command=True
        )
        self.assertTrue(ok)
        self.assertIn("Visual Studio Code", message)
        expected.assert_called_once()
        apply_operation.assert_called_once_with(100, "maximize")

    @patch("windows_tools.get_windows_info", return_value={"supported": True})
    @patch("windows_tools._apply_window_operation")
    @patch("windows_tools.is_expected_application_window", return_value=False)
    @patch("windows_tools.get_application_window_records")
    def test_window_is_revalidated_before_change(self, records, expected, apply_operation, _windows):
        records.return_value = [
            {"hwnd": 100, "window_pid": 10, "window_process_create_time": 1.0},
        ]
        ok, message = windows_tools.manage_application_window(
            "vscode", "maximize", source="manual", explicit_user_command=True
        )
        self.assertFalse(ok)
        self.assertIn("fenêtre a changé", message)
        apply_operation.assert_not_called()


if __name__ == "__main__":
    unittest.main()
