import json
import re
import sys

from pathlib import Path


# ============================================================
# CHEMINS
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT_DIR)
    )


# ============================================================
# WINDOWS
# ============================================================

from windows_tools import (
    is_application_running,
    open_application,
)


# ============================================================
# FICHIERS
# ============================================================

from file_tools import (
    create_folder,
    list_directory,
    move_file_within_root,
)


# ============================================================
# WEB
# ============================================================

from web_tools import (
    open_website,
)


# ============================================================
# ROUTINES
# ============================================================

from routine_tools import (
    execute_routine,
)


# ============================================================
# HABITUDES / BROUILLONS
# ============================================================

from habit_tools import (
    add_habit_draft_action,
    create_habit_draft,
    delete_habit_draft,
    format_habit_draft,
    get_habit_draft,
    get_pending_habits,
    record_session,
    remove_habit_draft_action,
    set_habit_draft_trigger,
    update_habit_draft_name,
)


# ============================================================
# DECISIONS SUR LES HABITUDES
# ============================================================

from habit_decision_tools import (
    accept_habit,
    confirm_habit_draft,
    reject_habit,
)


# ============================================================
# BACKENDS
# ============================================================

from backends.backend_manager import (
    get_backend_status,
    interpret as interpret_backend,
    load_agent_config,
)


# ============================================================
# CONFIGURATION
# ============================================================

SCHEMA_VERSION = 1

DEBUG = True


# ============================================================
# ACTIONS AUTORISEES
# ============================================================

SUPPORTED_ACTIONS = {
    # Applications
    "open_application",
    "check_application",

    # Web
    "open_website",

    # Fichiers
    "list_directory",
    "create_folder",
    "move_file_within_root",

    # Routines
    "run_routine",

    # Habitudes
    "list_habits",
    "modify_habit",
    "show_habit_draft",

    # Modification des brouillons
    "rename_habit_draft",
    "add_habit_draft_action",
    "remove_habit_draft_action",
    "set_habit_draft_trigger",
    "cancel_habit_draft",
    "confirm_habit_draft",

    # Décisions
    "accept_habit",
    "reject_habit",
}


# ============================================================
# ACTIONS QUI PEUVENT ETRE APPRISES
# ============================================================

LEARNABLE_AGENT_ACTIONS = {
    "open_application",
    "open_website",
}


# ============================================================
# CONFIGURATION GENERALE
# ============================================================

def get_agent_config():

    config = load_agent_config()

    if not isinstance(
        config,
        dict
    ):
        return {}

    return config


# ============================================================
# APPRENTISSAGE ACTIVE ?
# ============================================================

def is_learning_enabled():

    config = get_agent_config()

    learning = config.get(
        "learning",
        {}
    )

    if not isinstance(
        learning,
        dict
    ):
        return False

    return bool(
        learning.get(
            "enabled",
            False
        )
    )


# ============================================================
# VALIDATION D'UNE ACTION
# ============================================================

