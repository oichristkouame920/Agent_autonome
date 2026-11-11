import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

import gui


class GuiLightweightTests(unittest.TestCase):
    def test_command_is_only_trimmed(self):
        original = "  Déplace Rapport Final.PDF dans Archives  "
        self.assertEqual(
            gui.normalize_user_command(original),
            "Déplace Rapport Final.PDF dans Archives",
        )

    def test_empty_command(self):
        self.assertEqual(gui.normalize_user_command("   "), "")

    def test_command_limit_is_small_and_fixed(self):
        self.assertEqual(gui.MAX_COMMAND_LENGTH, 2000)

    @patch("gui.agent.get_agent_config")
    def test_runtime_summary_does_not_select_backend(self, config):
        config.return_value = {
            "backend": {"mode": "auto"},
            "learning": {"enabled": True},
        }
        backend_text, learning_text = gui.get_runtime_summary()
        self.assertIn("auto", backend_text)
        self.assertIn("chargé à la demande", backend_text)
        self.assertIn("activé", learning_text)


if __name__ == "__main__":
    unittest.main()
