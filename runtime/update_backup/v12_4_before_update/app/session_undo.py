"""Mémoire temporaire d'annulation fichier pour AgentLocal.

Une seule opération réversible est conservée en RAM pendant la session.
Aucune donnée n'est persistée sur disque.
"""
from __future__ import annotations

import time

_LAST_FILE_UNDO = None


def set_last_file_undo(record):
    global _LAST_FILE_UNDO
    if not isinstance(record, dict):
        _LAST_FILE_UNDO = None
        return
    value = dict(record)
    value["recorded_at_monotonic"] = time.monotonic()
    _LAST_FILE_UNDO = value


def get_last_file_undo(maximum_age_seconds=900):
    global _LAST_FILE_UNDO
    if not isinstance(_LAST_FILE_UNDO, dict):
        return None
    try:
        age = time.monotonic() - float(_LAST_FILE_UNDO.get("recorded_at_monotonic", 0.0))
        limit = max(1, int(maximum_age_seconds))
    except (TypeError, ValueError):
        _LAST_FILE_UNDO = None
        return None
    if age > limit:
        _LAST_FILE_UNDO = None
        return None
    return dict(_LAST_FILE_UNDO)


def clear_last_file_undo():
    global _LAST_FILE_UNDO
    _LAST_FILE_UNDO = None
