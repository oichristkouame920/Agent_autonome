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
import socket
import struct
import time
import uuid
import zlib
from datetime import datetime
from ctypes import wintypes
from pathlib import Path
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parents[1]
PERMISSIONS_FILE = ROOT_DIR / "config" / "permissions.json"

try:
    import psutil  # déjà utilisé par windows_tools.py dans AgentLocal
except Exception:  # pragma: no cover - secours si environnement incomplet
    psutil = None

from browser_bridge import activate_site_via_bridge, list_tabs_via_bridge, open_site_via_bridge
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
# BATTERIE / RESEAU - LECTURE SEULE, AUCUN TEST EXTERNE
# ============================================================

def read_power_info(query: str, explicit_user_command=False, source="manual"):
    ok, policy, error = _manual_only_check(
        "power_information_policy", explicit_user_command, source
    )
    if not ok:
        return False, error
    if not policy.get("read_only", False):
        return False, "La politique d'alimentation doit rester en lecture seule."

    query = str(query or "").strip().lower()
    allowed = set(policy.get("allowed_queries", []))
    if query not in allowed:
        return False, "Information d'alimentation non autorisée."
    if psutil is None or not hasattr(psutil, "sensors_battery"):
        return False, "La lecture de la batterie n'est pas disponible dans cet environnement."

    try:
        battery = psutil.sensors_battery()
    except Exception:
        battery = None
    if battery is None:
        return True, "Aucune batterie n'a été détectée. Ce PC est peut-être un ordinateur fixe."

    percent = max(0.0, min(100.0, float(battery.percent)))
    plugged = bool(battery.power_plugged)
    state = "branché au secteur" if plugged else "sur batterie"

    remaining = ""
    secsleft = getattr(battery, "secsleft", None)
    unknown_values = {None}
    if psutil is not None:
        unknown_values.update({getattr(psutil, "POWER_TIME_UNKNOWN", None), getattr(psutil, "POWER_TIME_UNLIMITED", None)})
    if not plugged and secsleft not in unknown_values:
        try:
            secsleft = int(secsleft)
            if secsleft >= 0:
                remaining = f" — autonomie estimée : {_format_duration(secsleft)}"
        except (TypeError, ValueError):
            pass

    if query == "battery":
        return True, f"Batterie : {percent:.0f}% — {state}{remaining}."
    if query == "power":
        return True, f"Alimentation : {state}. Batterie : {percent:.0f}%{remaining}."
    return False, "Information d'alimentation non implémentée."


def _network_active_interfaces():
    if psutil is None:
        return []
    try:
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
    except Exception:
        return []

    active = []
    for name, stat in stats.items():
        try:
            if not stat.isup:
                continue
        except Exception:
            continue
        lname = str(name).lower()
        if "loopback" in lname or lname.startswith("lo"):
            continue

        ipv4 = []
        ipv6 = []
        for addr in addrs.get(name, []):
            family = getattr(addr, "family", None)
            value = str(getattr(addr, "address", "") or "").split("%", 1)[0]
            if not value:
                continue
            if family == socket.AF_INET:
                if not value.startswith("127.") and value != "0.0.0.0":
                    ipv4.append(value)
            elif family == socket.AF_INET6:
                if value != "::1":
                    ipv6.append(value)

        # On garde une interface active même sans IP pour signaler l'état du lien.
        try:
            speed = float(stat.speed) if float(stat.speed) > 0 else None
        except Exception:
            speed = None
        active.append({
            "name": str(name),
            "ipv4": ipv4,
            "ipv6": ipv6,
            "speed_mbps": speed,
            "mtu": int(getattr(stat, "mtu", 0) or 0),
        })
    return active


def _format_mbps(value):
    try:
        value = max(0.0, float(value))
    except (TypeError, ValueError):
        return "inconnue"
    if value >= 1000.0:
        return f"{value / 1000.0:.2f} Gb/s"
    if value >= 10.0:
        return f"{value:.0f} Mb/s"
    if value >= 1.0:
        return f"{value:.1f} Mb/s"
    return f"{value:.2f} Mb/s"


