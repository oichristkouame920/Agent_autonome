import json
import socket
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
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


class PowerNetworkParserV105Tests(unittest.TestCase):
    def assert_action(self, text, action, target):
        result = interpret(text)
        self.assertTrue(result.get("understood"), msg=(text, result))
        actions = result.get("actions", [])
        self.assertEqual(len(actions), 1, msg=(text, result))
        self.assertEqual(actions[0]["action"], action, msg=(text, result))
        self.assertEqual(actions[0]["target"], target, msg=(text, result))

    def test_battery_and_power_language(self):
        for text in (
            "il me reste combien de batterie ?",
            "ma batterie est à combien ?",
            "donne moi le niveau de la batterie",
        ):
            with self.subTest(text=text):
                self.assert_action(text, "read_power_info", "battery")
        self.assert_action("je suis branché au secteur ?", "read_power_info", "power")

    def test_network_status_and_ip_language(self):
        self.assert_action("mon réseau est actif ?", "read_network_info", "status")
        self.assert_action("quelle est mon IP locale ?", "read_network_info", "local_ip")
        self.assert_action("quelles connexions réseau sont actives ?", "read_network_info", "interfaces")

    def test_connection_speed_language(self):
        for text in (
            "quelle est la vitesse de ma connexion ?",
            "ma connexion est à combien ?",
            "teste la vitesse de ma connexion",
            "vitesse de mon wifi",
        ):
            with self.subTest(text=text):
                self.assert_action(text, "read_network_info", "link_speed")
        self.assert_action("quel est le débit réseau actuel ?", "read_network_info", "traffic_speed")
        self.assert_action("fais un speedtest", "read_network_info", "internet_speed")

    def test_negative_network_speed_commands_do_nothing(self):
        for text in (
            "teste pas la vitesse de ma connexion",
            "mesure pas le débit réseau actuel",
            "faut pas tester la vitesse de ma connexion",
        ):
            with self.subTest(text=text):
                result = interpret(text)
                self.assertTrue(result.get("understood"), msg=(text, result))
                self.assertEqual(result.get("actions"), [], msg=(text, result))


class PowerNetworkContractV105Tests(unittest.TestCase):
    def test_valid_contracts(self):
        for action in (
            {"schema_version": 1, "action": "read_power_info", "target": "battery"},
            {"schema_version": 1, "action": "read_power_info", "target": "power"},
            {"schema_version": 1, "action": "read_network_info", "target": "status"},
            {"schema_version": 1, "action": "read_network_info", "target": "local_ip"},
            {"schema_version": 1, "action": "read_network_info", "target": "interfaces"},
            {"schema_version": 1, "action": "read_network_info", "target": "link_speed"},
            {"schema_version": 1, "action": "read_network_info", "target": "traffic_speed"},
            {"schema_version": 1, "action": "read_network_info", "target": "internet_speed"},
        ):
            with self.subTest(action=action):
                self.assertEqual(agent.validate_action(action), (True, None))

    def test_invalid_contracts(self):
        self.assertFalse(agent.validate_action({"schema_version": 1, "action": "read_power_info", "target": "shutdown"})[0])
        self.assertFalse(agent.validate_action({"schema_version": 1, "action": "read_network_info", "target": "change_wifi"})[0])
        self.assertFalse(agent.validate_action({"schema_version": 1, "action": "read_network_info", "target": "link_speed", "params": {"external": True}})[0])

    def test_policies_are_read_only_and_manual(self):
        permissions = json.loads((ROOT / "config" / "permissions.json").read_text(encoding="utf-8"))
        power = permissions["power_information_policy"]
        network = permissions["network_information_policy"]
        self.assertTrue(power["read_only"])
        self.assertTrue(network["read_only"])
        self.assertFalse(power["allow_from_routine"])
        self.assertFalse(power["allow_from_habit"])
        self.assertFalse(network["allow_from_routine"])
        self.assertFalse(network["allow_from_habit"])
        self.assertFalse(network["allow_external_speed_test"])
        self.assertTrue(network["allow_passive_traffic_sample"])


