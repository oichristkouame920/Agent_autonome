import atexit
import json
import os
import re
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from project_paths import PROJECT_ROOT, get_project_path, resolve_project_relative
from runtime_resilience import log_event
from backends.llm_fidelity import semantic_fidelity, normalized_confidence


SCHEMA_VERSION = 2
LLM_BACKEND_VERSION = "2026-10-26-v11.2-portable-runtime-local-llm"

ROOT_DIR = PROJECT_ROOT
MODELS_CONFIG_FILE = get_project_path("config") / "models.json"

DEFAULT_MODELS_CONFIG = {
    "schema_version": 2,
    "active_model": "qwen_small",
    "runtime": {
        "llama_cli": "tools/llama.cpp/llama-cli.exe",
        "timeout_seconds": 45,
        "minimum_confidence": 0.72,
        "probe_runtime_on_startup": True,
        "probe_fast_timeout_seconds": 10,
        "probe_slow_timeout_seconds": 30,
        "llama_server": "tools/llama.cpp/llama-server.exe",
        "warm_server_enabled": True,
        "warm_server_idle_seconds": 180,
        "warm_server_min_available_ram_mb": 850,
        "warm_server_start_timeout_seconds": 45,
        "warm_server_local_only": True,
    },
    "models": {
        "qwen_small": {
            "file": "models/Qwen3.5-0.8B-Q4_0.gguf",
            "companions": [],
            "context_size": 2048,
            "threads": 4,
            "max_tokens": 192,
            "temperature": 0.0,
        }
    },
}

FORBIDDEN_EXECUTION_TERMS = {
    "powershell",
    "cmd",
    "invite de commandes",
    "windows terminal",
    "terminal",
    "bash",
    "wsl",
}

_RUNTIME_PROBE_CACHE = {}
_LAST_RUNTIME_PROBE = {"state": "not_run", "detail": None, "elapsed_seconds": None}
_WARM_LOCK = threading.RLock()
def _is_windows_runtime():
    return os.name == "nt"


_WARM_SERVER = {
    "process": None,
    "port": None,
    "model_key": None,
    "last_used": 0.0,
    "timer": None,
    "last_error": None,
}


def _safe_copy_default():
    return json.loads(json.dumps(DEFAULT_MODELS_CONFIG))


