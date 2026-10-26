import importlib
import json
import re
import time

from pathlib import Path
from project_paths import PROJECT_ROOT, get_project_path
from runtime_resilience import log_event, log_exception


# ============================================================
# VERSION
# ============================================================

SCHEMA_VERSION = 1
ROUTING_PATCH_VERSION = "2026-10-26-v11.3-resilience"

# ============================================================
# RESILIENCE SESSION LLM
# ============================================================

LLAMA_FAILURE_THRESHOLD = 2
LLAMA_COOLDOWN_SECONDS = 120
_llama_consecutive_failures = 0
_llama_disabled_until = 0.0


def _llama_circuit_state():
    now = time.monotonic()
    remaining = max(0, int(_llama_disabled_until - now))
    return {
        "failures": _llama_consecutive_failures,
        "disabled": remaining > 0,
        "retry_after_seconds": remaining,
    }


def _record_llama_success():
    global _llama_consecutive_failures, _llama_disabled_until
    _llama_consecutive_failures = 0
    _llama_disabled_until = 0.0


def _record_llama_failure(error=None):
    global _llama_consecutive_failures, _llama_disabled_until
    _llama_consecutive_failures += 1
    if error is not None:
        log_exception("backend.llama", error)
    if _llama_consecutive_failures >= LLAMA_FAILURE_THRESHOLD:
        _llama_disabled_until = time.monotonic() + LLAMA_COOLDOWN_SECONDS
        log_event(
            "warning",
            "backend.llama",
            f"circuit ouvert pour {LLAMA_COOLDOWN_SECONDS}s apres {_llama_consecutive_failures} echecs",
        )


def _llama_session_available():
    state = _llama_circuit_state()
    if not state["disabled"] and _llama_disabled_until:
        _record_llama_success()
        state = _llama_circuit_state()
    return not state["disabled"]


# ============================================================
# CHEMINS
# ============================================================

ROOT_DIR = PROJECT_ROOT

AGENT_CONFIG_FILE = (
    get_project_path("config")
    / "agent.json"
)


# ============================================================
# CONFIGURATION PAR DEFAUT
# ============================================================

DEFAULT_CONFIG = {
    "schema_version": 1,

    "backend": {
        "mode": "auto",
        "preferred": "llama",
        "fallback": "deterministic",
    }
}


# ============================================================
# CHARGEMENT CONFIGURATION
# ============================================================

