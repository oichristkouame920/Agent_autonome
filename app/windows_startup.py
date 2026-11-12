"""Démarrage utilisateur Windows pour AgentLocal, sans droits administrateur."""
from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
VALUE_NAME = "AgentLocal"
RUNTIME_DIR = ROOT_DIR / "runtime"
VBS_FILE = RUNTIME_DIR / "start_agentlocal_background.vbs"
PREFERENCE_FILE = ROOT_DIR / "memory" / "windows_startup_preference.json"


def _startup_command() -> str:
    bat = ROOT_DIR / "AgentLocal.bat"
    return f'wscript.exe "{VBS_FILE}"'


def _vbs_text() -> str:
    bat = str(ROOT_DIR / "AgentLocal.bat").replace('"', '""')
    return (
        'Set shell = CreateObject("WScript.Shell")\r\n'
        f'shell.Run Chr(34) & "{bat}" & Chr(34) & " autostart", 0, False\r\n'
    )


def ensure_startup_script() -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    VBS_FILE.write_text(_vbs_text(), encoding="ascii")
    return VBS_FILE


def is_startup_enabled() -> bool:
    if os.name != "nt":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
        enabled = str(value).strip().lower() == _startup_command().strip().lower()
        if enabled:
            # Auto-reparation des anciennes versions VBS ecrites avec BOM.
            try:
                ensure_startup_script()
            except Exception:
                pass
        return enabled
    except Exception:
        return False



def _write_preference(enabled: bool) -> None:
    import json
    import tempfile
    PREFERENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"enabled": bool(enabled)}, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(prefix="startup_pref_", suffix=".json", dir=str(PREFERENCE_FILE.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        Path(tmp).replace(PREFERENCE_FILE)
    finally:
        try:
            Path(tmp).unlink(missing_ok=True)
        except OSError:
            pass


def read_preference() -> bool | None:
    import json
    try:
        data = json.loads(PREFERENCE_FILE.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict) and isinstance(data.get("enabled"), bool):
            return data["enabled"]
    except Exception:
        pass
    return None


def apply_default_if_unset(default_enabled: bool = True) -> tuple[bool, str]:
    # Le script VBS est toujours regenere avec un encodage compatible WSH.
    # Cela repare aussi automatiquement les anciennes versions UTF-8 BOM.
    try:
        ensure_startup_script()
    except Exception:
        pass
    pref = read_preference()
    if pref is not None:
        return True, "Préférence de démarrage déjà définie."
    return set_startup_enabled(bool(default_enabled))

def set_startup_enabled(enabled: bool) -> tuple[bool, str]:
    if os.name != "nt":
        return False, "Le démarrage automatique est disponible uniquement sous Windows."
    try:
        import winreg
        ensure_startup_script()
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _startup_command())
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
        _write_preference(bool(enabled))
        return True, "Démarrage automatique activé." if enabled else "Démarrage automatique désactivé."
    except Exception as exc:
        return False, f"Impossible de modifier le démarrage automatique ({type(exc).__name__})."


def status_text() -> str:
    return "Activé - démarrage discret avec Windows" if is_startup_enabled() else "Désactivé"