def load_models_config():
    """Charge config/models.json avec des valeurs de secours sures."""
    if not MODELS_CONFIG_FILE.exists():
        return _safe_copy_default()

    try:
        data = json.loads(MODELS_CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _safe_copy_default()

    if not isinstance(data, dict):
        return _safe_copy_default()

    merged = _safe_copy_default()
    merged.update({key: value for key, value in data.items() if key in {"schema_version", "active_model"}})

    runtime = data.get("runtime")
    if isinstance(runtime, dict):
        merged["runtime"].update(runtime)

    models = data.get("models")
    if isinstance(models, dict) and models:
        merged["models"] = models

    return merged


def _resolve_project_path(value):
    # Toutes les ressources internes du LLM restent relatives au projet.
    return resolve_project_relative(value)


def _resolve_optional_list(values):
    if not isinstance(values, list):
        return []
    resolved = []
    for value in values:
        raw = str(value or "").strip()
        if raw:
            resolved.append(_resolve_project_path(raw))
    return resolved


def get_active_model_config():
    config = load_models_config()
    active_name = str(config.get("active_model", "")).strip()
    models = config.get("models", {})
    if not isinstance(models, dict):
        models = {}

    model = models.get(active_name)
    if not isinstance(model, dict):
        return None, None, config

    model = dict(model)
    model["name"] = active_name
    model["path"] = _resolve_project_path(model.get("file", ""))
    model["companion_paths"] = _resolve_optional_list(model.get("companions", []))

    mmproj = str(model.get("mmproj", "") or "").strip()
    model["mmproj_path"] = _resolve_project_path(mmproj) if mmproj else None

    runtime = config.get("runtime", {})
    if not isinstance(runtime, dict):
        runtime = {}
    model["llama_cli_path"] = _resolve_project_path(
        runtime.get("llama_cli", "tools/llama.cpp/llama-cli.exe")
    )
    model["timeout_seconds"] = max(5, min(int(runtime.get("timeout_seconds", 45) or 45), 120))
    model["minimum_confidence"] = max(
        0.0, min(float(runtime.get("minimum_confidence", 0.72) or 0.72), 1.0)
    )
    model["probe_runtime_on_startup"] = bool(runtime.get("probe_runtime_on_startup", True))
    model["probe_fast_timeout_seconds"] = max(3, min(int(runtime.get("probe_fast_timeout_seconds", 10) or 10), 20))
    model["probe_slow_timeout_seconds"] = max(10, min(int(runtime.get("probe_slow_timeout_seconds", 30) or 30), 60))
    model["llama_server_path"] = _resolve_project_path(
        runtime.get("llama_server", "tools/llama.cpp/llama-server.exe")
    )
    model["warm_server_enabled"] = bool(runtime.get("warm_server_enabled", True))
    model["warm_server_idle_seconds"] = max(30, min(int(runtime.get("warm_server_idle_seconds", 180) or 180), 1800))
    model["warm_server_min_available_ram_mb"] = max(512, min(int(runtime.get("warm_server_min_available_ram_mb", 850) or 850), 8192))
    model["warm_server_start_timeout_seconds"] = max(10, min(int(runtime.get("warm_server_start_timeout_seconds", 45) or 45), 120))
    model["warm_server_local_only"] = bool(runtime.get("warm_server_local_only", True))

    model["context_size"] = max(512, min(int(model.get("context_size", 2048) or 2048), 8192))
    model["threads"] = max(1, min(int(model.get("threads", 4) or 4), 16))
    model["max_tokens"] = max(32, min(int(model.get("max_tokens", 192) or 192), 512))
    model["temperature"] = max(0.0, min(float(model.get("temperature", 0.0) or 0.0), 1.0))

    return active_name, model, config


def _probe_runtime_once(path: Path, timeout_seconds: int):
    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": max(3, int(timeout_seconds)),
        "shell": False,
        "cwd": str(path.parent),
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
    }
    return subprocess.run([str(path), "--version"], **kwargs)


