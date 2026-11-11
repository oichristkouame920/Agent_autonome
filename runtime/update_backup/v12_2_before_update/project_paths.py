"""Gestion centralisee des chemins internes d'AgentLocal.

Tous les emplacements internes restent relatifs a la racine du projet.
Les chemins absolus ne sont construits qu'en memoire a l'execution.
"""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath, PureWindowsPath

SCHEMA_VERSION = 2
PROJECT_ROOT = Path(__file__).resolve().parent
PATHS_CONFIG_FILE = PROJECT_ROOT / "config" / "paths.json"

DEFAULT_PATHS = {
    "config": "config",
    "models": "models",
    "tools": "tools",
    "llama_runtime": "tools/llama.cpp",
    "runtime": "runtime",
    "python_runtime": "runtime/python",
    "vendor": "vendor",
    "wheels": "vendor/wheels",
    "memory": "memory",
    "logs": "logs",
    "app": "app",
    "backends": "backends",
    "browser_extension": "browser_extension",
    "browser_native_host": "browser_native_host",
    "agent_tools": "agent_tools",
    "source": "source",
    "tests": "tests",
}


def _is_absolute_any_platform(value: str) -> bool:
    value = str(value or "").strip()
    if not value:
        return False
    win = PureWindowsPath(value)
    return (
        Path(value).is_absolute()
        or win.is_absolute()
        or bool(win.drive)
        or PurePosixPath(value).is_absolute()
    )


def _normalise_relative(value: str, fallback: str) -> str:
    value = str(value or "").strip().replace("\\", "/")
    if not value or _is_absolute_any_platform(value):
        value = fallback
    parts = []
    for part in PurePosixPath(value).parts:
        if part in {"", "."}:
            continue
        if part == "..":
            return fallback
        parts.append(part)
    return "/".join(parts) or fallback


def load_paths_config() -> dict:
    values = dict(DEFAULT_PATHS)
    if PATHS_CONFIG_FILE.is_file():
        try:
            data = json.loads(PATHS_CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        configured = data.get("paths", {}) if isinstance(data, dict) else {}
        if isinstance(configured, dict):
            for key, fallback in DEFAULT_PATHS.items():
                if key in configured:
                    values[key] = _normalise_relative(configured[key], fallback)
    return {"schema_version": SCHEMA_VERSION, "paths": values}


def get_relative_path(name: str) -> Path:
    values = load_paths_config()["paths"]
    if name not in values:
        raise KeyError(f"Chemin interne inconnu : {name}")
    return Path(values[name])


def resolve_project_relative(value: str | Path) -> Path:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("Chemin interne vide.")
    if _is_absolute_any_platform(raw):
        raise ValueError("Un chemin interne AgentLocal doit rester relatif.")
    normalised = _normalise_relative(raw, "")
    if not normalised:
        raise ValueError("Chemin interne invalide.")
    candidate = (PROJECT_ROOT / Path(normalised)).resolve()
    try:
        candidate.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("Le chemin sort de la racine AgentLocal.") from exc
    return candidate


def get_project_path(name: str) -> Path:
    return resolve_project_relative(get_relative_path(name))


def project_relative_string(path: str | Path) -> str:
    candidate = Path(path).resolve()
    try:
        relative = candidate.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("Le chemin n'appartient pas au projet AgentLocal.") from exc
    return relative.as_posix()


def ensure_portable_directories() -> None:
    """Cree seulement les dossiers locaux qui peuvent etre vides au depart."""
    for name in ("runtime", "python_runtime", "vendor", "wheels", "memory", "logs"):
        try:
            get_project_path(name).mkdir(parents=True, exist_ok=True)
        except (OSError, ValueError, KeyError):
            # Le diagnostic affichera une erreur plus precise si necessaire.
            pass