def validate_action(
    action_data
):

    # --------------------------------------------------------
    # FORMAT
    # --------------------------------------------------------

    if not isinstance(
        action_data,
        dict
    ):

        return (
            False,
            "Format d'action invalide."
        )

    # --------------------------------------------------------
    # VERSION
    # --------------------------------------------------------

    schema_version = action_data.get(
        "schema_version"
    )

    if schema_version != SCHEMA_VERSION:

        return (
            False,
            (
                "Version du contrat "
                f"non supportée : {schema_version}"
            )
        )

    # --------------------------------------------------------
    # ACTION
    # --------------------------------------------------------

    action = action_data.get(
        "action"
    )

    if not isinstance(
        action,
        str
    ):

        return (
            False,
            "Action manquante."
        )

    action = (
        action
        .lower()
        .strip()
    )

    if not action:

        return (
            False,
            "Action vide."
        )

    if action not in SUPPORTED_ACTIONS:

        return (
            False,
            (
                "Action inconnue ou interdite : "
                f"{action}"
            )
        )

    # --------------------------------------------------------
    # CIBLE
    # --------------------------------------------------------

    target = action_data.get(
        "target"
    )

    if not isinstance(
        target,
        str
    ):

        return (
            False,
            "Cible manquante."
        )

    target = (
        target
        .lower()
        .strip()
    )

    if not target:

        return (
            False,
            "Cible vide."
        )

    # ========================================================
    # IDENTIFIANTS D'HABITUDES
    # ========================================================

    habit_actions = {
        "modify_habit",
        "show_habit_draft",
        "rename_habit_draft",
        "add_habit_draft_action",
        "remove_habit_draft_action",
        "set_habit_draft_trigger",
        "cancel_habit_draft",
        "confirm_habit_draft",
        "accept_habit",
        "reject_habit",
    }

    if action in habit_actions:

        if not target.isdigit():

            return (
                False,
                (
                    "Identifiant d'habitude "
                    "invalide."
                )
            )

    # ========================================================
    # LISTE DES HABITUDES
    # ========================================================

    if action == "list_habits":

        if target != "pending":

            return (
                False,
                (
                    "Type de liste "
                    "d'habitudes invalide."
                )
            )

    # ========================================================
    # ROUTINE
    # ========================================================

    if action == "run_routine":

        if not re.fullmatch(
            r"[a-z0-9_-]+",
            target
        ):

            return (
                False,
                "Identifiant de routine invalide."
            )

    # ========================================================
    # APPLICATION / SITE
    # ========================================================

    if action in {
        "open_application",
        "check_application",
        "open_website",
    }:

        if not re.fullmatch(
            r"[a-z0-9_.-]+",
            target
        ):

            return (
                False,
                "Cible technique invalide."
            )

    # ========================================================
    # RACINES FICHIERS
    # ========================================================

    if action in {
        "list_directory",
        "create_folder",
        "move_file_within_root",
    }:

        if target not in {
            "desktop",
            "documents",
            "downloads",
        }:

            return (
                False,
                (
                    "Racine de fichiers "
                    "interdite ou inconnue."
                )
            )

    # ========================================================
    # PARAMETRES
    # ========================================================

    params = action_data.get(
        "params",
        {}
    )

    if params is None:
        params = {}

    if not isinstance(
        params,
        dict
    ):

        return (
            False,
            "Paramètres invalides."
        )

    # --------------------------------------------------------
    # CREATION D'UN DOSSIER
    # --------------------------------------------------------

    if action == "create_folder":

        name = params.get(
            "name"
        )

        if not isinstance(
            name,
            str
        ):

            return (
                False,
                "Nom de dossier invalide."
            )

        name = name.strip()

        if not name:

            return (
                False,
                "Le nom du dossier est vide."
            )

        if len(name) > 120:

            return (
                False,
                "Le nom du dossier est trop long."
            )

    # --------------------------------------------------------
    # DEPLACEMENT D'UN FICHIER
    # --------------------------------------------------------

    if action == "move_file_within_root":

        file_name = params.get(
            "file_name"
        )

        destination_folder = params.get(
            "destination_folder"
        )

        if not isinstance(
            file_name,
            str
        ):

            return (
                False,
                "Nom de fichier invalide."
            )

        if not isinstance(
            destination_folder,
            str
        ):

            return (
                False,
                "Dossier destination invalide."
            )

        file_name = file_name.strip()

        destination_folder = (
            destination_folder
            .strip()
        )

        if not file_name:

            return (
                False,
                "Le nom du fichier est vide."
            )

        if not destination_folder:

            return (
                False,
                (
                    "Le nom du dossier "
                    "destination est vide."
                )
            )

        if len(file_name) > 180:

            return (
                False,
                "Le nom du fichier est trop long."
            )

        if len(destination_folder) > 180:

            return (
                False,
                (
                    "Le nom du dossier destination "
                    "est trop long."
                )
            )

    # --------------------------------------------------------
    # RENOMMAGE HABITUDE
    # --------------------------------------------------------

    if action == "rename_habit_draft":

        name = params.get(
            "name"
        )

        if not isinstance(
            name,
            str
        ):

            return (
                False,
                "Nouveau nom invalide."
            )

        name = name.strip()

        if not name:

            return (
                False,
                "Le nouveau nom est vide."
            )

        if len(name) > 120:

            return (
                False,
                "Le nouveau nom est trop long."
            )

    # --------------------------------------------------------
    # DECLENCHEUR HABITUDE
    # --------------------------------------------------------

    if action == "set_habit_draft_trigger":

        trigger = params.get(
            "trigger"
        )

        if not isinstance(
            trigger,
            str
        ):

            return (
                False,
                "Déclencheur invalide."
            )

        trigger = trigger.strip()

        if not trigger:

            return (
                False,
                "Le déclencheur est vide."
            )

        if len(trigger) > 120:

            return (
                False,
                "Le déclencheur est trop long."
            )

    # --------------------------------------------------------
    # AJOUT / RETRAIT ACTION HABITUDE
    # --------------------------------------------------------

    if action in {
        "add_habit_draft_action",
        "remove_habit_draft_action",
    }:

        child_action = params.get(
            "action"
        )

        child_target = params.get(
            "target"
        )

        if child_action not in LEARNABLE_AGENT_ACTIONS:

            return (
                False,
                (
                    "Action interdite "
                    "dans un brouillon."
                )
            )

        if not isinstance(
            child_target,
            str
        ):

            return (
                False,
                (
                    "Cible du brouillon "
                    "invalide."
                )
            )

        child_target = (
            child_target
            .lower()
            .strip()
        )

        if not re.fullmatch(
            r"[a-z0-9_.-]+",
            child_target
        ):

            return (
                False,
                (
                    "Cible du brouillon "
                    "invalide."
                )
            )

    return (
        True,
        None
    )


