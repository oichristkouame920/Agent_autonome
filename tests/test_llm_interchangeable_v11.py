import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backends import backend_manager, llama_backend


class LlmInterchangeableV11Tests(unittest.TestCase):
    def test_llama_backend_module_contract(self):
        self.assertTrue(callable(llama_backend.interpret))
        self.assertTrue(callable(llama_backend.availability))
        self.assertTrue(callable(llama_backend.get_status))

    def test_missing_model_means_runtime_unavailable(self):
        ok, reason = llama_backend.availability()
        self.assertFalse(ok)
        self.assertTrue(reason)

    def test_backend_manager_falls_back_when_model_missing(self):
        ok, name, module, warning = backend_manager.select_backend()
        self.assertTrue(ok)
        self.assertEqual(name, "deterministic")
        self.assertIsNotNone(module)
        self.assertIn("Fallback", warning or "")

    def test_llm_command_is_revalidated_by_deterministic_backend(self):
        fake = '{"type":"command","canonical_command":"ouvre VS Code","confidence":0.94}'
        with patch.object(llama_backend, "availability", return_value=(True, None)), \
             patch.object(llama_backend, "get_active_model_config") as model_config, \
             patch.object(llama_backend, "_run_llama_cli", return_value=fake):
            model_config.return_value = (
                "test_model",
                {
                    "minimum_confidence": 0.72,
                    "llama_cli_path": Path("llama-cli.exe"),
                    "path": Path("model.gguf"),
                    "context_size": 2048,
                    "threads": 4,
                    "max_tokens": 128,
                    "temperature": 0.0,
                    "timeout_seconds": 30,
                },
                {},
            )
            result = llama_backend.interpret("je voudrais utiliser mon éditeur de code")
        self.assertTrue(result["understood"])
        self.assertEqual(result["actions"][0]["action"], "open_application")
        self.assertEqual(result["actions"][0]["target"], "vscode")
        self.assertEqual(result["routing"], "llm_normalized_then_deterministic")
        self.assertEqual(result["active_model"], "test_model")

    def test_low_confidence_never_creates_action(self):
        fake = '{"type":"command","canonical_command":"ouvre VS Code","confidence":0.31}'
        with patch.object(llama_backend, "availability", return_value=(True, None)), \
             patch.object(llama_backend, "get_active_model_config") as model_config, \
             patch.object(llama_backend, "_run_llama_cli", return_value=fake):
            model_config.return_value = (
                "test_model",
                {
                    "minimum_confidence": 0.72,
                    "llama_cli_path": Path("llama-cli.exe"),
                    "path": Path("model.gguf"),
                    "context_size": 2048,
                    "threads": 4,
                    "max_tokens": 128,
                    "temperature": 0.0,
                    "timeout_seconds": 30,
                },
                {},
            )
            result = llama_backend.interpret("fais le truc")
        self.assertEqual(result["actions"], [])
        self.assertTrue(result.get("conversation"))

    def test_forbidden_shell_canonical_command_is_refused(self):
        fake = '{"type":"command","canonical_command":"ouvre PowerShell","confidence":0.99}'
        with patch.object(llama_backend, "availability", return_value=(True, None)), \
             patch.object(llama_backend, "get_active_model_config") as model_config, \
             patch.object(llama_backend, "_run_llama_cli", return_value=fake):
            model_config.return_value = (
                "test_model",
                {
                    "minimum_confidence": 0.72,
                    "llama_cli_path": Path("llama-cli.exe"),
                    "path": Path("model.gguf"),
                    "context_size": 2048,
                    "threads": 4,
                    "max_tokens": 128,
                    "temperature": 0.0,
                    "timeout_seconds": 30,
                },
                {},
            )
            result = llama_backend.interpret("ouvre le terminal")
        self.assertEqual(result["actions"], [])
        self.assertEqual(result["llm_type"], "refusal")


if __name__ == "__main__":
    unittest.main()
