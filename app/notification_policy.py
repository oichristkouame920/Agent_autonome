"""Politique locale de notifications AgentLocal V12.5.

Gère fréquence, anti-spam, heures calmes et résumés sans modifier le stockage
des alertes ni déclencher d'action système.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
from pathlib import Path

try:
    from user_profile import load_preferences
except Exception:
    from app.user_profile import load_preferences

ROOT_DIR = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT_DIR / "memory" / "notification_state.json"
SCHEMA_VERSION = 1


def _default_state() -> dict:
    return {"schema_version": SCHEMA_VERSION, "last_by_code": {}, "last_digest_at": ""}


def _load_state() -> dict:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict) and data.get("schema_version") == SCHEMA_VERSION:
            if not isinstance(data.get("last_by_code"), dict):
                data["last_by_code"] = {}
            return data
    except Exception:
        pass
    return _default_state()


def _save_state(data: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="notifications_", suffix=".tmp", dir=str(STATE_FILE.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(tmp, STATE_FILE)
    finally:
        try:
            Path(tmp).unlink(missing_ok=True)
        except OSError:
            pass


def _parse_iso(value: object) -> dt.datetime | None:
    try:
        parsed = dt.datetime.fromisoformat(str(value or ""))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
    except Exception:
        return None


def _minutes(value: str) -> int:
    try:
        h, m = str(value).split(":", 1)
        return int(h) * 60 + int(m)
    except Exception:
        return 0


def in_quiet_hours(now: dt.datetime | None = None) -> bool:
    now = now or dt.datetime.now().astimezone()
    cfg = load_preferences().get("notifications", {})
    quiet = cfg.get("quiet_hours", {}) if isinstance(cfg, dict) else {}
    if not isinstance(quiet, dict) or not quiet.get("enabled", False):
        return False
    start = _minutes(str(quiet.get("start", "18:30")))
    end = _minutes(str(quiet.get("end", "07:00")))
    current = now.hour * 60 + now.minute
    return (start <= current < end) if start < end else (current >= start or current < end)


def _category_allowed(item: dict, cfg: dict) -> bool:
    categories = cfg.get("categories", {}) if isinstance(cfg, dict) else {}
    if not isinstance(categories, dict):
        return True
    source = str(item.get("source", ""))
    code = str(item.get("code", ""))
    if source in {"system_monitor", "morning_automation"} or code.startswith(("health.", "process.")):
        return bool(categories.get("system", True))
    if code.startswith("service.") or source == "briefing":
        return bool(categories.get("briefing", True))
    if code.startswith("morning."):
        return bool(categories.get("routine", True))
    if code.startswith("learning."):
        return bool(categories.get("habits", True))
    if code.startswith("update."):
        return bool(categories.get("updates", True))
    return True


def popup_allowed(item: dict, now: dt.datetime | None = None) -> bool:
    now = now or dt.datetime.now().astimezone()
    prefs = load_preferences()
    cfg = prefs.get("notifications", {}) if isinstance(prefs, dict) else {}
    mode = str(cfg.get("mode", "balanced")).lower()
    level = str(item.get("level", "info")).lower()
    if mode == "silent" or not _category_allowed(item, cfg):
        return False
    quiet = cfg.get("quiet_hours", {}) if isinstance(cfg, dict) else {}
    if in_quiet_hours(now):
        if not (level == "critical" and bool(quiet.get("allow_critical", True))):
            return False
    if level == "critical" and bool(cfg.get("critical_immediate", True)):
        pass
    elif mode == "discreet":
        return False
    elif mode == "periodic":
        return False
    elif mode == "balanced" and level == "info":
        return False

    cooldown = int(cfg.get("repeat_cooldown_minutes", 60) or 60)
    cooldown = max(5, min(cooldown, 1440))
    state = _load_state()
    last = _parse_iso(state.get("last_by_code", {}).get(str(item.get("code", ""))))
    if last and (now - last).total_seconds() < cooldown * 60:
        return False
    return True


def mark_popup(item: dict, now: dt.datetime | None = None) -> None:
    now = now or dt.datetime.now().astimezone()
    code = str(item.get("code", "")).strip()
    if not code:
        return
    state = _load_state()
    state.setdefault("last_by_code", {})[code] = now.isoformat(timespec="seconds")
    _save_state(state)


def digest_due(active_alerts: list[dict], now: dt.datetime | None = None) -> bool:
    now = now or dt.datetime.now().astimezone()
    prefs = load_preferences(); cfg = prefs.get("notifications", {}) if isinstance(prefs, dict) else {}
    if str(cfg.get("mode", "balanced")).lower() != "periodic" or not active_alerts or in_quiet_hours(now):
        return False
    try:
        minutes = int(cfg.get("summary_minutes", 60) or 60)
    except (TypeError, ValueError):
        minutes = 60
    minutes = 30 if minutes not in {30, 60, 120, 240} else minutes
    last = _parse_iso(_load_state().get("last_digest_at"))
    return last is None or (now - last).total_seconds() >= minutes * 60


def mark_digest(now: dt.datetime | None = None) -> None:
    now = now or dt.datetime.now().astimezone()
    state = _load_state(); state["last_digest_at"] = now.isoformat(timespec="seconds"); _save_state(state)


def notification_mode_label() -> str:
    mode = str(load_preferences().get("notifications", {}).get("mode", "balanced"))
    return {"realtime": "Temps réel", "balanced": "Équilibré", "discreet": "Discret", "periodic": "Résumé périodique", "silent": "Silencieux"}.get(mode, "Équilibré")
