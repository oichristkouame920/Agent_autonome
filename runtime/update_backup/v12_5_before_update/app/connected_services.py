"""Services Internet optionnels et strictement en lecture seule pour AgentLocal V12.

Principes de securite :
- HTTPS uniquement.
- Domaines autorises par configuration/politique.
- Requetes GET uniquement, sans cookie ni jeton.
- Taille de reponse et delai bornes.
- Les donnees recues sont du contenu d'affichage, jamais des commandes.
- Cache court pour limiter les requetes et ameliorer la reactivite.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import tempfile
import re
import html
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from project_paths import PROJECT_ROOT
from project_version import AGENTLOCAL_VERSION

CONFIG_PATH = PROJECT_ROOT / "config" / "connected_services.json"
PERMISSIONS_PATH = PROJECT_ROOT / "config" / "permissions.json"
STATE_PATH = PROJECT_ROOT / "runtime" / "connected_services_state.json"
USER_PREFERENCES_PATH = PROJECT_ROOT / "memory" / "user_preferences.json"

_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_LOCK = threading.Lock()

WEATHER_CODES = {
    0: "Ciel degage", 1: "Plutot degage", 2: "Partiellement nuageux", 3: "Couvert",
    45: "Brouillard", 48: "Brouillard givrant", 51: "Bruine legere", 53: "Bruine",
    55: "Bruine forte", 61: "Pluie legere", 63: "Pluie", 65: "Forte pluie",
    71: "Neige legere", 73: "Neige", 75: "Forte neige", 80: "Averses legeres",
    81: "Averses", 82: "Fortes averses", 95: "Orage", 96: "Orage avec grele",
    99: "Fort orage avec grele",
}


def _load_json(path: Path, default: dict) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else dict(default)
    except Exception:
        return dict(default)


def load_connected_config() -> dict:
    return _load_json(CONFIG_PATH, {})


def _load_policy() -> dict:
    data = _load_json(PERMISSIONS_PATH, {})
    policy = data.get("connected_services_policy", {}) if isinstance(data, dict) else {}
    return policy if isinstance(policy, dict) else {}


def _allowed_hosts() -> set[str]:
    policy = _load_policy()
    values = policy.get("allowed_hosts", [])
    if not isinstance(values, list):
        return set()
    return {str(v).strip().lower() for v in values if str(v).strip()}


def _cache_ttl(value: object, default: int = 900) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0, min(3600, parsed))


def _cache_get(key: str, ttl: int):
    ttl = _cache_ttl(ttl)
    if ttl <= 0:
        return None
    now = time.monotonic()
    with _CACHE_LOCK:
        row = _CACHE.get(key)
        if row and now - row[0] <= ttl:
            return copy.deepcopy(row[1])
    return None


def _cache_put(key: str, value: Any) -> Any:
    safe_value = copy.deepcopy(value)
    with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic(), safe_value)
    return copy.deepcopy(safe_value)


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme.lower() != "https" or (parsed.hostname or "").lower() not in _allowed_hosts():
            raise urllib.error.URLError("Redirection vers un domaine non autorise")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch(url: str, *, max_bytes: int | None = None) -> bytes:
    policy = _load_policy()
    if not policy.get("enabled", False):
        raise RuntimeError("Services connectes desactives par la politique de securite")
    if not policy.get("read_only", True):
        raise RuntimeError("Politique de services connectes invalide")

    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.username or parsed.password:
        raise RuntimeError("Identifiants dans URL interdits")
    try:
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError("Port Internet invalide") from exc
    if parsed.scheme.lower() != "https" or host not in _allowed_hosts() or port not in (None, 443):
        raise RuntimeError("Domaine Internet non autorise")

    timeout = float(policy.get("timeout_seconds", 4.0) or 4.0)
    timeout = min(8.0, max(1.0, timeout))
    maximum = int(max_bytes or policy.get("maximum_response_bytes", 1048576) or 1048576)
    maximum = min(4 * 1024 * 1024, max(4096, maximum))

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"AgentLocal/{AGENTLOCAL_VERSION} (read-only connected services)",
            "Accept": "application/json, application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.1",
            "Cache-Control": "no-cache",
        },
        method="GET",
    )
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    with opener.open(request, timeout=timeout) as response:
        final = urllib.parse.urlparse(response.geturl())
        if final.scheme.lower() != "https" or (final.hostname or "").lower() not in _allowed_hosts():
            raise RuntimeError("Reponse recue depuis un domaine non autorise")
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > maximum:
                    raise RuntimeError("Reponse Internet trop volumineuse")
            except ValueError:
                pass
        data = response.read(maximum + 1)
        if len(data) > maximum:
            raise RuntimeError("Reponse Internet trop volumineuse")
        return data


def _clean_text(value: object, limit: int = 240) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]




def _user_briefing_preferences() -> dict:
    """Lit uniquement les préférences de briefing locales si elles existent."""
    try:
        data = json.loads(USER_PREFERENCES_PATH.read_text(encoding="utf-8-sig"))
        block = data.get("briefing", {}) if isinstance(data, dict) else {}
        return block if isinstance(block, dict) else {}
    except Exception:
        return {}


def _service_config(name: str) -> dict:
    config = load_connected_config()
    block = config.get(name, {}) if isinstance(config, dict) else {}
    return block if isinstance(block, dict) else {}


def _finite_float(value: object, name: str) -> float:
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"Valeur meteo invalide : {name}")
    return number


def _bounded_int(value: object, minimum: int, maximum: int, name: str) -> int:
    number = int(value)
    if number < minimum or number > maximum:
        raise ValueError(f"Valeur meteo invalide : {name}")
    return number


def _fmt_number(value: object, digits: int = 0, fallback: str = "--") -> str:
    try:
        number = _finite_float(value, "format")
        return f"{number:.{digits}f}"
    except (TypeError, ValueError):
        return fallback


def get_weather(*, force: bool = False) -> tuple[bool, dict | str]:
    config = _service_config("weather")
    if not config.get("enabled", False):
        return False, "Le service meteo est desactive."
    city = _clean_text(config.get("city", "Abidjan"), 80) or "Abidjan"
    country_code = _clean_text(config.get("country_code", "CI"), 2).upper() or "CI"
    ttl = _cache_ttl(config.get("cache_seconds", 900), 900)
    cache_key = f"weather:{city}:{country_code}"
    if not force:
        cached = _cache_get(cache_key, ttl)
        if cached is not None:
            return True, cached
    try:
        q = urllib.parse.urlencode({"name": city, "count": 1, "language": "fr", "countryCode": country_code, "format": "json"})
        geo_raw = json.loads(_fetch(f"https://geocoding-api.open-meteo.com/v1/search?{q}").decode("utf-8"))
        results = geo_raw.get("results", []) if isinstance(geo_raw, dict) else []
        if not results:
            return False, f"Localite meteo introuvable : {city}."
        loc = results[0]
        lat = float(loc["latitude"])
        lon = float(loc["longitude"])
        params = urllib.parse.urlencode({
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": 1,
            "timezone": "auto",
        })
        weather_raw = json.loads(_fetch(f"https://api.open-meteo.com/v1/forecast?{params}").decode("utf-8"))
        current = weather_raw.get("current", {}) if isinstance(weather_raw, dict) else {}
        daily = weather_raw.get("daily", {}) if isinstance(weather_raw, dict) else {}
        code = int(current.get("weather_code", -1))
        result = {
            "city": _clean_text(loc.get("name", city), 80),
            "country": _clean_text(loc.get("country", "Cote d'Ivoire"), 80),
            "temperature_c": _finite_float(current.get("temperature_2m"), "temperature"),
            "apparent_c": _finite_float(current.get("apparent_temperature"), "ressenti"),
            "humidity_percent": _bounded_int(current.get("relative_humidity_2m"), 0, 100, "humidite"),
            "wind_kmh": max(0.0, _finite_float(current.get("wind_speed_10m"), "vent")),
            "precipitation_mm": max(0.0, _finite_float(current.get("precipitation", 0.0), "precipitation")),
            "condition": WEATHER_CODES.get(code, f"Code meteo {code}"),
            "min_c": _finite_float((daily.get("temperature_2m_min") or [None])[0], "minimum"),
            "max_c": _finite_float((daily.get("temperature_2m_max") or [None])[0], "maximum"),
            "rain_probability_percent": _bounded_int((daily.get("precipitation_probability_max") or [0])[0] or 0, 0, 100, "pluie"),
            "source": "Open-Meteo",
            "fetched_at": dt.datetime.now().isoformat(timespec="seconds"),
        }
        return True, _cache_put(cache_key, result)
    except Exception as exc:
        return False, f"Meteo indisponible ({type(exc).__name__}). Les fonctions locales restent actives."


def format_weather(data: dict) -> str:
    return (
        f"Meteo a {data.get('city', 'la localite configuree')} : {data.get('condition', '--')} ; "
        f"{_fmt_number(data.get('temperature_c'))} °C (ressenti {_fmt_number(data.get('apparent_c'))} °C) ; "
        f"min {_fmt_number(data.get('min_c'))} °C / max {_fmt_number(data.get('max_c'))} °C ; "
        f"humidite {data.get('humidity_percent', '--')} % ; vent {_fmt_number(data.get('wind_kmh'))} km/h ; "
        f"risque de pluie {data.get('rain_probability_percent', '--')} %. Source : {data.get('source', 'Open-Meteo')}."
    )


def _news_text_key(value: object) -> str:
    """Normalise un titre pour limiter les doublons entre les categories."""
    text = _clean_text(value, 300).lower()
    text = re.sub(r"[^\w\s-]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _news_is_excluded(title: str, excluded_keywords: list[str]) -> bool:
    lowered = title.lower()
    for keyword in excluded_keywords:
        keyword = str(keyword or "").strip().lower()
        if keyword and keyword in lowered:
            return True
    return False


def _news_source_score(source: str, preferred_sources: list[str]) -> int:
    lowered = source.lower()
    for index, preferred in enumerate(preferred_sources):
        preferred = str(preferred or "").strip().lower()
        if preferred and preferred in lowered:
            return max(1, 100 - index * 3)
    return 0


def _read_google_news_topic(
    *,
    query: str,
    category_id: str,
    category_label: str,
    language: str,
    country_code: str,
    per_topic_limit: int,
    excluded_keywords: list[str],
    preferred_sources: list[str],
    already_seen: set[str],
) -> list[dict]:
    """Recupere et classe un sujet RSS en lecture seule."""
    params = urllib.parse.urlencode({
        "q": query,
        "hl": language,
        "gl": country_code,
        "ceid": f"{country_code}:{language}",
    })
    raw = _fetch(
        f"https://news.google.com/rss/search?{params}",
        max_bytes=2 * 1024 * 1024,
    )
    if b"<!DOCTYPE" in raw.upper():
        raise RuntimeError("Flux RSS non autorise")

    root = ET.fromstring(raw)
    candidates: list[dict] = []

    for item in root.findall("./channel/item"):
        title = _clean_text(item.findtext("title"), 220)
        if not title or _news_is_excluded(title, excluded_keywords):
            continue

        key = _news_text_key(title)
        if not key or key in already_seen:
            continue

        link = _clean_text(item.findtext("link"), 500)
        pub = _clean_text(item.findtext("pubDate"), 120)
        source_node = item.find("source")
        source = _clean_text(
            source_node.text if source_node is not None else "Google Actualites",
            120,
        )

        timestamp = 0.0
        try:
            parsed = parsedate_to_datetime(pub) if pub else None
            if parsed:
                local_dt = parsed.astimezone()
                published = local_dt.strftime("%d/%m %H:%M")
                timestamp = local_dt.timestamp()
            else:
                published = ""
        except Exception:
            published = ""

        candidates.append({
            "title": title,
            "source": source,
            "published": published,
            "published_ts": timestamp,
            "link": link,
            "category": category_id,
            "category_label": category_label,
            "source_score": _news_source_score(source, preferred_sources),
            "dedupe_key": key,
        })

    candidates.sort(
        key=lambda row: (row.get("source_score", 0), row.get("published_ts", 0.0)),
        reverse=True,
    )

    results: list[dict] = []
    for row in candidates:
        key = str(row.pop("dedupe_key", ""))
        row.pop("source_score", None)
        row.pop("published_ts", None)
        if not key or key in already_seen:
            continue
        already_seen.add(key)
        results.append(row)
        if len(results) >= per_topic_limit:
            break

    return results


def get_news(*, force: bool = False) -> tuple[bool, list[dict] | str]:
    config = _service_config("news")
    user_briefing = _user_briefing_preferences()
    if user_briefing and not user_briefing.get("enabled", True):
        return False, "Le briefing est desactive dans la configuration de l'hote."
    if not config.get("enabled", False):
        return False, "Le service actualites est desactive."

    language = _clean_text(config.get("language", "fr"), 8) or "fr"
    country_code = _clean_text(config.get("country_code", "CI"), 2).upper() or "CI"

    try:
        limit = int(config.get("limit", 12) or 12)
    except (TypeError, ValueError):
        limit = 12
    limit = min(24, max(1, limit))

    try:
        per_topic_limit = int(config.get("per_topic_limit", 2) or 2)
    except (TypeError, ValueError):
        per_topic_limit = 2
    per_topic_limit = min(5, max(1, per_topic_limit))

    ttl = _cache_ttl(config.get("cache_seconds", 900), 900)

    topics = config.get("topics", [])
    if not isinstance(topics, list):
        topics = []

    excluded_keywords = config.get("exclude_keywords", [])
    if not isinstance(excluded_keywords, list):
        excluded_keywords = []

    preferred_sources = config.get("preferred_sources", [])
    if not isinstance(preferred_sources, list):
        preferred_sources = []

    cache_material = json.dumps(
        {
            "topics": topics,
            "excluded": excluded_keywords,
            "preferred": preferred_sources,
            "limit": limit,
            "per_topic": per_topic_limit,
            "language": language,
            "country": country_code,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    cache_key = f"news-priority:{cache_material}"

    if not force:
        cached = _cache_get(cache_key, ttl)
        if cached is not None:
            return True, cached

    if not topics:
        return False, "Aucun sujet d'actualite prioritaire n'est configure."

    all_items: list[dict] = []
    already_seen: set[str] = set()
    errors: list[str] = []

    selected_topics = user_briefing.get("topics", {}) if isinstance(user_briefing, dict) else {}
    if not isinstance(selected_topics, dict):
        selected_topics = {}

    for topic in topics:
        if not isinstance(topic, dict) or topic.get("enabled", True) is False:
            continue

        category_id = _clean_text(topic.get("id"), 60)
        if category_id and selected_topics and category_id in selected_topics and not bool(selected_topics.get(category_id)):
            continue
        category_label = _clean_text(topic.get("label"), 100)
        query = _clean_text(topic.get("query"), 500)
        if not category_id or not category_label or not query:
            continue

        try:
            items = _read_google_news_topic(
                query=query,
                category_id=category_id,
                category_label=category_label,
                language=language,
                country_code=country_code,
                per_topic_limit=per_topic_limit,
                excluded_keywords=excluded_keywords,
                preferred_sources=preferred_sources,
                already_seen=already_seen,
            )
            all_items.extend(items)
        except Exception as exc:
            errors.append(f"{category_label}: {type(exc).__name__}")

        if len(all_items) >= limit:
            break

    all_items = all_items[:limit]

    if not all_items:
        if errors:
            return False, (
                "Actualites prioritaires indisponibles. "
                "Les fonctions locales restent actives."
            )
        return False, "Aucune actualite prioritaire recente n'a ete recue."

    return True, _cache_put(cache_key, all_items)


def format_news(items: list[dict]) -> str:
    if not items:
        return "Aucune actualite prioritaire disponible."

    lines = ["ACTUALITES PRIORITAIRES"]
    grouped: dict[str, list[dict]] = {}
    category_order: list[str] = []

    for item in items:
        label = _clean_text(item.get("category_label", "Autres"), 100) or "Autres"
        if label not in grouped:
            grouped[label] = []
            category_order.append(label)
        grouped[label].append(item)

    for label in category_order:
        lines.append("")
        lines.append(label.upper())
        for item in grouped[label]:
            title = _clean_text(item.get("title"), 220)
            source = _clean_text(item.get("source"), 120)
            published = _clean_text(item.get("published"), 40)
            metadata = []
            if source:
                metadata.append(source)
            if published:
                metadata.append(published)
            suffix = f" — {' | '.join(metadata)}" if metadata else ""
            lines.append(f"- {title}{suffix}")

    lines.append("")
    lines.append(
        "Lecture seule : les informations Internet sont affichees comme des donnees "
        "et ne peuvent jamais declencher une action AgentLocal."
    )
    return "\n".join(lines)

def check_agentlocal_update(*, force: bool = False) -> tuple[bool, dict | str]:
    config = _service_config("updates")
    if not config.get("enabled", False):
        return False, "La verification AgentLocal en ligne est desactivee."
    repo = _clean_text(config.get("github_repository", ""), 160)
    branch = _clean_text(config.get("branch", "Modification"), 80) or "Modification"
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        return False, "Depot GitHub AgentLocal non configure."
    ttl = _cache_ttl(config.get("cache_seconds", 900), 900)
    key = f"update:{repo}:{branch}"
    if not force:
        cached = _cache_get(key, ttl)
        if cached is not None:
            return True, cached
    try:
        encoded_branch = urllib.parse.quote(branch, safe="")
        raw = json.loads(_fetch(f"https://api.github.com/repos/{repo}/commits/{encoded_branch}").decode("utf-8"))
        remote_sha = _clean_text(raw.get("sha", ""), 64).lower()
        if not re.fullmatch(r"[0-9a-f]{40,64}", remote_sha):
            return False, "Reponse GitHub invalide. Aucune mise a jour n'a ete installee."
        local_sha = _read_local_git_head().lower()
        if local_sha and not re.fullmatch(r"[0-9a-f]{40,64}", local_sha):
            local_sha = ""
        result = {
            "repository": repo,
            "branch": branch,
            "local_sha": local_sha,
            "remote_sha": remote_sha,
            "up_to_date": bool(local_sha and remote_sha and local_sha == remote_sha),
            "source": "GitHub API",
        }
        return True, _cache_put(key, result)
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403, 404}:
            return False, "Le depot GitHub configure n'est pas accessible sans authentification. Aucune mise a jour n'a ete installee."
        return False, f"Verification des mises a jour indisponible (HTTP {exc.code})."
    except Exception as exc:
        return False, f"Verification des mises a jour indisponible ({type(exc).__name__})."


def _read_local_git_head() -> str:
    git_dir = PROJECT_ROOT / ".git"
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            ref = head[5:].strip()
            ref_path = git_dir / Path(ref)
            if ref_path.exists():
                return ref_path.read_text(encoding="utf-8").strip()
            packed = git_dir / "packed-refs"
            if packed.exists():
                for line in packed.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if line and not line.startswith("#") and not line.startswith("^"):
                        sha, _, name = line.partition(" ")
                        if name.strip() == ref:
                            return sha.strip()
            return ""
        return head
    except Exception:
        return ""


def format_update_status(data: dict) -> str:
    if data.get("up_to_date"):
        return f"AgentLocal est aligne sur la branche {data.get('branch')} du depot configure. Aucune installation automatique n'a ete lancee."
    if data.get("local_sha") and data.get("remote_sha"):
        return (
            f"Une difference Git est detectee pour AgentLocal sur la branche {data.get('branch')}. "
            "Je n'installe rien automatiquement : verifie et integre les changements manuellement apres sauvegarde."
        )
    return "Etat distant AgentLocal lu, mais la comparaison locale n'est pas disponible. Aucune installation automatique n'a ete lancee."


def build_daily_briefing(*, force: bool = False) -> dict:
    weather_ok, weather = get_weather(force=force)
    news_ok, news = get_news(force=force)
    return {
        "date": dt.date.today().isoformat(),
        "weather_ok": weather_ok,
        "weather": weather,
        "news_ok": news_ok,
        "news": news,
    }


def format_daily_briefing(data: dict) -> str:
    lines = [f"Briefing du {dt.date.today().strftime('%d/%m/%Y')} :"]
    if data.get("weather_ok") and isinstance(data.get("weather"), dict):
        lines.append(format_weather(data["weather"]))
    else:
        lines.append(str(data.get("weather") or "Meteo indisponible."))
    if data.get("news_ok") and isinstance(data.get("news"), list):
        lines.append(format_news(data["news"]))
    else:
        lines.append(str(data.get("news") or "Actualites indisponibles."))
    return "\n\n".join(lines)


def _load_state() -> dict:
    return _load_json(STATE_PATH, {})


def should_show_morning_briefing(now: dt.datetime | None = None) -> bool:
    config = _service_config("morning_briefing")
    if not config.get("enabled", False):
        return False
    now = now or dt.datetime.now()
    try:
        start = max(0, min(23, int(config.get("start_hour", 5) or 5)))
        end = max(1, min(24, int(config.get("end_hour", 11) or 11)))
    except (TypeError, ValueError):
        start, end = 5, 11
    if start >= end:
        start, end = 5, 11
    if not start <= now.hour < end:
        return False
    if not config.get("show_once_per_day", True):
        return True
    state = _load_state()
    return state.get("last_morning_briefing_date") != now.date().isoformat()


def mark_morning_briefing_shown(now: dt.datetime | None = None) -> None:
    now = now or dt.datetime.now()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = _load_state()
    state["last_morning_briefing_date"] = now.date().isoformat()
    text = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    tmp_name = None
    try:
        fd, tmp_name = tempfile.mkstemp(prefix="connected_state_", suffix=".json", dir=str(STATE_PATH.parent))
        with os.fdopen(fd, "w", encoding="utf-8", closefd=True) as handle:
            handle.write(text)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        Path(tmp_name).replace(STATE_PATH)
    except OSError:
        pass
    finally:
        if tmp_name:
            try:
                Path(tmp_name).unlink(missing_ok=True)
            except OSError:
                pass