def _sample_network_traffic(active_names, seconds=1.0):
    if psutil is None:
        return None
    try:
        before = psutil.net_io_counters(pernic=True)
        started = time.monotonic()
        time.sleep(max(0.2, min(float(seconds), 2.0)))
        after = psutil.net_io_counters(pernic=True)
        elapsed = max(0.001, time.monotonic() - started)
    except Exception:
        return None

    recv = 0
    sent = 0
    for name in active_names:
        b = before.get(name)
        a = after.get(name)
        if b is None or a is None:
            continue
        recv += max(0, int(a.bytes_recv) - int(b.bytes_recv))
        sent += max(0, int(a.bytes_sent) - int(b.bytes_sent))
    return {
        "download_mbps": recv * 8.0 / elapsed / 1_000_000.0,
        "upload_mbps": sent * 8.0 / elapsed / 1_000_000.0,
        "seconds": elapsed,
    }


def read_network_info(query: str, explicit_user_command=False, source="manual"):
    ok, policy, error = _manual_only_check(
        "network_information_policy", explicit_user_command, source
    )
    if not ok:
        return False, error
    if not policy.get("read_only", False):
        return False, "La politique réseau doit rester en lecture seule."

    query = str(query or "").strip().lower()
    allowed = set(policy.get("allowed_queries", []))
    if query not in allowed:
        return False, "Information réseau non autorisée."

    interfaces = _network_active_interfaces()

    if query == "status":
        if not interfaces:
            return True, "Aucune interface réseau locale active n'a été détectée. Aucun serveur Internet n'a été contacté."
        names = ", ".join(item["name"] for item in interfaces[:5])
        return True, (
            f"Réseau local actif : {names}. "
            "Cette vérification ne garantit pas l'accès à Internet et n'a contacté aucun serveur externe."
        )

    if query == "local_ip":
        found = []
        for item in interfaces:
            for ip in item["ipv4"]:
                found.append(f"{item['name']} : {ip}")
        if not found:
            return True, "Aucune adresse IPv4 locale active n'a été détectée."
        return True, "Adresse(s) IP locale(s) : " + " ; ".join(found[:8]) + "."

    if query == "interfaces":
        if not interfaces:
            return True, "Aucune interface réseau locale active n'a été détectée."
        rows = []
        for item in interfaces[:8]:
            ip = item["ipv4"][0] if item["ipv4"] else "sans IPv4"
            speed = _format_mbps(item["speed_mbps"]) if item["speed_mbps"] else "vitesse non fournie par Windows"
            rows.append(f"{item['name']} — {ip} — {speed}")
        return True, "Interfaces réseau actives :\n- " + "\n- ".join(rows)

    if query == "link_speed":
        measured = [item for item in interfaces if item.get("speed_mbps")]
        if not measured:
            return True, (
                "Windows n'a fourni aucune vitesse de liaison pour les interfaces réseau actives. "
                "Aucun test Internet externe n'a été lancé."
            )
        rows = [f"{item['name']} : {_format_mbps(item['speed_mbps'])}" for item in measured[:8]]
        return True, (
            "Vitesse de liaison indiquée par Windows : " + " ; ".join(rows) + ". "
            "Il s'agit de la vitesse du lien local (Wi-Fi/Ethernet), pas du débit Internet réel."
        )

    if query == "traffic_speed":
        if not policy.get("allow_passive_traffic_sample", True):
            return False, "La mesure passive du trafic réseau est désactivée."
        if not interfaces:
            return True, "Aucune interface réseau active à mesurer."
        sample = _sample_network_traffic([item["name"] for item in interfaces], seconds=1.0)
        if sample is None:
            return False, "Impossible de mesurer l'activité réseau actuelle."
        return True, (
            "Activité réseau observée pendant environ 1 seconde : "
            f"réception {_format_mbps(sample['download_mbps'])}, "
            f"envoi {_format_mbps(sample['upload_mbps'])}. "
            "Aucun trafic de test n'a été généré : ce résultat montre l'activité actuelle, pas le débit Internet maximal."
        )

    if query == "internet_speed":
        return True, (
            "Le test de débit Internet réel n'est pas activé, car il nécessiterait de contacter un serveur externe et de générer du trafic. "
            "Je peux vérifier la vitesse de liaison locale ou mesurer passivement l'activité réseau actuelle."
        )

    return False, "Information réseau non implémentée."


