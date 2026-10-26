"""Resilience locale et diagnostic de demarrage pour AgentLocal.

Objectifs :
- ne jamais rendre le LLM indispensable au demarrage ;
- detecter les configurations critiques invalides avant une action ;
- conserver un journal local borne, sans enregistrer les commandes utilisateur ;
- permettre un mode degrade (deterministe) plutot qu'un crash complet.
"""
from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from project_paths import PROJECT_ROOT, ensure_portable_directories, get_project_path

SCHEMA_VERSION = 1
LOG_MAX_BYTES = 512 * 1024
LOG_BACKUP_COUNT = 3

_LOGGER: logging.Logger | None = None


def _safe_message(value: Any, limit: int = 400) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    return text[:limit]


def get_logger() -> logging.Logger:
    """Retourne un logger local borne. Echoue silencieusement si le disque est indisponible."""
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    logger = logging.getLogger("agentlocal")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        try:
            ensure_portable_directories()
            log_dir = get_project_path("logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                log_dir / "agentlocal.log",
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
            )
            logger.addHandler(handler)
        except Exception:
            logger.addHandler(logging.NullHandler())

    _LOGGER = logger
    return logger


def log_event(level: str, component: str, message: str) -> None:
    """Journalise un evenement technique. Ne pas y passer le texte brut de l'utilisateur."""
    logger = get_logger()
    entry = f"{_safe_message(component, 80)} | {_safe_message(message)}"
    method = getattr(logger, str(level or "info").lower(), logger.info)
    try:
        method(entry)
    except Exception:
        pass


def log_exception(component: str, error: BaseException) -> None:
    name = type(error).__name__
    log_event("error", component, f"{name}: {_safe_message(error, 280)}")


def _check_json(path: Path, *, critical: bool) -> dict:
    item = {
        "name": f"config/{path.name}",
        "status": "ok",
        "critical": critical,
        "detail": "valide",
    }
    if not path.is_file():
        item["status"] = "critical" if critical else "warning"
        item["detail"] = "fichier absent"
        return item
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        item["status"] = "critical" if critical else "warning"
        item["detail"] = f"JSON invalide ({type(exc).__name__})"
        return item
    if not isinstance(value, dict):
        item["status"] = "critical" if critical else "warning"
        item["detail"] = "racine JSON non objet"
    return item


def _check_writable_dir(name: str) -> dict:
    item = {"name": name, "status": "ok", "critical": False, "detail": "accessible"}
    try:
        path = get_project_path(name)
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".agentlocal_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except Exception as exc:
        item["status"] = "warning"
        item["detail"] = f"ecriture indisponible ({type(exc).__name__})"
    return item


def startup_health_report() -> dict:
    """Diagnostic leger. Ne lance pas de commande utilisateur ni le modele LLM."""
    checks: list[dict] = []
    ensure_portable_directories()

    config_dir = get_project_path("config")
    # permissions.json est critique : sans politique valide, aucune action ne doit etre lancee.
    checks.append(_check_json(config_dir / "permissions.json", critical=True))
    checks.append(_check_json(config_dir / "agent.json", critical=False))
    checks.append(_check_json(config_dir / "paths.json", critical=False))
    checks.append(_check_json(config_dir / "runtime.json", critical=False))
    checks.append(_check_json(config_dir / "models.json", critical=False))
    checks.append(_check_json(config_dir / "sites.json", critical=False))
    checks.append(_check_json(config_dir / "routines.json", critical=False))

    checks.append(_check_writable_dir("logs"))
    checks.append(_check_writable_dir("memory"))

    try:
        from backends.backend_manager import get_backend_status

        status = get_backend_status()
        deterministic_ok = bool(status.get("deterministic_available"))
        checks.append(
            {
                "name": "backend deterministic",
                "status": "ok" if deterministic_ok else "critical",
                "critical": True,
                "detail": "disponible" if deterministic_ok else "indisponible",
            }
        )
        llama_ok = bool(status.get("llama_available"))
        checks.append(
            {
                "name": "backend LLM local",
                "status": "ok" if llama_ok else "warning",
                "critical": False,
                "detail": "disponible" if llama_ok else "indisponible - mode deterministe possible",
            }
        )
    except Exception as exc:
        checks.append(
            {
                "name": "backends",
                "status": "critical",
                "critical": True,
                "detail": f"diagnostic impossible ({type(exc).__name__})",
            }
        )
        log_exception("startup_health.backends", exc)

    # Avertissement seulement : AgentLocal vise 4 Go de RAM, mais doit rester utilisable en mode degrade.
    try:
        import psutil

        available = int(psutil.virtual_memory().available)
        if available < 384 * 1024 * 1024:
            checks.append(
                {
                    "name": "memoire disponible",
                    "status": "warning",
                    "critical": False,
                    "detail": "moins de 384 Mo disponibles",
                }
            )
        else:
            checks.append(
                {
                    "name": "memoire disponible",
                    "status": "ok",
                    "critical": False,
                    "detail": f"{available // (1024 * 1024)} Mo disponibles",
                }
            )
    except Exception:
        pass

    critical_count = sum(1 for c in checks if c["status"] == "critical")
    warning_count = sum(1 for c in checks if c["status"] == "warning")
    if critical_count:
        overall = "critical"
    elif warning_count:
        overall = "degraded"
    else:
        overall = "healthy"

    report = {
        "schema_version": SCHEMA_VERSION,
        "project_root": str(PROJECT_ROOT),
        "overall": overall,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "checks": checks,
    }
    log_event("info", "startup_health", f"etat={overall}; critiques={critical_count}; avertissements={warning_count}")
    return report


def format_health_summary(report: dict) -> str:
    overall = str(report.get("overall", "unknown"))
    if overall == "healthy":
        return "État : opérationnel"
    if overall == "degraded":
        return "État : opérationnel en mode dégradé"
    return "État : mode sûr - action désactivée"


def critical_health_messages(report: dict) -> list[str]:
    values = []
    for item in report.get("checks", []):
        if isinstance(item, dict) and item.get("status") == "critical":
            values.append(f"{item.get('name')}: {item.get('detail')}")
    return values
