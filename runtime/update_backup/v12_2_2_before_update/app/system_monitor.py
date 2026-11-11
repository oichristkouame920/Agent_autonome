"""Surveillance locale légère du PC pour AgentLocal V12.2."""
from __future__ import annotations

import ctypes
import json
import os
import shutil
import time
from collections import deque
from pathlib import Path

import psutil

ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT_DIR / "config" / "automation.json"


def load_monitor_config() -> dict:
    defaults = {
        "enabled": True,
        "scan_seconds": 15,
        "ram_warning_percent": 80,
        "ram_critical_percent": 92,
        "cpu_warning_percent": 85,
        "cpu_sustain_seconds": 120,
        "disk_warning_free_gb": 15,
        "disk_critical_free_gb": 5,
        "detect_hung_windows": True,
        "detect_suspended_processes": True,
        "max_process_alerts": 5,
    }
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
        cfg = data.get("health_monitor", {}) if isinstance(data, dict) else {}
        if isinstance(cfg, dict):
            defaults.update(cfg)
    except Exception:
        pass
    return defaults


def is_session_unlocked() -> bool:
    """Détecte si le bureau interactif Windows est actuellement accessible."""
    if os.name != "nt":
        return True
    try:
        user32 = ctypes.windll.user32
        DESKTOP_SWITCHDESKTOP = 0x0100
        handle = user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
        if not handle:
            return False
        try:
            return bool(user32.SwitchDesktop(handle))
        finally:
            user32.CloseDesktop(handle)
    except Exception:
        return True


def _network_interface_up() -> bool:
    try:
        stats = psutil.net_if_stats()
        for name, item in stats.items():
            low = name.lower()
            if item.isup and not low.startswith(("loopback", "lo")):
                return True
    except Exception:
        pass
    return False


def _hung_windows(limit: int = 5) -> list[dict]:
    if os.name != "nt":
        return []
    try:
        user32 = ctypes.windll.user32
        results: list[dict] = []
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        @EnumWindowsProc
        def callback(hwnd, _lparam):
            if len(results) >= limit:
                return False
            if not user32.IsWindowVisible(hwnd) or not user32.IsHungAppWindow(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            try:
                name = psutil.Process(pid.value).name()
            except Exception:
                name = "processus"
            results.append({"pid": int(pid.value), "name": name, "title": buf.value[:180]})
            return True

        user32.EnumWindows(callback, 0)
        return results
    except Exception:
        return []


def _suspended_processes(limit: int = 5) -> list[dict]:
    results = []
    stopped = {getattr(psutil, "STATUS_STOPPED", "stopped"), "stopped"}
    try:
        for proc in psutil.process_iter(["pid", "name", "status"]):
            try:
                if proc.info.get("status") in stopped:
                    results.append({"pid": proc.info.get("pid"), "name": proc.info.get("name") or "processus"})
                    if len(results) >= limit:
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return results


def collect_snapshot() -> dict:
    mem = psutil.virtual_memory()
    cpu = float(psutil.cpu_percent(interval=None))
    drive = os.environ.get("SystemDrive", "C:") + "\\" if os.name == "nt" else str(Path.home().anchor or "/")
    usage = shutil.disk_usage(drive)
    cfg = load_monitor_config()
    max_proc = max(1, min(int(cfg.get("max_process_alerts", 5) or 5), 10))
    return {
        "timestamp": time.time(),
        "cpu_percent": cpu,
        "ram_percent": float(mem.percent),
        "disk_free_bytes": int(usage.free),
        "disk_total_bytes": int(usage.total),
        "process_count": len(psutil.pids()),
        "network_interface_up": _network_interface_up(),
        "session_unlocked": is_session_unlocked(),
        "hung_windows": _hung_windows(max_proc) if cfg.get("detect_hung_windows", True) else [],
        "suspended_processes": _suspended_processes(max_proc) if cfg.get("detect_suspended_processes", True) else [],
    }


class SystemHealthMonitor:
    def __init__(self) -> None:
        self.cpu_samples: deque[tuple[float, float]] = deque(maxlen=240)

    def evaluate(self, snapshot: dict) -> list[dict]:
        cfg = load_monitor_config()
        now = float(snapshot.get("timestamp", time.time()))
        cpu = float(snapshot.get("cpu_percent", 0) or 0)
        ram = float(snapshot.get("ram_percent", 0) or 0)
        free_gb = float(snapshot.get("disk_free_bytes", 0) or 0) / (1024 ** 3)
        self.cpu_samples.append((now, cpu))
        sustain = max(10, int(cfg.get("cpu_sustain_seconds", 120) or 120))
        while self.cpu_samples and now - self.cpu_samples[0][0] > sustain + 30:
            self.cpu_samples.popleft()
        alerts = []

        ram_crit = float(cfg.get("ram_critical_percent", 92) or 92)
        ram_warn = float(cfg.get("ram_warning_percent", 80) or 80)
        if ram >= ram_crit:
            alerts.append({"code": "health.ram", "level": "critical", "title": "Mémoire presque saturée", "message": f"RAM utilisée : {ram:.0f} %."})
        elif ram >= ram_warn:
            alerts.append({"code": "health.ram", "level": "warning", "title": "Mémoire élevée", "message": f"RAM utilisée : {ram:.0f} %."})

        disk_crit = float(cfg.get("disk_critical_free_gb", 5) or 5)
        disk_warn = float(cfg.get("disk_warning_free_gb", 15) or 15)
        if free_gb < disk_crit:
            alerts.append({"code": "health.disk", "level": "critical", "title": "Espace disque critique", "message": f"Il reste environ {free_gb:.1f} Go libres sur le disque système."})
        elif free_gb < disk_warn:
            alerts.append({"code": "health.disk", "level": "warning", "title": "Espace disque faible", "message": f"Il reste environ {free_gb:.1f} Go libres sur le disque système."})

        cpu_warn = float(cfg.get("cpu_warning_percent", 85) or 85)
        samples = list(self.cpu_samples)
        high_since = None
        for stamp, value in reversed(samples):
            if value < cpu_warn:
                break
            high_since = stamp
        if high_since is not None and now - high_since >= sustain:
            alerts.append({"code": "health.cpu", "level": "warning", "title": "CPU élevé de façon prolongée", "message": f"CPU supérieur à {cpu_warn:.0f} % pendant environ {max(1, sustain // 60)} min."})

        if not bool(snapshot.get("network_interface_up", False)):
            alerts.append({"code": "health.network", "level": "warning", "title": "Réseau indisponible", "message": "Aucune interface réseau active n'a été détectée. Les fonctions locales restent disponibles."})

        for proc in snapshot.get("hung_windows", []) or []:
            pid = int(proc.get("pid", 0) or 0)
            name = str(proc.get("name", "processus"))
            alerts.append({"code": f"process.hung.{pid}", "level": "warning", "title": "Application ne répond pas", "message": f"{name} (PID {pid}) semble ne plus répondre."})

        for proc in snapshot.get("suspended_processes", []) or []:
            pid = int(proc.get("pid", 0) or 0)
            name = str(proc.get("name", "processus"))
            alerts.append({"code": f"process.suspended.{pid}", "level": "info", "title": "Processus suspendu", "message": f"{name} (PID {pid}) est actuellement suspendu."})
        return alerts
