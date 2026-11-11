import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

import runtime_resilience
from backends import backend_manager


class ResilienceV113Tests(unittest.TestCase):
    def setUp(self):
        backend_manager._llama_consecutive_failures = 0
        backend_manager._llama_disabled_until = 0.0

    def tearDown(self):
        backend_manager._llama_consecutive_failures = 0
        backend_manager._llama_disabled_until = 0.0

    def test_health_report_has_no_critical_error_on_reference_project(self):
        report = runtime_resilience.startup_health_report()
        self.assertIn(report["overall"], {"healthy", "degraded"})
        self.assertEqual(report["critical_count"], 0)

    def test_llama_circuit_opens_after_two_failures(self):
        backend_manager._record_llama_failure(RuntimeError("x"))
        self.assertFalse(backend_manager._llama_circuit_state()["disabled"])
        backend_manager._record_llama_failure(RuntimeError("x"))
        state = backend_manager._llama_circuit_state()
        self.assertTrue(state["disabled"])
        self.assertGreater(state["retry_after_seconds"], 0)

    def test_llama_success_resets_circuit(self):
        backend_manager._record_llama_failure(RuntimeError("x"))
        backend_manager._record_llama_failure(RuntimeError("x"))
        backend_manager._record_llama_success()
        state = backend_manager._llama_circuit_state()
        self.assertFalse(state["disabled"])
        self.assertEqual(state["failures"], 0)

    @patch("backends.backend_manager._llama_session_available", return_value=False)
    @patch("backends.backend_manager.get_backend_config")
    def test_auto_mode_falls_back_when_llama_circuit_is_open(self, config, _session):
        config.return_value = {"mode": "auto", "preferred": "llama", "fallback": "deterministic"}
        ok, name, module, warning = backend_manager.select_backend()
        self.assertTrue(ok)
        self.assertEqual(name, "deterministic")
        self.assertIsNotNone(module)
        self.assertIsNotNone(warning)

    def test_logger_is_bounded_rotating_logger_or_safe_fallback(self):
        logger = runtime_resilience.get_logger()
        self.assertIsNotNone(logger)
        # Le test ne depend pas de la possibilite d'ecrire sur le disque.
        runtime_resilience.log_event("info", "test", "evenement technique")


if __name__ == "__main__":
    unittest.main()
