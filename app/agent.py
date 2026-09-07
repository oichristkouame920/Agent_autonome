import re
import subprocess
from pathlib import Path

from windows_tools import (
    is_application_running,
    open_application,
)


# ============================================================
# CHEMINS DU PROJET
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]


LLAMA_EXE = (
    ROOT_DIR
    / "llama.cpp"
    / "build"
    / "bin"
    / "Release"
    / "llama-cli.exe"
)


MODEL_FILE = (
    ROOT_DIR
    / "models"
    / "Qwen3.5-0.8B-Q4_0.gguf"
)


# ============================================================
# MODE DEBUG
# ============================================================

# True pendant le développement.
#
# Permet de voir exactement
# la réponse générée par le LLM.

DEBUG = True


# ============================================================
# PROMPT SYSTEME
# ============================================================

SYSTEM_PROMPT = (
    "Tu es AgentLocal, un assistant local "
    "qui répond principalement en français "
    "et parle toujours de lui à la première personne. "

    "Tu n'inventes jamais tes capacités, "
    "tes accès ou les résultats d'une action. "

    "Tu n'exécutes jamais directement "
    "une action Windows. "

    "Lorsque l'utilisateur demande une ou plusieurs "
    "actions sur l'ordinateur, "
    "tu dois produire une ligne ACTION_REQUEST "
    "pour chaque action demandée. "

    "Le format exact est : "
    "ACTION_REQUEST | action=nom_action | "
    "target=cible | status=waiting_for_tool. "

    "Les seules actions actuellement disponibles sont "
    "open_application et check_application. "

    "Les seules applications actuellement connues sont "
    "edge et vscode. "

    "Si l'utilisateur dit ouvre Edge, "
    "réponds exactement : "
    "ACTION_REQUEST | action=open_application | "
    "target=edge | status=waiting_for_tool. "

    "Si l'utilisateur dit ouvre VS Code, "
    "réponds exactement : "
    "ACTION_REQUEST | action=open_application | "
    "target=vscode | status=waiting_for_tool. "

    "Si l'utilisateur dit ouvre Edge et VS Code, "
    "réponds avec exactement deux lignes : "
    "ACTION_REQUEST | action=open_application | "
    "target=edge | status=waiting_for_tool\n"
    "ACTION_REQUEST | action=open_application | "
    "target=vscode | status=waiting_for_tool. "

    "Si l'utilisateur demande si Edge est ouvert, "
    "réponds exactement : "
    "ACTION_REQUEST | action=check_application | "
    "target=edge | status=waiting_for_tool. "

    "Si l'utilisateur demande si VS Code est ouvert, "
    "réponds exactement : "
    "ACTION_REQUEST | action=check_application | "
    "target=vscode | status=waiting_for_tool. "

    "Si l'utilisateur demande plusieurs vérifications, "
    "produis également une ligne ACTION_REQUEST "
    "pour chaque application. "

    "Si plusieurs actions sont demandées, "
    "tu ne dois en oublier aucune. "

    "Une action comprise n'est pas forcément autorisée. "

    "Tu ne peux jamais t'accorder toi-même "
    "une nouvelle permission. "

    "Tu ne dois jamais affirmer qu'une action "
    "a réussi avant confirmation du programme. "

    "Pour une conversation normale ne demandant "
    "aucune action système, "
    "réponds naturellement, clairement "
    "et brièvement en français."
)


# ============================================================
# FORMAT ACTION_REQUEST
# ============================================================

ACTION_PATTERN = re.compile(
    r"ACTION_REQUEST\s*\|\s*"
    r"action\s*=\s*([a-zA-Z0-9_-]+)\s*\|\s*"
    r"target\s*=\s*([a-zA-Z0-9_.-]+)\s*\|\s*"
    r"status\s*=\s*waiting_for_tool",
    re.IGNORECASE,
)


# ============================================================
# ALIAS DES APPLICATIONS
# ============================================================

TARGET_ALIASES = {

    # --------------------------------------------------------
    # EDGE
    # --------------------------------------------------------

    "edge": "edge",

    "msedge": "edge",

    "microsoftedge": "edge",

    "microsoft-edge": "edge",

    "microsoft_edge": "edge",


    # --------------------------------------------------------
    # VS CODE
    # --------------------------------------------------------

    "vscode": "vscode",

    "vs-code": "vscode",

    "vs_code": "vscode",

    "code": "vscode",

    "visualstudiocode": "vscode",

    "visual-studio-code": "vscode",

    "visual_studio_code": "vscode",
}


def normalize_target(target):
    """
    Transforme les différentes façons
    de nommer une application
    en identifiant interne unique.
    """

    target = (
        target
        .lower()
        .strip()
    )

    return TARGET_ALIASES.get(
        target,
        target
    )


# ============================================================
# VERIFICATION DES FICHIERS LOCAUX
# ============================================================

