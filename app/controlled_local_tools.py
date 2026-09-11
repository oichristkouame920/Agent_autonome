"""Nouvelles actions locales contrôlées d'AgentLocal.

Principes :
- Windows 10/11, faible empreinte mémoire.
- Refus par défaut si la politique manque ou est invalide.
- Actions manuelles explicites uniquement.
- Aucune exécution shell.
- Aucun contenu de presse-papiers persisté.
- Mémoire de référence uniquement en RAM pendant la session.
"""

from __future__ import annotations

import ctypes
import json
import os
import platform
import shutil
import time
from ctypes import wintypes
from pathlib import Path
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parents[1]
PERMISSIONS_FILE = ROOT_DIR / "config" / "permissions.json"

try:
    import psutil  # déjà utilisé par windows_tools.py dans AgentLocal
except Exception:  # pragma: no cover - secours si environnement incomplet
    psutil = None

from browser_bridge import activate_site_via_bridge, list_tabs_via_bridge
from file_tools import DISPLAY_NAMES, is_blocked_file_type, resolve_allowed_root
from recursive_file_tools import get_unique_reference_for_context
from session_context import get_last_reference
from web_tools import resolve_site


# ============================================================
# POLITIQUES
# ============================================================

def _load_permissions():
    try:
        with open(PERMISSIONS_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _policy(name: str):
    value = _load_permissions().get(name, {})
    return value if isinstance(value, dict) else {}


def _manual_only_check(policy_name: str, explicit_user_command: bool, source: str):
    policy = _policy(policy_name)
    if not policy.get("enabled", False):
        return False, policy, "Cette fonction est désactivée par la politique locale."
    if str(source or "").strip().lower() != "manual":
        return False, policy, "Cette fonction est réservée aux commandes manuelles."
    if policy.get("require_explicit_user_command", True) and not explicit_user_command:
        return False, policy, "Une commande explicite de l'utilisateur est requise."
    if policy.get("allow_from_routine", False) or policy.get("allow_from_habit", False):
        return False, policy, "Configuration dangereuse détectée : routines/habitudes doivent rester interdites."
    return True, policy, None


# ============================================================
# FORMATAGE
# ============================================================

def _format_bytes(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "inconnu"
    units = ("o", "Ko", "Mo", "Go", "To")
    index = 0
    while value >= 1024 and index < len(units) - 1:
        value /= 1024.0
        index += 1
    if index <= 1:
        return f"{value:.0f} {units[index]}"
    return f"{value:.1f} {units[index]}"


def _format_duration(seconds):
    try:
        seconds = max(0, int(seconds))
    except (TypeError, ValueError):
        return "durée inconnue"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} j")
    if hours or days:
        parts.append(f"{hours} h")
    parts.append(f"{minutes} min")
    return " ".join(parts)


# ============================================================
# INFORMATIONS SYSTÈME - LECTURE SEULE
# ============================================================

def _memory_info():
    if psutil is not None:
        mem = psutil.virtual_memory()
        return {
            "total": int(mem.total),
            "available": int(mem.available),
            "used": int(mem.used),
            "percent": float(mem.percent),
        }

    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", wintypes.DWORD),
                ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            used = int(status.ullTotalPhys - status.ullAvailPhys)
            return {
                "total": int(status.ullTotalPhys),
                "available": int(status.ullAvailPhys),
                "used": used,
                "percent": float(status.dwMemoryLoad),
            }
    return None


def _cpu_percent():
    if psutil is not None:
        return float(psutil.cpu_percent(interval=0.15))
    return None


def _uptime_seconds():
    if psutil is not None:
        return max(0.0, time.time() - float(psutil.boot_time()))
    if os.name == "nt":
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.GetTickCount64.restype = ctypes.c_ulonglong
            return float(kernel32.GetTickCount64()) / 1000.0
        except Exception:
            return None
    return None


def _system_drive_root():
    if os.name == "nt":
        drive = os.environ.get("SystemDrive", "C:").rstrip("\\/")
        return drive + "\\"
    return str(Path.home().anchor or "/")


def read_system_info(query: str, explicit_user_command=False, source="manual"):
    ok, policy, error = _manual_only_check(
        "system_information_policy", explicit_user_command, source
    )
    if not ok:
        return False, error
    if not policy.get("read_only", False):
        return False, "La politique système doit rester en lecture seule."

    query = str(query or "").strip().lower()
    allowed = set(policy.get("allowed_queries", []))
    if query not in allowed:
        return False, "Information système non autorisée."

    if query == "memory":
        info = _memory_info()
        if not info:
            return False, "Impossible de lire l'état de la mémoire de façon sûre."
        return True, (
            f"RAM : {info['percent']:.0f}% utilisée — "
            f"{_format_bytes(info['used'])} utilisés sur {_format_bytes(info['total'])}, "
            f"{_format_bytes(info['available'])} disponibles."
        )

    if query == "disk":
        root = _system_drive_root()
        try:
            total, used, free = shutil.disk_usage(root)
        except OSError as exc:
            return False, f"Impossible de lire l'espace disque : {exc}"
        percent = (used / total * 100.0) if total else 0.0
        return True, (
            f"Disque système {root} : {_format_bytes(free)} libres sur {_format_bytes(total)} "
            f"({percent:.0f}% utilisés)."
        )

    if query == "cpu":
        percent = _cpu_percent()
        if percent is None:
            return False, "Impossible de mesurer l'utilisation du processeur de façon sûre."
        name = platform.processor().strip()
        suffix = f" — {name}" if name else ""
        return True, f"Processeur : {percent:.0f}% d'utilisation{suffix}."

    if query == "uptime":
        seconds = _uptime_seconds()
        if seconds is None:
            return False, "Impossible de lire le temps de fonctionnement du PC."
        return True, f"Le PC est allumé depuis environ {_format_duration(seconds)}."

    if query == "summary":
        pieces = []
        mem = _memory_info()
        if mem:
            pieces.append(f"RAM {mem['percent']:.0f}%")
        cpu = _cpu_percent()
        if cpu is not None:
            pieces.append(f"CPU {cpu:.0f}%")
        try:
            total, used, free = shutil.disk_usage(_system_drive_root())
            pieces.append(f"disque libre {_format_bytes(free)}")
        except OSError:
            pass
        uptime = _uptime_seconds()
        if uptime is not None:
            pieces.append(f"allumé depuis {_format_duration(uptime)}")
        if not pieces:
            return False, "Aucune information système n'a pu être lue."
        return True, "État du PC : " + " ; ".join(pieces) + "."

    return False, "Information système non implémentée."


# ============================================================
# PRESSE-PAPIERS TEXTE - WINDOWS API, PAS DE SHELL
# ============================================================

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002


def _open_clipboard(user32):
    for _ in range(8):
        if user32.OpenClipboard(None):
            return True
        time.sleep(0.02)
    return False


def _windows_read_clipboard_text():
    if os.name != "nt":
        return False, None, "Le presse-papiers contrôlé est disponible uniquement sous Windows."

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL

    if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
        return False, None, "Le presse-papiers ne contient pas de texte lisible."
    if not _open_clipboard(user32):
        return False, None, "Le presse-papiers est momentanément utilisé par une autre application."

    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return False, None, "Impossible de lire le texte du presse-papiers."
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            return False, None, "Impossible d'accéder au texte du presse-papiers."
        try:
            text = ctypes.wstring_at(pointer)
        finally:
            kernel32.GlobalUnlock(handle)
        return True, text, None
    finally:
        user32.CloseClipboard()


def _windows_write_clipboard_text(text: str):
    if os.name != "nt":
        return False, "Le presse-papiers contrôlé est disponible uniquement sous Windows."

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL

    if not _open_clipboard(user32):
        return False, "Le presse-papiers est momentanément utilisé par une autre application."

    handle = None
    handed_to_clipboard = False
    try:
        if not user32.EmptyClipboard():
            return False, "Impossible de préparer le presse-papiers."

        payload = (text + "\x00").encode("utf-16-le")
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(payload))
        if not handle:
            return False, "Mémoire insuffisante pour copier le texte."

        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            return False, "Impossible de préparer le texte à copier."
        try:
            ctypes.memmove(pointer, payload, len(payload))
        finally:
            kernel32.GlobalUnlock(handle)

        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            return False, "Windows a refusé la copie dans le presse-papiers."
        handed_to_clipboard = True
        return True, "Texte copié dans le presse-papiers."
    finally:
        user32.CloseClipboard()
        if handle and not handed_to_clipboard:
            kernel32.GlobalFree(handle)