# ============================================================
# FORMAT DES HABITUDES EN ATTENTE
# ============================================================

def format_pending_habits():

    habits = get_pending_habits()

    if not habits:

        return (
            "Aucune habitude "
            "n'est actuellement en attente."
        )

    lines = [
        "=" * 55,
        "HABITUDES EN ATTENTE",
        "=" * 55,
    ]

    for habit in habits:

        habit_id = habit.get(
            "id"
        )

        lines.append("")
        lines.append(
            f"ID : {habit_id}"
        )

        lines.append(
            (
                "Nom : "
                f"{habit.get('title')}"
            )
        )

        lines.append(
            (
                "Profil : "
                f"{habit.get('profile')}"
            )
        )

        lines.append(
            (
                "Jours observés : "
                f"{habit.get('distinct_days')}"
            )
        )

        lines.append(
            (
                "Occurrences : "
                f"{habit.get('occurrences')}"
            )
        )

        lines.append(
            (
                "Heure typique : "
                f"{habit.get('typical_time')}"
            )
        )

        lines.append("")
        lines.append(
            "Actions :"
        )

        actions = habit.get(
            "actions",
            []
        )

        for index, action_data in enumerate(
            actions,
            start=1
        ):

            lines.append(
                (
                    f"  {index}. "
                    f"{action_data.get('action')} "
                    f"-> "
                    f"{action_data.get('target')}"
                )
            )

        lines.append("")

        lines.append(
            (
                "Modifier : "
                f"modifie l'habitude {habit_id}"
            )
        )

        lines.append(
            (
                "Accepter : "
                f"accepte l'habitude {habit_id}"
            )
        )

        lines.append(
            (
                "Refuser : "
                f"refuse l'habitude {habit_id}"
            )
        )

        lines.append(
            "-" * 55
        )

    return "\n".join(
        lines
    )


# ============================================================
# CREATION / OUVERTURE D'UN BROUILLON
# ============================================================