def probe_llama_runtime(llama_cli_path, timeout_seconds=10, retry_timeout_seconds=30):
    """Sonde llama.cpp en deux temps pour eviter les faux negatifs de demarrage lent."""
    global _LAST_RUNTIME_PROBE
    path = Path(llama_cli_path)
    if not path.is_file():
        _LAST_RUNTIME_PROBE = {"state": "missing", "detail": f"llama-cli introuvable : {path}", "elapsed_seconds": 0.0}
        return False, _LAST_RUNTIME_PROBE["detail"]

    cache_key = (str(path.resolve()), path.stat().st_mtime_ns, path.stat().st_size)
    cached = _RUNTIME_PROBE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if not _is_windows_runtime():
        result = (True, "Sonde d'execution reportee a Windows.")
        _RUNTIME_PROBE_CACHE[cache_key] = result
        _LAST_RUNTIME_PROBE = {"state": "deferred", "detail": result[1], "elapsed_seconds": 0.0}
        return result

    fast_timeout = max(3, min(int(timeout_seconds or 10), 20))
    slow_timeout = max(fast_timeout, min(int(retry_timeout_seconds or 30), 60))
    started = time.monotonic()
    try:
        completed = _probe_runtime_once(path, fast_timeout)
    except subprocess.TimeoutExpired:
        # Le premier lancement peut etre ralenti par Windows Defender, Smart App Control
        # ou le chargement initial des DLL. Une seconde chance plus longue evite de
        # declarer le LLM indisponible alors qu'il fonctionne reellement.
        try:
            completed = _probe_runtime_once(path, slow_timeout)
        except (OSError, subprocess.SubprocessError) as exc:
            elapsed = round(time.monotonic() - started, 3)
            result = (False, f"Runtime llama.cpp inutilisable apres seconde tentative : {exc}")
            _LAST_RUNTIME_PROBE = {"state": "failed", "detail": result[1], "elapsed_seconds": elapsed}
        else:
            elapsed = round(time.monotonic() - started, 3)
            if completed.returncode == 0:
                result = (True, "Runtime llama.cpp valide apres demarrage lent.")
                _LAST_RUNTIME_PROBE = {"state": "slow_ready", "detail": result[1], "elapsed_seconds": elapsed}
            else:
                detail = (completed.stderr or completed.stdout or "").strip()
                result = (False, "llama-cli ne demarre pas correctement" + (f" : {detail[-500:]}" if detail else "."))
                _LAST_RUNTIME_PROBE = {"state": "failed", "detail": result[1], "elapsed_seconds": elapsed}
    except (OSError, subprocess.SubprocessError) as exc:
        elapsed = round(time.monotonic() - started, 3)
        result = (False, f"Runtime llama.cpp inutilisable : {exc}")
        _LAST_RUNTIME_PROBE = {"state": "failed", "detail": result[1], "elapsed_seconds": elapsed}
    else:
        elapsed = round(time.monotonic() - started, 3)
        if completed.returncode == 0:
            result = (True, None)
            _LAST_RUNTIME_PROBE = {"state": "ready", "detail": None, "elapsed_seconds": elapsed}
        else:
            detail = (completed.stderr or completed.stdout or "").strip()
            result = (False, "llama-cli ne demarre pas correctement" + (f" : {detail[-500:]}" if detail else "."))
            _LAST_RUNTIME_PROBE = {"state": "failed", "detail": result[1], "elapsed_seconds": elapsed}

    _RUNTIME_PROBE_CACHE[cache_key] = result
    return result


def availability():
    """Retourne l'etat reel du backend local sans charger le modele en memoire."""
    active_name, model, _ = get_active_model_config()
    if not active_name or model is None:
        return False, "Aucun modele actif valide dans config/models.json."

    llama_cli = model["llama_cli_path"]
    model_path = model["path"]

    if not llama_cli.is_file():
        return False, f"llama-cli introuvable : {llama_cli}"
    if not model_path.is_file():
        return False, f"Modele GGUF introuvable : {model_path}"

    for companion in model.get("companion_paths", []):
        if not companion.is_file():
            return False, f"Fichier annexe du modele introuvable : {companion}"

    mmproj = model.get("mmproj_path")
    if mmproj is not None and not mmproj.is_file():
        return False, f"Fichier mmproj introuvable : {mmproj}"

    if model.get("probe_runtime_on_startup"):
        ok, reason = probe_llama_runtime(
            llama_cli,
            model.get("probe_fast_timeout_seconds", 10),
            model.get("probe_slow_timeout_seconds", 30),
        )
        if not ok:
            return False, reason

    return True, None


def is_available():
    ok, _ = availability()
    return ok


def get_status():
    active_name, model, _ = get_active_model_config()
    ok, reason = availability()
    return {
        "available": ok,
        "reason": reason,
        "active_model": active_name,
        "model_path": str(model["path"]) if model else None,
        "llama_cli": str(model["llama_cli_path"]) if model else None,
        "companions": [str(p) for p in model.get("companion_paths", [])] if model else [],
        "mmproj": str(model["mmproj_path"]) if model and model.get("mmproj_path") else None,
        "context_size": model.get("context_size") if model else None,
        "threads": model.get("threads") if model else None,
        "runtime_probe": dict(_LAST_RUNTIME_PROBE),
        "warm_server_configured": bool(model and model.get("warm_server_enabled")),
        "warm_server_binary": str(model.get("llama_server_path")) if model else None,
        "warm_server_running": warm_server_status().get("running"),
        "warm_server_port": warm_server_status().get("port"),
        "warm_server_last_error": warm_server_status().get("last_error"),
    }