def read_clipboard_text(explicit_user_command=False, source="manual"):
    ok, policy, error = _manual_only_check("clipboard_policy", explicit_user_command, source)
    if not ok:
        return False, error
    if not policy.get("allow_read_text", False):
        return False, "La lecture du presse-papiers est désactivée."

    success, text, message = _windows_read_clipboard_text()
    if not success:
        return False, message

    maximum = int(policy.get("maximum_text_characters", 8192))
    maximum = max(1, min(maximum, 65536))
    if not text:
        return True, "Le presse-papiers texte est vide."
    if len(text) > maximum:
        return False, f"Le texte du presse-papiers dépasse la limite autorisée de {maximum} caractères."
    return True, f"Presse-papiers : {text}"


def write_clipboard_text(text: str, explicit_user_command=False, source="manual"):
    ok, policy, error = _manual_only_check("clipboard_policy", explicit_user_command, source)
    if not ok:
        return False, error
    if not policy.get("allow_write_text", False):
        return False, "L'écriture dans le presse-papiers est désactivée."
    if not isinstance(text, str) or not text or "\x00" in text:
        return False, "Le texte à copier est invalide."

    maximum = int(policy.get("maximum_text_characters", 8192))
    maximum = max(1, min(maximum, 65536))
    if len(text) > maximum:
        return False, f"Le texte dépasse la limite autorisée de {maximum} caractères."
    return _windows_write_clipboard_text(text)