# ============================================================
# AUDIO WINDOWS CONTROLE - CORE AUDIO, AUCUN SHELL
# ============================================================


class _AudioGUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _audio_guid(value: str):
    parsed = uuid.UUID(str(value).strip("{}"))
    raw = parsed.bytes_le
    result = _AudioGUID()
    result.Data1 = int.from_bytes(raw[0:4], "little")
    result.Data2 = int.from_bytes(raw[4:6], "little")
    result.Data3 = int.from_bytes(raw[6:8], "little")
    for index in range(8):
        result.Data4[index] = raw[8 + index]
    return result


def _audio_release(pointer):
    if not pointer or not getattr(pointer, "value", None):
        return
    try:
        table = ctypes.cast(
            pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
        ).contents
        release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(table[2])
        release(pointer)
    except Exception:
        pass


def _audio_method(pointer, index, restype, *argtypes):
    table = ctypes.cast(
        pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
    ).contents
    prototype = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return prototype(table[index])


def _with_default_audio_endpoint(operation):
    """Exécute une opération bornée sur IAudioEndpointVolume du périphérique de sortie par défaut."""
    if os.name != "nt":
        return False, "Le contrôle audio est disponible uniquement sous Windows."

    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole32.CoInitializeEx.restype = ctypes.c_long
    ole32.CoCreateInstance.argtypes = [
        ctypes.POINTER(_AudioGUID), ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(_AudioGUID), ctypes.POINTER(ctypes.c_void_p),
    ]
    ole32.CoCreateInstance.restype = ctypes.c_long
    ole32.CoUninitialize.argtypes = []
    ole32.CoUninitialize.restype = None

    # COINIT_APARTMENTTHREADED = 0x2. RPC_E_CHANGED_MODE est acceptable :
    # le thread possède déjà un appartement COM compatible avec les appels.
    hr_init = int(ole32.CoInitializeEx(None, 0x2))
    init_code = hr_init & 0xFFFFFFFF
    if hr_init < 0 and init_code != 0x80010106:
        return False, "Windows n'a pas pu initialiser le contrôle audio."
    should_uninitialize = hr_init in (0, 1)

    enumerator = ctypes.c_void_p()
    device = ctypes.c_void_p()
    endpoint = ctypes.c_void_p()
    try:
        clsid_enum = _audio_guid("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
        iid_enum = _audio_guid("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
        hr = int(ole32.CoCreateInstance(
            ctypes.byref(clsid_enum), None, 23, ctypes.byref(iid_enum), ctypes.byref(enumerator)
        ))
        if hr < 0 or not enumerator.value:
            return False, "Windows n'a pas trouvé le gestionnaire audio par défaut."

        get_default = _audio_method(
            enumerator, 4, ctypes.c_long,
            ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p),
        )
        # eRender = 0. On essaie d'abord eMultimedia = 1, puis eConsole = 0.
        last_hr = -1
        for role in (1, 0):
            device.value = None
            last_hr = int(get_default(enumerator, 0, role, ctypes.byref(device)))
            if last_hr >= 0 and device.value:
                break
        if last_hr < 0 or not device.value:
            return False, "Aucun périphérique audio de sortie par défaut n'a été trouvé."

        iid_endpoint = _audio_guid("{5CDF2C82-841E-4546-9722-0CF74078229A}")
        activate = _audio_method(
            device, 3, ctypes.c_long,
            ctypes.POINTER(_AudioGUID), wintypes.DWORD, ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        )
        hr = int(activate(
            device, ctypes.byref(iid_endpoint), 23, None, ctypes.byref(endpoint)
        ))
        if hr < 0 or not endpoint.value:
            return False, "Windows n'a pas pu accéder au volume principal."

        return operation(endpoint)
    except Exception:
        return False, "Le contrôle audio Windows a rencontré une erreur locale."
    finally:
        _audio_release(endpoint)
        _audio_release(device)
        _audio_release(enumerator)
        if should_uninitialize:
            try:
                ole32.CoUninitialize()
            except Exception:
                pass


def _audio_get_state_raw(endpoint):
    volume = ctypes.c_float(0.0)
    muted = wintypes.BOOL(False)
    get_volume = _audio_method(
        endpoint, 9, ctypes.c_long, ctypes.POINTER(ctypes.c_float)
    )
    get_mute = _audio_method(
        endpoint, 15, ctypes.c_long, ctypes.POINTER(wintypes.BOOL)
    )
    if int(get_volume(endpoint, ctypes.byref(volume))) < 0:
        return False, "Windows n'a pas pu lire le niveau du volume."
    if int(get_mute(endpoint, ctypes.byref(muted))) < 0:
        return False, "Windows n'a pas pu lire l'état muet."
    percent = max(0, min(100, int(round(float(volume.value) * 100.0))))
    return True, {"percent": percent, "muted": bool(muted.value)}


def _audio_set_volume_raw(endpoint, percent: int):
    setter = _audio_method(
        endpoint, 7, ctypes.c_long, ctypes.c_float, ctypes.c_void_p
    )
    scalar = ctypes.c_float(max(0.0, min(1.0, float(percent) / 100.0)))
    if int(setter(endpoint, scalar, None)) < 0:
        return False, "Windows a refusé le changement de volume."
    return _audio_get_state_raw(endpoint)


def _audio_set_mute_raw(endpoint, muted: bool):
    setter = _audio_method(
        endpoint, 14, ctypes.c_long, wintypes.BOOL, ctypes.c_void_p
    )
    if int(setter(endpoint, wintypes.BOOL(bool(muted)), None)) < 0:
        return False, "Windows a refusé le changement du mode muet."
    return _audio_get_state_raw(endpoint)


def _audio_policy_check(explicit_user_command, source):
    return _manual_only_check("audio_control_policy", explicit_user_command, source)


def read_audio_state(explicit_user_command=False, source="manual"):
    ok, policy, error = _audio_policy_check(explicit_user_command, source)
    if not ok:
        return False, error
    if not policy.get("allow_read_volume", False):
        return False, "La lecture du volume est désactivée."

    success, state = _with_default_audio_endpoint(_audio_get_state_raw)
    if not success:
        return False, state
    status = "son coupé" if state["muted"] else "son actif"
    return True, f"Volume principal : {state['percent']}% — {status}."


def set_audio_volume(percent: int, explicit_user_command=False, source="manual"):
    ok, policy, error = _audio_policy_check(explicit_user_command, source)
    if not ok:
        return False, error
    if not policy.get("allow_set_volume", False):
        return False, "Le réglage précis du volume est désactivé."
    if isinstance(percent, bool) or not isinstance(percent, int):
        return False, "Le niveau de volume doit être un pourcentage entier."

    minimum = max(0, int(policy.get("minimum_volume_percent", 0)))
    maximum = min(100, int(policy.get("maximum_volume_percent", 100)))
    if minimum > maximum or percent < minimum or percent > maximum:
        return False, f"Le volume autorisé doit être compris entre {minimum}% et {maximum}%."

    success, state = _with_default_audio_endpoint(
        lambda endpoint: _audio_set_volume_raw(endpoint, percent)
    )
    if not success:
        return False, state
    suffix = " Le son reste coupé." if state["muted"] else ""
    return True, f"Volume réglé à {state['percent']}%.{suffix}"


def change_audio_volume(delta: int, explicit_user_command=False, source="manual"):
    ok, policy, error = _audio_policy_check(explicit_user_command, source)
    if not ok:
        return False, error
    if not policy.get("allow_relative_change", False):
        return False, "Le changement relatif du volume est désactivé."
    if isinstance(delta, bool) or not isinstance(delta, int) or delta == 0:
        return False, "La variation de volume est invalide."

    max_delta = max(1, min(50, int(policy.get("maximum_relative_change_percent", 25))))
    if abs(delta) > max_delta:
        return False, (
            f"Une variation relative est limitée à {max_delta}%. "
            "Pour un changement plus important, indique directement le niveau final, par exemple « mets le volume à 70% »."
        )

    minimum = max(0, int(policy.get("minimum_volume_percent", 0)))
    maximum = min(100, int(policy.get("maximum_volume_percent", 100)))

    def operation(endpoint):
        success, state = _audio_get_state_raw(endpoint)
        if not success:
            return False, state
        target = max(minimum, min(maximum, int(state["percent"]) + delta))
        return _audio_set_volume_raw(endpoint, target)

    success, state = _with_default_audio_endpoint(operation)
    if not success:
        return False, state
    suffix = " Le son reste coupé." if state["muted"] else ""
    return True, f"Volume principal : {state['percent']}%.{suffix}"


def set_audio_mute(muted: bool, explicit_user_command=False, source="manual"):
    ok, policy, error = _audio_policy_check(explicit_user_command, source)
    if not ok:
        return False, error
    if not policy.get("allow_mute_control", False):
        return False, "Le contrôle du mode muet est désactivé."
    if not isinstance(muted, bool):
        return False, "L'état du mode muet est invalide."

    success, state = _with_default_audio_endpoint(
        lambda endpoint: _audio_set_mute_raw(endpoint, muted)
    )
    if not success:
        return False, state
    if state["muted"]:
        return True, f"Son coupé. Le niveau reste réglé à {state['percent']}%."
    return True, f"Son réactivé. Volume principal : {state['percent']}%."


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




def _normalized_host(value: str):
    try:
        host = (urlparse(value).hostname or "").strip().lower().rstrip(".")
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def check_browser_site_open(site_name: str, explicit_user_command=False, source="manual"):
    """Vérifie en lecture seule si un site est déjà présent dans un onglet Edge."""
    ok, policy, error = _manual_only_check("browser_tab_policy", explicit_user_command, source)
    if not ok:
        return False, error
    if not policy.get("allow_check_site_open", False):
        return False, "La vérification des sites ouverts est désactivée."

    success, url, error = resolve_site(site_name)
    if not success:
        return False, error

    target_host = _normalized_host(url)
    if not target_host:
        return False, "Le site demandé n'a pas de domaine vérifiable."

    success, tabs, message = list_tabs_via_bridge()
    if not success:
        return False, message

    allow_subdomains = bool(policy.get("allow_subdomains", False))
    matches = 0
    for tab in tabs:
        host = _normalized_host(str(tab.get("url", "")))
        if not host:
            continue
        if host == target_host or (allow_subdomains and host.endswith("." + target_host)):
            matches += 1

    if matches:
        return True, f"Oui, {site_name} est ouvert dans Edge ({matches} onglet(s) correspondant(s))."
    return True, f"Non, je ne vois aucun onglet Edge ouvert pour {site_name}."


def open_browser_site_existing_window(site_name: str, explicit_user_command=False, source="manual"):
    """Ouvre un site dans une fenêtre Edge déjà existante, sans lancer Edge."""
    ok, policy, error = _manual_only_check("browser_tab_policy", explicit_user_command, source)
    if not ok:
        return False, error
    if not policy.get("allow_open_site_in_existing_window", False):
        return False, "L'ouverture dans une fenêtre Edge existante est désactivée."

    success, url, error = resolve_site(site_name)
    if not success:
        return False, error

    success, message = open_site_via_bridge(url)
    if not success:
        return False, message
    return True, f"Site ouvert dans la fenêtre Edge existante : {url}"

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
# CAPTURE D'ECRAN CONTROLEE - WINDOWS GDI, AUCUN SHELL
# ============================================================


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(chunk_type)
    crc = zlib.crc32(payload, crc) & 0xFFFFFFFF
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", crc)
    )


