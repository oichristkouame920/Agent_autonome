"""Profil local et préférences de l'hôte pour AgentLocal V12.4.

Aucune donnée de profil n'est embarquée dans le pack distribué. Les fichiers sont
créés sous memory/ sur chaque machine. Les écritures sont atomiques et les valeurs
sont bornées afin qu'une configuration corrompue ne puisse pas modifier les règles
de sécurité d'AgentLocal.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import socket
import tempfile
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT_DIR / "memory"
PROFILE_FILE = MEMORY_DIR / "user_profile.json"
PREFERENCES_FILE = MEMORY_DIR / "user_preferences.json"
ONBOARDING_FILE = MEMORY_DIR / "onboarding_state.json"
DECLARED_HABITS_FILE = MEMORY_DIR / "declared_habits.json"

SCHEMA_VERSION = 1

DEFAULT_PROFILE = {
    "schema_version": SCHEMA_VERSION,
    "display_name": "",
    "machine_name": "",
    "usage_mode": "work",
    "language": "fr",
    "configured": False,
    "created_at": "",
    "updated_at": "",
}

DEFAULT_PREFERENCES = {
    "schema_version": SCHEMA_VERSION,
    "assistant": {
        "response_style": "natural",
        "emoji_level": "light",
        "daily_quote": True,
        "smart_suggestions": True,
        "response_detail": "balanced",
    },
    "learning": {
        "enabled": True,
        "onboarding_mode": "hybrid",
        "initial_days": 2,
        "continuous_learning": True,
    },
    "morning": {
        "enabled": True,
        "start_time": "07:00",
        "end_time": "09:30",
        "trigger": "first_unlock_seen",
    },
    "briefing": {
        "enabled": True,
        "topics": {
            "middle_east": True,
            "ukraine": True,
            "oil_energy": True,
            "technology": True,
            "military_defense": True,
            "major_geopolitics": True,
            "france_domestic": False,
            "protests": False,
            "sports": False,
            "entertainment": False,
        },
    },
    "alerts": {
        "enabled": True,
        "background_notifications": True,
    },
    "appearance": {
        "theme": "agentlocal",
        "accent_color": "#356AE6",
        "sidebar_color": "#101A2E",
        "card_color": "#FFFFFF",
        "density": "comfortable",
        "font_scale": 1.0,
        "patterns": True,
        "animations": True,
        "home_cards": {
            "pc": True,
            "briefing": True,
            "routine": True,
            "alerts": True,
            "quote": True,
            "habits": True,
            "network": False,
            "processes": False,
        },
    },
    "notifications": {
        "mode": "balanced",
        "summary_minutes": 60,
        "critical_immediate": True,
        "repeat_cooldown_minutes": 60,
        "quiet_hours": {
            "enabled": False,
            "start": "18:30",
            "end": "07:00",
            "allow_critical": True,
        },
        "categories": {
            "system": True,
            "briefing": True,
            "routine": True,
            "habits": True,
            "updates": True,
        },
    },
    "understanding": {
        "typo_tolerance": 2,
        "store_unrecognized": True,
        "learn_confirmed_expressions": True,
        "context_turns": 4,
    },
    "privacy": {
        "observe_action_metadata": True,
        "observe_private_content": False,
        "capture_keystrokes": False,
        "automatic_sensitive_actions": False,
    },
}

DEFAULT_ONBOARDING = {
    "schema_version": SCHEMA_VERSION,
    "completed": False,
    "current_step": 0,
    "started_at": "",
    "completed_at": "",
    "initial_learning_started_at": "",
    "initial_learning_completed_at": "",
}

DEFAULT_DECLARED_HABITS = {
    "schema_version": SCHEMA_VERSION,
    "typical_start_time": "07:30",
    "typical_end_time": "",
    "frequent_apps": [],
    "frequent_sites": [],
    "notes": "",
    "updated_at": "",
}

_ALLOWED_USAGE = {"work", "personal", "mixed"}
_ALLOWED_RESPONSE_STYLE = {"natural", "professional", "concise"}
_ALLOWED_EMOJI = {"none", "light", "expressive"}
_ALLOWED_DETAIL = {"short", "balanced", "detailed"}
_ALLOWED_ONBOARDING = {"questions", "observe", "hybrid"}
_KNOWN_TOPICS = set(DEFAULT_PREFERENCES["briefing"]["topics"])
_ALLOWED_THEMES = {"agentlocal", "minimal", "blue_night", "dark", "nature", "violet", "enterprise", "windows"}
_ALLOWED_DENSITY = {"compact", "comfortable"}
_ALLOWED_NOTIFICATION_MODES = {"realtime", "balanced", "discreet", "periodic", "silent"}


def _now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def default_machine_name() -> str:
    try:
        value = socket.gethostname().strip()
    except Exception:
        value = ""
    return value[:80] or "PC-Windows"


def _deep_merge(default: dict, value: object) -> dict:
    result = copy.deepcopy(default)
    if not isinstance(value, dict):
        return result
    for key, incoming in value.items():
        if key not in result:
            continue
        if isinstance(result[key], dict) and isinstance(incoming, dict):
            result[key] = _deep_merge(result[key], incoming)
        else:
            result[key] = incoming
    return result


def _load(path: Path, default: dict) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return copy.deepcopy(default)
    return _deep_merge(default, data)


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f"{path.stem}_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(tmp_name, path)
    finally:
        try:
            Path(tmp_name).unlink(missing_ok=True)
        except OSError:
            pass


def _clean_text(value: object, limit: int) -> str:
    text = " ".join(str(value or "").strip().split())
    return text[:limit]


def _valid_hhmm(value: object, fallback: str) -> str:
    try:
        hour_s, minute_s = str(value).strip().split(":", 1)
        hour, minute = int(hour_s), int(minute_s)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    except Exception:
        pass
    return fallback


def sanitize_profile(data: object) -> dict:
    value = _deep_merge(DEFAULT_PROFILE, data)
    value["schema_version"] = SCHEMA_VERSION
    value["display_name"] = _clean_text(value.get("display_name"), 60)
    value["machine_name"] = _clean_text(value.get("machine_name"), 80) or default_machine_name()
    usage = str(value.get("usage_mode", "work")).strip().lower()
    value["usage_mode"] = usage if usage in _ALLOWED_USAGE else "work"
    value["language"] = "fr"
    value["configured"] = bool(value.get("configured", False))
    value["created_at"] = _clean_text(value.get("created_at"), 40)
    value["updated_at"] = _clean_text(value.get("updated_at"), 40)
    return value


def sanitize_preferences(data: object) -> dict:
    value = _deep_merge(DEFAULT_PREFERENCES, data)
    value["schema_version"] = SCHEMA_VERSION

    assistant = value["assistant"]
    style = str(assistant.get("response_style", "natural")).strip().lower()
    assistant["response_style"] = style if style in _ALLOWED_RESPONSE_STYLE else "natural"
    emoji = str(assistant.get("emoji_level", "light")).strip().lower()
    assistant["emoji_level"] = emoji if emoji in _ALLOWED_EMOJI else "light"
    assistant["daily_quote"] = bool(assistant.get("daily_quote", True))
    assistant["smart_suggestions"] = bool(assistant.get("smart_suggestions", True))
    detail = str(assistant.get("response_detail", "balanced")).strip().lower()
    assistant["response_detail"] = detail if detail in _ALLOWED_DETAIL else "balanced"

    learning = value["learning"]
    learning["enabled"] = bool(learning.get("enabled", True))
    mode = str(learning.get("onboarding_mode", "hybrid")).strip().lower()
    learning["onboarding_mode"] = mode if mode in _ALLOWED_ONBOARDING else "hybrid"
    try:
        days = int(learning.get("initial_days", 2) or 2)
    except (TypeError, ValueError):
        days = 2
    learning["initial_days"] = max(1, min(days, 14))
    learning["continuous_learning"] = bool(learning.get("continuous_learning", True))

    morning = value["morning"]
    morning["enabled"] = bool(morning.get("enabled", True))
    morning["start_time"] = _valid_hhmm(morning.get("start_time"), "07:00")
    morning["end_time"] = _valid_hhmm(morning.get("end_time"), "09:30")
    morning["trigger"] = "first_unlock_seen"

    briefing = value["briefing"]
    briefing["enabled"] = bool(briefing.get("enabled", True))
    topics = briefing.get("topics", {})
    if not isinstance(topics, dict):
        topics = {}
    briefing["topics"] = {key: bool(topics.get(key, DEFAULT_PREFERENCES["briefing"]["topics"][key])) for key in _KNOWN_TOPICS}

    alerts = value["alerts"]
    alerts["enabled"] = bool(alerts.get("enabled", True))
    alerts["background_notifications"] = bool(alerts.get("background_notifications", True))

    appearance = value["appearance"]
    theme = str(appearance.get("theme", "agentlocal")).strip().lower()
    appearance["theme"] = theme if theme in _ALLOWED_THEMES else "agentlocal"
    density = str(appearance.get("density", "comfortable")).strip().lower()
    appearance["density"] = density if density in _ALLOWED_DENSITY else "comfortable"
    for field, fallback in (("accent_color", "#356AE6"), ("sidebar_color", "#101A2E"), ("card_color", "#FFFFFF")):
        text = str(appearance.get(field, fallback)).strip()
        if len(text) != 7 or not text.startswith("#"):
            text = fallback
        try:
            int(text[1:], 16)
        except Exception:
            text = fallback
        appearance[field] = text.upper()
    try:
        scale = float(appearance.get("font_scale", 1.0) or 1.0)
    except (TypeError, ValueError):
        scale = 1.0
    appearance["font_scale"] = max(0.85, min(scale, 1.25))
    appearance["patterns"] = bool(appearance.get("patterns", True))
    appearance["animations"] = bool(appearance.get("animations", True))
    home_cards = appearance.get("home_cards", {})
    if not isinstance(home_cards, dict):
        home_cards = {}
    appearance["home_cards"] = {key: bool(home_cards.get(key, default)) for key, default in DEFAULT_PREFERENCES["appearance"]["home_cards"].items()}

    notifications = value["notifications"]
    mode = str(notifications.get("mode", "balanced")).strip().lower()
    notifications["mode"] = mode if mode in _ALLOWED_NOTIFICATION_MODES else "balanced"
    try:
        summary_minutes = int(notifications.get("summary_minutes", 60) or 60)
    except (TypeError, ValueError):
        summary_minutes = 60
    notifications["summary_minutes"] = summary_minutes if summary_minutes in {30, 60, 120, 240} else 60
    notifications["critical_immediate"] = bool(notifications.get("critical_immediate", True))
    try:
        cooldown = int(notifications.get("repeat_cooldown_minutes", 60) or 60)
    except (TypeError, ValueError):
        cooldown = 60
    notifications["repeat_cooldown_minutes"] = max(5, min(cooldown, 1440))
    quiet = notifications.get("quiet_hours", {})
    if not isinstance(quiet, dict): quiet = {}
    notifications["quiet_hours"] = {
        "enabled": bool(quiet.get("enabled", False)),
        "start": _valid_hhmm(quiet.get("start"), "18:30"),
        "end": _valid_hhmm(quiet.get("end"), "07:00"),
        "allow_critical": bool(quiet.get("allow_critical", True)),
    }
    categories = notifications.get("categories", {})
    if not isinstance(categories, dict): categories = {}
    notifications["categories"] = {key: bool(categories.get(key, default)) for key, default in DEFAULT_PREFERENCES["notifications"]["categories"].items()}

    understanding = value["understanding"]
    try:
        typo = int(understanding.get("typo_tolerance", 2) or 2)
    except (TypeError, ValueError):
        typo = 2
    understanding["typo_tolerance"] = max(0, min(typo, 3))
    understanding["store_unrecognized"] = bool(understanding.get("store_unrecognized", True))
    understanding["learn_confirmed_expressions"] = bool(understanding.get("learn_confirmed_expressions", True))
    try:
        turns = int(understanding.get("context_turns", 4) or 4)
    except (TypeError, ValueError):
        turns = 4
    understanding["context_turns"] = max(1, min(turns, 8))

    # Ces quatre garanties sont volontairement fermées : elles ne sont pas
    # reconfigurables vers un état moins sûr depuis l'interface utilisateur.
    privacy = value["privacy"]
    privacy["observe_action_metadata"] = bool(privacy.get("observe_action_metadata", True))
    privacy["observe_private_content"] = False
    privacy["capture_keystrokes"] = False
    privacy["automatic_sensitive_actions"] = False
    return value


def sanitize_onboarding(data: object) -> dict:
    value = _deep_merge(DEFAULT_ONBOARDING, data)
    value["schema_version"] = SCHEMA_VERSION
    value["completed"] = bool(value.get("completed", False))
    try:
        step = int(value.get("current_step", 0) or 0)
    except (TypeError, ValueError):
        step = 0
    value["current_step"] = max(0, min(step, 6))
    for field in ("started_at", "completed_at", "initial_learning_started_at", "initial_learning_completed_at"):
        value[field] = _clean_text(value.get(field), 40)
    return value


def sanitize_declared_habits(data: object) -> dict:
    value = _deep_merge(DEFAULT_DECLARED_HABITS, data)
    value["schema_version"] = SCHEMA_VERSION
    value["typical_start_time"] = _valid_hhmm(value.get("typical_start_time"), "07:30")
    end = _clean_text(value.get("typical_end_time"), 8)
    value["typical_end_time"] = _valid_hhmm(end, "") if end else ""
    for field in ("frequent_apps", "frequent_sites"):
        rows = value.get(field, [])
        if not isinstance(rows, list):
            rows = []
        clean: list[str] = []
        for row in rows:
            item = _clean_text(row, 80)
            if item and item not in clean:
                clean.append(item)
        value[field] = clean[:20]
    value["notes"] = _clean_text(value.get("notes"), 300)
    value["updated_at"] = _clean_text(value.get("updated_at"), 40)
    return value


def load_profile() -> dict:
    profile = sanitize_profile(_load(PROFILE_FILE, DEFAULT_PROFILE))
    if not profile["machine_name"]:
        profile["machine_name"] = default_machine_name()
    return profile


def save_profile(profile: dict) -> dict:
    value = sanitize_profile(profile)
    now = _now_iso()
    if not value.get("created_at"):
        value["created_at"] = now
    value["updated_at"] = now
    _atomic_write(PROFILE_FILE, value)
    return copy.deepcopy(value)


def load_preferences() -> dict:
    return sanitize_preferences(_load(PREFERENCES_FILE, DEFAULT_PREFERENCES))


def save_preferences(preferences: dict) -> dict:
    value = sanitize_preferences(preferences)
    _atomic_write(PREFERENCES_FILE, value)
    return copy.deepcopy(value)


def load_onboarding() -> dict:
    return sanitize_onboarding(_load(ONBOARDING_FILE, DEFAULT_ONBOARDING))


def save_onboarding(state: dict) -> dict:
    value = sanitize_onboarding(state)
    if not value.get("started_at"):
        value["started_at"] = _now_iso()
    _atomic_write(ONBOARDING_FILE, value)
    return copy.deepcopy(value)


def load_declared_habits() -> dict:
    return sanitize_declared_habits(_load(DECLARED_HABITS_FILE, DEFAULT_DECLARED_HABITS))


def save_declared_habits(data: dict) -> dict:
    value = sanitize_declared_habits(data)
    value["updated_at"] = _now_iso()
    _atomic_write(DECLARED_HABITS_FILE, value)
    return copy.deepcopy(value)


def is_onboarding_complete() -> bool:
    return bool(load_onboarding().get("completed", False))


def begin_onboarding() -> dict:
    state = load_onboarding()
    state["completed"] = False
    state["current_step"] = 1
    if not state.get("started_at"):
        state["started_at"] = _now_iso()
    return save_onboarding(state)


def complete_onboarding(*, profile: dict, preferences: dict, declared_habits: dict) -> None:
    profile = dict(profile)
    profile["configured"] = True
    save_profile(profile)
    preferences = save_preferences(preferences)
    save_declared_habits(declared_habits)
    state = load_onboarding()
    now = _now_iso()
    state.update({
        "completed": True,
        "current_step": 6,
        "completed_at": now,
        "initial_learning_started_at": now if preferences["learning"]["enabled"] else "",
        "initial_learning_completed_at": "",
    })
    save_onboarding(state)


def reset_onboarding() -> None:
    state = copy.deepcopy(DEFAULT_ONBOARDING)
    state["started_at"] = _now_iso()
    save_onboarding(state)


def get_display_name(fallback: str = "") -> str:
    return str(load_profile().get("display_name") or fallback).strip()


def preference(path: str, default: Any = None) -> Any:
    current: Any = load_preferences()
    for part in str(path or "").split("."):
        if not part or not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return copy.deepcopy(current)


def update_preference(path: str, value: Any) -> dict:
    prefs = load_preferences()
    parts = [p for p in str(path or "").split(".") if p]
    if not parts:
        return prefs
    current = prefs
    for part in parts[:-1]:
        node = current.get(part)
        if not isinstance(node, dict):
            return prefs
        current = node
    if parts[-1] not in current:
        return prefs
    current[parts[-1]] = value
    return save_preferences(prefs)
