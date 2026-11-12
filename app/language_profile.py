"""Profil linguistique local V12.5.

Enregistre uniquement des expressions explicitement validées et un journal borné
des incompréhensions. Aucun contenu privé n'est observé en arrière-plan.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
FILE = ROOT_DIR / "memory" / "language_profile.json"
SCHEMA_VERSION = 1
MAX_EXPRESSIONS = 120
MAX_UNDERSTOOD_FAILURES = 80


def _default() -> dict:
    return {"schema_version": SCHEMA_VERSION, "expressions": {}, "unrecognized": []}


def _load() -> dict:
    try:
        data = json.loads(FILE.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict) and data.get("schema_version") == SCHEMA_VERSION:
            if not isinstance(data.get("expressions"), dict): data["expressions"] = {}
            if not isinstance(data.get("unrecognized"), list): data["unrecognized"] = []
            return data
    except Exception:
        pass
    return _default()


def _save(data: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="language_", suffix=".tmp", dir=str(FILE.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as h:
            json.dump(data, h, ensure_ascii=False, indent=2); h.write("\n"); h.flush()
            try: os.fsync(h.fileno())
            except OSError: pass
        os.replace(tmp, FILE)
    finally:
        try: Path(tmp).unlink(missing_ok=True)
        except OSError: pass


def summary() -> dict:
    data = _load()
    return {"learned": len(data["expressions"]), "unrecognized": len(data["unrecognized"])}


def learned_expressions(limit: int = 12) -> list[tuple[str, str]]:
    data = _load(); return list(data["expressions"].items())[: max(1, min(limit, 40))]


def resolve_expression(phrase: str) -> str | None:
    key = " ".join(str(phrase or "").strip().split()).casefold()
    if not key:
        return None
    value = _load().get("expressions", {}).get(key)
    return str(value).strip() if value else None

def remember_expression(phrase: str, intent: str) -> bool:
    phrase = " ".join(str(phrase or "").strip().split())[:160]
    intent = " ".join(str(intent or "").strip().split())[:120]
    if not phrase or not intent: return False
    data = _load(); data["expressions"][phrase.casefold()] = intent
    if len(data["expressions"]) > MAX_EXPRESSIONS:
        data["expressions"] = dict(list(data["expressions"].items())[-MAX_EXPRESSIONS:])
    _save(data); return True


def record_unrecognized(phrase: str) -> None:
    phrase = " ".join(str(phrase or "").strip().split())[:180]
    if not phrase: return
    data = _load()
    if phrase not in data["unrecognized"]:
        data["unrecognized"].append(phrase)
        data["unrecognized"] = data["unrecognized"][-MAX_UNDERSTOOD_FAILURES:]
        _save(data)


def clear_unrecognized() -> None:
    data = _load(); data["unrecognized"] = []; _save(data)
