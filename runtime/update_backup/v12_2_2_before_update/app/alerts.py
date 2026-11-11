"""Stockage local et sûr des alertes AgentLocal V12.2."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
ALERTS_FILE = ROOT_DIR / "memory" / "alerts.json"
LOCK = threading.RLock()
SCHEMA_VERSION = 1
LEVELS = {"info", "warning", "critical"}
STATUSES = {"active", "resolved"}
MAX_ALERTS = 300
MAX_TEXT = 1200


def _default() -> dict:
    return {"schema_version": SCHEMA_VERSION, "alerts": []}


def _clean_text(value, limit=MAX_TEXT) -> str:
    return str(value or "").strip()[:limit]


def _load() -> dict:
    try:
        data = json.loads(ALERTS_FILE.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
            return _default()
        alerts = data.get("alerts")
        if not isinstance(alerts, list):
            return _default()
        clean = []
        for item in alerts[-MAX_ALERTS:]:
            if not isinstance(item, dict):
                continue
            level = str(item.get("level", "info")).lower()
            status = str(item.get("status", "active")).lower()
            if level not in LEVELS or status not in STATUSES:
                continue
            clean.append({
                "id": _clean_text(item.get("id"), 64) or f"a-{uuid.uuid4().hex[:10]}",
                "code": _clean_text(item.get("code"), 120),
                "level": level,
                "title": _clean_text(item.get("title"), 160),
                "message": _clean_text(item.get("message")),
                "source": _clean_text(item.get("source"), 100),
                "status": status,
                "seen": bool(item.get("seen", False)),
                "count": max(1, int(item.get("count", 1) or 1)),
                "created_at": _clean_text(item.get("created_at"), 64),
                "updated_at": _clean_text(item.get("updated_at"), 64),
                "resolved_at": _clean_text(item.get("resolved_at"), 64) or None,
            })
        return {"schema_version": SCHEMA_VERSION, "alerts": clean}
    except Exception:
        return _default()


def _save(data: dict) -> None:
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(prefix="alerts_", suffix=".json", dir=str(ALERTS_FILE.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        Path(tmp).replace(ALERTS_FILE)
    finally:
        try:
            Path(tmp).unlink(missing_ok=True)
        except OSError:
            pass


def raise_alert(code: str, level: str, title: str, message: str, source: str = "monitor") -> dict:
    code = _clean_text(code, 120)
    level = str(level or "info").lower()
    if not code or level not in LEVELS:
        raise ValueError("Alerte invalide")
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    with LOCK:
        data = _load()
        alerts = data["alerts"]
        existing = next((a for a in alerts if a.get("code") == code), None)
        if existing:
            existing.update({
                "level": level,
                "title": _clean_text(title, 160),
                "message": _clean_text(message),
                "source": _clean_text(source, 100),
                "status": "active",
                "seen": False,
                "updated_at": now,
                "resolved_at": None,
                "count": int(existing.get("count", 1) or 1) + 1,
            })
            item = existing
        else:
            item = {
                "id": f"a-{uuid.uuid4().hex[:10]}",
                "code": code,
                "level": level,
                "title": _clean_text(title, 160),
                "message": _clean_text(message),
                "source": _clean_text(source, 100),
                "status": "active",
                "seen": False,
                "count": 1,
                "created_at": now,
                "updated_at": now,
                "resolved_at": None,
            }
            alerts.append(item)
        data["alerts"] = alerts[-MAX_ALERTS:]
        _save(data)
        return dict(item)


def resolve_alert(code: str) -> bool:
    code = _clean_text(code, 120)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    changed = False
    with LOCK:
        data = _load()
        for item in data["alerts"]:
            if item.get("code") == code and item.get("status") == "active":
                item["status"] = "resolved"
                item["resolved_at"] = now
                item["updated_at"] = now
                changed = True
        if changed:
            _save(data)
    return changed


def resolve_missing(prefixes: tuple[str, ...], active_codes: set[str]) -> None:
    with LOCK:
        data = _load()
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        changed = False
        for item in data["alerts"]:
            code = str(item.get("code", ""))
            if item.get("status") == "active" and code.startswith(prefixes) and code not in active_codes:
                item["status"] = "resolved"
                item["resolved_at"] = now
                item["updated_at"] = now
                changed = True
        if changed:
            _save(data)


def mark_seen(alert_id: str) -> bool:
    key = _clean_text(alert_id, 64)
    with LOCK:
        data = _load()
        for item in data["alerts"]:
            if item.get("id") == key:
                item["seen"] = True
                item["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
                _save(data)
                return True
    return False


def list_alerts(status: str | None = None, limit: int = 100) -> list[dict]:
    data = _load()
    items = [dict(x) for x in data["alerts"]]
    if status in STATUSES:
        items = [x for x in items if x.get("status") == status]
    order = {"critical": 0, "warning": 1, "info": 2}
    items.sort(key=lambda x: (order.get(x.get("level"), 9), str(x.get("updated_at", ""))), reverse=False)
    return items[: max(1, min(int(limit or 100), 300))]


def get_alert_summary() -> dict:
    active = list_alerts("active", 300)
    return {
        "active": len(active),
        "critical": sum(1 for x in active if x.get("level") == "critical"),
        "warning": sum(1 for x in active if x.get("level") == "warning"),
        "info": sum(1 for x in active if x.get("level") == "info"),
        "unseen": sum(1 for x in active if not x.get("seen")),
    }