def _write_bgra_png(path: Path, width: int, height: int, bgra: bytes) -> None:
    """Ecrit un PNG RGB avec uniquement la bibliothèque standard."""
    compressor = zlib.compressobj(level=6)
    compressed_parts = []
    row_size = width * 4
    for row_index in range(height):
        start = row_index * row_size
        row = bgra[start:start + row_size]
        rgb = bytearray(width * 3)
        rgb[0::3] = row[2::4]  # R
        rgb[1::3] = row[1::4]  # G
        rgb[2::3] = row[0::4]  # B
        piece = compressor.compress(b"\x00" + bytes(rgb))
        if piece:
            compressed_parts.append(piece)
    tail = compressor.flush()
    if tail:
        compressed_parts.append(tail)
    payload = b"".join(compressed_parts)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        signature
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", payload)
        + _png_chunk(b"IEND", b"")
    )


def _capture_windows_rect_to_png(x: int, y: int, width: int, height: int, destination: Path):
    if os.name != "nt":
        return False, "La capture d'écran contrôlée est disponible uniquement sous Windows."
    if width <= 0 or height <= 0:
        return False, "Dimensions de capture invalides."

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    HANDLE = ctypes.c_void_p
    SRCCOPY = 0x00CC0020
    CAPTUREBLT = 0x40000000
    DIB_RGB_COLORS = 0
    BI_RGB = 0

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class RGBQUAD(ctypes.Structure):
        _fields_ = [
            ("rgbBlue", ctypes.c_ubyte),
            ("rgbGreen", ctypes.c_ubyte),
            ("rgbRed", ctypes.c_ubyte),
            ("rgbReserved", ctypes.c_ubyte),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [
            ("bmiHeader", BITMAPINFOHEADER),
            ("bmiColors", RGBQUAD * 1),
        ]

    user32.GetDC.argtypes = [HANDLE]
    user32.GetDC.restype = HANDLE
    user32.ReleaseDC.argtypes = [HANDLE, HANDLE]
    user32.ReleaseDC.restype = ctypes.c_int
    gdi32.CreateCompatibleDC.argtypes = [HANDLE]
    gdi32.CreateCompatibleDC.restype = HANDLE
    gdi32.CreateCompatibleBitmap.argtypes = [HANDLE, ctypes.c_int, ctypes.c_int]
    gdi32.CreateCompatibleBitmap.restype = HANDLE
    gdi32.SelectObject.argtypes = [HANDLE, HANDLE]
    gdi32.SelectObject.restype = HANDLE
    gdi32.BitBlt.argtypes = [
        HANDLE, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        HANDLE, ctypes.c_int, ctypes.c_int, wintypes.DWORD,
    ]
    gdi32.BitBlt.restype = wintypes.BOOL
    gdi32.GetDIBits.argtypes = [
        HANDLE, HANDLE, wintypes.UINT, wintypes.UINT, ctypes.c_void_p,
        ctypes.POINTER(BITMAPINFO), wintypes.UINT,
    ]
    gdi32.GetDIBits.restype = ctypes.c_int
    gdi32.DeleteObject.argtypes = [HANDLE]
    gdi32.DeleteObject.restype = wintypes.BOOL
    gdi32.DeleteDC.argtypes = [HANDLE]
    gdi32.DeleteDC.restype = wintypes.BOOL

    screen_dc = user32.GetDC(None)
    if not screen_dc:
        return False, "Impossible d'accéder à l'écran de façon sûre."

    memory_dc = None
    bitmap = None
    previous = None
    try:
        memory_dc = gdi32.CreateCompatibleDC(screen_dc)
        if not memory_dc:
            return False, "Impossible de préparer la capture d'écran."
        bitmap = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
        if not bitmap:
            return False, "Impossible de créer l'image de capture."
        previous = gdi32.SelectObject(memory_dc, bitmap)
        if not previous:
            return False, "Impossible de sélectionner l'image de capture."

        if not gdi32.BitBlt(
            memory_dc, 0, 0, width, height,
            screen_dc, x, y, SRCCOPY | CAPTUREBLT,
        ):
            return False, "Windows n'a pas pu copier l'image de l'écran."

        info = BITMAPINFO()
        info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        info.bmiHeader.biWidth = width
        info.bmiHeader.biHeight = -height  # top-down
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        info.bmiHeader.biCompression = BI_RGB
        image_size = width * height * 4
        buffer = ctypes.create_string_buffer(image_size)

        lines = gdi32.GetDIBits(
            memory_dc, bitmap, 0, height, buffer,
            ctypes.byref(info), DIB_RGB_COLORS,
        )
        if lines != height:
            return False, "Windows n'a pas pu lire tous les pixels de la capture."

        destination.parent.mkdir(parents=True, exist_ok=True)
        _write_bgra_png(destination, width, height, buffer.raw)
        return True, None
    finally:
        if previous and memory_dc:
            try:
                gdi32.SelectObject(memory_dc, previous)
            except Exception:
                pass
        if bitmap:
            gdi32.DeleteObject(bitmap)
        if memory_dc:
            gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(None, screen_dc)


def _screenshot_rect(mode: str):
    if os.name != "nt":
        return None, "La capture d'écran contrôlée est disponible uniquement sous Windows."

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int

    if mode == "full_screen":
        # Bureau virtuel : couvre aussi les écrans secondaires quand ils existent.
        x = user32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
        y = user32.GetSystemMetrics(77)   # SM_YVIRTUALSCREEN
        width = user32.GetSystemMetrics(78)   # SM_CXVIRTUALSCREEN
        height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
        return (x, y, width, height), None

    if mode == "active_window":
        user32.GetForegroundWindow.restype = ctypes.c_void_p
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None, "Aucune fenêtre active n'a été détectée."
        rect = wintypes.RECT()
        user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.RECT)]
        user32.GetWindowRect.restype = wintypes.BOOL
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None, "Impossible de lire les dimensions de la fenêtre active."
        width = int(rect.right - rect.left)
        height = int(rect.bottom - rect.top)
        return (int(rect.left), int(rect.top), width, height), None

    return None, "Mode de capture non autorisé."