def check_local_files():
    """
    Vérifie que llama.cpp
    et le modèle GGUF existent.
    """

    if not LLAMA_EXE.exists():

        return (
            False,
            (
                "llama-cli.exe introuvable : "
                f"{LLAMA_EXE}"
            )
        )

    if not MODEL_FILE.exists():

        return (
            False,
            (
                "Modèle GGUF introuvable : "
                f"{MODEL_FILE}"
            )
        )

    return True, None


# ============================================================
# COMMUNICATION AVEC LE LLM LOCAL
# ============================================================

def ask_llm(user_message):
    """
    Lance le LLM local pour une seule instruction.

    Le LLM :
    - fonctionne hors ligne ;
    - ne possède aucun accès Windows direct ;
    - produit uniquement une intention.
    """

    valid, error = (
        check_local_files()
    )

    if not valid:
        return None, error

    command = [

        str(LLAMA_EXE),

        # ----------------------------------------------------
        # MODELE
        # ----------------------------------------------------

        "-m",
        str(MODEL_FILE),

        # ----------------------------------------------------
        # CONTEXTE REDUIT
        # ----------------------------------------------------

        "-c",
        "1024",

        # ----------------------------------------------------
        # MAXIMUM DE TOKENS GENERES
        # ----------------------------------------------------

        "-n",
        "140",

        # ----------------------------------------------------
        # THREADS CPU
        # ----------------------------------------------------

        "-t",
        "4",

        # ----------------------------------------------------
        # DESACTIVE LE RAISONNEMENT LONG
        # ----------------------------------------------------

        "--reasoning",
        "off",

        # ----------------------------------------------------
        # INTERDIT LES TELECHARGEMENTS
        # ----------------------------------------------------

        "--offline",

        # ----------------------------------------------------
        # UNE SEULE REPONSE
        # ----------------------------------------------------

        "--single-turn",

        # ----------------------------------------------------
        # ENTREES / SORTIES SIMPLIFIEES
        # ----------------------------------------------------

        "--simple-io",

        # ----------------------------------------------------
        # NE REAFFICHE PAS LE PROMPT
        # ----------------------------------------------------

        "--no-display-prompt",

        # ----------------------------------------------------
        # CACHE LES STATISTIQUES
        # ----------------------------------------------------

        "--no-show-timings",

        # ----------------------------------------------------
        # PROMPT SYSTEME
        # ----------------------------------------------------

        "-sys",
        SYSTEM_PROMPT,

        # ----------------------------------------------------
        # MESSAGE UTILISATEUR
        # ----------------------------------------------------

        "-p",
        user_message,
    ]

    try:

        result = subprocess.run(
            command,

            capture_output=True,

            text=True,

            encoding="utf-8",

            errors="replace",

            timeout=120,
        )

    except subprocess.TimeoutExpired:

        return (
            None,
            (
                "Le LLM local a dépassé "
                "le délai maximum."
            )
        )

    except OSError as error:

        return (
            None,
            (
                "Impossible de démarrer "
                f"le LLM local : {error}"
            )
        )

    # --------------------------------------------------------
    # ERREUR DU PROCESSUS
    # --------------------------------------------------------

    if result.returncode != 0:

        technical_error = (
            result.stderr.strip()
        )

        if technical_error:

            return (
                None,
                (
                    "Le LLM s'est arrêté "
                    f"avec le code {result.returncode}.\n"
                    f"{technical_error}"
                )
            )

        return (
            None,
            (
                "Le LLM s'est arrêté "
                f"avec le code {result.returncode}."
            )
        )

    # --------------------------------------------------------
    # REPONSE
    # --------------------------------------------------------

    response = (
        result.stdout.strip()
    )

    if not response:

        return (
            None,
            (
                "Le LLM n'a produit "
                "aucune réponse."
            )
        )

    return response, None


# ============================================================
# EXTRACTION DE PLUSIEURS ACTIONS
# ============================================================

def extract_actions(llm_response):
    """
    Extrait tous les ACTION_REQUEST
    présents dans la réponse.

    Exemple :

    ouvre Edge et VS Code

    peut produire :

    ACTION_REQUEST ... edge
    ACTION_REQUEST ... vscode
    """

    actions = []

    seen = set()

    for match in ACTION_PATTERN.finditer(
        llm_response
    ):

        action = (
            match
            .group(1)
            .lower()
            .strip()
        )

        target = normalize_target(
            match.group(2)
        )

        # ----------------------------------------------------
        # Evite les doublons accidentels du LLM.
        # ----------------------------------------------------

        action_key = (
            action,
            target
        )

        if action_key in seen:
            continue

        seen.add(
            action_key
        )

        actions.append({
            "action": action,
            "target": target,
        })

    return actions


# ============================================================
# EXECUTION SECURISEE
# ============================================================

