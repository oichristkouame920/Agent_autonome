import copy
import json
import os
import re
import tempfile
import unicodedata

from pathlib import Path

from habit_tools import (
    get_habit_draft,
    get_pending_habits,
    set_habit_status,
)


# ============================================================
# VERSION
# ============================================================

SCHEMA_VERSION = 1


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
# ACTIONS AUTORISEES DEPUIS UNE HABITUDE
# ============================================================

LEARNED_ROUTINE_ACTIONS = {
    "open_application",
    "open_website",
}


# ============================================================
# NORMALISATION TEXTE
# ============================================================

def remove_accents(
    text
):

    normalized = unicodedata.normalize(
        "NFKD",
        text
    )

    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(
            character
        )
    )


def normalize_trigger_text(
    value
):

    if not isinstance(
        value,
        str
    ):

        return ""

    value = (
        value
        .lower()
        .strip()
    )

    value = remove_accents(
        value
    )

    value = value.replace(
        "’",
        "'"
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# ============================================================
# CHARGEMENT ROUTINES.JSON
# ============================================================

def load_routines_config():

    if not ROUTINES_FILE.exists():

        return (
            False,
            None,
            "routines.json est introuvable."
        )

    try:

        with open(
            ROUTINES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

    except json.JSONDecodeError as error:

        return (
            False,
            None,
            (
                "routines.json contient "
                f"un JSON invalide : {error}"
            )
        )

    except OSError as error:

        return (
            False,
            None,
            (
                "Impossible de lire "
                f"routines.json : {error}"
            )
        )

    if not isinstance(
        data,
        dict
    ):

        return (
            False,
            None,
            "Le format de routines.json est invalide."
        )

    version = data.get(
        "schema_version",
        SCHEMA_VERSION
    )

    if version != SCHEMA_VERSION:

        return (
            False,
            None,
            (
                "Version de routines.json "
                f"non supportée : {version}"
            )
        )

    data.setdefault(
        "schema_version",
        SCHEMA_VERSION
    )

    data.setdefault(
        "profiles",
        {}
    )

    data.setdefault(
        "routines",
        {}
    )

    if not isinstance(
        data["routines"],
        dict
    ):

        return (
            False,
            None,
            "La section routines est invalide."
        )

    return (
        True,
        data,
        None
    )


# ============================================================
# SAUVEGARDE ATOMIQUE
# ============================================================

def save_routines_config(
    data
):

    ROUTINES_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_path = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=ROUTINES_FILE.parent,
            prefix="routines_",
            suffix=".tmp",
            delete=False
        ) as temp_file:

            json.dump(
                data,
                temp_file,
                ensure_ascii=False,
                indent=2
            )

            temp_file.write(
                "\n"
            )

            temp_file.flush()

            os.fsync(
                temp_file.fileno()
            )

            temp_path = Path(
                temp_file.name
            )

        os.replace(
            temp_path,
            ROUTINES_FILE
        )

        return (
            True,
            None
        )

    except OSError as error:

        if (
            temp_path is not None
            and temp_path.exists()
        ):

            try:
                temp_path.unlink()

            except OSError:
                pass

        return (
            False,
            (
                "Impossible de sauvegarder "
                f"routines.json : {error}"
            )
        )


# ============================================================
# HABITUDE EN ATTENTE
# ============================================================

def get_pending_habit(
    proposal_id
):

    try:

        proposal_id = int(
            proposal_id
        )

    except (
        TypeError,
        ValueError
    ):

        return None

    habits = get_pending_habits()

    for habit in habits:

        if habit.get(
            "id"
        ) == proposal_id:

            return habit

    return None


# ============================================================
# IDENTIFIANT TECHNIQUE
# ============================================================

def slugify(
    value
):

    value = str(
        value
    ).lower().strip()

    value = remove_accents(
        value
    )

    value = re.sub(
        r"[^a-z0-9_-]+",
        "_",
        value
    )

    value = re.sub(
        r"_+",
        "_",
        value
    )

    return value.strip(
        "_"
    )


def build_routine_id(
    habit
):

    proposal_id = habit.get(
        "id"
    )

    profile = slugify(
        habit.get(
            "profile",
            "unknown"
        )
    )

    if not profile:

        profile = "unknown"

    return (
        f"habit_{proposal_id}_{profile}"
    )


# ============================================================
# VALIDATION ACTIONS
# ============================================================

def validate_actions(
    actions
):

    if not isinstance(
        actions,
        list
    ):

        return (
            False,
            None,
            "Liste d'actions invalide."
        )

    if not actions:

        return (
            False,
            None,
            "Aucune action dans la routine."
        )

    clean_actions = []

    seen = set()

    for action_data in actions:

        if not isinstance(
            action_data,
            dict
        ):

            return (
                False,
                None,
                "Une action est invalide."
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
                None,
                "Action manquante."
            )

        if not isinstance(
            target,
            str
        ):

            return (
                False,
                None,
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

        if action not in LEARNED_ROUTINE_ACTIONS:

            return (
                False,
                None,
                (
                    "Action interdite dans "
                    f"une routine apprise : {action}"
                )
            )

        if not re.fullmatch(
            r"[a-z0-9_.-]+",
            target
        ):

            return (
                False,
                None,
                (
                    "Cible invalide : "
                    f"{target}"
                )
            )

        key = (
            action,
            target
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        clean_actions.append({
            "action": action,
            "target": target,
        })

    if not clean_actions:

        return (
            False,
            None,
            "Aucune action valide."
        )

    return (
        True,
        clean_actions,
        None
    )


def validate_habit_actions(
    habit
):

    return validate_actions(
        habit.get(
            "actions",
            []
        )
    )


# ============================================================
# VALIDATION DECLENCHEURS
# ============================================================

def validate_triggers(
    triggers
):

    if not isinstance(
        triggers,
        list
    ):

        return (
            False,
            None,
            "Liste de déclencheurs invalide."
        )

    clean_triggers = []

    seen = set()

    for trigger in triggers:

        if not isinstance(
            trigger,
            str
        ):

            continue

        trigger = trigger.strip()

        if not trigger:

            continue

        if len(trigger) > 120:

            return (
                False,
                None,
                (
                    "Un déclencheur dépasse "
                    "120 caractères."
                )
            )

        normalized = normalize_trigger_text(
            trigger
        )

        if not normalized:

            continue

        if normalized in seen:

            continue

        seen.add(
            normalized
        )

        clean_triggers.append(
            trigger
        )

    if not clean_triggers:

        return (
            False,
            None,
            (
                "La routine doit avoir au moins "
                "un déclencheur."
            )
        )

    return (
        True,
        clean_triggers,
        None
    )


# ============================================================
# COLLISION DE DECLENCHEURS
# ============================================================

def find_trigger_collision(
    config,
    triggers,
    ignored_routine_id=None
):

    wanted = {
        normalize_trigger_text(
            trigger
        )
        for trigger in triggers
    }

    routines = config.get(
        "routines",
        {}
    )

    for routine_id, routine in routines.items():

        if routine_id == ignored_routine_id:

            continue

        if not isinstance(
            routine,
            dict
        ):

            continue

        existing_triggers = routine.get(
            "triggers",
            []
        )

        if not isinstance(
            existing_triggers,
            list
        ):

            continue

        for trigger in existing_triggers:

            normalized = normalize_trigger_text(
                trigger
            )

            if normalized in wanted:

                return (
                    routine_id,
                    trigger
                )

    return None


# ============================================================
# DECLENCHEURS PAR DEFAUT
# ============================================================

def build_default_triggers(
    habit
):

    proposal_id = habit.get(
        "id"
    )

    return [
        f"lance habitude {proposal_id}",
        f"routine habitude {proposal_id}",
        f"lance ma routine {proposal_id}",
    ]


# ============================================================
# ROUTINE DEPUIS HABITUDE ORIGINALE
# ============================================================

def build_routine_from_habit(
    habit,
    actions
):

    return {
        "name": habit.get(
            "title",
            "Routine apprise"
        ),

        "enabled": True,

        "confirmed": True,

        "triggers": build_default_triggers(
            habit
        ),

        "actions": actions,

        "metadata": {
            "source": "learned_habit",

            "habit_proposal_id": habit.get(
                "id"
            ),

            "profile": habit.get(
                "profile"
            ),

            "daypart": habit.get(
                "daypart"
            ),

            "typical_time": habit.get(
                "typical_time"
            ),

            "created_from_schema": SCHEMA_VERSION,
        },
    }


# ============================================================
# ROUTINE DEPUIS BROUILLON
# ============================================================

def build_routine_from_draft(
    habit,
    draft,
    actions,
    triggers
):

    return {
        "name": draft[
            "name"
        ],

        "enabled": True,

        "confirmed": True,

        "triggers": triggers,

        "actions": actions,

        "metadata": {
            "source": "learned_habit_modified",

            "habit_proposal_id": habit.get(
                "id"
            ),

            "profile": habit.get(
                "profile"
            ),

            "daypart": habit.get(
                "daypart"
            ),

            "typical_time": habit.get(
                "typical_time"
            ),

            "created_from_schema": SCHEMA_VERSION,
        },
    }


# ============================================================
# ACCEPTATION DIRECTE
# ============================================================

def accept_habit(
    proposal_id
):

    habit = get_pending_habit(
        proposal_id
    )

    if habit is None:

        return (
            False,
            (
                "Habitude inexistante ou "
                "déjà traitée."
            )
        )

    # --------------------------------------------------------
    # BROUILLON EXISTANT
    # --------------------------------------------------------

    if get_habit_draft(
        proposal_id
    ) is not None:

        return (
            False,
            (
                "Cette habitude possède "
                "un brouillon de modification.\n"
                "Utilisez la confirmation "
                "du brouillon."
            )
        )

    valid, actions, error = (
        validate_habit_actions(
            habit
        )
    )

    if not valid:

        return (
            False,
            error
        )

    success, config, error = (
        load_routines_config()
    )

    if not success:

        return (
            False,
            error
        )

    original_config = copy.deepcopy(
        config
    )

    routine_id = build_routine_id(
        habit
    )

    routines = config[
        "routines"
    ]

    if routine_id in routines:

        return (
            False,
            (
                "Une routine avec cet identifiant "
                f"existe déjà : {routine_id}"
            )
        )

    routine = build_routine_from_habit(
        habit,
        actions
    )

    collision = find_trigger_collision(
        config,
        routine["triggers"]
    )

    if collision is not None:

        conflict_id, conflict_trigger = collision

        return (
            False,
            (
                "Déclencheur déjà utilisé par "
                f"la routine {conflict_id} : "
                f"{conflict_trigger}"
            )
        )

    routines[
        routine_id
    ] = routine

    saved, save_error = (
        save_routines_config(
            config
        )
    )

    if not saved:

        return (
            False,
            save_error
        )

    status_success, status_message = (
        set_habit_status(
            habit["id"],
            "accepted"
        )
    )

    if not status_success:

        rollback_success, rollback_error = (
            save_routines_config(
                original_config
            )
        )

        if not rollback_success:

            return (
                False,
                (
                    "Erreur critique de cohérence. "
                    f"{status_message} "
                    "Rollback impossible : "
                    f"{rollback_error}"
                )
            )

        return (
            False,
            status_message
        )

    return (
        True,
        (
            "Habitude acceptée.\n"
            f"Routine créée : {routine_id}\n"
            f"Nom : {routine['name']}\n"
            f"Commande : {routine['triggers'][0]}"
        )
    )


# ============================================================
# CONFIRMATION D'UN BROUILLON
# ============================================================

def confirm_habit_draft(
    proposal_id
):
    """
    Transforme le brouillon en vraie routine.

    La routine n'est créée qu'après
    cette confirmation explicite.
    """

    habit = get_pending_habit(
        proposal_id
    )

    if habit is None:

        return (
            False,
            (
                "Habitude inexistante "
                "ou déjà traitée."
            )
        )

    draft = get_habit_draft(
        proposal_id
    )

    if draft is None:

        return (
            False,
            (
                "Aucun brouillon à confirmer "
                "pour cette habitude."
            )
        )

    # ========================================================
    # NOM
    # ========================================================

    name = draft.get(
        "name"
    )

    if not isinstance(
        name,
        str
    ):

        return (
            False,
            "Nom du brouillon invalide."
        )

    name = name.strip()

    if not name:

        return (
            False,
            "Le nom de la routine est vide."
        )

    if len(name) > 120:

        return (
            False,
            "Le nom de la routine est trop long."
        )

    # ========================================================
    # ACTIONS
    # ========================================================

    valid, actions, error = (
        validate_actions(
            draft.get(
                "actions",
                []
            )
        )
    )

    if not valid:

        return (
            False,
            error
        )

    # ========================================================
    # DECLENCHEURS
    # ========================================================

    valid, triggers, error = (
        validate_triggers(
            draft.get(
                "triggers",
                []
            )
        )
    )

    if not valid:

        return (
            False,
            error
        )

    # ========================================================
    # CONFIG
    # ========================================================

    success, config, error = (
        load_routines_config()
    )

    if not success:

        return (
            False,
            error
        )

    original_config = copy.deepcopy(
        config
    )

    routine_id = build_routine_id(
        habit
    )

    routines = config[
        "routines"
    ]

    # ========================================================
    # ID DEJA UTILISE
    # ========================================================

    if routine_id in routines:

        return (
            False,
            (
                "Une routine avec cet identifiant "
                f"existe déjà : {routine_id}"
            )
        )

    # ========================================================
    # COLLISION DECLENCHEUR
    # ========================================================

    collision = find_trigger_collision(
        config,
        triggers
    )

    if collision is not None:

        conflict_id, conflict_trigger = collision

        return (
            False,
            (
                "Impossible de confirmer : "
                "un déclencheur est déjà utilisé.\n"
                f"Routine : {conflict_id}\n"
                f"Déclencheur : {conflict_trigger}"
            )
        )

    # ========================================================
    # CREATION ROUTINE
    # ========================================================

    routine = build_routine_from_draft(
        habit,
        {
            **draft,
            "name": name,
        },
        actions,
        triggers
    )

    routines[
        routine_id
    ] = routine

    # ========================================================
    # SAUVEGARDE
    # ========================================================

    saved, save_error = (
        save_routines_config(
            config
        )
    )

    if not saved:

        return (
            False,
            save_error
        )

    # ========================================================
    # HABITUDE -> ACCEPTED
    #
    # set_habit_status supprimera également
    # le brouillon SQLite.
    # ========================================================

    status_success, status_message = (
        set_habit_status(
            habit["id"],
            "accepted"
        )
    )

    if not status_success:

        rollback_success, rollback_error = (
            save_routines_config(
                original_config
            )
        )

        if not rollback_success:

            return (
                False,
                (
                    "Erreur critique de cohérence.\n"
                    f"{status_message}\n"
                    "Rollback de routines.json impossible : "
                    f"{rollback_error}"
                )
            )

        return (
            False,
            status_message
        )

    return (
        True,
        (
            "Modification confirmée.\n"
            f"Routine créée : {routine_id}\n"
            f"Nom : {name}\n"
            f"Commande : {triggers[0]}\n"
            f"Actions : {len(actions)}"
        )
    )


# ============================================================
# REFUS
# ============================================================

def reject_habit(
    proposal_id
):

    habit = get_pending_habit(
        proposal_id
    )

    if habit is None:

        return (
            False,
            (
                "Habitude inexistante ou "
                "déjà traitée."
            )
        )

    success, message = (
        set_habit_status(
            habit["id"],
            "rejected"
        )
    )

    if not success:

        return (
            False,
            message
        )

    return (
        True,
        (
            "Habitude refusée.\n"
            "Elle ne sera pas transformée "
            "en routine."
        )
    )


# ============================================================
# TEST MANUEL
# ============================================================

def main():

    print()

    print(
        "=" * 60
    )

    print(
        "DECISIONS D'HABITUDES - AgentLocal"
    )

    print(
        "=" * 60
    )

    print()

    print(
        "Ce module gère :"
    )

    print(
        "  - acceptation directe"
    )

    print(
        "  - confirmation d'un brouillon"
    )

    print(
        "  - refus"
    )

    print()


if __name__ == "__main__":

    main()