def _available_ram_mb():
    try:
        import psutil
        return int(psutil.virtual_memory().available // (1024 * 1024))
    except Exception:
        return None


def _warm_model_key(model):
    path = Path(model.get("path", ""))
    try:
        stat = path.stat()
        return (str(path.resolve()), stat.st_mtime_ns, stat.st_size, int(model.get("context_size", 2048)))
    except OSError:
        return (str(path), None, None, int(model.get("context_size", 2048)))


def warm_server_status():
    with _WARM_LOCK:
        process = _WARM_SERVER.get("process")
        running = bool(process is not None and process.poll() is None)
        return {
            "running": running,
            "port": _WARM_SERVER.get("port") if running else None,
            "last_used": _WARM_SERVER.get("last_used") or None,
            "last_error": _WARM_SERVER.get("last_error"),
        }


def _cancel_idle_timer_locked():
    timer = _WARM_SERVER.get("timer")
    if timer is not None:
        try:
            timer.cancel()
        except Exception:
            pass
    _WARM_SERVER["timer"] = None


def _stop_warm_server_locked(reason=None):
    _cancel_idle_timer_locked()
    process = _WARM_SERVER.get("process")
    if process is not None and process.poll() is None:
        try:
            process.terminate()
            process.wait(timeout=3)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
    _WARM_SERVER["process"] = None
    _WARM_SERVER["port"] = None
    _WARM_SERVER["model_key"] = None
    _WARM_SERVER["last_used"] = 0.0
    if reason:
        _WARM_SERVER["last_error"] = str(reason)[:400]


def stop_warm_server(reason=None):
    with _WARM_LOCK:
        _stop_warm_server_locked(reason=reason)


def _idle_shutdown():
    with _WARM_LOCK:
        process = _WARM_SERVER.get("process")
        if process is None or process.poll() is not None:
            _stop_warm_server_locked()
            return
        idle_seconds = float(_WARM_SERVER.get("idle_seconds") or 180)
        elapsed = time.monotonic() - float(_WARM_SERVER.get("last_used") or 0.0)
        if elapsed >= idle_seconds:
            _stop_warm_server_locked(reason="Serveur LLM local arrete apres inactivite.")
            return
        delay = max(1.0, idle_seconds - elapsed)
        timer = threading.Timer(delay, _idle_shutdown)
        timer.daemon = True
        _WARM_SERVER["timer"] = timer
        timer.start()


def _touch_warm_server_locked(idle_seconds):
    _WARM_SERVER["last_used"] = time.monotonic()
    _WARM_SERVER["idle_seconds"] = int(idle_seconds)
    _cancel_idle_timer_locked()
    timer = threading.Timer(float(idle_seconds), _idle_shutdown)
    timer.daemon = True
    _WARM_SERVER["timer"] = timer
    timer.start()


def _warm_server_eligible(model):
    if not _is_windows_runtime():
        return False, "Serveur chaud reserve a Windows."
    if not model.get("warm_server_enabled", False):
        return False, "Serveur chaud desactive."
    if not model.get("warm_server_local_only", True):
        return False, "Configuration refusee : le serveur LLM doit rester local uniquement."
    server = Path(model.get("llama_server_path", ""))
    if not server.is_file():
        return False, f"llama-server introuvable : {server}"
    available_mb = _available_ram_mb()
    threshold = int(model.get("warm_server_min_available_ram_mb", 850))
    if available_mb is not None and available_mb < threshold:
        return False, f"RAM disponible insuffisante pour garder le modele charge ({available_mb} Mo < {threshold} Mo)."
    return True, None


def _find_loopback_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


def _server_args(model, port):
    args = [
        str(model["llama_server_path"]),
        "-m", str(model["path"]),
        "-c", str(model["context_size"]),
        "-t", str(model["threads"]),
        "--host", "127.0.0.1",
        "--port", str(int(port)),
        "--no-webui",
    ]
    if model.get("mmproj_path"):
        args.extend(["--mmproj", str(model["mmproj_path"])])
    return args


def _server_health(port, timeout=1.0):
    request = urllib.request.Request(f"http://127.0.0.1:{int(port)}/health", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=float(timeout)) as response:
            if int(getattr(response, "status", 200)) != 200:
                return False
            payload = json.loads(response.read(65536).decode("utf-8", errors="replace"))
            return payload.get("status") == "ok"
    except urllib.error.HTTPError as exc:
        # 503 signifie que le serveur est vivant mais charge encore le modele.
        if exc.code == 503:
            return False
        return False
    except Exception:
        return False


def _ensure_warm_server(model):
    eligible, reason = _warm_server_eligible(model)
    if not eligible:
        return False, reason

    model_key = _warm_model_key(model)
    with _WARM_LOCK:
        current = _WARM_SERVER.get("process")
        if current is not None and current.poll() is None and _WARM_SERVER.get("model_key") == model_key:
            _touch_warm_server_locked(model.get("warm_server_idle_seconds", 180))
            return True, None
        if current is not None:
            _stop_warm_server_locked(reason="Redemarrage du serveur LLM pour changement de modele.")

        port = _find_loopback_port()
        kwargs = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.DEVNULL,
            "shell": False,
            "cwd": str(Path(model["llama_server_path"]).parent),
        }
        if _is_windows_runtime():
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            process = subprocess.Popen(_server_args(model, port), **kwargs)
        except Exception as exc:
            _WARM_SERVER["last_error"] = f"Demarrage llama-server impossible : {exc}"
            return False, _WARM_SERVER["last_error"]
        _WARM_SERVER.update({"process": process, "port": port, "model_key": model_key, "last_error": None})

    deadline = time.monotonic() + float(model.get("warm_server_start_timeout_seconds", 45))
    while time.monotonic() < deadline:
        with _WARM_LOCK:
            process = _WARM_SERVER.get("process")
            if process is None or process.poll() is not None:
                code = None if process is None else process.returncode
                _stop_warm_server_locked(reason=f"llama-server s'est arrete pendant le chargement (code {code}).")
                return False, _WARM_SERVER.get("last_error")
        if _server_health(port, timeout=1.0):
            with _WARM_LOCK:
                _touch_warm_server_locked(model.get("warm_server_idle_seconds", 180))
            return True, None
        time.sleep(0.25)

    stop_warm_server("Chargement llama-server trop long ; retour a llama-cli.")
    return False, "Chargement llama-server trop long ; retour a llama-cli."


