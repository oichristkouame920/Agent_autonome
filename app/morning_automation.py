"""Déclencheur de routine matinale au premier déverrouillage observé."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, time as dtime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT_DIR / "config" / "automation.json"
STATE_FILE = ROOT_DIR / "memory" / "morning_automation_state.json"
PREFERENCES_FILE = ROOT_DIR / "memory" / "user_preferences.json"


def load_config() -> dict:
    default = {
        "enabled": True,
        "start_time": "07:00",
        "end_time": "09:30",
        "trigger": "first_unlock_seen",
        "once_per_day": True,
        "show_popup": True,
        "late_prompt_after_window": True,
        "actions": ["system_health", "pending_tasks", "briefing"],
    }
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
        cfg = data.get("morning_automation", {}) if isinstance(data, dict) else {}
        if isinstance(cfg, dict):
            default.update(cfg)
    except Exception:
        pass
    # Les préférences de l'hôte peuvent ajuster la fenêtre et activer/désactiver
    # la routine, mais jamais changer le déclencheur de sécurité.
    try:
        prefs = json.loads(PREFERENCES_FILE.read_text(encoding="utf-8-sig"))
        morning = prefs.get("morning", {}) if isinstance(prefs, dict) else {}
        if isinstance(morning, dict):
            for key in ("enabled", "start_time", "end_time"):
                if key in morning:
                    default[key] = morning[key]
    except Exception:
        pass
    default["trigger"] = "first_unlock_seen"
    return default


def _parse_hhmm(value: str, fallback: dtime) -> dtime:
    try:
        h, m = str(value).split(":", 1)
        h, m = int(h), int(m)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return dtime(h, m)
    except Exception:
        pass
    return fallback


def _load_state() -> dict:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(prefix="morning_", suffix=".json", dir=str(STATE_FILE.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        Path(tmp).replace(STATE_FILE)
    finally:
        try:
            Path(tmp).unlink(missing_ok=True)
        except OSError:
            pass


def morning_status(now: datetime | None = None, unlocked: bool = True) -> dict:
    now = now or datetime.now().astimezone()
    cfg = load_config()
    state = _load_state()
    today = now.date().isoformat()
    start = _parse_hhmm(cfg.get("start_time", "07:00"), dtime(7, 0))
    end = _parse_hhmm(cfg.get("end_time", "09:30"), dtime(9, 30))
    current = now.timetz().replace(tzinfo=None)
    done = state.get("last_completed_date") == today
    if not cfg.get("enabled", True):
        status = "disabled"
    elif done:
        status = "done"
    elif current < start:
        status = "waiting_window"
    elif current <= end:
        status = "due" if unlocked else "waiting_unlock"
    else:
        status = "missed"
    return {"status": status, "config": cfg, "state": state, "start": start.strftime("%H:%M"), "end": end.strftime("%H:%M")}


def should_trigger(now: datetime | None = None, unlocked: bool = True) -> bool:
    return morning_status(now, unlocked).get("status") == "due"


def mark_completed(success: bool = True, now: datetime | None = None, summary: str = "") -> None:
    now = now or datetime.now().astimezone()
    state = _load_state()
    state.update({
        "last_completed_date": now.date().isoformat(),
        "last_completed_at": now.isoformat(timespec="seconds"),
        "last_success": bool(success),
        "last_summary": str(summary or "")[:1000],
    })
    _save_state(state)


def mark_late_prompted(now: datetime | None = None) -> None:
    now = now or datetime.now().astimezone()
    state = _load_state()
    state["last_late_prompt_date"] = now.date().isoformat()
    _save_state(state)


def should_prompt_late(now: datetime | None = None, unlocked: bool = True) -> bool:
    now = now or datetime.now().astimezone()
    status = morning_status(now, unlocked)
    if status.get("status") != "missed" or not unlocked:
        return False
    cfg = status.get("config", {})
    if not cfg.get("late_prompt_after_window", True):
        return False
    state = status.get("state", {})
    return state.get("last_late_prompt_date") != now.date().isoformat()