def open_habit_draft(
    proposal_id
):

    success, draft, message = (
        create_habit_draft(
            proposal_id
        )
    )

    if not success:

        return (
            False,
            message
        )

    if not isinstance(
        draft,
        dict
    ):

        return (
            False,
            (
                "Le brouillon n'a pas pu "
                "être chargé."
            )
        )

    return (
        True,
        (
            f"{message}\n\n"
            f"{format_habit_draft(draft)}\n\n"
            "Aucune modification n'a encore "
            "été appliquée à routines.json."
        )
    )


# ============================================================
# AFFICHAGE D'UN BROUILLON
# ============================================================

def show_habit_draft(
    proposal_id
):

    draft = get_habit_draft(
        proposal_id
    )

    if draft is None:

        return (
            False,
            (
                "Aucun brouillon pour "
                "cette habitude."
            )
        )

    return (
        True,
        format_habit_draft(
            draft
        )
    )


# ============================================================
# RESULTAT APRES MODIFICATION
# ============================================================

def format_draft_change_result(
    proposal_id,
    success,
    message
):

    if not success:

        return (
            False,
            message
        )

    draft = get_habit_draft(
        proposal_id
    )

    if draft is None:

        return (
            True,
            message
        )

    return (
        True,
        (
            f"{message}\n\n"
            f"{format_habit_draft(draft)}"
        )
    )


# ============================================================
# EXECUTION D'UNE ACTION
# ============================================================

def execute_action(
    action_data
):

    valid, error = validate_action(
        action_data
    )

    if not valid:

        return (
            False,
            error
        )

    action = (
        action_data[
            "action"
        ]
        .lower()
        .strip()
    )

    target = (
        action_data[
            "target"
        ]
        .lower()
        .strip()
    )

    params = action_data.get(
        "params",
        {}
    )

    # ========================================================
    # APPLICATION
    # ========================================================

    if action == "open_application":

        return open_application(
            target
        )

    # ========================================================
    # VERIFICATION APPLICATION
    # ========================================================

    if action == "check_application":

        running, message = (
            is_application_running(
                target
            )
        )

        return (
            True,
            message
        )

    # ========================================================
    # LISTER UN DOSSIER AUTORISE
    # ========================================================

    if action == "list_directory":

        return list_directory(
            target
        )

    # ========================================================
    # CREER UN DOSSIER AUTORISE
    # ========================================================

    if action == "create_folder":

        return create_folder(
            target,
            params["name"],
            explicit_user_command=True
        )

    # ========================================================
    # DEPLACER UN FICHIER
    # ========================================================

    if action == "move_file_within_root":

        return move_file_within_root(
            target,
            params["file_name"],
            params["destination_folder"],
            explicit_user_command=True
        )

    # ========================================================
    # SITE
    # ========================================================

    if action == "open_website":

        return open_website(
            target
        )

    # ========================================================
    # ROUTINE
    # ========================================================

    if action == "run_routine":

        success, results = (
            execute_routine(
                target
            )
        )

        if not results:

            return (
                success,
                (
                    "La routine n'a retourné "
                    "aucun résultat."
                )
            )

        return (
            success,
            "\n".join(
                results
            )
        )

    # ========================================================
    # LISTE DES HABITUDES
    # ========================================================

    if action == "list_habits":

        return (
            True,
            format_pending_habits()
        )

    # ========================================================
    # MODIFIER UNE HABITUDE
    # ========================================================

    if action == "modify_habit":

        return open_habit_draft(
            int(target)
        )

    # ========================================================
    # AFFICHER LE BROUILLON
    # ========================================================

    if action == "show_habit_draft":

        return show_habit_draft(
            int(target)
        )

    # ========================================================
    # RENOMMER LE BROUILLON
    # ========================================================

    if action == "rename_habit_draft":

        success, message = (
            update_habit_draft_name(
                int(target),
                params["name"]
            )
        )

        return format_draft_change_result(
            int(target),
            success,
            message
        )

    # ========================================================
    # AJOUTER UNE ACTION
    # ========================================================

    if action == "add_habit_draft_action":

        success, message = (
            add_habit_draft_action(
                int(target),
                params["action"],
                params["target"]
            )
        )

        return format_draft_change_result(
            int(target),
            success,
            message
        )

    # ========================================================
    # RETIRER UNE ACTION
    # ========================================================

    if action == "remove_habit_draft_action":

        success, message = (
            remove_habit_draft_action(
                int(target),
                params["action"],
                params["target"]
            )
        )

        return format_draft_change_result(
            int(target),
            success,
            message
        )

    # ========================================================
    # CHANGER LE DECLENCHEUR
    # ========================================================

    if action == "set_habit_draft_trigger":

        success, message = (
            set_habit_draft_trigger(
                int(target),
                params["trigger"]
            )
        )

        return format_draft_change_result(
            int(target),
            success,
            message
        )

    # ========================================================
    # ANNULER LA MODIFICATION
    # ========================================================

    if action == "cancel_habit_draft":

        return delete_habit_draft(
            int(target)
        )

    # ========================================================
    # CONFIRMER LE BROUILLON
    # ========================================================

    if action == "confirm_habit_draft":

        return confirm_habit_draft(
            int(target)
        )

    # ========================================================
    # ACCEPTER UNE HABITUDE
    # ========================================================

    if action == "accept_habit":

        if get_habit_draft(
            int(target)
        ) is not None:

            return (
                False,
                (
                    "Cette habitude possède "
                    "un brouillon de modification.\n"
                    "L'acceptation directe est bloquée "
                    "pour éviter de perdre "
                    "les modifications du brouillon."
                )
            )

        return accept_habit(
            int(target)
        )

    # ========================================================
    # REFUSER UNE HABITUDE
    # ========================================================

    if action == "reject_habit":

        return reject_habit(
            int(target)
        )

    # ========================================================
    # SECURITE
    # ========================================================

    return (
        False,
        (
            "Action autorisée mais "
            "aucun exécuteur n'est défini : "
            f"{action}"
        )
    )


