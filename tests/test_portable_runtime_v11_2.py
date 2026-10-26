import json
import sys
import unittest
from pathlib import Path, PureWindowsPath
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import portable_runtime
import project_paths
from backends import llama_backend


class PortableRuntimeV112Tests(unittest.TestCase):
    def test_new_runtime_paths_follow_project_root(self):
        self.assertEqual(project_paths.get_project_path("runtime"), ROOT / "runtime")
        self.assertEqual(project_paths.get_project_path("python_runtime"), ROOT / "runtime" / "python")
        self.assertEqual(project_paths.get_project_path("wheels"), ROOT / "vendor" / "wheels")

    def test_runtime_config_is_relative(self):
        data = json.loads((ROOT / "config" / "runtime.json").read_text(encoding="utf-8"))
        for section in ("python", "llama"):
            for key, value in data[section].items():
                if not isinstance(value, str) or key.endswith("args"):
                    continue
                if "/" not in value and "\\" not in value:
                    continue
                self.assertFalse(Path(value).is_absolute(), value)
                self.assertFalse(PureWindowsPath(value).is_absolute(), value)
                self.assertFalse(bool(PureWindowsPath(value).drive), value)

    def test_models_config_supports_portable_companions(self):
        config = llama_backend.load_models_config()
        model = config["models"][config["active_model"]]
        self.assertIn("companions", model)
        self.assertIsInstance(model["companions"], list)

    def test_absolute_model_companion_is_rejected(self):
        fake = {
            "schema_version": 2,
            "active_model": "x",
            "runtime": {"llama_cli": "tools/llama.cpp/llama-cli.exe"},
            "models": {
                "x": {
                    "file": "models/x.gguf",
                    "companions": [r"C:\\Temp\\mmproj.gguf"],
                }
            },
        }
        with patch.object(llama_backend, "load_models_config", return_value=fake):
            with self.assertRaises(ValueError):
                llama_backend.get_active_model_config()

    def test_python_portable_is_preferred_to_venv(self):
        candidates = portable_runtime.python_candidates()
        self.assertGreaterEqual(len(candidates), 2)
        self.assertEqual(candidates[0].mode, "portable")
        self.assertEqual(candidates[1].mode, "venv")

    def test_llama_runtime_paths_are_relative_to_root(self):
        runtime_dir, executable, _, _ = portable_runtime.llama_runtime_paths()
        self.assertEqual(runtime_dir, ROOT / "tools" / "llama.cpp")
        self.assertEqual(executable, ROOT / "tools" / "llama.cpp" / "llama-cli.exe")

    def test_launcher_does_not_embed_old_machine_path(self):
        content = (ROOT / "lancer_agentlocal_gui.bat").read_text(encoding="utf-8", errors="replace").casefold()
        self.assertNotIn(r"c:\\users\\ancienpc", content)
        self.assertIn(r"runtime\python\python.exe", content)
        self.assertIn(r".venv\scripts\python.exe", content)

    def test_runtime_builder_uses_project_relative_destination(self):
        content = (ROOT / "preparer_runtime_python_portable.py").read_text(encoding="utf-8")
        self.assertIn('get_project_path("python_runtime")', content)
        self.assertNotIn(r"C:\Users\AncienPC", content)


if __name__ == "__main__":
    unittest.main()
