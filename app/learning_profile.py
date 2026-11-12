"""Synthèse de la phase initiale d'apprentissage de l'hôte (V12.4).

Le module observe uniquement les métadonnées d'actions déjà enregistrées par
AgentLocal (type d'action, cible, heure). Il ne lit ni frappes clavier, ni contenu
d'e-mails/messages, ni contenu privé pour apprendre des habitudes.
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from collections import Counter
from pathlib import Path

from habit_tools import DATABASE_FILE, get_learning_summary, get_pending_habits
from user_profile import load_declared_habits, load_onboarding, load_preferences, save_onboarding, save_preferences


def _parse_iso(value: object) -> dt.datetime | None:
    try:
        parsed = dt.datetime.fromisoformat(str(value or ""))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
        return parsed
    except Exception:
        return None


def initial_learning_status(now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now().astimezone()
    prefs = load_preferences()
    state = load_onboarding()
    learning = prefs.get("learning", {})
    enabled = bool(learning.get("enabled", True))
    days = max(1, min(int(learning.get("initial_days", 2) or 2), 14))
    started = _parse_iso(state.get("initial_learning_started_at"))

    if not state.get("completed"):
        return {"status": "onboarding", "day": 0, "days": days, "progress": 0, "label": "Configuration initiale à terminer"}
    if not enabled:
        return {"status": "disabled", "day": 0, "days": days, "progress": 0, "label": "Apprentissage désactivé"}
    if started is None:
        state["initial_learning_started_at"] = now.isoformat(timespec="seconds")
        save_onboarding(state)
        started = now

    elapsed = max(0.0, (now - started).total_seconds())
    duration = days * 86400.0
    progress = max(0, min(100, int((elapsed / duration) * 100)))
    day = min(days, int(elapsed // 86400) + 1)
    complete = elapsed >= duration
    if complete and not state.get("initial_learning_completed_at"):
        state["initial_learning_completed_at"] = now.isoformat(timespec="seconds")
        save_onboarding(state)
    label = (
        "Phase initiale terminée · apprentissage continu actif"
        if complete and learning.get("continuous_learning", True)
        else "Phase initiale terminée"
        if complete
        else f"Jour {day} sur {days}"
    )
    return {"status": "complete" if complete else "learning", "day": day, "days": days, "progress": 100 if complete else progress, "label": label}


def _observed_targets(limit: int = 6) -> list[dict]:
    if not Path(DATABASE_FILE).exists():
        return []
    counter: Counter[str] = Counter()
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        try:
            rows = connection.execute(
                "SELECT actions_json FROM activity_sessions WHERE source='manual' ORDER BY created_at DESC LIMIT 250"
            ).fetchall()
        finally:
            connection.close()
    except Exception:
        return []
    for (raw,) in rows:
        try:
            actions = json.loads(raw)
        except Exception:
            continue
        if not isinstance(actions, list):
            continue
        for action in actions:
            if not isinstance(action, dict):
                continue
            kind = str(action.get("action", "")).strip()
            if kind not in {"open_application", "open_website"}:
                continue
            target = str(action.get("target", "")).strip()
            if target:
                counter[target] += 1
    return [{"target": name, "count": count} for name, count in counter.most_common(max(1, limit))]


def learning_dashboard() -> dict:
    status = initial_learning_status()
    declared = load_declared_habits()
    try:
        summary = get_learning_summary()
    except Exception:
        summary = {"manual_sessions": 0, "pending": 0, "accepted": 0, "rejected": 0, "drafts": 0}
    try:
        pending = get_pending_habits()[:6]
    except Exception:
        pending = []
    return {
        "initial": status,
        "declared": declared,
        "summary": summary,
        "pending": pending,
        "observed_targets": _observed_targets(),
    }


def restart_initial_learning() -> dict:
    state = load_onboarding()
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    state["initial_learning_started_at"] = now
    state["initial_learning_completed_at"] = ""
    save_onboarding(state)
    prefs = load_preferences()
    prefs["learning"]["enabled"] = True
    save_preferences(prefs)
    return initial_learning_status()


def set_learning_enabled(enabled: bool) -> dict:
    prefs = load_preferences()
    prefs["learning"]["enabled"] = bool(enabled)
    save_preferences(prefs)
    return initial_learning_status()
