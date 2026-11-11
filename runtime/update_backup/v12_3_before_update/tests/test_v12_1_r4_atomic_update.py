from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AtomicUpdateR4Tests(unittest.TestCase):
    def test_launcher_archives_every_obsolete_conformity_verifier(self):
        text = (ROOT / "AgentLocal.bat").read_text(encoding="utf-8-sig").casefold()
        self.assertIn("verifier_conformite_pack_*.py", text)
        self.assertIn("verifier_conformite_pack_v12.py", text)

    def test_global_runner_ignores_old_conformity_verifiers(self):
        text = (ROOT / "tester_agentlocal.ps1").read_text(encoding="utf-8-sig").casefold()
        self.assertIn('^verifier_conformite_pack_', text)
        self.assertIn('verifier_conformite_pack_v12.py', text)

    def test_user_launcher_has_no_utf8_bom(self):
        raw = (ROOT / "AgentLocal.bat").read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        self.assertTrue(raw.lstrip().startswith(b"@echo off"))


if __name__ == "__main__":
    unittest.main()