def take_screenshot(mode: str, explicit_user_command=False, source="manual"):
    """Capture explicitement demandée, sauvegardée localement dans Images."""
    ok, policy, error = _manual_only_check(
        "screenshot_policy", explicit_user_command, source
    )
    if not ok:
        return False, error

    mode = str(mode or "").strip().lower()
    allowed_modes = set(policy.get("allowed_modes", []))
    if mode not in allowed_modes:
        return False, "Mode de capture non autorisé par la politique locale."
    if str(policy.get("format", "png")).lower() != "png":
        return False, "La politique de capture doit utiliser le format PNG."

    rect, error = _screenshot_rect(mode)
    if rect is None:
        return False, error
    x, y, width, height = rect

    max_pixels = int(policy.get("maximum_pixels", 40000000))
    max_pixels = max(1000000, min(max_pixels, 100000000))
    if width <= 0 or height <= 0 or width * height > max_pixels:
        return False, "La zone à capturer est trop grande pour la politique locale."

    pictures_root = resolve_allowed_root("pictures")
    if pictures_root is None:
        return False, "Le dossier Images n'est pas disponible dans les racines autorisées."

    folder_name = str(policy.get("subfolder", "Captures AgentLocal")).strip()
    if not folder_name or any(char in folder_name for char in '<>:"/\\|?*'):
        return False, "Le dossier de destination configuré est invalide."

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    label = "ecran" if mode == "full_screen" else "fenetre_active"
    output_dir = Path(pictures_root) / folder_name
    destination = output_dir / f"AgentLocal_{label}_{timestamp}.png"

    success, error = _capture_windows_rect_to_png(x, y, width, height, destination)
    if not success:
        return False, error

    try:
        relative = destination.relative_to(Path(pictures_root))
        display_path = f"Images\\{str(relative).replace('/', '\\')}"
    except ValueError:
        display_path = str(destination)
    return True, f"Capture enregistrée : {display_path}"