def _run_llama_server(prompt, model):
    ok, reason = _ensure_warm_server(model)
    if not ok:
        raise RuntimeError(reason or "Serveur LLM local indisponible.")
    with _WARM_LOCK:
        port = int(_WARM_SERVER["port"])

    body = json.dumps({
        "prompt": prompt,
        "n_predict": int(model["max_tokens"]),
        "temperature": float(model["temperature"]),
        "cache_prompt": True,
        "stream": False,
    }).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/completion",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=float(model["timeout_seconds"])) as response:
            raw = response.read(4 * 1024 * 1024)
        payload = json.loads(raw.decode("utf-8", errors="replace"))
        content = payload.get("content")
        if not isinstance(content, str):
            raise RuntimeError("Reponse llama-server sans contenu texte.")
        with _WARM_LOCK:
            _touch_warm_server_locked(model.get("warm_server_idle_seconds", 180))
        return content.strip()
    except Exception:
        # Un serveur devenu invalide ne doit pas rester accroche en memoire.
        stop_warm_server("Erreur pendant une requete llama-server.")
        raise


def _strip_hidden_reasoning(text):
    """Supprime les traces de raisonnement internes avant parsing ou affichage."""
    value = str(text or "")
    # Balises courantes des modeles de raisonnement.
    value = re.sub(r"<think>.*?</think>", "", value, flags=re.I | re.S)
    value = re.sub(r"\[Start thinking\].*?\[End thinking\]", "", value, flags=re.I | re.S)
    # Certaines versions n'emettent pas de marqueur de fin. Si un objet JSON suit,
    # on conserve directement la partie JSON, qui est le seul contrat autorise.
    lowered = value.casefold()
    if "[start thinking]" in lowered or "thinking process:" in lowered:
        brace = value.find("{")
        if brace >= 0:
            value = value[brace:]
        else:
            # Sans sortie structuree exploitable, ne jamais exposer le raisonnement.
            return ""
    return value.strip()


