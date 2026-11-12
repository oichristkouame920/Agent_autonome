"""Taches Windows autorisees ponctuellement avec UAC.

Ce module ne traite JAMAIS du texte libre comme une commande systeme.
Seuls les identifiants explicitement allowlistes sont executables.
"""
from __future__ import annotations

import argparse
import ctypes
import subprocess
import sys
from pathlib import Path

ALLOWED_ADMIN_ACTIONS = frozenset({"flush_dns_cache"})


def is_windows_admin() -> bool:
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError, ValueError):
        return False


def system_executable(filename: str) -> Path:
    """Resoudre system32 sans PATH, sans variable d'environnement controlable."""
    if sys.platform != "win32":
        raise RuntimeError("Cette action est reservee a Windows.")
    if filename != "ipconfig.exe":
        raise ValueError("Executable non autorise.")
    buf = ctypes.create_unicode_buffer(32768)
    count = ctypes.windll.kernel32.GetSystemDirectoryW(buf, len(buf))
    if count <= 0 or count >= len(buf):
        raise RuntimeError("Le repertoire systeme Windows est introuvable.")
    return Path(buf.value) / filename


def execute_admin_action(action_id: str) -> tuple[bool, str]:
    if action_id not in ALLOWED_ADMIN_ACTIONS:
        return False, "Action d'administration refusee : non autorisee."
    if not is_windows_admin():
        return False, "Windows exige une elevation UAC pour cette operation."
    if action_id == "flush_dns_cache":
        executable = system_executable("ipconfig.exe")
        try:
            result = subprocess.run(
                [str(executable), "/flushdns"],
                shell=False, capture_output=True, text=True,
                timeout=30, check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"Impossible de vider le cache DNS : {type(exc).__name__}."
        if result.returncode != 0:
            return False, f"Echec de l'operation DNS (code {result.returncode})."
        return True, "Cache DNS Windows vide avec succes."
    return False, "Action refusee."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AgentLocal - actions administrateur ponctuelles")
    parser.add_argument("--action", required=True, choices=sorted(ALLOWED_ADMIN_ACTIONS))
    args = parser.parse_args(argv)
    ok, message = execute_admin_action(args.action)
    print(message)
    if sys.platform == "win32":
        try:
            from tkinter import messagebox
            (messagebox.showinfo if ok else messagebox.showerror)("AgentLocal - operation Windows", message)
        except Exception:
            pass
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