# ============================================================
# VALIDATION DE POLITIQUE POUR LE CONTRAT AGENT
# ============================================================

_ACTION_POLICY_MAP = {
    "read_system_info": "system_information_policy",
    "read_power_info": "power_information_policy",
    "read_network_info": "network_information_policy",
    "read_clipboard": "clipboard_policy",
    "write_clipboard": "clipboard_policy",
    "copy_file_path": "clipboard_policy",
    "list_browser_tabs": "browser_tab_policy",
    "activate_browser_tab": "browser_tab_policy",
    "check_browser_site": "browser_tab_policy",
    "open_browser_site_existing_edge": "browser_tab_policy",
    "open_last_reference": "session_context_policy",
    "read_last_reference": "session_context_policy",
    "copy_last_reference_path": "session_context_policy",
    "take_screenshot": "screenshot_policy",
    "read_audio_state": "audio_control_policy",
    "set_audio_volume": "audio_control_policy",
    "change_audio_volume": "audio_control_policy",
    "set_audio_mute": "audio_control_policy",
}


def validate_controlled_action_policy(action: str):
    policy_name = _ACTION_POLICY_MAP.get(str(action or "").strip().lower())
    if not policy_name:
        return False, "Action locale contrôlée inconnue."
    ok, _, error = _manual_only_check(policy_name, True, "manual")
    return (True, None) if ok else (False, error)