def _run_llama_adaptive(prompt, model):
    eligible, _ = _warm_server_eligible(model)
    if eligible:
        try:
            return _run_llama_server(prompt, model), "llama-server-warm"
        except Exception as exc:
            log_event("warning", "backend.llama.warm", f"fallback cli : {type(exc).__name__}")
    return _run_llama_cli(prompt, model), "llama-cli"


atexit.register(stop_warm_server)

def _local_conversation_style_hint():
    path = ROOT_DIR / "memory" / "user_preferences.json"
    try:
        prefs = json.loads(path.read_text(encoding="utf-8-sig"))
        assistant = prefs.get("assistant", {}) if isinstance(prefs, dict) else {}
    except Exception:
        assistant = {}
    style = str(assistant.get("response_style", "natural")).lower()
    emoji = str(assistant.get("emoji_level", "light")).lower()
    detail = str(assistant.get("response_detail", "balanced")).lower()
    style_label = {"professional": "professionnel et direct", "concise": "tres concis", "natural": "naturel et chaleureux"}.get(style, "naturel et chaleureux")
    emoji_label = {"none": "sans emoji", "expressive": "avec quelques emoji utiles", "light": "avec au plus un emoji utile"}.get(emoji, "avec au plus un emoji utile")
    detail_label = {"short": "reponse courte", "detailed": "reponse un peu plus detaillee", "balanced": "reponse equilibree"}.get(detail, "reponse equilibree")
    return f"Pour une reponse conversationnelle uniquement : ton {style_label}, {emoji_label}, {detail_label}."


def _build_prompt(user_message):
    return f"""Tu es la couche de comprehension linguistique locale d'AgentLocal.
Tu ne commandes jamais Windows et tu n'executes jamais rien.
Ton role est seulement de reformuler la demande utilisateur en une commande francaise courte et explicite que le moteur deterministe d'AgentLocal devra ensuite valider.

Regles imperatives :
- Ne jamais inventer un nom de fichier, dossier, application, site, nombre, chemin ou destination.
- Conserver les noms propres et noms de fichiers exactement comme l'utilisateur les a fournis.
- Respecter les negations. Une phrase negative ne doit jamais devenir une action positive.
- Ne jamais proposer PowerShell, CMD, Windows Terminal, Bash, WSL ni une commande shell.
- Si la demande est ambigue, demander une precision.
- Si c'est une simple conversation, repondre brievement sans proposer d'action.
- {_local_conversation_style_hint()}
- Une commande canonique doit representer une seule intention claire, sauf si l'utilisateur demande explicitement plusieurs actions.
- Repondre UNIQUEMENT avec un objet JSON, sans markdown ni texte autour.

Formats autorises :
{{"type":"command","canonical_command":"...","confidence":0.00}}
{{"type":"clarification","reply":"...","confidence":0.00}}
{{"type":"conversation","reply":"...","confidence":0.00}}
{{"type":"refusal","reply":"...","confidence":0.00}}

Demande utilisateur : {json.dumps(str(user_message), ensure_ascii=False)}
"""