# ============================================================
# EXECUTION DE PLUSIEURS ACTIONS
# ============================================================

def execute_actions(
    actions
):

    display_results = []

    activity_results = []

    for action_data in actions:

        valid, error = validate_action(
            action_data
        )

        if not valid:

            display_results.append(
                (
                    "REFUSE : "
                    f"{error}"
                )
            )

            continue

        action = (
            action_data[
                "action"
            ]
            .lower()
            .strip()
        )

        target = (
            action_data[
                "target"
            ]
            .lower()
            .strip()
        )

        success, message = execute_action(
            action_data
        )

        # ----------------------------------------------------
        # AFFICHAGE
        # ----------------------------------------------------

        if success:

            display_results.append(
                message
            )

        else:

            display_results.append(
                (
                    "REFUSE : "
                    f"{message}"
                )
            )

        # ----------------------------------------------------
        # APPRENTISSAGE
        # ----------------------------------------------------

        if action in LEARNABLE_AGENT_ACTIONS:

            activity_results.append({
                "action": action,
                "target": target,
                "success": bool(
                    success
                ),
            })

    return (
        display_results,
        activity_results
    )


# ============================================================
# APPRENTISSAGE
# ============================================================

def learn_from_actions(
    activity_results
):

    if not is_learning_enabled():
        return []

    if not activity_results:
        return []

    try:

        previous_pending = (
            get_pending_habits()
        )

        previous_ids = {
            habit["id"]
            for habit in previous_pending
        }

        recorded, result = record_session(
            activity_results,
            source="manual"
        )

        if DEBUG:

            if recorded:

                print(
                    "[APPRENTISSAGE] "
                    "Session manuelle enregistrée."
                )

            else:

                print(
                    "[APPRENTISSAGE] "
                    f"{result}"
                )

        if not recorded:

            return []

        current_pending = (
            get_pending_habits()
        )

        return [
            habit
            for habit in current_pending
            if habit["id"] not in previous_ids
        ]

    except Exception as error:

        if DEBUG:

            print(
                "[APPRENTISSAGE] "
                "Erreur non bloquante : "
                f"{error}"
            )

        return []


