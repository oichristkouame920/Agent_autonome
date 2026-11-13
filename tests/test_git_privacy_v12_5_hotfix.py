"""Tests de regression Git : portabilite, index et exclusions privees."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from app.git_privacy import PRIVATE_PATHS, check_private_exclusions


class PrivacyGitHotfixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def _ignore(self, content):
        (self.root / ".gitignore").write_text(content, encoding="utf-8")

    def test_global_memory_coverage_without_git(self):
        self._ignore("memory/\n/config/security_center.json\n/config/connected_services.json\n")
        issues, mode = check_private_exclusions(self.root, (
            "memory/user_profile.json", "memory/declared_habits.json",
            "config/security_center.json", "config/connected_services.json",
        ))
        self.assertEqual(issues, [])
        self.assertEqual(mode, "gitignore-local")

    def test_memory_star_coverage_without_git(self):
        self._ignore("/memory/*\n!/memory/.gitkeep\n")
        issues, _ = check_private_exclusions(self.root, ("memory/user_profile.json",))
        self.assertEqual(issues, [])

    def test_missing_ignore_does_not_pass(self):
        issues, _ = check_private_exclusions(self.root, ("memory/user_profile.json",))
        self.assertTrue(issues)

    def test_missing_rule_does_not_pass(self):
        self._ignore("# no privacy rules\n")
        issues, _ = check_private_exclusions(self.root, ("memory/user_profile.json",))
        self.assertIn("Regle .gitignore manquante : memory/user_profile.json", issues)

    def test_negated_rule_does_not_pass(self):
        self._ignore("/memory/*\n!/memory/user_profile.json\n")
        issues, _ = check_private_exclusions(self.root, ("memory/user_profile.json",))
        self.assertTrue(issues)

    def test_suspicious_path_does_not_pass(self):
        self._ignore("/memory/*\n")
        issues, _ = check_private_exclusions(self.root, ("../secrets.txt",))
        self.assertTrue(issues)

    @unittest.skipUnless(shutil.which("git"), "Git non disponible")
    def test_real_git_detects_tracked_private_file(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self._ignore("/memory/*\n")
        personal = self.root / "memory" / "user_profile.json"
        personal.parent.mkdir(parents=True)
        personal.write_text("{}", encoding="utf-8")
        paths = ("memory/user_profile.json",)
        issues, mode = check_private_exclusions(self.root, paths)
        self.assertEqual((issues, mode), ([], "git"))
        subprocess.run(["git", "-C", str(self.root), "add", "-f", "memory/user_profile.json"], check=True)
        issues, _ = check_private_exclusions(self.root, paths)
        self.assertIn("Encore suivi dans l'index Git : memory/user_profile.json", issues)
        subprocess.run(["git", "-C", str(self.root), "rm", "--cached", "-q", "memory/user_profile.json"], check=True)
        issues, _ = check_private_exclusions(self.root, paths)
        self.assertEqual(issues, [])

    def test_project_rules_verified_all_targets(self):
        project = Path(__file__).resolve().parents[1]
        issues, method = check_private_exclusions(project, PRIVATE_PATHS)
        self.assertEqual(issues, [], f"methode={method}: {issues}")


if __name__ == "__main__":
    unittest.main()