class FakePsutil:
    POWER_TIME_UNKNOWN = -1
    POWER_TIME_UNLIMITED = -2

    @staticmethod
    def sensors_battery():
        return SimpleNamespace(percent=73.0, power_plugged=False, secsleft=7200)

    @staticmethod
    def net_if_stats():
        return {
            "Wi-Fi": SimpleNamespace(isup=True, speed=866.0, mtu=1500),
            "Loopback Pseudo-Interface": SimpleNamespace(isup=True, speed=0.0, mtu=65536),
        }

    @staticmethod
    def net_if_addrs():
        return {
            "Wi-Fi": [SimpleNamespace(family=socket.AF_INET, address="192.168.1.24")],
            "Loopback Pseudo-Interface": [SimpleNamespace(family=socket.AF_INET, address="127.0.0.1")],
        }

    _io_call = 0

    @classmethod
    def net_io_counters(cls, pernic=True):
        cls._io_call += 1
        if cls._io_call % 2:
            return {"Wi-Fi": SimpleNamespace(bytes_recv=1_000_000, bytes_sent=500_000)}
        return {"Wi-Fi": SimpleNamespace(bytes_recv=2_000_000, bytes_sent=750_000)}


class PowerNetworkToolV105Tests(unittest.TestCase):
    def test_battery_read_is_local_and_formatted(self):
        with patch("controlled_local_tools.psutil", FakePsutil):
            ok, message = controlled_local_tools.read_power_info(
                "battery", explicit_user_command=True, source="manual"
            )
        self.assertTrue(ok)
        self.assertIn("73%", message)
        self.assertIn("sur batterie", message)
        self.assertIn("2 h", message)

    def test_link_speed_uses_adapter_metadata_only(self):
        with patch("controlled_local_tools.psutil", FakePsutil):
            ok, message = controlled_local_tools.read_network_info(
                "link_speed", explicit_user_command=True, source="manual"
            )
        self.assertTrue(ok)
        self.assertIn("Wi-Fi", message)
        self.assertIn("866", message)
        self.assertIn("pas du débit Internet réel", message)

    def test_local_ip(self):
        with patch("controlled_local_tools.psutil", FakePsutil):
            ok, message = controlled_local_tools.read_network_info(
                "local_ip", explicit_user_command=True, source="manual"
            )
        self.assertTrue(ok)
        self.assertIn("192.168.1.24", message)

    def test_passive_traffic_measurement_generates_no_test_traffic(self):
        FakePsutil._io_call = 0
        with patch("controlled_local_tools.psutil", FakePsutil), patch("controlled_local_tools.time.sleep", return_value=None):
            ok, message = controlled_local_tools.read_network_info(
                "traffic_speed", explicit_user_command=True, source="manual"
            )
        self.assertTrue(ok)
        self.assertIn("Aucun trafic de test n'a été généré", message)

    def test_real_internet_speedtest_is_explicitly_not_enabled(self):
        with patch("controlled_local_tools.psutil", FakePsutil):
            ok, message = controlled_local_tools.read_network_info(
                "internet_speed", explicit_user_command=True, source="manual"
            )
        self.assertTrue(ok)
        self.assertIn("n'est pas activé", message)
        self.assertIn("serveur externe", message)

    def test_routine_is_rejected_before_reading_network(self):
        with patch("controlled_local_tools._network_active_interfaces") as network:
            ok, _ = controlled_local_tools.read_network_info(
                "link_speed", explicit_user_command=True, source="routine"
            )
        self.assertFalse(ok)
        network.assert_not_called()


class PowerNetworkRoutingExecutionV105Tests(unittest.TestCase):
    def test_speed_bypasses_llama(self):
        class DummyLlama:
            calls = 0
            @classmethod
            def interpret(cls, _message):
                cls.calls += 1
                return {"schema_version": 1, "backend": "llama", "understood": False, "actions": []}

        original = backend_manager.select_backend
        try:
            backend_manager.select_backend = lambda: (True, "llama", DummyLlama, None)
            result = backend_manager.interpret("quelle est la vitesse de ma connexion ?")
            self.assertEqual(result.get("backend"), "deterministic")
            self.assertEqual(result.get("routing"), "deterministic_preflight")
            self.assertEqual(result["actions"][0]["action"], "read_network_info")
            self.assertEqual(DummyLlama.calls, 0)
        finally:
            backend_manager.select_backend = original

    @patch("agent.controlled_read_network_info", return_value=(True, "ok"))
    def test_exact_proof_required(self, tool):
        action = {"schema_version": 1, "action": "read_network_info", "target": "link_speed"}
        self.assertEqual(agent.execute_action(action, user_message="quelle est la vitesse de ma connexion ?"), (True, "ok"))
        tool.assert_called_once_with("link_speed", explicit_user_command=True, source="manual")

    @patch("agent.controlled_read_network_info", return_value=(True, "ok"))
    def test_contract_swap_is_rejected(self, tool):
        action = {"schema_version": 1, "action": "read_network_info", "target": "local_ip"}
        ok, _ = agent.execute_action(action, user_message="quelle est la vitesse de ma connexion ?")
        self.assertFalse(ok)
        tool.assert_not_called()


if __name__ == "__main__":
    unittest.main()