# ============================================================
# NOTIFICATION HABITUDE
# ============================================================

def format_habit_notification(
    habit
):

    habit_id = habit.get(
        "id"
    )

    return (
        "\n"
        "=======================================================\n"
        "HABITUDE DETECTEE\n"
        "=======================================================\n"
        f"ID : {habit_id}\n"
        f"Nom : {habit.get('title')}\n"
        f"Occurrences : {habit.get('occurrences')}\n"
        f"Jours : {habit.get('distinct_days')}\n"
        f"Heure typique : {habit.get('typical_time')}\n\n"
        f"Modifier : modifie l'habitude {habit_id}\n"
        f"Accepter : accepte l'habitude {habit_id}\n"
        f"Refuser : refuse l'habitude {habit_id}"
    )


# ============================================================
# INTERPRETATION
# ============================================================

def interpret_instruction(
    user_message
):

    result = interpret_backend(
        user_message
    )

    if DEBUG:

        print()

        print(
            "----- INTERPRETATION BACKEND -----"
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2
            )
        )

        print(
            "----------------------------------"
        )

        print()

    return result


# ============================================================
# TRAITEMENT
# ============================================================

def process_instruction(
    user_message
):

    result = interpret_instruction(
        user_message
    )

    if not isinstance(
        result,
        dict
    ):

        return (
            "ERREUR : format backend invalide."
        )

    actions = result.get(
        "actions",
        []
    )

    if not isinstance(
        actions,
        list
    ):

        actions = []

    if not actions:

        reply = result.get(
            "reply"
        )

        if (
            isinstance(
                reply,
                str
            )
            and reply.strip()
        ):

            return reply.strip()

        error = result.get(
            "error"
        )

        if error:

            return (
                "ERREUR D'INTERPRETATION : "
                f"{error}"
            )

        return (
            "Je suis actuellement en mode "
            "déterministe et je n'ai pas "
            "reconnu cette instruction."
        )

    display_results, activity_results = (
        execute_actions(
            actions
        )
    )

    new_habits = learn_from_actions(
        activity_results
    )

    for habit in new_habits:

        display_results.append(
            format_habit_notification(
                habit
            )
        )

    return "\n\n".join(
        display_results
    )


# ============================================================
# INTERFACE
# ============================================================

def main():

    status = get_backend_status()

    print()

    print(
        "=" * 65
    )

    print(
        "AgentLocal"
    )

    print(
        "Multi-backend + routines + apprentissage"
    )

    print(
        "=" * 65
    )

    print()

    print(
        "Backend actif :",
        status.get(
            "selected",
            "aucun"
        )
    )

    print(
        "Apprentissage :",
        (
            "activé"
            if is_learning_enabled()
            else "désactivé"
        )
    )

    print()

    print(
        "Commandes de test :"
    )

    print(
        "  ouvre github"
    )

    print(
        "  ouvre l'explorateur"
    )

    print(
        "  liste mes documents"
    )

    print(
        "  crée un dossier Factures dans Documents"
    )

    print(
        "  déplace facture.pdf dans Factures"
    )

    print(
        "  prépare mon environnement de travail"
    )

    print(
        "  affiche mes habitudes"
    )

    print()

    print(
        "Tape 'quit' pour arrêter."
    )

    print()

    # ========================================================
    # BOUCLE PRINCIPALE
    # ========================================================

    while True:

        try:

            user_message = input(
                "A vous de commencer > "
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

        if not user_message:
            continue

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

        print()

        print(
            "Analyse..."
        )

        print()

        result = process_instruction(
            user_message
        )

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