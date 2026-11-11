"""Mise a niveau non destructive de config/models.json pour le LLM adaptatif V12.2.1."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from project_paths import get_project_path

CONFIG_FILE = get_project_path("config") / "models.json"
RUNTIME_DEFAULTS = {
    "probe_fast_timeout_seconds": 10,
    "probe_slow_timeout_seconds": 30,
    "llama_server": "tools/llama.cpp/llama-server.exe",
    "warm_server_enabled": True,
    "warm_server_idle_seconds": 180,
    "warm_server_min_available_ram_mb": 850,
    "warm_server_start_timeout_seconds": 45,
    "warm_server_local_only": True,
}


def upgrade(path: Path = CONFIG_FILE) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    runtime = data.setdefault("runtime", {})
    if not isinstance(runtime, dict):
        runtime = {}
        data["runtime"] = runtime
    changed = False
    for key, value in RUNTIME_DEFAULTS.items():
        if key not in runtime:
            runtime[key] = value
            changed = True
    # Securite : le serveur chaud ne doit jamais etre configurable en ecoute externe.
    if runtime.get("warm_server_local_only") is not True:
        runtime["warm_server_local_only"] = True
        changed = True
    if not changed:
        return True

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="models.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            Path(tmp_name).unlink(missing_ok=True)
        except Exception:
            pass
    return True


if __name__ == "__main__":
    if not upgrade():
        raise SystemExit("Impossible de mettre a niveau config/models.json")
    print("Configuration LLM adaptative V12.2.1 : OK")
