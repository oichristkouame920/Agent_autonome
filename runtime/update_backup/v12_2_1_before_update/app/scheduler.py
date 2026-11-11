"""Planificateur local AgentLocal V12.1 R2.

Durcissement R2 :
- validation stricte des donnees persistantes avant toute execution ;
- sauvegarde automatique d'un fichier schedules.json corrompu ;
- ecriture atomique + fsync ;
- limite du nombre de planifications ;
- prevention des doublons exacts ;
- verrou d'execution inter-processus par jour pour eviter une double execution ;
- aucune planification n'est activee sans confirmation explicite.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT_DIR / "memory" / "schedules.json"
CLAIM_DIR = ROOT_DIR / "runtime" / "schedule_claims"
LOCK = threading.RLock()
SCHEMA_VERSION = 1
MAX_SCHEDULES = 64
MAX_RESULT_LENGTH = 500
ALLOWED_KINDS = {"routine", "briefing", "habit_summary"}
WEEKDAYS = {
    "lundi": 0,
    "mardi": 1,
    "mercredi": 2,
    "jeudi": 3,
    "vendredi": 4,
    "samedi": 5,
    "dimanche": 6,
}
_ID_RE = re.compile(r"p-[0-9a-f]{8}")
_ROUTINE_RE = re.compile(r"[a-z0-9_-]+")
_TIME_RE = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _default_config() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "enabled": True,
        "poll_seconds": 20,
        "catch_up_minutes": 60,
        "schedules": {},
    }


def _bounded_int(value, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _sanitize_trigger(trigger: object) -> dict | None:
    if not isinstance(trigger, dict) or trigger.get("type") != "weekly":
        return None
    time_value = str(trigger.get("time", "")).strip()
    if not _TIME_RE.fullmatch(time_value):
        return None
    days = trigger.get("days")
    if not isinstance(days, list) or not days:
        return None
    if any(type(day) is not int or day < 0 or day > 6 for day in days):
        return None
    clean_days = sorted(set(days))
    if not clean_days:
        return None
    return {"type": "weekly", "time": time_value, "days": clean_days}


def _sanitize_schedule(schedule_id: str, item: object) -> dict | None:
    schedule_id = str(schedule_id or "").strip().lower()
    if not _ID_RE.fullmatch(schedule_id) or not isinstance(item, dict):
        return None

    kind = str(item.get("kind", "")).strip().lower()
    if kind not in ALLOWED_KINDS:
        return None

    target = str(item.get("target", "")).strip().lower()
    if kind == "routine":
        if not _ROUTINE_RE.fullmatch(target):
            return None
    elif target != "today":
        return None

    trigger = _sanitize_trigger(item.get("trigger"))
    if trigger is None:
        return None

    confirmed = bool(item.get("confirmed", False))
    # Une planification jamais confirmee ne peut pas etre activee, meme si le
    # fichier JSON a ete modifie manuellement.
    enabled = bool(item.get("enabled", False)) and confirmed

    name = str(item.get("name") or _default_name(kind, target)).strip()[:120]
    if not name:
        name = _default_name(kind, target)

    clean = {
        "id": schedule_id,
        "name": name,
        "kind": kind,
        "target": target,
        "trigger": trigger,
        "confirmed": confirmed,
        "enabled": enabled,
        "created_at": str(item.get("created_at") or "")[:64] or None,
        "last_run_at": str(item.get("last_run_at") or "")[:64] or None,
        "last_run_local_date": None,
        "last_result": None,
    }

    last_date = str(item.get("last_run_local_date") or "").strip()
    if _DATE_RE.fullmatch(last_date):
        clean["last_run_local_date"] = last_date

    confirmed_at = str(item.get("confirmed_at") or "").strip()
    if confirmed_at:
        clean["confirmed_at"] = confirmed_at[:64]

    result = item.get("last_result")
    if isinstance(result, dict):
        clean["last_result"] = {
            "success": bool(result.get("success", False)),
            "message": str(result.get("message") or "")[:MAX_RESULT_LENGTH],
        }
    return clean


def _sanitize_config(data: object) -> dict:
    default = _default_config()
    if not isinstance(data, dict) or data.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        return default

    schedules = data.get("schedules")
    clean_schedules: dict[str, dict] = {}
    if isinstance(schedules, dict):
        for schedule_id, item in schedules.items():
            clean = _sanitize_schedule(str(schedule_id), item)
            if clean is not None:
                clean_schedules[clean["id"]] = clean
            if len(clean_schedules) >= MAX_SCHEDULES:
                break

    return {
        "schema_version": SCHEMA_VERSION,
        "enabled": bool(data.get("enabled", True)),
        "poll_seconds": _bounded_int(data.get("poll_seconds"), 20, 10, 300),
        "catch_up_minutes": _bounded_int(data.get("catch_up_minutes"), 60, 0, 1440),
        "schedules": clean_schedules,
    }


def _backup_invalid_config() -> None:
    if not CONFIG_FILE.exists():
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = CONFIG_FILE.with_name(f"schedules.corrupt-{stamp}.json")
    try:
        # copy instead of rename: even if the backup fails, the original is not
        # removed before recovery is ready to be written.
        backup.write_bytes(CONFIG_FILE.read_bytes())
    except OSError:
        return


def _atomic_write(data: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    clean = _sanitize_config(data)
    text = json.dumps(clean, ensure_ascii=False, indent=2) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix="schedules_", suffix=".json", dir=str(CONFIG_FILE.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", closefd=True) as handle:
            handle.write(text)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        Path(tmp_name).replace(CONFIG_FILE)
    finally:
        try:
            Path(tmp_name).unlink(missing_ok=True)
        except OSError:
            pass


def load_config() -> dict:
    with LOCK:
        if not CONFIG_FILE.exists():
            data = _default_config()
            _atomic_write(data)
            return data
        try:
            raw = CONFIG_FILE.read_text(encoding="utf-8")
            parsed = json.loads(raw)
        except (OSError, UnicodeError, json.JSONDecodeError):
            _backup_invalid_config()
            data = _default_config()
            try:
                _atomic_write(data)
            except OSError:
                pass
            return data

        if not isinstance(parsed, dict) or parsed.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
            _backup_invalid_config()
            data = _default_config()
            try:
                _atomic_write(data)
            except OSError:
                pass
            return data

        return _sanitize_config(parsed)


def save_config(data: dict) -> None:
    with LOCK:
        _atomic_write(data)


def normalize_time(hour: int, minute: int = 0) -> str:
    hour = int(hour)
    minute = int(minute)
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("Heure invalide")
    return f"{hour:02d}:{minute:02d}"


def build_trigger(hour: int, minute: int = 0, days=None) -> dict:
    if days is None:
        days = list(range(7))
    clean_values = set()
    for day in days:
        try:
            value = int(day)
        except (TypeError, ValueError):
            continue
        if 0 <= value <= 6:
            clean_values.add(value)
    clean_days = sorted(clean_values)
    if not clean_days:
        raise ValueError("Aucun jour valide")
    return {"type": "weekly", "time": normalize_time(hour, minute), "days": clean_days}


def _safe_id(existing: set[str] | None = None) -> str:
    existing = existing or set()
    for _ in range(32):
        candidate = "p-" + uuid.uuid4().hex[:8]
        if candidate not in existing:
            return candidate
    raise RuntimeError("Impossible de generer un identifiant de planification unique")


def _same_schedule(item: dict, kind: str, target: str, trigger: dict) -> bool:
    return (
        item.get("kind") == kind
        and item.get("target") == target
        and item.get("trigger") == trigger
    )


def create_draft(kind: str, target: str, trigger: dict, name: str | None = None) -> dict:
    kind = str(kind or "").strip().lower()
    target = str(target or "").strip().lower()
    if kind not in ALLOWED_KINDS:
        raise ValueError("Type de planification interdit")
    if kind == "routine" and not _ROUTINE_RE.fullmatch(target):
        raise ValueError("Routine invalide")
    if kind in {"briefing", "habit_summary"}:
        target = "today"
    clean_trigger = _sanitize_trigger(trigger)
    if clean_trigger is None:
        raise ValueError("Declencheur de planification invalide")

    with LOCK:
        data = load_config()
        schedules = data.setdefault("schedules", {})
        for existing in schedules.values():
            if isinstance(existing, dict) and _same_schedule(existing, kind, target, clean_trigger):
                # Evite les doubles executions accidentelles si la meme demande
                # est soumise deux fois.
                return dict(existing)
        if len(schedules) >= MAX_SCHEDULES:
            raise ValueError(f"Limite de {MAX_SCHEDULES} planifications atteinte")

        schedule_id = _safe_id(set(schedules))
        created_at = datetime.now().astimezone().isoformat(timespec="seconds")
        item = {
            "id": schedule_id,
            "name": (name or _default_name(kind, target))[:120],
            "kind": kind,
            "target": target,
            "trigger": clean_trigger,
            "confirmed": False,
            "enabled": False,
            "created_at": created_at,
            "last_run_at": None,
            "last_run_local_date": None,
            "last_result": None,
        }
        schedules[schedule_id] = item
        save_config(data)
        return dict(item)


def _default_name(kind: str, target: str) -> str:
    if kind == "routine":
        return f"Routine {target}"
    if kind == "briefing":
        return "Briefing du jour"
    return "Résumé des habitudes"


def get_schedule(schedule_id: str) -> dict | None:
    key = str(schedule_id or "").strip().lower()
    item = load_config().get("schedules", {}).get(key)
    return dict(item) if isinstance(item, dict) else None


def list_schedules(include_pending: bool = True) -> list[dict]:
    items = []
    for item in load_config().get("schedules", {}).values():
        if not isinstance(item, dict):
            continue
        if not include_pending and not item.get("confirmed"):
            continue
        items.append(dict(item))
    items.sort(key=lambda x: (str(x.get("trigger", {}).get("time", "99:99")), str(x.get("name", "")), str(x.get("id", ""))))
    return items


def confirm_schedule(schedule_id: str) -> tuple[bool, str]:
    schedule_id = str(schedule_id or "").strip().lower()
    with LOCK:
        data = load_config()
        item = data.get("schedules", {}).get(schedule_id)
        if not isinstance(item, dict):
            return False, "Planification introuvable."
        item["confirmed"] = True
        item["enabled"] = True
        item["confirmed_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        save_config(data)
    return True, f"Planification {schedule_id} confirmée et activée."


def set_enabled(schedule_id: str, enabled: bool) -> tuple[bool, str]:
    schedule_id = str(schedule_id or "").strip().lower()
    with LOCK:
        data = load_config()
        item = data.get("schedules", {}).get(schedule_id)
        if not isinstance(item, dict):
            return False, "Planification introuvable."
        if enabled and not item.get("confirmed"):
            return False, "Cette planification doit d'abord être confirmée."
        item["enabled"] = bool(enabled)
        save_config(data)
    return True, f"Planification {schedule_id} {'activée' if enabled else 'désactivée'}."


def delete_schedule(schedule_id: str) -> tuple[bool, str]:
    schedule_id = str(schedule_id or "").strip().lower()
    with LOCK:
        data = load_config()
        schedules = data.get("schedules", {})
        if schedule_id not in schedules:
            return False, "Planification introuvable."
        schedules.pop(schedule_id, None)
        save_config(data)
    return True, f"Planification {schedule_id} supprimée."


def _claim_path(schedule_id: str, now: datetime) -> Path:
    return CLAIM_DIR / f"{schedule_id}-{now.date().isoformat()}.lock"


def _claim_exists(schedule_id: str, now: datetime) -> bool:
    return _claim_path(schedule_id, now).exists()


def _cleanup_old_claims(now: datetime) -> None:
    try:
        CLAIM_DIR.mkdir(parents=True, exist_ok=True)
        cutoff = now.timestamp() - 14 * 86400
        for path in CLAIM_DIR.glob("p-????????-????-??-??.lock"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
            except OSError:
                continue
    except OSError:
        pass


def claim_schedule(schedule_id: str, now: datetime | None = None) -> bool:
    """Reserve une execution pour la journee, y compris entre deux processus GUI.

    Le verrou est volontairement conserve jusqu'au jour suivant. Une fermeture
    brutale pendant l'execution ne relancera donc pas automatiquement la meme
    action, ce qui privilegie la securite contre les doubles executions.
    """
    now = now or datetime.now().astimezone()
    schedule_id = str(schedule_id or "").strip().lower()
    if not _ID_RE.fullmatch(schedule_id):
        return False
    _cleanup_old_claims(now)
    try:
        CLAIM_DIR.mkdir(parents=True, exist_ok=True)
        path = _claim_path(schedule_id, now)
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, now.isoformat(timespec="seconds").encode("utf-8", errors="ignore"))
        finally:
            os.close(fd)
        return True
    except FileExistsError:
        return False
    except OSError:
        # Si le verrou inter-processus ne peut pas etre cree, on refuse
        # l'automatisation plutot que de risquer un doublon.
        return False


def _due_window(item: dict, now: datetime, catch_up_minutes: int) -> bool:
    if not item.get("confirmed") or not item.get("enabled"):
        return False
    if _sanitize_schedule(str(item.get("id", "")), item) is None:
        return False
    trigger = item.get("trigger", {})
    days = trigger.get("days", [])
    if now.weekday() not in days:
        return False
    try:
        hour, minute = [int(x) for x in str(trigger.get("time", "")).split(":", 1)]
        planned = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except (TypeError, ValueError):
        return False
    delta = now - planned
    if delta < timedelta(0) or delta > timedelta(minutes=max(0, catch_up_minutes)):
        return False
    if item.get("last_run_local_date") == now.date().isoformat():
        return False
    if _claim_exists(str(item.get("id", "")), now):
        return False
    return True


def get_due_schedules(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now().astimezone()
    with LOCK:
        data = load_config()
        if not data.get("enabled", True):
            return []
        catch_up = _bounded_int(data.get("catch_up_minutes"), 60, 0, 1440)
        items = [dict(item) for item in data.get("schedules", {}).values() if isinstance(item, dict) and item.get("confirmed")]
    items.sort(key=lambda x: (str(x.get("trigger", {}).get("time", "99:99")), str(x.get("name", ""))))
    return [item for item in items if _due_window(item, now, catch_up)]


def mark_run(schedule_id: str, success: bool, result: str, now: datetime | None = None) -> None:
    now = now or datetime.now().astimezone()
    schedule_id = str(schedule_id or "").strip().lower()
    with LOCK:
        data = load_config()
        item = data.get("schedules", {}).get(schedule_id)
        if not isinstance(item, dict):
            return
        item["last_run_at"] = now.isoformat(timespec="seconds")
        item["last_run_local_date"] = now.date().isoformat()
        item["last_result"] = {"success": bool(success), "message": str(result or "")[:MAX_RESULT_LENGTH]}
        save_config(data)


def format_trigger(trigger: dict) -> str:
    clean = _sanitize_trigger(trigger)
    if clean is None:
        return "déclencheur invalide"
    time_value = clean["time"]
    days = clean["days"]
    if days == list(range(7)):
        return f"tous les jours à {time_value}"
    reverse = {value: key for key, value in WEEKDAYS.items()}
    labels = [reverse.get(day, str(day)) for day in days]
    return f"{', '.join(labels)} à {time_value}"


def format_schedule(item: dict) -> str:
    status = "active" if item.get("enabled") else ("en attente" if not item.get("confirmed") else "désactivée")
    return f"{item.get('id')} — {item.get('name')} — {format_trigger(item.get('trigger', {}))} — {status}"


def format_schedule_list() -> str:
    items = list_schedules(include_pending=True)
    if not items:
        return "Aucune planification enregistrée."
    lines = ["Planifications AgentLocal :"]
    lines.extend(f"{i}. {format_schedule(item)}" for i, item in enumerate(items, 1))
    lines.append("\nUne planification en attente ne s'exécute jamais avant confirmation explicite.")
    return "\n".join(lines)


def resolve_schedule_ref(reference: str) -> str | None:
    ref = str(reference or "").strip().lower().replace(" ", "-")
    if _ID_RE.fullmatch(ref) and get_schedule(ref):
        return ref
    if ref.isdigit():
        index = int(ref) - 1
        items = list_schedules(include_pending=True)
        if 0 <= index < len(items):
            return str(items[index].get("id"))
    return None


def has_active_kind(kind: str) -> bool:
    wanted = str(kind or "").strip().lower()
    if wanted not in ALLOWED_KINDS:
        return False
    return any(
        item.get("kind") == wanted and item.get("confirmed") and item.get("enabled")
        for item in list_schedules(include_pending=False)
    )
