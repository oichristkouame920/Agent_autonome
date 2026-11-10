"""Mémoire de session minimale pour AgentLocal.

V11.8 : contexte éphémère pour références de fichiers, dernière entité manipulée
et choix conversationnels en attente. Rien n'est persisté sur disque.
"""
from __future__ import annotations

import threading
from copy import deepcopy

_LOCK = threading.Lock()
_LAST_REFERENCE = None
_LAST_ENTITY = None
_PENDING_CHOICE = None


def set_last_reference(root_name: str, relative_path: str, item_type: str) -> None:
    root_name = str(root_name or "").strip().lower()
    relative_path = str(relative_path or "").strip()
    item_type = str(item_type or "").strip().lower()
    if not root_name or not relative_path or item_type not in {"file", "dir"}:
        return
    value = {"root_name": root_name, "relative_path": relative_path, "item_type": item_type}
    global _LAST_REFERENCE
    with _LOCK:
        _LAST_REFERENCE = value


def get_last_reference():
    with _LOCK:
        return deepcopy(_LAST_REFERENCE)


def set_last_entity(kind: str, target: str, action: str = "") -> None:
    kind = str(kind or "").strip().lower()
    target = str(target or "").strip()
    action = str(action or "").strip().lower()
    if kind not in {"application", "website", "browser_tab", "directory", "file"} or not target:
        return
    global _LAST_ENTITY
    with _LOCK:
        _LAST_ENTITY = {"kind": kind, "target": target, "action": action}


def get_last_entity():
    with _LOCK:
        return deepcopy(_LAST_ENTITY)


def set_pending_choice(prompt_id: str, choices: dict[str, str]) -> None:
    prompt_id = str(prompt_id or "").strip()
    clean: dict[str, str] = {}
    for key, command in (choices or {}).items():
        key = str(key or "").strip().lower()
        command = str(command or "").strip()
        if key and command:
            clean[key] = command
    global _PENDING_CHOICE
    with _LOCK:
        _PENDING_CHOICE = {"prompt_id": prompt_id, "choices": clean} if prompt_id and clean else None


def get_pending_choice():
    with _LOCK:
        return deepcopy(_PENDING_CHOICE)


def clear_pending_choice() -> None:
    global _PENDING_CHOICE
    with _LOCK:
        _PENDING_CHOICE = None


def resolve_pending_choice(value: str) -> str | None:
    text = str(value or "").strip().lower().replace("’", "'")
    text = " ".join(text.split()).strip(" .!?")
    if not text:
        return None
    with _LOCK:
        pending = deepcopy(_PENDING_CHOICE)
    if not pending:
        return None
    choices = pending.get("choices", {})
    command = choices.get(text)
    if command:
        clear_pending_choice()
        return command
    return None


def clear_session_context() -> None:
    global _LAST_REFERENCE, _LAST_ENTITY, _PENDING_CHOICE
    with _LOCK:
        _LAST_REFERENCE = None
        _LAST_ENTITY = None
        _PENDING_CHOICE = None
