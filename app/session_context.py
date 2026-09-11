"""Mémoire de session minimale pour AgentLocal.

Cette mémoire est volontairement éphémère : elle vit uniquement dans le
processus Python courant et n'est jamais écrite dans memory/ ni ailleurs.
Elle ne stocke qu'une dernière référence de fichier/dossier déjà résolue par
les garde-fous existants.
"""

from __future__ import annotations

import threading
from copy import deepcopy

_LOCK = threading.Lock()
_LAST_REFERENCE = None


def set_last_reference(root_name: str, relative_path: str, item_type: str) -> None:
    root_name = str(root_name or "").strip().lower()
    relative_path = str(relative_path or "").strip()
    item_type = str(item_type or "").strip().lower()

    if not root_name or not relative_path or item_type not in {"file", "dir"}:
        return

    value = {
        "root_name": root_name,
        "relative_path": relative_path,
        "item_type": item_type,
    }

    global _LAST_REFERENCE
    with _LOCK:
        _LAST_REFERENCE = value


def get_last_reference():
    with _LOCK:
        return deepcopy(_LAST_REFERENCE)


def clear_session_context() -> None:
    global _LAST_REFERENCE
    with _LOCK:
        _LAST_REFERENCE = None