def load_agent_config():
    """
    Charge config/agent.json.

    Si le fichier est absent ou invalide,
    AgentLocal utilise une configuration
    de secours sûre.
    """

    if not AGENT_CONFIG_FILE.exists():

        return DEFAULT_CONFIG.copy()

    try:

        with open(
            AGENT_CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

    except (
        OSError,
        json.JSONDecodeError
    ):

        return DEFAULT_CONFIG.copy()

    if not isinstance(
        data,
        dict
    ):

        return DEFAULT_CONFIG.copy()

    return data


# ============================================================
# CONFIG BACKEND
# ============================================================

def get_backend_config():

    config = load_agent_config()

    backend = config.get(
        "backend",
        {}
    )

    if not isinstance(
        backend,
        dict
    ):

        backend = {}

    mode = str(
        backend.get(
            "mode",
            "auto"
        )
    ).lower().strip()

    preferred = str(
        backend.get(
            "preferred",
            "llama"
        )
    ).lower().strip()

    fallback = str(
        backend.get(
            "fallback",
            "deterministic"
        )
    ).lower().strip()

    valid_modes = {
        "auto",
        "llama",
        "deterministic",
    }

    if mode not in valid_modes:
        mode = "auto"

    return {
        "mode": mode,
        "preferred": preferred,
        "fallback": fallback,
    }


# ============================================================
# CHARGEMENT DYNAMIQUE D'UN BACKEND
# ============================================================

def load_backend_module(
    backend_name
):
    """
    Charge un backend uniquement s'il existe.

    Le gestionnaire ne fait jamais planter
    AgentLocal parce qu'un backend manque.
    """

    backend_name = (
        str(backend_name)
        .lower()
        .strip()
    )

    if backend_name == "deterministic":

        module_name = (
            "backends.deterministic_backend"
        )

    elif backend_name == "llama":

        module_name = (
            "backends.llama_backend"
        )

    else:

        return (
            False,
            None,
            (
                "Backend inconnu : "
                f"{backend_name}"
            )
        )

    try:

        module = importlib.import_module(
            module_name
        )

    except ModuleNotFoundError:

        return (
            False,
            None,
            (
                "Backend non installé : "
                f"{backend_name}"
            )
        )

    except Exception as error:

        return (
            False,
            None,
            (
                "Impossible de charger "
                f"{backend_name} : {error}"
            )
        )

    # --------------------------------------------------------
    # VERIFICATION DU CONTRAT
    # --------------------------------------------------------

    interpret_function = getattr(
        module,
        "interpret",
        None
    )

    if not callable(
        interpret_function
    ):

        return (
            False,
            None,
            (
                f"Le backend {backend_name} "
                "ne possède pas interpret()."
            )
        )

    return (
        True,
        module,
        None
    )




# ============================================================
# DISPONIBILITE REELLE D'UN BACKEND
# ============================================================

def get_backend_runtime_availability(module):
    """
    Vérifie la disponibilité réelle d'un backend lorsqu'il expose
    availability() ou is_available(). Pour le déterministe, l'import
    réussi suffit. Cette vérification ne lance jamais le modèle.
    """
    availability_function = getattr(module, "availability", None)
    if callable(availability_function):
        try:
            value = availability_function()
        except Exception as error:
            return False, str(error)

        if isinstance(value, tuple):
            ok = bool(value[0])
            reason = value[1] if len(value) > 1 else None
            return ok, reason

        return bool(value), None

    is_available_function = getattr(module, "is_available", None)
    if callable(is_available_function):
        try:
            return bool(is_available_function()), None
        except Exception as error:
            return False, str(error)

    return True, None


# ============================================================
# DISPONIBILITE BACKEND
# ============================================================

def is_backend_available(
    backend_name
):
    """
    Vérifie uniquement si le backend Python
    existe et respecte le contrat.

    Important :
    cette fonction ne lance PAS llama-cli.exe.

    Donc Smart App Control ne génère aucun
    blocage ou popup pendant cette étape.
    """

    success, module, error = (
        load_backend_module(
            backend_name
        )
    )

    if not success or module is None:
        return False

    runtime_ok, _ = get_backend_runtime_availability(module)
    return runtime_ok


# ============================================================
# CHOIX DU BACKEND
# ============================================================

def select_backend():
    """
    Sélectionne le moteur à utiliser.

    MODE auto :
        preferred si disponible
        sinon fallback

    MODE deterministic :
        deterministic uniquement

    MODE llama :
        llama demandé explicitement
        sinon fallback si llama indisponible
    """

    config = get_backend_config()

    mode = config[
        "mode"
    ]

    preferred = config[
        "preferred"
    ]

    fallback = config[
        "fallback"
    ]

    # ========================================================
    # MODE DETERMINISTE FORCE
    # ========================================================

    if mode == "deterministic":

        success, module, error = (
            load_backend_module(
                "deterministic"
            )
        )

        if success:

            runtime_ok, runtime_reason = get_backend_runtime_availability(module)
            if runtime_ok:
                return (
                    True,
                    "deterministic",
                    module,
                    None
                )
            error = runtime_reason or error

        return (
            False,
            None,
            None,
            error
        )

    # ========================================================
    # MODE LLAMA FORCE
    # ========================================================

    if mode == "llama":

        if not _llama_session_available():
            fallback_success, fallback_module, fallback_error = load_backend_module(fallback)
            if fallback_success:
                fallback_runtime_ok, fallback_runtime_reason = get_backend_runtime_availability(fallback_module)
                if fallback_runtime_ok:
                    state = _llama_circuit_state()
                    return (
                        True,
                        fallback,
                        fallback_module,
                        f"LLM temporairement desactive apres echecs. Nouvel essai dans {state['retry_after_seconds']} s.",
                    )
                fallback_error = fallback_runtime_reason or fallback_error
            return False, None, None, fallback_error or "LLM temporairement indisponible."

        success, module, error = (
            load_backend_module(
                "llama"
            )
        )

        if success:

            runtime_ok, runtime_reason = get_backend_runtime_availability(module)
            if runtime_ok:
                return (
                    True,
                    "llama",
                    module,
                    None
                )
            error = runtime_reason or error

        # ----------------------------------------------------
        # FALLBACK DE SECURITE
        # ----------------------------------------------------

        fallback_success, fallback_module, fallback_error = (
            load_backend_module(
                fallback
            )
        )

        if fallback_success:

            fallback_runtime_ok, fallback_runtime_reason = get_backend_runtime_availability(fallback_module)
            if fallback_runtime_ok:
                return (
                    True,
                    fallback,
                    fallback_module,
                    (
                        "Le backend llama n'est pas "
                        "disponible. Utilisation du "
                        f"backend {fallback}."
                    )
                )
            fallback_error = fallback_runtime_reason or fallback_error

        return (
            False,
            None,
            None,
            (
                f"{error} "
                f"{fallback_error}"
            )
        )

    # ========================================================
    # MODE AUTO
    # ========================================================

    # --------------------------------------------------------
    # BACKEND PREFERE
    # --------------------------------------------------------

    if preferred == "llama" and not _llama_session_available():
        success, module, error = (False, None, "LLM temporairement desactive apres echecs de session.")
    else:
        success, module, error = (
            load_backend_module(
                preferred
            )
        )

    if success:

        runtime_ok, runtime_reason = get_backend_runtime_availability(module)
        if runtime_ok:
            return (
                True,
                preferred,
                module,
                None
            )
        error = runtime_reason or error

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    fallback_success, fallback_module, fallback_error = (
        load_backend_module(
            fallback
        )
    )

    if fallback_success:

        fallback_runtime_ok, fallback_runtime_reason = get_backend_runtime_availability(fallback_module)
        if fallback_runtime_ok:
            return (
                True,
                fallback,
                fallback_module,
                (
                    f"Backend {preferred} indisponible. "
                    f"Fallback vers {fallback}."
                )
            )
        fallback_error = fallback_runtime_reason or fallback_error

    return (
        False,
        None,
        None,
        (
            "Aucun backend disponible. "
            f"{error} "
            f"{fallback_error}"
        )
    )


# ============================================================
# PRE-INTERPRETATION DETERMINISTE A HAUTE CONFIANCE
# ============================================================

DETERMINISTIC_PREFLIGHT_ACTIONS = {
    "open_application",
    "close_application",
    "check_application",
    "manage_window",
    "run_routine",
    "open_website",
    "close_website",
    "read_system_info",
    "read_power_info",
    "read_network_info",
    "read_clipboard",
    "write_clipboard",
    "copy_file_path",
    "list_browser_tabs",
    "activate_browser_tab",
    "open_last_reference",
    "read_last_reference",
    "copy_last_reference_path",
    "advanced_file_search",
    "take_screenshot",
    "read_audio_state",
    "set_audio_volume",
    "change_audio_volume",
    "set_audio_mute",
    "create_zip_archive",
    "extract_zip_archive",
    "undo_last_file_action",
    "inspect_file_metadata",
    "calculate_file_sha256",
    "compare_files_sha256",
    "find_duplicate_files",
}


def _is_high_confidence_deterministic_result(result, module):
    """
    Ne court-circuite le backend principal que pour une intention explicite
    et fermee. Les manipulations de fichiers nommés restent hors preflight ;
    seule la recherche avancée par métadonnées, strictement lecture seule et
    sans nom libre de fichier, peut passer ici.
    """
    if not isinstance(result, dict) or not result.get("understood"):
        return False

    actions = result.get("actions", [])
    if not isinstance(actions, list):
        return False

    # Petite conversation locale (aide, organisation ambigue des fenetres, etc.).
    if not actions:
        return bool(result.get("conversation") and str(result.get("reply", "")).strip())

    configured_sites = set()
    loader = getattr(module, "load_site_names", None)
    if callable(loader):
        try:
            configured_sites = set(loader())
        except Exception:
            configured_sites = set()

    for item in actions:
        if not isinstance(item, dict):
            return False
        action = str(item.get("action", "")).strip().lower()
        target = str(item.get("target", "")).strip().lower()

        if action not in DETERMINISTIC_PREFLIGHT_ACTIONS:
            return False

        # Un nom de site generique n'est pas suffisant : il doit deja etre
        # present dans la liste blanche sites.json.
        if action in {"open_website", "close_website"}:
            explicit_domain = bool(
                re.fullmatch(r"[a-z0-9][a-z0-9.-]*\.[a-z]{2,63}", target)
            )
            if target not in configured_sites and not explicit_domain:
                return False

    return True


def _deterministic_preflight(user_message):
    success, module, _ = load_backend_module("deterministic")
    if not success or module is None:
        return None

    try:
        result = module.interpret(user_message)
    except Exception:
        return None

    if _is_high_confidence_deterministic_result(result, module):
        result = dict(result)
        result["backend"] = "deterministic"
        result["routing"] = "deterministic_preflight"
        return result

    return None


# ============================================================
# INTERPRETATION
# ============================================================

def interpret(
    user_message
):
    """
    Point d'entrée unique destiné à AgentLocal.

    Agent.py n'aura plus besoin de savoir
    quel moteur est réellement utilisé.
    """

    success, backend_name, module, warning = (
        select_backend()
    )

    if not success:

        return {
            "schema_version": SCHEMA_VERSION,
            "backend": None,
            "understood": False,
            "actions": [],
            "error": warning,
        }

    # Les intentions explicites et fermees sont d'abord verifiees par le
    # moteur deterministe. Cela evite de charger/invoquer le LLM pour une
    # commande simple et garantit le meme comportement dans la GUI.
    if backend_name != "deterministic":
        preflight = _deterministic_preflight(user_message)
        if preflight is not None:
            if warning:
                preflight["backend_warning"] = warning
            return preflight

    try:

        result = module.interpret(
            user_message
        )

    except Exception as error:

        if backend_name == "llama":
            _record_llama_failure(error)

        # ----------------------------------------------------
        # SI LE BACKEND PRINCIPAL ECHOUE AU MOMENT
        # DE L'INTERPRETATION, ON TENTE LE DETERMINISTE.
        # ----------------------------------------------------

        if backend_name != "deterministic":

            fallback_success, fallback_module, _ = (
                load_backend_module(
                    "deterministic"
                )
            )

            if fallback_success:

                try:

                    fallback_result = (
                        fallback_module.interpret(
                            user_message
                        )
                    )

                    fallback_result[
                        "backend_warning"
                    ] = (
                        f"Le backend {backend_name} "
                        "a échoué. Passage automatique "
                        "au backend deterministic."
                    )

                    return fallback_result

                except Exception:
                    pass

        return {
            "schema_version": SCHEMA_VERSION,
            "backend": backend_name,
            "understood": False,
            "actions": [],
            "error": str(error),
        }

    # ========================================================
    # VERIFICATION DU FORMAT RETOURNE
    # ========================================================

    if not isinstance(
        result,
        dict
    ):

        if backend_name == "llama":
            _record_llama_failure(RuntimeError("format de reponse LLM invalide"))

        return {
            "schema_version": SCHEMA_VERSION,
            "backend": backend_name,
            "understood": False,
            "actions": [],
            "error": (
                "Le backend a retourné "
                "un format invalide."
            ),
        }

    # --------------------------------------------------------
    # GARANTIT LES CHAMPS MINIMAUX
    # --------------------------------------------------------

    result.setdefault(
        "schema_version",
        SCHEMA_VERSION
    )

    result.setdefault(
        "backend",
        backend_name
    )

    result.setdefault(
        "understood",
        False
    )

    result.setdefault(
        "actions",
        []
    )

    if warning:

        result[
            "backend_warning"
        ] = warning

    if backend_name == "llama":
        _record_llama_success()

    return result


# ============================================================
# INFORMATIONS BACKEND
# ============================================================

def get_backend_status():
    """
    Retourne un état simple utilisable
    plus tard dans l'interface graphique.
    """

    config = get_backend_config()

    deterministic_available = (
        is_backend_available(
            "deterministic"
        )
    )

    llama_available = (
        is_backend_available(
            "llama"
        )
    )

    success, selected, module, warning = (
        select_backend()
    )

    llama_status = None
    success_llama_module, llama_module, _ = load_backend_module("llama")
    if success_llama_module and llama_module is not None:
        status_function = getattr(llama_module, "get_status", None)
        if callable(status_function):
            try:
                llama_status = status_function()
            except Exception:
                llama_status = None

    return {
        "schema_version": SCHEMA_VERSION,

        "mode": config[
            "mode"
        ],

        "preferred": config[
            "preferred"
        ],

        "fallback": config[
            "fallback"
        ],

        "deterministic_available": (
            deterministic_available
        ),

        "llama_available": (
            llama_available
        ),

        "selected": (
            selected
            if success
            else None
        ),

        "warning": warning,
        "llama_status": llama_status,
        "llama_session_circuit": _llama_circuit_state(),
    }


# ============================================================
# TEST MANUEL
# ============================================================

def main():

    print()
    print("=" * 60)
    print("BACKEND MANAGER - AgentLocal")
    print("=" * 60)
    print()

    status = get_backend_status()

    print(
        "Mode :",
        status["mode"]
    )

    print(
        "Backend préféré :",
        status["preferred"]
    )

    print(
        "Fallback :",
        status["fallback"]
    )

    print()

    print(
        "Deterministic disponible :",
        status[
            "deterministic_available"
        ]
    )

    print(
        "Llama disponible :",
        status[
            "llama_available"
        ]
    )

    print()

    print(
        "Backend sélectionné :",
        status["selected"]
    )

    if status["warning"]:

        print(
            "Information :",
            status["warning"]
        )

    print()
    print("-" * 60)
    print()

    while True:

        try:

            user_message = input(
                "Vous > "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError
        ):

            break

        if user_message.lower() in {
            "quit",
            "exit",
            "quitter",
            "stop",
            "sort",
            "arrête",
            "ferme",
            "quitte",
        }:

            break

        result = interpret(
            user_message
        )

        print()

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2
            )
        )

        print()


if __name__ == "__main__":
    main()