def _run_llama_cli(prompt, model):
    args = [
        str(model["llama_cli_path"]),
        "-m", str(model["path"]),
        "-c", str(model["context_size"]),
        "-t", str(model["threads"]),
        "-n", str(model["max_tokens"]),
        "--temp", str(model["temperature"]),
        "--no-display-prompt",
    ]

    if model.get("mmproj_path"):
        args.extend(["--mmproj", str(model["mmproj_path"])])

    args.extend(["-p", prompt])

    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": model["timeout_seconds"],
        "shell": False,
        "cwd": str(Path(model["llama_cli_path"]).parent),
    }

    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    completed = subprocess.run(args, **kwargs)
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise RuntimeError(stderr[-1200:] or f"llama-cli a quitte avec le code {completed.returncode}.")

    return (completed.stdout or "").strip()


def _extract_json_object(text):
    text = str(text or "").strip()
    if not text:
        return None

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _normalize_confidence(value):
    return normalized_confidence(value)


def _contains_forbidden_shell_target(text):
    lowered = str(text or "").casefold()
    return any(term in lowered for term in FORBIDDEN_EXECUTION_TERMS)


def _safe_non_action_result(kind, reply, confidence, active_name):
    return {
        "schema_version": SCHEMA_VERSION,
        "backend": "llama",
        "understood": True,
        "actions": [],
        "conversation": True,
        "reply": str(reply or "").strip() or "Je prefere que tu precises ta demande.",
        "llm_type": kind,
        "llm_confidence": confidence,
        "active_model": active_name,
    }


def interpret(user_message):
    """Le LLM normalise la demande; le backend deterministe reste l'autorite finale."""
    ok, reason = availability()
    if not ok:
        raise RuntimeError(reason)

    active_name, model, _ = get_active_model_config()
    raw_output, inference_engine = _run_llama_adaptive(_build_prompt(user_message), model)
    raw_output = _strip_hidden_reasoning(raw_output)
    parsed = _extract_json_object(raw_output)
    if not isinstance(parsed, dict):
        raise RuntimeError("Le modele local n'a pas retourne un JSON exploitable.")

    kind = str(parsed.get("type", "")).strip().lower()
    confidence = _normalize_confidence(parsed.get("confidence"))

    if kind in {"conversation", "clarification", "refusal"}:
        result = _safe_non_action_result(kind, _strip_hidden_reasoning(parsed.get("reply")), confidence, active_name)
        result["llm_engine"] = inference_engine
        return result

    if kind != "command":
        return _safe_non_action_result(
            "clarification",
            "Je n'ai pas suffisamment confiance dans mon interpretation. Peux-tu reformuler ?",
            confidence,
            active_name,
        )

    canonical = str(parsed.get("canonical_command", "")).strip()
    if not canonical:
        return _safe_non_action_result(
            "clarification",
            "Je n'ai pas reussi a identifier une commande precise.",
            confidence,
            active_name,
        )

    if confidence < model["minimum_confidence"]:
        return _safe_non_action_result(
            "clarification",
            "Je ne suis pas assez sur de ce que tu veux faire. Peux-tu preciser ?",
            confidence,
            active_name,
        )

    faithful, explanation = semantic_fidelity(user_message, canonical)
    if not faithful:
        return _safe_non_action_result(
            "clarification", explanation, confidence, active_name,
        )

    if _contains_forbidden_shell_target(canonical):
        return _safe_non_action_result(
            "refusal",
            "Cette demande vise un terminal ou un shell non autorise par AgentLocal.",
            confidence,
            active_name,
        )

    from backends import deterministic_backend

    deterministic = deterministic_backend.interpret(canonical)
    if not isinstance(deterministic, dict) or not deterministic.get("understood"):
        return _safe_non_action_result(
            "clarification",
            "J'ai compris l'idee generale, mais je ne peux pas la convertir en action sure. Peux-tu preciser ?",
            confidence,
            active_name,
        )

    result = dict(deterministic)
    result["backend"] = "llama"
    result["routing"] = "llm_normalized_then_deterministic"
    result["llm_confidence"] = confidence
    result["llm_canonical_command"] = canonical
    result["active_model"] = active_name
    result["llm_engine"] = inference_engine
    return result
