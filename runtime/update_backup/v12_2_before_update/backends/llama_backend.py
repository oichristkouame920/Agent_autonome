import json
import os
import subprocess
from pathlib import Path

from project_paths import PROJECT_ROOT, get_project_path, resolve_project_relative


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

    model["context_size"] = max(512, min(int(model.get("context_size", 2048) or 2048), 8192))
    model["threads"] = max(1, min(int(model.get("threads", 4) or 4), 16))
    model["max_tokens"] = max(32, min(int(model.get("max_tokens", 192) or 192), 512))
    model["temperature"] = max(0.0, min(float(model.get("temperature", 0.0) or 0.0), 1.0))

    return active_name, model, config


def probe_llama_runtime(llama_cli_path, timeout_seconds=10):
    """Verifie que llama-cli peut reellement demarrer (DLL comprises), sans charger de modele."""
    path = Path(llama_cli_path)
    if not path.is_file():
        return False, f"llama-cli introuvable : {path}"

    cache_key = (str(path.resolve()), path.stat().st_mtime_ns, path.stat().st_size)
    cached = _RUNTIME_PROBE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    # Notre runtime cible est Windows. Les tests sur une autre plateforme ne doivent pas
    # tenter d'executer un .exe Windows.
    if os.name != "nt":
        result = (True, "Sonde d'execution reportee a Windows.")
        _RUNTIME_PROBE_CACHE[cache_key] = result
        return result

    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": max(3, min(int(timeout_seconds or 10), 30)),
        "shell": False,
        "cwd": str(path.parent),
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
    }
    try:
        completed = subprocess.run([str(path), "--version"], **kwargs)
    except (OSError, subprocess.SubprocessError) as exc:
        result = (False, f"Runtime llama.cpp inutilisable : {exc}")
    else:
        if completed.returncode == 0:
            result = (True, None)
        else:
            detail = (completed.stderr or completed.stdout or "").strip()
            result = (
                False,
                "llama-cli ne demarre pas correctement"
                + (f" : {detail[-500:]}" if detail else "."),
            )

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
        ok, reason = probe_llama_runtime(llama_cli)
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
    }


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
    try:
        return max(0.0, min(float(value), 1.0))
    except (TypeError, ValueError):
        return 0.0


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
    raw_output = _run_llama_cli(_build_prompt(user_message), model)
    parsed = _extract_json_object(raw_output)
    if not isinstance(parsed, dict):
        raise RuntimeError("Le modele local n'a pas retourne un JSON exploitable.")

    kind = str(parsed.get("type", "")).strip().lower()
    confidence = _normalize_confidence(parsed.get("confidence"))

    if kind in {"conversation", "clarification", "refusal"}:
        return _safe_non_action_result(kind, parsed.get("reply"), confidence, active_name)

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
    return result
