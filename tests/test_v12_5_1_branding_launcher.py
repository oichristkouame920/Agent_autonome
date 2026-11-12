import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BrandingLauncherV1251Tests(unittest.TestCase):
    def test_branding_assets_exist_and_have_expected_headers(self):
        ico = ROOT / "assets" / "agentlocal.ico"
        png = ROOT / "assets" / "agentlocal_icon.png"
        self.assertTrue(ico.is_file())
        self.assertTrue(png.is_file())
        self.assertEqual(ico.read_bytes()[:4], b"\x00\x00\x01\x00")
        self.assertEqual(png.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_vbs_launchers_are_ascii_without_bom(self):
        for rel in ("runtime/start_agentlocal_gui.vbs", "runtime/create_agentlocal_shortcuts.vbs"):
            data = (ROOT / rel).read_bytes()
            self.assertFalse(data.startswith(b"\xef\xbb\xbf"), rel)
            data.decode("ascii")

    def test_gui_uses_branding_and_splash(self):
        text = (ROOT / "app" / "gui.py").read_text(encoding="utf-8")
        self.assertIn("_apply_window_icon", text)
        self.assertIn("_show_startup_splash", text)
        self.assertIn("SetCurrentProcessExplicitAppUserModelID", text)

    def test_desktop_shortcut_targets_silent_gui_launcher(self):
        text = (ROOT / "runtime" / "create_agentlocal_shortcuts.vbs").read_text(encoding="ascii")
        self.assertIn("AgentLocal.lnk", text)
        self.assertIn("start_agentlocal_gui.vbs", text)
        self.assertIn("agentlocal.ico", text)

    def test_central_version(self):
        from project_version import AGENTLOCAL_VERSION
        self.assertEqual(AGENTLOCAL_VERSION, "12.5")


if __name__ == "__main__":
    unittest.main()
