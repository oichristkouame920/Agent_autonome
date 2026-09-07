import json

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from windows_tools import (
    is_application_running,
    open_application,
)

from web_tools import (
    open_website,
    open_websites,
)


# ============================================================
# CHEMINS
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]

ROUTINES_FILE = (
    ROOT_DIR
    / "config"
    / "routines.json"
)


# ============================================================
# ACTIONS AUTORISEES
# ============================================================

ALLOWED_ROUTINE_ACTIONS = {
    "open_application",
    "check_application",
    "open_website",
}


# ============================================================
# CHARGEMENT
# ============================================================

def load_routines():
    """
    Charge config/routines.json.
    """

    if not ROUTINES_FILE.exists():

        return {}

    try:

        with open(
            ROUTINES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

            if not isinstance(
                data,
                dict
            ):
                return {}

            return data

    except (
        OSError,
        json.JSONDecodeError
    ):
        return {}


# ============================================================
# PROFIL ACTIF
# ============================================================

def get_active_profile():

    config = load_routines()

    profile_name = config.get(
        "active_profile"
    )

    if not profile_name:

        return (
            False,
            None,
            "Aucun profil actif."
        )

    profiles = config.get(
        "profiles",
        {}
    )

    profile = profiles.get(
        profile_name
    )

    if not isinstance(
        profile,
        dict
    ):

        return (
            False,
            None,
            (
                "Profil inconnu : "
                f"{profile_name}"
            )
        )

    result = {
        "id": profile_name
    }

    result.update(
        profile
    )

    return (
        True,
        result,
        None
    )


# ============================================================
# RECUPERATION ROUTINE
# ============================================================

def get_routine(
    routine_name
):

    if not isinstance(
        routine_name,
        str
    ):

        return (
            False,
            None,
            "Nom de routine invalide."
        )

    routine_name = (
        routine_name
        .lower()
        .strip()
    )

    config = load_routines()

    routine = (
        config
        .get(
            "routines",
            {}
        )
        .get(
            routine_name
        )
    )

    if not isinstance(
        routine,
        dict
    ):

        return (
            False,
            None,
            (
                "Routine inconnue : "
                f"{routine_name}"
            )
        )

    if not routine.get(
        "enabled",
        False
    ):

        return (
            False,
            None,
            (
                "Routine désactivée : "
                f"{routine_name}"
            )
        )

    if not routine.get(
        "confirmed",
        False
    ):

        return (
            False,
            None,
            (
                "Routine non confirmée : "
                f"{routine_name}"
            )
        )

    return (
        True,
        routine,
        None
    )


# ============================================================
# VALIDATION ACTION
# ============================================================

def validate_routine_action(
    action_data
):

    if not isinstance(
        action_data,
        dict
    ):

        return (
            False,
            "Action de routine invalide."
        )

    action = action_data.get(
        "action"
    )

    target = action_data.get(
        "target"
    )

    if not isinstance(
        action,
        str
    ):

        return (
            False,
            "Action manquante."
        )

    if not isinstance(
        target,
        str
    ):

        return (
            False,
            "Cible manquante."
        )

    action = (
        action
        .lower()
        .strip()
    )

    target = (
        target
        .lower()
        .strip()
    )

    if not action:

        return (
            False,
            "Action manquante."
        )

    if not target:

        return (
            False,
            "Cible manquante."
        )

    if action not in ALLOWED_ROUTINE_ACTIONS:

        return (
            False,
            (
                "Action interdite dans "
                f"une routine : {action}"
            )
        )

    return (
        True,
        None
    )


# ============================================================
# EXECUTION ACTION
# ============================================================

def execute_routine_action(
    action_data
):

    valid, error = (
        validate_routine_action(
            action_data
        )
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

    # --------------------------------------------------------
    # APPLICATION
    # --------------------------------------------------------

    if action == "open_application":

        return open_application(
            target
        )

    # --------------------------------------------------------
    # VERIFICATION
    # --------------------------------------------------------

    if action == "check_application":

        running, message = (
            is_application_running(
                target
            )
        )

        # La vérification elle-même
        # a bien été exécutée.
        return (
            True,
            message
        )

    # --------------------------------------------------------
    # SITE UNIQUE
    # --------------------------------------------------------

    if action == "open_website":

        return open_website(
            target
        )

    return (
        False,
        (
            "Action interdite : "
            f"{action}"
        )
    )


# ============================================================
# EXECUTION RAPIDE D'UNE ROUTINE
# ============================================================

def execute_routine(
    routine_name
):
    """
    Optimisation :

    VS Code
        \
         -> lancés simultanément
        /
    Edge + tous les sites

    Les sites eux-mêmes sont envoyés
    en une seule commande à Edge.
    """

    valid, routine, error = (
        get_routine(
            routine_name
        )
    )

    if not valid:

        return (
            False,
            [error]
        )

    actions = routine.get(
        "actions",
        []
    )

    if not isinstance(
        actions,
        list
    ):

        return (
            False,
            [
                "Liste d'actions invalide."
            ]
        )

    if not actions:

        return (
            False,
            [
                (
                    "La routine ne contient "
                    "aucune action."
                )
            ]
        )

    # ========================================================
    # CLASSIFICATION
    # ========================================================

    application_actions = []

    website_targets = []

    other_actions = []

    initial_results = []

    for action_data in actions:

        valid_action, validation_error = (
            validate_routine_action(
                action_data
            )
        )

        if not valid_action:

            initial_results.append(
                (
                    "REFUSE : "
                    f"{validation_error}"
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

        if action == "open_website":

            website_targets.append(
                target
            )

        elif action == "open_application":

            application_actions.append(
                {
                    "action": action,
                    "target": target,
                }
            )

        else:

            other_actions.append(
                {
                    "action": action,
                    "target": target,
                }
            )

    # ========================================================
    # RESULTATS
    # ========================================================

    results = list(
        initial_results
    )

    success_count = 0

    # ========================================================
    # FONCTIONS DE LANCEMENT
    # ========================================================

    def launch_application(
        action_data
    ):

        return execute_routine_action(
            action_data
        )

    def launch_sites():

        return open_websites(
            website_targets
        )

    # ========================================================
    # EXECUTION PARALLELE
    # ========================================================

    total_parallel_jobs = (
        len(application_actions)
        +
        (
            1
            if website_targets
            else 0
        )
    )

    if total_parallel_jobs > 0:

        max_workers = min(
            total_parallel_jobs,
            4
        )

        with ThreadPoolExecutor(
            max_workers=max_workers
        ) as executor:

            futures = []

            # ------------------------------------------------
            # APPLICATIONS
            # ------------------------------------------------

            for action_data in application_actions:

                future = executor.submit(
                    launch_application,
                    action_data
                )

                futures.append(
                    (
                        "application",
                        future
                    )
                )

            # ------------------------------------------------
            # EDGE + SITES
            # ------------------------------------------------

            if website_targets:

                future = executor.submit(
                    launch_sites
                )

                futures.append(
                    (
                        "web",
                        future
                    )
                )

            # ------------------------------------------------
            # RESULTATS
            # ------------------------------------------------

            for kind, future in futures:

                try:

                    result = (
                        future.result()
                    )

                except Exception as error:

                    results.append(
                        (
                            "ERREUR : "
                            f"{error}"
                        )
                    )

                    continue

                # --------------------------------------------
                # APPLICATION
                # --------------------------------------------

                if kind == "application":

                    success, message = (
                        result
                    )

                    if success:

                        success_count += 1

                        results.append(
                            (
                                "OK : "
                                f"{message}"
                            )
                        )

                    else:

                        results.append(
                            (
                                "REFUSE : "
                                f"{message}"
                            )
                        )

                # --------------------------------------------
                # WEB
                # --------------------------------------------

                elif kind == "web":

                    web_success, web_messages = (
                        result
                    )

                    if web_success:

                        success_count += 1

                    results.extend(
                        web_messages
                    )

    # ========================================================
    # AUTRES ACTIONS
    # ========================================================

    for action_data in other_actions:

        success, message = (
            execute_routine_action(
                action_data
            )
        )

        if success:

            success_count += 1

            results.append(
                (
                    "OK : "
                    f"{message}"
                )
            )

        else:

            results.append(
                (
                    "REFUSE : "
                    f"{message}"
                )
            )

    return (
        success_count > 0,
        results
    )


# ============================================================
# ROUTINE DE DEMARRAGE
# ============================================================

def execute_profile_startup():
    """
    Sera utilisée plus tard lorsque
    nous activerons le démarrage Windows.
    """

    valid, profile, error = (
        get_active_profile()
    )

    if not valid:

        return (
            False,
            [error]
        )

    if not profile.get(
        "startup_enabled",
        False
    ):

        return (
            False,
            [
                (
                    "Le démarrage automatique "
                    "est désactivé pour ce profil."
                )
            ]
        )

    routine_name = profile.get(
        "startup_routine"
    )

    if not routine_name:

        return (
            False,
            [
                (
                    "Aucune routine de démarrage "
                    "n'est configurée."
                )
            ]
        )

    return execute_routine(
        routine_name
    )


# ============================================================
# TEST MANUEL
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("TEST ROUTINE RAPIDE")
    print("=" * 60)
    print()

    success, results = (
        execute_routine(
            "work_start"
        )
    )

    for result in results:

        print(
            result
        )

    print()

    print(
        "Résultat global :",
        success
    )