def copy_file_path(root_name: str, file_name: str, explicit_user_command=False, source="manual"):
    ok, policy, error = _manual_only_check("clipboard_policy", explicit_user_command, source)
    if not ok:
        return False, error
    if not policy.get("allow_copy_authorized_file_path", False):
        return False, "La copie de chemins de fichiers est désactivée."

    success, reference = get_unique_reference_for_context(
        file_name, root_name=root_name, item_type="file"
    )
    if not success:
        return False, reference

    if is_blocked_file_type(reference["relative_path"]):
        return False, "Le chemin de ce type de fichier protégé ne peut pas être copié."
    root = resolve_allowed_root(reference["root_name"])
    if root is None:
        return False, "Racine de fichiers non autorisée."
    full_path = root / Path(reference["relative_path"])
    return write_clipboard_text(
        str(full_path), explicit_user_command=True, source="manual"
    )


# ============================================================
# ONGLETS EDGE VIA LE PONT LOCAL EXISTANT
# ============================================================

def list_browser_tabs(explicit_user_command=False, source="manual"):
    ok, policy, error = _manual_only_check("browser_tab_policy", explicit_user_command, source)
    if not ok:
        return False, error
    if not policy.get("allow_list_tabs", False):
        return False, "La consultation des onglets est désactivée."

    success, tabs, message = list_tabs_via_bridge()
    if not success:
        return False, message

    maximum = int(policy.get("maximum_listed_tabs", 20))
    maximum = max(1, min(maximum, 50))
    tabs = tabs[:maximum]
    if not tabs:
        return True, "Aucun onglet Edge n'a été retourné par le pont local."

    lines = [f"Onglets Edge visibles par le pont local ({len(tabs)}) :"]
    for index, tab in enumerate(tabs, 1):
        url = str(tab.get("url", ""))
        title = str(tab.get("title", "")).strip() or "Sans titre"
        title = " ".join(title.replace("\r", " ").replace("\n", " ").split())[:180]
        host = (urlparse(url).hostname or "adresse inconnue")[:253]
        active = " [actif]" if tab.get("active") else ""
        lines.append(f"{index}. {title} — {host}{active}")
    return True, "\n".join(lines)


