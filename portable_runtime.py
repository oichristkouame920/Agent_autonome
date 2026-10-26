"""Diagnostic et resolution des runtimes portables d'AgentLocal."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from project_paths import PROJECT_ROOT, get_project_path, resolve_project_relative

RUNTIME_CONFIG_FILE = get_project_path("config") / "runtime.json"

DEFAULT_RUNTIME_CONFIG = {
    "schema_version": 1,
    "python": {
        "portable_executable": "runtime/python/python.exe",
        "portable_gui_executable": "runtime/python/pythonw.exe",
        "venv_executable": ".venv/Scripts/python.exe",
        "venv_gui_executable": ".venv/Scripts/pythonw.exe",
        "requirements": "requirements.txt",
        "offline_wheels": "vendor/wheels",
    },
    "llama": {
        "runtime_dir": "tools/llama.cpp",
        "executable": "tools/llama.cpp/llama-cli.exe",
        "probe_args": ["--version"],
        "probe_timeout_seconds": 10,
    },
}


@dataclass(frozen=True)
class PythonCandidate:
    mode: str
    console: Path | None
    gui: Path | None


def _clone_default():
    return json.loads(json.dumps(DEFAULT_RUNTIME_CONFIG))


def load_runtime_config() -> dict:
    config = _clone_default()
    if not RUNTIME_CONFIG_FILE.is_file():
        return config
    try:
        data = json.loads(RUNTIME_CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return config
    if not isinstance(data, dict):
        return config
    for section in ("python", "llama"):
        if isinstance(data.get(section), dict):
            config[section].update(data[section])
    return config


def _resolve_relative(value: str) -> Path:
    return resolve_project_relative(value)


def python_candidates() -> list[PythonCandidate]:
    cfg = load_runtime_config()["python"]
    candidates = []

    portable_console = _resolve_relative(cfg["portable_executable"])
    portable_gui = _resolve_relative(cfg["portable_gui_executable"])
    candidates.append(PythonCandidate("portable", portable_console, portable_gui))

    venv_console = _resolve_relative(cfg["venv_executable"])
    venv_gui = _resolve_relative(cfg["venv_gui_executable"])
    candidates.append(PythonCandidate("venv", venv_console, venv_gui))
    return candidates


def first_existing_python() -> PythonCandidate | None:
    for candidate in python_candidates():
        if candidate.console and candidate.console.is_file():
            return candidate
    return None


def requirements_file() -> Path:
    return _resolve_relative(load_runtime_config()["python"]["requirements"])


def offline_wheels_dir() -> Path:
    return _resolve_relative(load_runtime_config()["python"]["offline_wheels"])


def llama_runtime_paths() -> tuple[Path, Path, list[str], int]:
    cfg = load_runtime_config()["llama"]
    runtime_dir = _resolve_relative(cfg["runtime_dir"])
    executable = _resolve_relative(cfg["executable"])
    args = cfg.get("probe_args") or ["--version"]
    if not isinstance(args, list):
        args = ["--version"]
    args = [str(x) for x in args]
    timeout = max(3, min(int(cfg.get("probe_timeout_seconds", 10) or 10), 30))
    return runtime_dir, executable, args, timeout


def _run_probe(command: list[str], cwd: Path | None = None, timeout: int = 10) -> tuple[bool, str]:
    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": timeout,
        "shell": False,
    }
    if cwd:
        kwargs["cwd"] = str(cwd)
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(command, **kwargs)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    output = (completed.stdout or completed.stderr or "").strip()
    return completed.returncode == 0, output[-800:]


def probe_python(executable: Path, imports: Iterable[str] = ("tkinter", "psutil", "pypdf")) -> tuple[bool, str]:
    if not executable.is_file():
        return False, f"Python introuvable : {executable}"
    statement = "; ".join(f"import {name}" for name in imports)
    statement += "; import sys; print(sys.version.split()[0])"
    return _run_probe([str(executable), "-c", statement], cwd=PROJECT_ROOT, timeout=20)


def probe_llama_runtime() -> tuple[bool, str]:
    runtime_dir, executable, args, timeout = llama_runtime_paths()
    if not runtime_dir.is_dir():
        return False, f"Dossier llama.cpp introuvable : {runtime_dir}"
    if not executable.is_file():
        return False, f"llama-cli introuvable : {executable}"
    if os.name != "nt":
        return True, "Sonde d'execution reportee a Windows."
    return _run_probe([str(executable), *args], cwd=runtime_dir, timeout=timeout)


def runtime_summary() -> dict:
    python_info = []
    for candidate in python_candidates():
        exists = bool(candidate.console and candidate.console.is_file())
        python_info.append(
            {
                "mode": candidate.mode,
                "console": str(candidate.console) if candidate.console else None,
                "gui": str(candidate.gui) if candidate.gui else None,
                "available": exists,
            }
        )

    llama_dir, llama_exe, _, _ = llama_runtime_paths()
    return {
        "project_root": str(PROJECT_ROOT),
        "python_candidates": python_info,
        "requirements": str(requirements_file()),
        "offline_wheels": str(offline_wheels_dir()),
        "llama_runtime_dir": str(llama_dir),
        "llama_executable": str(llama_exe),
    }


if __name__ == "__main__":
    print(json.dumps(runtime_summary(), ensure_ascii=False, indent=2))
