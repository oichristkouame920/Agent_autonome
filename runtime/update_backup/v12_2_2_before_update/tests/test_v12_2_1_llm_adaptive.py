import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from backends import llama_backend
import upgrade_llm_config_v12_2_1 as upgrader


class AdaptiveLlmV1221Tests(unittest.TestCase):
    def tearDown(self):
        llama_backend.stop_warm_server()
        llama_backend._RUNTIME_PROBE_CACHE.clear()
        llama_backend._LAST_RUNTIME_PROBE = {"state": "not_run", "detail": None, "elapsed_seconds": None}

    def test_reasoning_markers_are_never_exposed_before_json(self):
        raw = '[Start thinking]\nThinking Process:\nsecret\n{"type":"conversation","reply":"Bonjour","confidence":0.9}'
        cleaned = llama_backend._strip_hidden_reasoning(raw)
        self.assertEqual(cleaned, '{"type":"conversation","reply":"Bonjour","confidence":0.9}')
        self.assertNotIn("Thinking Process", cleaned)

    def test_think_xml_is_removed(self):
        raw = '<think>secret reasoning</think>{"type":"conversation","reply":"OK","confidence":0.9}'
        self.assertEqual(
            llama_backend._strip_hidden_reasoning(raw),
            '{"type":"conversation","reply":"OK","confidence":0.9}',
        )

    def test_probe_retries_after_fast_timeout(self):
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "llama-cli.exe"
            exe.write_bytes(b"fake")
            timeout = subprocess.TimeoutExpired(cmd=[str(exe), "--version"], timeout=10)
            ok_result = subprocess.CompletedProcess([str(exe), "--version"], 0, "version ok", "")
            with mock.patch.object(llama_backend, "_is_windows_runtime", return_value=True), \
                 mock.patch.object(llama_backend, "_probe_runtime_once", side_effect=[timeout, ok_result]) as run:
                ok, reason = llama_backend.probe_llama_runtime(exe, 10, 30)
            self.assertTrue(ok)
            self.assertIn("demarrage lent", reason)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(llama_backend._LAST_RUNTIME_PROBE["state"], "slow_ready")

    def test_warm_server_is_loopback_only(self):
        model = {
            "llama_server_path": Path("llama-server.exe"),
            "path": Path("model.gguf"),
            "context_size": 2048,
            "threads": 4,
            "mmproj_path": None,
        }
        args = llama_backend._server_args(model, 18181)
        host_index = args.index("--host") + 1
        self.assertEqual(args[host_index], "127.0.0.1")
        self.assertNotIn("0.0.0.0", args)

    def test_low_ram_disables_warm_mode_without_disabling_llama(self):
        model = {
            "warm_server_enabled": True,
            "warm_server_local_only": True,
            "llama_server_path": Path("llama-server.exe"),
            "warm_server_min_available_ram_mb": 850,
        }
        with mock.patch.object(llama_backend, "_is_windows_runtime", return_value=True), \
             mock.patch.object(Path, "is_file", return_value=True), \
             mock.patch.object(llama_backend, "_available_ram_mb", return_value=400):
            ok, reason = llama_backend._warm_server_eligible(model)
        self.assertFalse(ok)
        self.assertIn("RAM", reason)

    def test_adaptive_runner_falls_back_to_cli(self):
        model = {"warm_server_enabled": False}
        with mock.patch.object(llama_backend, "_run_llama_cli", return_value='{"type":"conversation","reply":"OK","confidence":1}') as cli:
            output, engine = llama_backend._run_llama_adaptive("x", model)
        self.assertEqual(engine, "llama-cli")
        self.assertIn('"reply":"OK"', output)
        cli.assert_called_once()

    def test_config_upgrade_preserves_model_and_adds_warm_settings(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "models.json"
            path.write_text(json.dumps({
                "schema_version": 2,
                "active_model": "custom",
                "runtime": {"llama_cli": "my/llama-cli.exe"},
                "models": {"custom": {"file": "models/custom.gguf"}},
            }), encoding="utf-8")
            self.assertTrue(upgrader.upgrade(path))
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["active_model"], "custom")
            self.assertEqual(data["models"]["custom"]["file"], "models/custom.gguf")
            self.assertEqual(data["runtime"]["llama_cli"], "my/llama-cli.exe")
            self.assertTrue(data["runtime"]["warm_server_enabled"])
            self.assertTrue(data["runtime"]["warm_server_local_only"])
            self.assertEqual(data["runtime"]["probe_slow_timeout_seconds"], 30)


if __name__ == "__main__":
    unittest.main()