def activate_browser_tab(site_name: str, explicit_user_command=False, source="manual"):
    ok, policy, error = _manual_only_check("browser_tab_policy", explicit_user_command, source)
    if not ok:
        return False, error
    if not policy.get("allow_activate_tab", False):
        return False, "L'activation d'onglets est désactivée."

    success, url, error = resolve_site(site_name)
    if not success:
        return False, error

    allow_subdomains = bool(policy.get("allow_subdomains", False))
    success, message = activate_site_via_bridge(url, allow_subdomains=allow_subdomains)
    if not success:
        return False, message
    return True, f"Onglet activé pour {site_name}."


# ============================================================
# MÉMOIRE DE SESSION - AUCUNE PERSISTANCE
# ============================================================

def _session_policy_check(explicit_user_command, source):
    return _manual_only_check("session_context_policy", explicit_user_command, source)


def open_last_reference(explicit_user_command=False, source="manual"):
    ok, policy, error = _session_policy_check(explicit_user_command, source)
    if not ok:
        return False, error
    if not policy.get("allow_open_last_reference", False):
        return False, "L'ouverture par référence de session est désactivée."

    reference = get_last_reference()
    if not reference:
        return False, "Je n'ai pas de fichier ou dossier précédent suffisamment précis dans cette session."

    # Import local pour ne pas charger inutilement les outils d'ouverture.
    from controlled_open_tools import open_directory, open_file

    if reference["item_type"] == "dir":
        return open_directory(
            reference["root_name"],
            relative_path=reference["relative_path"],
            explicit_user_command=True,
            source="manual",
        )
    return open_file(
        reference["root_name"],
        reference["relative_path"],
        explicit_user_command=True,
        source="manual",
    )


def read_last_reference(explicit_user_command=False, source="manual"):
    ok, policy, error = _session_policy_check(explicit_user_command, source)
    if not ok:
        return False, error
    if not policy.get("allow_read_last_reference", False):
        return False, "La lecture par référence de session est désactivée."

    reference = get_last_reference()
    if not reference:
        return False, "Je n'ai pas de fichier précédent suffisamment précis dans cette session."
    if reference["item_type"] != "file":
        return False, "La dernière référence est un dossier, pas un fichier lisible."

    from recursive_file_tools import read_file_content

    return read_file_content(
        reference["root_name"],
        reference["relative_path"],
        explicit_user_command=True,
        source="manual",
    )


def copy_last_reference_path(explicit_user_command=False, source="manual"):
    ok, policy, error = _session_policy_check(explicit_user_command, source)
    if not ok:
        return False, error
    if not policy.get("allow_copy_last_reference_path", False):
        return False, "La copie du chemin précédent est désactivée."

    reference = get_last_reference()
    if not reference:
        return False, "Je n'ai pas de référence précédente suffisamment précise dans cette session."

    if is_blocked_file_type(reference["relative_path"]):
        return False, "Le chemin de ce type de fichier protégé ne peut pas être copié."
    root = resolve_allowed_root(reference["root_name"])
    if root is None:
        return False, "Racine de fichiers non autorisée."
    full_path = root / Path(reference["relative_path"])
    return write_clipboard_text(
        str(full_path), explicit_user_command=True, source="manual"
    )

# ============================================================
# VALIDATION DE POLITIQUE POUR LE CONTRAT AGENT
# ============================================================

_ACTION_POLICY_MAP = {
    "read_system_info": "system_information_policy",
    "read_clipboard": "clipboard_policy",
    "write_clipboard": "clipboard_policy",
    "copy_file_path": "clipboard_policy",
    "list_browser_tabs": "browser_tab_policy",
    "activate_browser_tab": "browser_tab_policy",
    "open_last_reference": "session_context_policy",
    "read_last_reference": "session_context_policy",
    "copy_last_reference_path": "session_context_policy",
}


def validate_controlled_action_policy(action: str):
    policy_name = _ACTION_POLICY_MAP.get(str(action or "").strip().lower())
    if not policy_name:
        return False, "Action locale contrôlée inconnue."
    ok, _, error = _manual_only_check(policy_name, True, "manual")
    return (True, None) if ok else (False, error)
