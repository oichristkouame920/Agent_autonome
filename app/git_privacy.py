"""Verification read-only des exclusions Git des donnees locales AgentLocal.

Utilise Git lorsqu'il est disponible dans le projet. En distribution sans .git,
accepte les regles simples du .gitignore sans demander d'installer Git.
Ne lit jamais le contenu des fichiers personnels.
"""
from __future__ import annotations

import fnmatch
import shutil
import subprocess
from pathlib import Path, PurePosixPath

PRIVATE_MEMORY = (
    "memory/user_profile.json",
    "memory/user_preferences.json",
    "memory/onboarding_state.json",
    "memory/declared_habits.json",
    "memory/notification_state.json",
    "memory/language_profile.json",
)
PRIVATE_CONFIG = (
    "config/security_center.json",
    "config/connected_services.json",
    "config/browser_bridge.json",
    "browser_extension/bridge_config.js",
)
PRIVATE_PATHS = PRIVATE_MEMORY + PRIVATE_CONFIG


def _simple_rule_matches(pattern: str, rel: str) -> bool:
    """Correspondances minimales conservatrices pour les packs sans depot Git."""
    pattern = pattern.lstrip("/")
    if not pattern:
        return False
    if pattern.endswith("/"):
        folder = pattern.rstrip("/")
        return rel == folder or rel.startswith(folder + "/")
    if "/" in pattern:
        return fnmatch.fnmatchcase(rel, pattern)
    return any(fnmatch.fnmatchcase(segment, pattern) for segment in rel.split("/"))


def _fallback_ignored(gitignore: str, rel: str) -> bool:
    ignored = False
    for raw in gitignore.splitlines():
        rule = raw.strip()
        if not rule or rule.startswith("#"):
            continue
        unignore = rule.startswith("!")
        if unignore:
            rule = rule[1:]
        if _simple_rule_matches(rule, rel):
            ignored = not unignore
    return ignored


def _run_git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        check=False,
        timeout=8,
    )


def _git_project_available(root: Path) -> bool:
    if shutil.which("git") is None:
        return False
    proc = _run_git(root, "rev-parse", "--show-toplevel")
    if proc.returncode:
        return False
    try:
        return Path(proc.stdout.strip()).resolve() == root.resolve()
    except (OSError, ValueError):
        return False


def check_private_exclusions(
    root: Path,
    paths: tuple[str, ...] = PRIVATE_PATHS,
    *,
    check_index: bool = True,
) -> tuple[list[str], str]:
    """Retourne (problemes, methode) sans modifier aucun fichier / index.

    Une exclusion reelle est exigee, et un fichier encore suivi par Git est
    signale : un .gitignore ne retire pas les fichiers de l'index.
    """
    root = Path(root).resolve()
    ignore_file = root / ".gitignore"
    if not ignore_file.is_file():
        return [".gitignore absent"], "missing"
    rules = ignore_file.read_text(encoding="utf-8-sig", errors="replace")
    with_git = _git_project_available(root)
    issues = []
    for rel in paths:
        rel = rel.replace("\\", "/")
        parts = PurePosixPath(rel).parts
        if not parts or ".." in parts or rel.startswith("/"):
            issues.append("Chemin interdit dans le controle Git : " + rel)
            continue
        if with_git:
            result = _run_git(root, "check-ignore", "--no-index", "--quiet", "--", rel)
            if result.returncode == 1:
                issues.append("Non ignore par Git : " + rel)
            elif result.returncode != 0:
                issues.append("Verification Git impossible pour : " + rel)
            if check_index:
                index = _run_git(root, "ls-files", "--error-unmatch", "--", rel)
                if index.returncode == 0:
                    issues.append("Encore suivi dans l'index Git : " + rel)
                elif index.returncode != 1:
                    issues.append("Index Git non verifiable pour : " + rel)
        elif not _fallback_ignored(rules, rel):
            issues.append("Regle .gitignore manquante : " + rel)
    return issues, ("git" if with_git else "gitignore-local")