def execute_action(action_data):
    """
    Python décide quelles actions
    existent réellement.

    Même si le LLM invente une action,
    elle sera refusée ici.
    """

    action = action_data[
        "action"
    ]

    target = action_data[
        "target"
    ]

    # --------------------------------------------------------
    # OUVRIR UNE APPLICATION
    # --------------------------------------------------------

    if action == "open_application":

        return open_application(
            target
        )

    # --------------------------------------------------------
    # VERIFIER UNE APPLICATION
    # --------------------------------------------------------

    if action == "check_application":

        return is_application_running(
            target
        )

    # --------------------------------------------------------
    # TOUT LE RESTE EST INTERDIT
    # --------------------------------------------------------

    return (
        False,
        (
            "Action inconnue ou "
            f"interdite : {action}"
        )
    )


# ============================================================
# EXECUTION DE PLUSIEURS ACTIONS
# ============================================================

def execute_actions(actions):
    """
    Exécute toutes les actions
    l'une après l'autre.

    L'échec d'une action
    n'empêche pas les suivantes.
    """

    results = []

    for action_data in actions:

        success, message = (
            execute_action(
                action_data
            )
        )

        if success:

            results.append(
                f"OK : {message}"
            )

        else:

            results.append(
                f"REFUSE : {message}"
            )

    return results


# ============================================================
# TRAITEMENT D'UNE INSTRUCTION
# ============================================================

def process_instruction(user_message):
    """
    Chaîne complète :

    Utilisateur
        ↓
    LLM
        ↓
    ACTION_REQUEST
        ↓
    Python
        ↓
    Permissions
        ↓
    Windows
        ↓
    Résultats réels
    """

    llm_response, error = (
        ask_llm(
            user_message
        )
    )

    if error:

        return (
            f"ERREUR : {error}"
        )

    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------

    if DEBUG:

        print()

        print(
            "----- REPONSE BRUTE DU LLM -----"
        )

        print(
            llm_response
        )

        print(
            "--------------------------------"
        )

        print()

    # --------------------------------------------------------
    # EXTRACTION DE TOUTES LES ACTIONS
    # --------------------------------------------------------

    actions = extract_actions(
        llm_response
    )

    # --------------------------------------------------------
    # AUCUNE ACTION :
    # CONVERSATION NORMALE
    # --------------------------------------------------------

    if not actions:
        return llm_response

    # --------------------------------------------------------
    # EXECUTION DE TOUTES LES ACTIONS
    # --------------------------------------------------------

    results = execute_actions(
        actions
    )

    return "\n".join(
        results
    )


# ============================================================
# INTERFACE CONSOLE
# ============================================================

def main():

    print()

    print(
        "=" * 58
    )

    print(
        "AgentLocal"
    )

    print(
        "LLM local + moteur de permissions Windows"
    )

    print(
        "=" * 58
    )

    print()

    print(
        "Mode : LOCAL"
    )

    print(
        "LLM : Qwen3.5 0.8B"
    )

    print(
        "Internet LLM : désactivé"
    )

    print(
        "Accès fichiers : désactivé"
    )

    print(
        "Shell libre : désactivé"
    )

    print()

    print(
        "Applications disponibles :"
    )

    print(
        "  - Edge"
    )

    print(
        "  - VS Code"
    )

    print()

    print(
        "Exemples :"
    )

    print(
        "  ouvre Edge"
    )

    print(
        "  ouvre VS Code"
    )

    print(
        "  ouvre Edge et VS Code"
    )

    print(
        "  vérifie si Edge est ouvert"
    )

    print(
        "  vérifie si VS Code est ouvert"
    )

    print()

    print(
        "Tape 'quit' pour arrêter AgentLocal."
    )

    print()

    # ========================================================
    # BOUCLE PRINCIPALE
    # ========================================================

    while True:

        try:

            user_message = input(
                "Vous > "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError
        ):

            print()

            print(
                "AgentLocal arrêté."
            )

            break

        # ----------------------------------------------------
        # MESSAGE VIDE
        # ----------------------------------------------------

        if not user_message:
            continue

        # ----------------------------------------------------
        # ARRET
        # ----------------------------------------------------

        if user_message.lower() in {
            "quit",
            "exit",
            "quitter",
            "stop",
        }:

            print()

            print(
                "AgentLocal arrêté."
            )

            break

        # ----------------------------------------------------
        # ANALYSE
        # ----------------------------------------------------

        print()

        print(
            "Analyse..."
        )

        result = process_instruction(
            user_message
        )

        # ----------------------------------------------------
        # RESULTAT
        # ----------------------------------------------------

        print()

        print(
            "AgentLocal >"
        )

        print(
            result
        )

        print()


# ============================================================
# DEMARRAGE
# ============================================================

if __name__ == "__main__":
    main()