import json
import re
import sys
import unicodedata
from pathlib import Path


# ============================================================
# CHEMINS
# ============================================================
# PREUVE EXPLICITE : LECTURE CONTENU
# ============================================================

def verify_explicit_read_file_content(
    user_message,
    target,
    params
):
    """
    La lecture n'est autorisée que si le texte brut de
    l'utilisateur correspond exactement au contrat backend.
    """

    text = prepare_command_text(
        user_message
    )

    patterns = [
        (
            r"^"
            r"(?:lis|lire)"
            r"\s+"
            r"(?:(?:le|la)\s+fichier\s+)?"
            r"(.+?)"
            r"\s+dans\s+"
            r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
            r"(" + SECURITY_ROOT_PATTERN + r")"
            r"\s*[.!?]?\s*$"
        ),
        (
            r"^"
            r"(?:affiche|afficher|montre|montrer)"
            r"\s+le\s+contenu\s+(?:de|du)\s+"
            r"(.+?)"
            r"\s+dans\s+"
            r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
            r"(" + SECURITY_ROOT_PATTERN + r")"
            r"\s*[.!?]?\s*$"
        ),
    ]

    match = None

    for pattern in patterns:

        match = re.fullmatch(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:
            break

    if not match:
        return False

    requested_file = (
        match
        .group(1)
        .strip()
    )

    requested_root = normalize_security_root(
        match.group(2)
    )

    backend_file = params.get(
        "file_name"
    )

    if not requested_root:
        return False

    if requested_root != target:
        return False

    return bool(
        same_security_value(
            requested_file,
            backend_file
        )
    )


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
    close_application,
    get_application_config,
    is_application_running,
    manage_application_window,
    open_application,
)


# ============================================================
# FICHIERS
# ============================================================

from file_tools import (
    copy_file_between_roots,
    create_file_with_content,
    create_folder,
    delete_file_to_recycle_bin,
    list_directory,
    move_file_between_roots,
    move_file_within_root,
    modify_file_content,
    read_file_content,
    rename_file,
    rename_file_auto,
)


# ============================================================
# WEB
# ============================================================

from web_tools import (
    close_website,
    open_website,
)


# ============================================================
# ROUTINES
# ============================================================

from routine_tools import (
    execute_routine,
)


# ============================================================
# HABITUDES
# ============================================================

from habit_tools import (
    add_habit_draft_action,
    create_habit_draft,
    delete_habit_draft,
    format_habit_draft,
    get_habit_draft,
    get_pending_habits,
    get_habits_by_status,
    get_learning_summary,
    record_session,
    remove_habit_draft_action,
    set_habit_draft_trigger,
    update_habit_draft_name,
)


# ============================================================
# DECISIONS HABITUDES
# ============================================================

from habit_decision_tools import (
    accept_habit,
    confirm_habit_draft,
    reject_habit,
)


# ============================================================
# BACKEND
# ============================================================

from backends.backend_manager import (
    get_backend_status,
    interpret as interpret_backend,
    load_agent_config,
)

from backends.deterministic_backend import (
    interpret as interpret_deterministic_for_proof,
)

try:
    from language_profile import resolve_expression as resolve_learned_expression, record_unrecognized
    from user_profile import preference as user_preference
except Exception:
    resolve_learned_expression = None
    record_unrecognized = None
    user_preference = None


# ============================================================
# VERSION
# ============================================================

SCHEMA_VERSION = 1

DEBUG = True


# ============================================================
# RACINES FICHIERS AUTORISEES
# ============================================================

ALLOWED_FILE_ROOTS = {
    "desktop",
    "documents",
    "downloads",
    "pictures",
    "videos",
    "music",
}


# ============================================================
# ACTIONS FICHIERS NECESSITANT UNE PREUVE EXPLICITE
# ============================================================

FILE_ACTIONS_REQUIRING_EXPLICIT_PROOF = {
    "list_directory",
    "create_folder",
    "create_file_with_content",
    "modify_file_content",
    "move_file_within_root",
    "move_file_between_roots",
    "copy_file_between_roots",
    "rename_file",
    "rename_file_auto",
    "delete_file",
    "read_file_content",
}


# ============================================================
# ACTIONS INTERACTIVES NECESSITANT UNE PREUVE EXPLICITE
# ============================================================

INTERACTIVE_ACTIONS_REQUIRING_EXPLICIT_PROOF = {
    "open_application",
    "close_application",
    "manage_window",
    "open_website",
    "close_website",
}


# ============================================================
# ALIAS DES RACINES
# ============================================================

FILE_ROOT_ALIASES = {
    # Bureau
    "bureau": "desktop",
    "desktop": "desktop",

    # Documents
    "document": "documents",
    "documents": "documents",

    # Téléchargements
    "telechargement": "downloads",
    "telechargements": "downloads",
    "telechargment": "downloads",
    "telechargments": "downloads",
    "telechagement": "downloads",
    "telechagements": "downloads",
    "telechargemnt": "downloads",
    "telechargemnts": "downloads",
    "download": "downloads",
    "downloads": "downloads",

    # Images
    "image": "pictures",
    "images": "pictures",
    "photo": "pictures",
    "photos": "pictures",
    "picture": "pictures",
    "pictures": "pictures",

    # Vidéos
    "video": "videos",
    "videos": "videos",

    # Musique
    "musique": "music",
    "musiques": "music",
    "music": "music",
}


SECURITY_ROOT_PATTERN = (
    r"bureau|desktop|"
    r"documents?|"
    r"téléchargements?|telechargements?|downloads?|"
    r"images?|photos?|pictures?|"
    r"vidéos?|videos?|"
    r"musiques?|music"
)


# ============================================================
# ACTIONS AUTORISEES
# ============================================================

SUPPORTED_ACTIONS = {
    # Applications
    "open_application",
    "close_application",
    "check_application",
    "manage_window",

    # Web
    "open_website",
    "close_website",

    # Fichiers
    "list_directory",
    "create_folder",
    "create_file_with_content",
    "modify_file_content",
    "move_file_within_root",
    "move_file_between_roots",
    "copy_file_between_roots",
    "rename_file",
    "rename_file_auto",
    "delete_file",
    "read_file_content",

    # Routines
    "run_routine",

    # Habitudes
    "list_habits",
    "modify_habit",
    "show_habit_draft",

    # Brouillons habitudes
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
# ACTIONS APPRENABLES
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

    if isinstance(
        config,
        dict
    ):
        return config

    return {}


# ============================================================
# APPRENTISSAGE ACTIVE ?
# ============================================================

def is_learning_enabled():

    # V12.4 : la préférence de l'hôte pilote l'apprentissage quand elle existe.
    # Elle ne change aucune permission d'action et reste stockée localement.
    try:
        from user_profile import load_preferences
        preferences = load_preferences()
        learning_pref = preferences.get("learning", {}) if isinstance(preferences, dict) else {}
        if isinstance(learning_pref, dict) and "enabled" in learning_pref:
            return bool(learning_pref.get("enabled"))
    except Exception:
        pass

    learning = (
        get_agent_config()
        .get(
            "learning",
            {}
        )
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
# NORMALISATION RACINE SECURITE
# ============================================================

def normalize_security_root(
    value
):

    if not isinstance(
        value,
        str
    ):
        return None

    value = (
        value
        .strip()
        .lower()
        .replace(
            "’",
            "'"
        )
    )

    # --------------------------------------------------------
    # Retire les accents uniquement pour les noms de racines.
    # --------------------------------------------------------

    value = unicodedata.normalize(
        "NFKD",
        value
    )

    value = "".join(
        character
        for character in value
        if not unicodedata.combining(
            character
        )
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    ).strip()

    # --------------------------------------------------------
    # Préfixes naturels
    # --------------------------------------------------------

    for prefix in (
        "mes ",
        "mon ",
        "ma ",
        "le ",
        "la ",
        "les ",
    ):

        if value.startswith(
            prefix
        ):

            value = (
                value[
                    len(prefix):
                ]
                .strip()
            )

            break

    return FILE_ROOT_ALIASES.get(
        value
    )


# ============================================================
# NORMALISATION DES NOMS DE FICHIERS
# ============================================================

def normalize_security_value(
    value
):
    """
    Normalisation stricte pour comparer
    un nom provenant de l'utilisateur avec
    le nom proposé par le backend.

    Les accents ne sont PAS retirés.

    Exemple :
        café.txt != cafe.txt
    """

    if not isinstance(
        value,
        str
    ):
        return ""

    value = unicodedata.normalize(
        "NFC",
        value
    )

    value = (
        value
        .replace(
            "’",
            "'"
        )
        .strip()
        .casefold()
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def same_security_value(
    first,
    second
):

    return (
        normalize_security_value(
            first
        )
        ==
        normalize_security_value(
            second
        )
    )


# ============================================================
# PREPARATION TEXTE COMMANDE
# ============================================================

def prepare_command_text(
    user_message
):

    if not isinstance(
        user_message,
        str
    ):
        return ""

    text = unicodedata.normalize(
        "NFC",
        user_message
    )

    text = (
        text
        .replace(
            "’",
            "'"
        )
        .strip()
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


# ============================================================
# PREUVE EXPLICITE : LISTER
# ============================================================

def verify_explicit_list_directory(
    user_message,
    target
):

    text = prepare_command_text(
        user_message
    )

    patterns = [
        r"^(?:liste|lister)(?:-moi|\s+moi)?\s+(.+)$",
        r"^(?:affiche|afficher)(?:-moi|\s+moi)?\s+(.+)$",
        r"^(?:montre|montrer)(?:-moi|\s+moi)?\s+(.+)$",
        r"^voir\s+(.+)$",
    ]

    for pattern in patterns:

        match = re.fullmatch(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if not match:
            continue

        raw_target = (
            match
            .group(1)
            .strip()
        )

        folded = (
            raw_target
            .casefold()
        )

        for prefix in (
            "le contenu de ",
            "le contenu du ",
            "le contenu des ",
        ):

            if folded.startswith(
                prefix
            ):

                raw_target = (
                    raw_target[
                        len(prefix):
                    ]
                    .strip()
                )

                break

        return (
            normalize_security_root(
                raw_target
            )
            ==
            target
        )

    return False


# ============================================================
# PREUVE EXPLICITE : CREER DOSSIER
# ============================================================

def verify_explicit_create_folder(
    user_message,
    target,
    params
):

    text = prepare_command_text(
        user_message
    )

    pattern = (
        r"^"
        r"(?:crée|cree|créer|creer)"
        r"\s+"
        r"(?:(?:un|le)\s+)?"
        r"dossier"
        r"\s+"
        r"(.+?)"
        r"\s+dans\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"("
        + SECURITY_ROOT_PATTERN
        + r")"
        r"\s*[.!?]?\s*$"
    )

    match = re.fullmatch(
        pattern,
        text,
        flags=re.IGNORECASE
    )

    if not match:
        return False

    requested_name = (
        match
        .group(1)
        .strip()
    )

    requested_root = (
        normalize_security_root(
            match.group(2)
        )
    )

    backend_name = params.get(
        "name"
    )

    return bool(
        requested_root
        ==
        target

        and

        same_security_value(
            requested_name,
            backend_name
        )
    )


# ============================================================
# PREUVE EXPLICITE : CREER FICHIER AVEC CONTENU
# ============================================================

def verify_explicit_create_file_with_content(
    user_message,
    target,
    params
):
    """
    Vérifie la phrase utilisateur brute, y compris le contenu.

    Le contenu n'est pas comparé avec une normalisation sémantique :
    le backend doit avoir conservé exactement le texte demandé
    (hors espaces externes et normalisation Unicode NFC).
    """

    if not isinstance(
        user_message,
        str
    ):
        return False

    text = unicodedata.normalize(
        "NFC",
        user_message
    ).replace(
        "’",
        "'"
    ).strip()

    patterns = [
        (
            r"^"
            r"(?:crée|cree|créer|creer)"
            r"\s+"
            r"(?:(?:le|un)\s+fichier\s+)?"
            r"(.+?)"
            r"\s+dans\s+"
            r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
            r"(" + SECURITY_ROOT_PATTERN + r")"
            r"\s+avec\s+le\s+contenu"
            r"\s*:?[ \t]*"
            r"(.+?)"
            r"\s*$"
        ),
        (
            r"^"
            r"(?:crée|cree|créer|creer)"
            r"\s+"
            r"(?:(?:le|un)\s+fichier\s+)?"
            r"(.+?)"
            r"\s+dans\s+"
            r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
            r"(" + SECURITY_ROOT_PATTERN + r")"
            r"\s+contenant"
            r"\s*:?[ \t]*"
            r"(.+?)"
            r"\s*$"
        ),
    ]

    match = None

    for pattern in patterns:
        match = re.fullmatch(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:
            break

    if not match:
        return False

    requested_file = (
        match
        .group(1)
        .strip()
    )

    requested_root = normalize_security_root(
        match.group(2)
    )

    requested_content = unicodedata.normalize(
        "NFC",
        match.group(3).strip()
    )

    backend_file = params.get(
        "file_name"
    )

    backend_content = params.get(
        "content"
    )

    if not isinstance(
        backend_content,
        str
    ):
        return False

    backend_content = unicodedata.normalize(
        "NFC",
        backend_content.strip()
    )

    return bool(
        requested_root
        ==
        target

        and

        same_security_value(
            requested_file,
            backend_file
        )

        and

        requested_content
        ==
        backend_content
    )



# ============================================================
# PREUVE EXPLICITE : MODIFICATION FICHIER EXISTANT
# ============================================================

def verify_explicit_modify_file_content(
    user_message,
    target,
    params
):
    """
    Vérifie le nom, la racine, le mode et le contenu à partir de la
    phrase brute. Un backend ne peut donc pas inventer une modification.
    """

    if not isinstance(
        user_message,
        str
    ):
        return False

    text = unicodedata.normalize(
        "NFC",
        user_message
    ).replace(
        "’",
        "'"
    ).strip()

    backend_file = params.get(
        "file_name"
    )

    backend_content = params.get(
        "content"
    )

    backend_mode = (
        str(
            params.get(
                "mode",
                ""
            )
        )
        .strip()
        .lower()
    )

    if not isinstance(
        backend_content,
        str
    ):
        return False

    backend_content = unicodedata.normalize(
        "NFC",
        backend_content.strip()
    )

    patterns = [
        (
            "replace_content",
            (
                r"^"
                r"(?:remplace|remplacer)"
                r"\s+le\s+contenu\s+(?:de|du)\s+"
                r"(?:(?:le|la)\s+fichier\s+)?"
                r"(.+?)"
                r"\s+dans\s+"
                r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
                r"(" + SECURITY_ROOT_PATTERN + r")"
                r"\s+par"
                r"\s*:?[ \t]*"
                r"(.+?)"
                r"\s*$"
            )
        ),
        (
            "append_line",
            (
                r"^"
                r"(?:ajoute|ajouter)"
                r"\s+une\s+ligne\s+[àa]\s+"
                r"(?:(?:le|la)\s+fichier\s+)?"
                r"(.+?)"
                r"\s+dans\s+"
                r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
                r"(" + SECURITY_ROOT_PATTERN + r")"
                r"\s+avec\s+le\s+contenu"
                r"\s*:?[ \t]*"
                r"(.+?)"
                r"\s*$"
            )
        ),
        (
            "append_content",
            (
                r"^"
                r"(?:ajoute|ajouter)"
                r"\s+(?:au|à|a)\s+fichier\s+"
                r"(.+?)"
                r"\s+dans\s+"
                r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
                r"(" + SECURITY_ROOT_PATTERN + r")"
                r"\s+le\s+contenu"
                r"\s*:?[ \t]*"
                r"(.+?)"
                r"\s*$"
            )
        ),
    ]

    for expected_mode, pattern in patterns:
        match = re.fullmatch(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if not match:
            continue

        requested_file = match.group(1).strip()
        requested_root = normalize_security_root(
            match.group(2)
        )
        requested_content = unicodedata.normalize(
            "NFC",
            match.group(3).strip()
        )

        return bool(
            expected_mode
            ==
            backend_mode

            and

            requested_root
            ==
            target

            and

            same_security_value(
                requested_file,
                backend_file
            )

            and

            requested_content
            ==
            backend_content
        )

    return False


# ============================================================
# PREUVE EXPLICITE : DEPLACEMENT ENTRE RACINES
# ============================================================

def verify_explicit_move_between_roots(
    user_message,
    target,
    params
):

    text = prepare_command_text(
        user_message
    )

    backend_source = (
        str(
            params.get(
                "source_root",
                ""
            )
        )
        .strip()
        .lower()
    )

    backend_destination = (
        str(
            params.get(
                "destination_root",
                ""
            )
        )
        .strip()
        .lower()
    )

    backend_file = params.get(
        "file_name"
    )

    backend_folder = params.get(
        "destination_folder"
    )

    # --------------------------------------------------------
    # target doit être identique à la source.
    # --------------------------------------------------------

    if backend_source != target:
        return False

    # ========================================================
    # AVEC SOUS-DOSSIER
    # ========================================================

    pattern_with_folder = (
        r"^"
        r"(?:déplace|deplace|déplacer|deplacer)"
        r"\s+"
        r"(?:(?:le|la)\s+fichier\s+)?"
        r"(.+?)"
        r"\s+"
        r"(?:de|du|des)"
        r"\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"("
        + SECURITY_ROOT_PATTERN
        + r")"
        r"\s+"
        r"(?:vers|dans)"
        r"\s+"
        r"(?:(?:le|un)\s+dossier\s+)"
        r"(.+?)"
        r"\s+"
        r"(?:dans|de|du|des)"
        r"\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"("
        + SECURITY_ROOT_PATTERN
        + r")"
        r"\s*[.!?]?\s*$"
    )

    match = re.fullmatch(
        pattern_with_folder,
        text,
        flags=re.IGNORECASE
    )

    if match:

        requested_file = (
            match
            .group(1)
            .strip()
        )

        requested_source = (
            normalize_security_root(
                match.group(2)
            )
        )

        requested_folder = (
            match
            .group(3)
            .strip()
        )

        requested_destination = (
            normalize_security_root(
                match.group(4)
            )
        )

        return bool(
            requested_source
            ==
            backend_source

            and

            requested_destination
            ==
            backend_destination

            and

            same_security_value(
                requested_file,
                backend_file
            )

            and

            isinstance(
                backend_folder,
                str
            )

            and

            same_security_value(
                requested_folder,
                backend_folder
            )
        )

    # ========================================================
    # DIRECTEMENT VERS UNE AUTRE RACINE
    # ========================================================

    pattern_direct = (
        r"^"
        r"(?:déplace|deplace|déplacer|deplacer)"
        r"\s+"
        r"(?:(?:le|la)\s+fichier\s+)?"
        r"(.+?)"
        r"\s+"
        r"(?:de|du|des)"
        r"\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"("
        + SECURITY_ROOT_PATTERN
        + r")"
        r"\s+"
        r"(?:vers|dans)"
        r"\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"("
        + SECURITY_ROOT_PATTERN
        + r")"
        r"\s*[.!?]?\s*$"
    )

    match = re.fullmatch(
        pattern_direct,
        text,
        flags=re.IGNORECASE
    )

    if not match:
        return False

    requested_file = (
        match
        .group(1)
        .strip()
    )

    requested_source = (
        normalize_security_root(
            match.group(2)
        )
    )

    requested_destination = (
        normalize_security_root(
            match.group(3)
        )
    )

    return bool(
        requested_source
        ==
        backend_source

        and

        requested_destination
        ==
        backend_destination

        and

        same_security_value(
            requested_file,
            backend_file
        )

        and

        backend_folder is None
    )


# ============================================================
# PREUVE EXPLICITE : DEPLACEMENT INTERNE
# ============================================================

def verify_explicit_move_within_root(
    user_message,
    target,
    params
):

    # --------------------------------------------------------
    # Pour le moment, la forme historique reste limitée
    # à Documents.
    # --------------------------------------------------------

    if target != "documents":
        return False

    text = prepare_command_text(
        user_message
    )

    pattern = (
        r"^"
        r"(?:déplace|deplace|déplacer|deplacer)"
        r"\s+"
        r"(?:(?:le|la)\s+fichier\s+)?"
        r"(.+?)"
        r"\s+"
        r"(?:dans|vers)"
        r"\s+"
        r"(?:(?:le|un)\s+dossier\s+)?"
        r"(.+?)"
        r"\s*[.!?]?\s*$"
    )

    match = re.fullmatch(
        pattern,
        text,
        flags=re.IGNORECASE
    )

    if not match:
        return False

    requested_file = (
        match
        .group(1)
        .strip()
    )

    requested_folder = (
        match
        .group(2)
        .strip()
    )

    # --------------------------------------------------------
    # Empêche qu'une racine Windows soit interprétée
    # comme un simple sous-dossier.
    # --------------------------------------------------------

    if normalize_security_root(
        requested_folder
    ):
        return False

    return bool(
        same_security_value(
            requested_file,
            params.get(
                "file_name"
            )
        )

        and

        same_security_value(
            requested_folder,
            params.get(
                "destination_folder"
            )
        )
    )


# ============================================================
# PREUVE EXPLICITE : RENOMMAGE
# ============================================================

def verify_explicit_rename_file(
    user_message,
    target,
    params
):
    """
    Préparation du renommage ultra contrôlé.

    Forme obligatoire :

        renomme ancien.pdf en nouveau.pdf dans Documents

    Le renommage n'est accepté que si la commande
    utilisateur correspond exactement au contrat
    proposé par le backend.
    """

    text = prepare_command_text(
        user_message
    )

    pattern = (
        r"^"
        r"(?:renomme|renommer)"
        r"\s+"
        r"(?:(?:le|la)\s+fichier\s+)?"
        r"(.+?)"
        r"\s+en\s+"
        r"(.+?)"
        r"\s+dans\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"("
        + SECURITY_ROOT_PATTERN
        + r")"
        r"\s*[.!?]?\s*$"
    )

    match = re.fullmatch(
        pattern,
        text,
        flags=re.IGNORECASE
    )

    if not match:
        return False

    requested_old_name = (
        match
        .group(1)
        .strip()
    )

    requested_new_name = (
        match
        .group(2)
        .strip()
    )

    requested_root = (
        normalize_security_root(
            match.group(3)
        )
    )

    return bool(
        requested_root
        ==
        target

        and

        same_security_value(
            requested_old_name,
            params.get(
                "old_name"
            )
        )

        and

        same_security_value(
            requested_new_name,
            params.get(
                "new_name"
            )
        )
    )


# ============================================================
# PREUVE EXPLICITE : RENOMMAGE SANS RACINE
# ============================================================

def verify_explicit_rename_file_auto(
    user_message,
    target,
    params
):
    """
    Forme acceptée :

        renomme ancien.pdf en nouveau.pdf

    La racine n'est pas fournie par le backend. Elle sera
    recherchée de façon déterministe uniquement dans les six
    dossiers utilisateur autorisés.
    """

    if target != "auto":
        return False

    text = prepare_command_text(
        user_message
    )

    pattern = (
        r"^"
        r"(?:renomme|renommer)"
        r"\s+"
        r"(?:(?:le|la)\s+fichier\s+)?"
        r"(.+?)"
        r"\s+en\s+"
        r"(.+?)"
        r"\s*[.!?]?\s*$"
    )

    match = re.fullmatch(
        pattern,
        text,
        flags=re.IGNORECASE
    )

    if not match:
        return False

    requested_old_name = (
        match
        .group(1)
        .strip()
    )

    requested_new_name = (
        match
        .group(2)
        .strip()
    )

    # Une commande contenant explicitement "dans <racine>" doit
    # être traitée par rename_file, jamais par le mode automatique.
    tail_root_pattern = (
        r"\s+dans\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"(?:"
        + SECURITY_ROOT_PATTERN
        + r")\s*[.!?]?\s*$"
    )

    if re.search(
        tail_root_pattern,
        text,
        flags=re.IGNORECASE
    ):
        return False

    return bool(
        same_security_value(
            requested_old_name,
            params.get(
                "old_name"
            )
        )

        and

        same_security_value(
            requested_new_name,
            params.get(
                "new_name"
            )
        )
    )


# ============================================================
# PREUVE EXPLICITE : SUPPRESSION CONTROLEE
# ============================================================

def verify_explicit_delete_file(
    user_message,
    target,
    params
):
    """
    Formes acceptées :

        supprime rapport.pdf dans Documents
        supprimer rapport.pdf de Documents

    La suppression définitive, la suppression de masse,
    les jokers et les chemins arbitraires ne sont jamais
    considérés comme une preuve explicite valide.
    """

    text = prepare_command_text(
        user_message
    )

    # --------------------------------------------------------
    # Refus explicite des formulations destructives.
    # --------------------------------------------------------

    normalized_text = unicodedata.normalize(
        "NFKD",
        text
    )

    normalized_text = "".join(
        character
        for character in normalized_text
        if not unicodedata.combining(
            character
        )
    ).casefold()

    forbidden_fragments = (
        "definitivement",
        "de facon definitive",
        "de maniere definitive",
        "sans passer par la corbeille",
        "sans corbeille",
        "vide la corbeille",
        "vider la corbeille",
    )

    if any(
        fragment in normalized_text
        for fragment in forbidden_fragments
    ):
        return False

    pattern = (
        r"^"
        r"(?:supprime|supprimer)"
        r"\s+"
        r"(?:(?:le|la)\s+fichier\s+)?"
        r"(.+?)"
        r"\s+"
        r"(?:dans|de|du|des)"
        r"\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"("
        + SECURITY_ROOT_PATTERN
        + r")"
        r"\s*[.!?]?\s*$"
    )

    match = re.fullmatch(
        pattern,
        text,
        flags=re.IGNORECASE
    )

    if not match:
        return False

    requested_file = (
        match
        .group(1)
        .strip()
    )

    requested_root = (
        normalize_security_root(
            match.group(2)
        )
    )

    if (
        not requested_file
        or
        len(requested_file) > 180
        or
        "/" in requested_file
        or
        "\\" in requested_file
        or
        "*" in requested_file
        or
        "?" in requested_file
        or
        ".." in requested_file
    ):
        return False

    normalized_file = normalize_security_value(
        requested_file
    )

    mass_terms = {
        "tout",
        "tous",
        "toutes",
        "tout le contenu",
        "tous les fichiers",
        "toutes les photos",
        "toutes les images",
        "toutes les videos",
        "toutes les musiques",
        "les fichiers",
        "les documents",
        "les photos",
        "les images",
        "les videos",
        "les musiques",
    }

    if normalized_file in mass_terms:
        return False

    return bool(
        requested_root
        ==
        target

        and

        same_security_value(
            requested_file,
            params.get(
                "file_name"
            )
        )
    )


# ============================================================
# PREUVE EXPLICITE : COPIE ENTRE RACINES
# ============================================================

def verify_explicit_copy_between_roots(
    user_message,
    target,
    params
):
    """
    La copie n'est valide que si le texte brut de l'utilisateur
    correspond exactement au contrat proposé par le backend.

    Formes acceptées :
        copie rapport.pdf de Documents vers Bureau
        copier rapport.pdf de Documents vers Téléchargements
        copie rapport.pdf de Documents vers le dossier Archives dans Bureau
    """

    text = prepare_command_text(
        user_message
    )

    backend_source = (
        str(
            params.get(
                "source_root",
                ""
            )
        )
        .strip()
        .lower()
    )

    backend_destination = (
        str(
            params.get(
                "destination_root",
                ""
            )
        )
        .strip()
        .lower()
    )

    backend_file = params.get(
        "file_name"
    )

    backend_folder = params.get(
        "destination_folder"
    )

    if backend_source != target:
        return False

    mass_terms = {
        "tout",
        "tous",
        "toutes",
        "tout le contenu",
        "tous les fichiers",
        "toutes les photos",
        "toutes les images",
        "toutes les videos",
        "toutes les musiques",
        "les fichiers",
        "les documents",
        "les photos",
        "les images",
        "les videos",
        "les musiques",
    }

    # ========================================================
    # AVEC SOUS-DOSSIER
    # ========================================================

    pattern_with_folder = (
        r"^"
        r"(?:copie|copier)"
        r"\s+"
        r"(?:(?:le|la)\s+fichier\s+)?"
        r"(.+?)"
        r"\s+"
        r"(?:de|du|des)"
        r"\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"("
        + SECURITY_ROOT_PATTERN
        + r")"
        r"\s+"
        r"(?:vers|dans)"
        r"\s+"
        r"(?:(?:le|un)\s+dossier\s+)"
        r"(.+?)"
        r"\s+"
        r"(?:dans|de|du|des)"
        r"\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"("
        + SECURITY_ROOT_PATTERN
        + r")"
        r"\s*[.!?]?\s*$"
    )

    match = re.fullmatch(
        pattern_with_folder,
        text,
        flags=re.IGNORECASE
    )

    if match:
        requested_file = (
            match
            .group(1)
            .strip()
        )

        requested_source = normalize_security_root(
            match.group(2)
        )

        requested_folder = (
            match
            .group(3)
            .strip()
        )

        requested_destination = normalize_security_root(
            match.group(4)
        )

        if normalize_security_value(
            requested_file
        ) in mass_terms:
            return False

        if (
            not requested_file
            or
            len(requested_file) > 180
            or
            "/" in requested_file
            or
            "\\" in requested_file
            or
            "*" in requested_file
            or
            "?" in requested_file
            or
            ".." in requested_file
        ):
            return False

        return bool(
            requested_source
            ==
            backend_source

            and

            requested_destination
            ==
            backend_destination

            and

            same_security_value(
                requested_file,
                backend_file
            )

            and

            isinstance(
                backend_folder,
                str
            )

            and

            same_security_value(
                requested_folder,
                backend_folder
            )
        )

    # ========================================================
    # DIRECTEMENT VERS UNE AUTRE RACINE
    # ========================================================

    pattern_direct = (
        r"^"
        r"(?:copie|copier)"
        r"\s+"
        r"(?:(?:le|la)\s+fichier\s+)?"
        r"(.+?)"
        r"\s+"
        r"(?:de|du|des)"
        r"\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"("
        + SECURITY_ROOT_PATTERN
        + r")"
        r"\s+"
        r"(?:vers|dans)"
        r"\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"("
        + SECURITY_ROOT_PATTERN
        + r")"
        r"\s*[.!?]?\s*$"
    )

    match = re.fullmatch(
        pattern_direct,
        text,
        flags=re.IGNORECASE
    )

    if not match:
        return False

    requested_file = (
        match
        .group(1)
        .strip()
    )

    requested_source = normalize_security_root(
        match.group(2)
    )

    requested_destination = normalize_security_root(
        match.group(3)
    )

    if normalize_security_value(
        requested_file
    ) in mass_terms:
        return False

    if (
        not requested_file
        or
        len(requested_file) > 180
        or
        "/" in requested_file
        or
        "\\" in requested_file
        or
        "*" in requested_file
        or
        "?" in requested_file
        or
        ".." in requested_file
    ):
        return False

    return bool(
        requested_source
        ==
        backend_source

        and

        requested_destination
        ==
        backend_destination

        and

        same_security_value(
            requested_file,
            backend_file
        )

        and

        backend_folder is None
    )


# ============================================================
# PREUVE EXPLICITE GLOBALE
# ============================================================

def verify_explicit_file_action(
    user_message,
    action_data
):

    if not isinstance(
        user_message,
        str
    ):

        return (
            False,
            (
                "Aucune commande utilisateur "
                "explicite n'a été fournie."
            )
        )

    if not isinstance(
        action_data,
        dict
    ):

        return (
            False,
            "Contrat d'action fichier invalide."
        )

    action = (
        str(
            action_data.get(
                "action",
                ""
            )
        )
        .strip()
        .lower()
    )

    target = (
        str(
            action_data.get(
                "target",
                ""
            )
        )
        .strip()
        .lower()
    )

    params = action_data.get(
        "params",
        {}
    )

    if not isinstance(
        params,
        dict
    ):
        params = {}

    verified = False

    if action == "list_directory":

        verified = (
            verify_explicit_list_directory(
                user_message,
                target
            )
        )

    elif action == "create_folder":

        verified = (
            verify_explicit_create_folder(
                user_message,
                target,
                params
            )
        )

    elif action == "create_file_with_content":

        verified = (
            verify_explicit_create_file_with_content(
                user_message,
                target,
                params
            )
        )

    elif action == "modify_file_content":

        verified = (
            verify_explicit_modify_file_content(
                user_message,
                target,
                params
            )
        )

    elif action == "move_file_between_roots":

        verified = (
            verify_explicit_move_between_roots(
                user_message,
                target,
                params
            )
        )

    elif action == "copy_file_between_roots":

        verified = (
            verify_explicit_copy_between_roots(
                user_message,
                target,
                params
            )
        )

    elif action == "move_file_within_root":

        verified = (
            verify_explicit_move_within_root(
                user_message,
                target,
                params
            )
        )

    elif action == "rename_file":

        verified = (
            verify_explicit_rename_file(
                user_message,
                target,
                params
            )
        )

    elif action == "rename_file_auto":

        verified = (
            verify_explicit_rename_file_auto(
                user_message,
                target,
                params
            )
        )

    elif action == "delete_file":

        verified = (
            verify_explicit_delete_file(
                user_message,
                target,
                params
            )
        )

    elif action == "read_file_content":

        verified = (
            verify_explicit_read_file_content(
                user_message,
                target,
                params
            )
        )

    if verified:

        return (
            True,
            None
        )

    return (
        False,
        (
            "La manipulation de fichiers a été refusée : "
            "la commande utilisateur ne correspond pas "
            "exactement à l'action proposée par le backend."
        )
    )


# ============================================================
# PREUVE EXPLICITE APPLICATIONS / SITES
# ============================================================

def verify_explicit_interactive_action(
    user_message,
    action,
    target,
    params=None
):
    """
    Réinterprète la phrase brute avec le parseur déterministe
    strict, indépendamment du backend principal choisi.

    Ainsi, un backend LLM ne peut pas inventer une ouverture ou
    une fermeture qui n'existe pas explicitement dans la commande
    utilisateur.
    """

    if not isinstance(
        user_message,
        str
    ):
        return (
            False,
            "Commande utilisateur explicite absente."
        )

    user_message = user_message.strip()

    if not user_message:
        return (
            False,
            "Commande utilisateur explicite absente."
        )

    try:
        proof = interpret_deterministic_for_proof(
            user_message
        )
    except Exception:
        return (
            False,
            "Impossible de vérifier la commande utilisateur."
        )

    actions = proof.get(
        "actions",
        []
    )

    if not isinstance(
        actions,
        list
    ):
        actions = []

    expected_action = (
        str(action)
        .strip()
        .lower()
    )

    expected_target = (
        str(target)
        .strip()
        .lower()
    )

    expected_params = params if isinstance(params, dict) else {}
    expected_operation = (
        str(expected_params.get("operation", ""))
        .strip()
        .lower()
    )

    for candidate in actions:
        if not isinstance(
            candidate,
            dict
        ):
            continue

        candidate_action = (
            str(
                candidate.get(
                    "action",
                    ""
                )
            )
            .strip()
            .lower()
        )

        candidate_target = (
            str(
                candidate.get(
                    "target",
                    ""
                )
            )
            .strip()
            .lower()
        )

        if (
            candidate_action
            ==
            expected_action
            and
            candidate_target
            ==
            expected_target
        ):

            if expected_action == "manage_window":
                candidate_params = candidate.get("params", {})
                if not isinstance(candidate_params, dict):
                    continue
                candidate_operation = (
                    str(candidate_params.get("operation", ""))
                    .strip()
                    .lower()
                )
                if candidate_operation != expected_operation:
                    continue

            return (
                True,
                None
            )

    return (
        False,
        (
            "Commande refusée : l'action interactive proposée "
            "ne correspond pas exactement à la phrase "
            "écrite par l'utilisateur."
        )
    )


# ============================================================
# VALIDATION DES ACTIONS
# ============================================================

def validate_action(
    action_data
):

    if not isinstance(
        action_data,
        dict
    ):

        return (
            False,
            "Format d'action invalide."
        )

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
    # HABITUDES
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
                "Identifiant d'habitude invalide."
            )

    # ========================================================
    # LISTE HABITUDES
    # ========================================================

    if action == "list_habits":

        if target not in {"pending", "summary"}:

            return (
                False,
                (
                    "Type de liste "
                    "d'habitudes invalide."
                )
            )

    # ========================================================
    # ROUTINES
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
        "close_application",
        "check_application",
        "manage_window",
        "open_website",
        "close_website",
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
        "create_file_with_content",
        "modify_file_content",
        "move_file_within_root",
        "move_file_between_roots",
        "copy_file_between_roots",
        "rename_file",
        "delete_file",
        "read_file_content",
    }:

        if target not in ALLOWED_FILE_ROOTS:

            return (
                False,
                (
                    "Racine de fichiers "
                    "interdite ou inconnue."
                )
            )

    if action == "rename_file_auto":

        if target != "auto":

            return (
                False,
                "Cible de recherche automatique invalide."
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

    # ========================================================
    # GESTION FENETRE
    # ========================================================

    if action == "manage_window":

        if set(params.keys()) != {"operation"}:
            return (
                False,
                "Paramètres de gestion de fenêtre invalides."
            )

        operation = (
            str(params.get("operation", ""))
            .strip()
            .lower()
        )

        if operation not in {
            "focus",
            "maximize",
            "minimize",
            "restore",
            "snap_left",
            "snap_right",
        }:
            return (
                False,
                "Opération de fenêtre inconnue ou interdite."
            )

    # ========================================================
    # CREATION DOSSIER
    # ========================================================

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

    # ========================================================
    # CREATION FICHIER AVEC CONTENU
    # ========================================================

    if action == "create_file_with_content":

        file_name = params.get(
            "file_name"
        )

        content = params.get(
            "content"
        )

        if (
            not isinstance(
                file_name,
                str
            )
            or
            not file_name.strip()
        ):
            return (
                False,
                "Nom de fichier à créer invalide."
            )

        file_name = file_name.strip()

        if len(file_name) > 180:
            return (
                False,
                "Le nom du fichier à créer est trop long."
            )

        if (
            "/" in file_name
            or
            "\\" in file_name
            or
            "*" in file_name
            or
            "?" in file_name
            or
            ".." in file_name
        ):
            return (
                False,
                "Le nom du fichier à créer contient une syntaxe interdite."
            )

        if not isinstance(
            content,
            str
        ):
            return (
                False,
                "Le contenu du fichier à créer est invalide."
            )

        if "\x00" in content:
            return (
                False,
                "Le contenu binaire est interdit."
            )

        # Borne de contrat. file_tools.py applique ensuite
        # la limite finale en octets issue de permissions.json.
        if len(content) > 65536:
            return (
                False,
                "Le contenu demandé est trop volumineux."
            )


    # ========================================================
    # MODIFICATION FICHIER EXISTANT
    # ========================================================

    if action == "modify_file_content":

        file_name = params.get(
            "file_name"
        )

        content = params.get(
            "content"
        )

        mode = (
            str(
                params.get(
                    "mode",
                    ""
                )
            )
            .strip()
            .lower()
        )

        if (
            not isinstance(
                file_name,
                str
            )
            or
            not file_name.strip()
        ):
            return (
                False,
                "Nom de fichier à modifier invalide."
            )

        file_name = file_name.strip()

        if len(file_name) > 180:
            return (
                False,
                "Le nom du fichier à modifier est trop long."
            )

        if (
            "/" in file_name
            or
            "\\" in file_name
            or
            "*" in file_name
            or
            "?" in file_name
            or
            ".." in file_name
        ):
            return (
                False,
                "Le nom du fichier à modifier contient une syntaxe interdite."
            )

        if mode not in {
            "replace_content",
            "append_content",
            "append_line",
        }:
            return (
                False,
                "Mode de modification invalide."
            )

        if not isinstance(
            content,
            str
        ):
            return (
                False,
                "Le contenu de modification est invalide."
            )

        if "\x00" in content:
            return (
                False,
                "Le contenu binaire est interdit."
            )

        if len(content) > 65536:
            return (
                False,
                "Le contenu de modification est trop volumineux."
            )

        if (
            mode == "append_line"
            and
            ("\n" in content or "\r" in content)
        ):
            return (
                False,
                "Une seule ligne peut être ajoutée avec ce mode."
            )

    # ========================================================
    # DEPLACEMENT INTERNE
    # ========================================================

    if action == "move_file_within_root":

        file_name = params.get(
            "file_name"
        )

        destination_folder = params.get(
            "destination_folder"
        )

        if (
            not isinstance(
                file_name,
                str
            )
            or
            not file_name.strip()
        ):

            return (
                False,
                "Nom de fichier invalide."
            )

        if (
            not isinstance(
                destination_folder,
                str
            )
            or
            not destination_folder.strip()
        ):

            return (
                False,
                "Dossier destination invalide."
            )

        if len(
            file_name.strip()
        ) > 180:

            return (
                False,
                "Le nom du fichier est trop long."
            )

        if len(
            destination_folder.strip()
        ) > 180:

            return (
                False,
                (
                    "Le nom du dossier "
                    "destination est trop long."
                )
            )

    # ========================================================
    # DEPLACEMENT ENTRE RACINES
    # ========================================================

    if action == "move_file_between_roots":

        source_root = params.get(
            "source_root"
        )

        destination_root = params.get(
            "destination_root"
        )

        file_name = params.get(
            "file_name"
        )

        destination_folder = params.get(
            "destination_folder"
        )

        # ----------------------------------------------------
        # Source
        # ----------------------------------------------------

        if not isinstance(
            source_root,
            str
        ):

            return (
                False,
                "Racine source invalide."
            )

        source_root = (
            source_root
            .strip()
            .lower()
        )

        if source_root not in ALLOWED_FILE_ROOTS:

            return (
                False,
                (
                    "Racine source "
                    "interdite ou inconnue."
                )
            )

        # ----------------------------------------------------
        # Destination
        # ----------------------------------------------------

        if not isinstance(
            destination_root,
            str
        ):

            return (
                False,
                "Racine destination invalide."
            )

        destination_root = (
            destination_root
            .strip()
            .lower()
        )

        if destination_root not in ALLOWED_FILE_ROOTS:

            return (
                False,
                (
                    "Racine destination "
                    "interdite ou inconnue."
                )
            )

        # ----------------------------------------------------
        # target = source obligatoire
        # ----------------------------------------------------

        if source_root != target:

            return (
                False,
                (
                    "Incohérence entre la cible "
                    "et la racine source."
                )
            )

        # ----------------------------------------------------
        # Racines différentes
        # ----------------------------------------------------

        if source_root == destination_root:

            return (
                False,
                (
                    "Les deux racines doivent "
                    "être différentes."
                )
            )

        # ----------------------------------------------------
        # Nom fichier
        # ----------------------------------------------------

        if (
            not isinstance(
                file_name,
                str
            )
            or
            not file_name.strip()
        ):

            return (
                False,
                "Nom de fichier invalide."
            )

        if len(
            file_name.strip()
        ) > 180:

            return (
                False,
                "Le nom du fichier est trop long."
            )

        # ----------------------------------------------------
        # Sous-dossier destination facultatif
        # ----------------------------------------------------

        if destination_folder is not None:

            if (
                not isinstance(
                    destination_folder,
                    str
                )
                or
                not destination_folder.strip()
            ):

                return (
                    False,
                    "Dossier destination invalide."
                )

            if len(
                destination_folder.strip()
            ) > 180:

                return (
                    False,
                    (
                        "Le nom du dossier "
                        "destination est trop long."
                    )
                )

    # ========================================================
    # COPIE ENTRE RACINES
    # ========================================================

    if action == "copy_file_between_roots":

        source_root = params.get(
            "source_root"
        )

        destination_root = params.get(
            "destination_root"
        )

        file_name = params.get(
            "file_name"
        )

        destination_folder = params.get(
            "destination_folder"
        )

        if not isinstance(
            source_root,
            str
        ):
            return (
                False,
                "Racine source de copie invalide."
            )

        source_root = (
            source_root
            .strip()
            .lower()
        )

        if source_root not in ALLOWED_FILE_ROOTS:
            return (
                False,
                "Racine source de copie interdite ou inconnue."
            )

        if not isinstance(
            destination_root,
            str
        ):
            return (
                False,
                "Racine destination de copie invalide."
            )

        destination_root = (
            destination_root
            .strip()
            .lower()
        )

        if destination_root not in ALLOWED_FILE_ROOTS:
            return (
                False,
                "Racine destination de copie interdite ou inconnue."
            )

        if source_root != target:
            return (
                False,
                (
                    "Incohérence entre la cible de copie "
                    "et la racine source."
                )
            )

        if source_root == destination_root:
            return (
                False,
                "Les deux racines de copie doivent être différentes."
            )

        if (
            not isinstance(
                file_name,
                str
            )
            or
            not file_name.strip()
        ):
            return (
                False,
                "Nom de fichier à copier invalide."
            )

        file_name = file_name.strip()

        if len(
            file_name
        ) > 180:
            return (
                False,
                "Le nom du fichier à copier est trop long."
            )

        if (
            "/" in file_name
            or
            "\\" in file_name
            or
            "*" in file_name
            or
            "?" in file_name
            or
            ".." in file_name
        ):
            return (
                False,
                "Le nom du fichier à copier contient une syntaxe interdite."
            )

        if destination_folder is not None:
            if (
                not isinstance(
                    destination_folder,
                    str
                )
                or
                not destination_folder.strip()
            ):
                return (
                    False,
                    "Sous-dossier destination de copie invalide."
                )

            destination_folder = destination_folder.strip()

            if len(
                destination_folder
            ) > 180:
                return (
                    False,
                    (
                        "Le nom du sous-dossier destination "
                        "de copie est trop long."
                    )
                )

            if (
                "/" in destination_folder
                or
                "\\" in destination_folder
                or
                "*" in destination_folder
                or
                "?" in destination_folder
                or
                ".." in destination_folder
            ):
                return (
                    False,
                    (
                        "Le sous-dossier destination de copie "
                        "contient une syntaxe interdite."
                    )
                )

    # ========================================================
    # RENOMMAGE FICHIER
    # ========================================================

    if action in {
        "rename_file",
        "rename_file_auto",
    }:

        old_name = params.get(
            "old_name"
        )

        new_name = params.get(
            "new_name"
        )

        if (
            not isinstance(
                old_name,
                str
            )
            or
            not old_name.strip()
        ):

            return (
                False,
                "Ancien nom de fichier invalide."
            )

        if (
            not isinstance(
                new_name,
                str
            )
            or
            not new_name.strip()
        ):

            return (
                False,
                "Nouveau nom de fichier invalide."
            )

        old_name = old_name.strip()
        new_name = new_name.strip()

        if (
            len(old_name) > 180
            or
            len(new_name) > 180
        ):

            return (
                False,
                "Un nom de fichier est trop long."
            )

        if (
            old_name.casefold()
            ==
            new_name.casefold()
        ):

            return (
                False,
                (
                    "L'ancien et le nouveau nom "
                    "ne peuvent pas être identiques."
                )
            )

    # ========================================================
    # SUPPRESSION FICHIER
    # ========================================================

    if action == "delete_file":

        file_name = params.get(
            "file_name"
        )

        if (
            not isinstance(
                file_name,
                str
            )
            or
            not file_name.strip()
        ):

            return (
                False,
                "Nom de fichier à supprimer invalide."
            )

        file_name = file_name.strip()

        if len(file_name) > 180:

            return (
                False,
                "Le nom du fichier est trop long."
            )

    # ========================================================
    # LECTURE CONTENU FICHIER
    # ========================================================

    if action == "read_file_content":

        file_name = params.get(
            "file_name"
        )

        if (
            not isinstance(
                file_name,
                str
            )
            or
            not file_name.strip()
        ):

            return (
                False,
                "Nom de fichier à lire invalide."
            )

        file_name = file_name.strip()

        if len(file_name) > 180:

            return (
                False,
                "Le nom du fichier est trop long."
            )

    # ========================================================
    # RENOMMAGE HABITUDE
    # ========================================================

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

    # ========================================================
    # DECLENCHEUR HABITUDE
    # ========================================================

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

    # ========================================================
    # ACTION BROUILLON HABITUDE
    # ========================================================

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
# HABITUDES EN ATTENTE
# ============================================================

def format_habit_summary():

    summary = get_learning_summary()
    accepted = int(summary.get("accepted", 0))
    pending = int(summary.get("pending", 0))
    drafts = int(summary.get("drafts", 0))

    if accepted == 0 and pending == 0 and drafts == 0:
        return (
            "Je n’ai encore aucune habitude validée ni proposition en attente. "
            "Si l’apprentissage est activé, je continuerai à observer uniquement "
            "les actions autorisées et je te proposerai une routine quand un schéma "
            "répété sera suffisamment clair."
        )

    lines = []
    accepted_habits = get_habits_by_status("accepted")
    if accepted_habits:
        lines.append("Habitudes validées :")
        for habit in accepted_habits[:5]:
            label = habit.get("title") or f"Habitude #{habit.get('id')}"
            typical = habit.get("typical_time")
            suffix = f" · vers {typical}" if typical else ""
            lines.append(f"- {label}{suffix}")
        if len(accepted_habits) > 5:
            lines.append(f"- {len(accepted_habits) - 5} autre(s) habitude(s) validée(s).")

    habits = get_pending_habits()
    if habits:
        if lines:
            lines.append("")
        lines.append("Propositions en attente :")
        for habit in habits[:5]:
            lines.append(f"- #{habit.get('id')} {habit.get('title')}")
        if len(habits) > 5:
            lines.append(f"- {len(habits) - 5} autre(s) proposition(s).")

    if drafts:
        if lines:
            lines.append("")
        lines.append(f"Brouillons de modification : {drafts}.")

    return "\n".join(lines)


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

        lines.extend(
            [
                "",
                f"ID : {habit_id}",
                f"Nom : {habit.get('title')}",
                f"Profil : {habit.get('profile')}",
                (
                    "Jours observés : "
                    f"{habit.get('distinct_days')}"
                ),
                (
                    "Occurrences : "
                    f"{habit.get('occurrences')}"
                ),
                (
                    "Heure typique : "
                    f"{habit.get('typical_time')}"
                ),
                "",
                "Actions :",
            ]
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
                    "-> "
                    f"{action_data.get('target')}"
                )
            )

        lines.extend(
            [
                "",
                (
                    "Modifier : "
                    f"modifie l'habitude {habit_id}"
                ),
                (
                    "Accepter : "
                    f"accepte l'habitude {habit_id}"
                ),
                (
                    "Refuser : "
                    f"refuse l'habitude {habit_id}"
                ),
                "-" * 55,
            ]
        )

    return "\n".join(
        lines
    )


# ============================================================
# OUVRIR BROUILLON HABITUDE
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
# AFFICHER BROUILLON HABITUDE
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
# RESULTAT MODIFICATION BROUILLON
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
    action_data,
    user_message=None
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
    # PREUVE EXPLICITE FICHIERS
    # ========================================================

    explicit_file_command = False

    if action in FILE_ACTIONS_REQUIRING_EXPLICIT_PROOF:

        explicit_file_command, proof_error = (
            verify_explicit_file_action(
                user_message,
                action_data
            )
        )

        if not explicit_file_command:

            return (
                False,
                proof_error
            )

    # ========================================================
    # PREUVE EXPLICITE APPLICATIONS / SITES
    # ========================================================

    explicit_interactive_command = False

    if action in INTERACTIVE_ACTIONS_REQUIRING_EXPLICIT_PROOF:

        explicit_interactive_command, proof_error = (
            verify_explicit_interactive_action(
                user_message,
                action,
                target,
                params=params
            )
        )

        if not explicit_interactive_command:

            return (
                False,
                proof_error
            )

    # ========================================================
    # APPLICATION
    # ========================================================

    if action == "open_application":

        return open_application(
            target,
            source="manual",
            explicit_user_command=(
                explicit_interactive_command
            )
        )

    if action == "close_application":

        return close_application(
            target,
            source="manual",
            explicit_user_command=(
                explicit_interactive_command
            )
        )

    if action == "check_application":

        running, message = (
            is_application_running(
                target,
                source="manual"
            )
        )

        return (
            True,
            message
        )

    if action == "manage_window":

        return manage_application_window(
            target,
            params["operation"],
            source="manual",
            explicit_user_command=(
                explicit_interactive_command
            )
        )

    # ========================================================
    # FICHIERS
    # ========================================================

    if action == "list_directory":

        return list_directory(
            target
        )

    if action == "create_folder":

        return create_folder(
            target,
            params[
                "name"
            ],
            explicit_user_command=(
                explicit_file_command
            )
        )

    if action == "create_file_with_content":

        return create_file_with_content(
            target,
            params[
                "file_name"
            ],
            params[
                "content"
            ],
            explicit_user_command=(
                explicit_file_command
            ),
            source="manual"
        )

    if action == "modify_file_content":

        return modify_file_content(
            target,
            params[
                "file_name"
            ],
            params[
                "content"
            ],
            params[
                "mode"
            ],
            explicit_user_command=(
                explicit_file_command
            ),
            source="manual"
        )

    if action == "move_file_within_root":

        return move_file_within_root(
            target,
            params[
                "file_name"
            ],
            params[
                "destination_folder"
            ],
            explicit_user_command=(
                explicit_file_command
            )
        )

    if action == "move_file_between_roots":

        return move_file_between_roots(
            params[
                "source_root"
            ],
            params[
                "destination_root"
            ],
            params[
                "file_name"
            ],
            destination_folder_name=(
                params.get(
                    "destination_folder"
                )
            ),
            explicit_user_command=(
                explicit_file_command
            )
        )

    if action == "copy_file_between_roots":

        return copy_file_between_roots(
            params[
                "source_root"
            ],
            params[
                "destination_root"
            ],
            params[
                "file_name"
            ],
            destination_folder_name=(
                params.get(
                    "destination_folder"
                )
            ),
            explicit_user_command=(
                explicit_file_command
            ),
            source="manual"
        )

    if action == "rename_file":

        return rename_file(
            target,
            params[
                "old_name"
            ],
            params[
                "new_name"
            ],
            explicit_user_command=(
                explicit_file_command
            )
        )

    if action == "rename_file_auto":

        return rename_file_auto(
            params[
                "old_name"
            ],
            params[
                "new_name"
            ],
            explicit_user_command=(
                explicit_file_command
            )
        )

    if action == "delete_file":

        return delete_file_to_recycle_bin(
            target,
            params[
                "file_name"
            ],
            explicit_user_command=(
                explicit_file_command
            )
        )

    if action == "read_file_content":

        return read_file_content(
            target,
            params[
                "file_name"
            ],
            explicit_user_command=(
                explicit_file_command
            ),
            source="manual"
        )

    # ========================================================
    # WEB
    # ========================================================

    if action == "open_website":

        return open_website(
            target,
            source="manual",
            explicit_user_command=(
                explicit_interactive_command
            )
        )

    if action == "close_website":

        return close_website(
            target,
            source="manual",
            explicit_user_command=(
                explicit_interactive_command
            )
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
    # HABITUDES
    # ========================================================

    if action == "list_habits":

        if target == "summary":
            return True, format_habit_summary()

        return (
            True,
            format_pending_habits()
        )

    if action == "modify_habit":

        return open_habit_draft(
            int(
                target
            )
        )

    if action == "show_habit_draft":

        return show_habit_draft(
            int(
                target
            )
        )

    if action == "rename_habit_draft":

        success, message = (
            update_habit_draft_name(
                int(
                    target
                ),
                params[
                    "name"
                ]
            )
        )

        return format_draft_change_result(
            int(
                target
            ),
            success,
            message
        )

    if action == "add_habit_draft_action":

        success, message = (
            add_habit_draft_action(
                int(
                    target
                ),
                params[
                    "action"
                ],
                params[
                    "target"
                ]
            )
        )

        return format_draft_change_result(
            int(
                target
            ),
            success,
            message
        )

    if action == "remove_habit_draft_action":

        success, message = (
            remove_habit_draft_action(
                int(
                    target
                ),
                params[
                    "action"
                ],
                params[
                    "target"
                ]
            )
        )

        return format_draft_change_result(
            int(
                target
            ),
            success,
            message
        )

    if action == "set_habit_draft_trigger":

        success, message = (
            set_habit_draft_trigger(
                int(
                    target
                ),
                params[
                    "trigger"
                ]
            )
        )

        return format_draft_change_result(
            int(
                target
            ),
            success,
            message
        )

    if action == "cancel_habit_draft":

        return delete_habit_draft(
            int(
                target
            )
        )

    if action == "confirm_habit_draft":

        return confirm_habit_draft(
            int(
                target
            )
        )

    if action == "accept_habit":

        if get_habit_draft(
            int(
                target
            )
        ) is not None:

            return (
                False,
                (
                    "Cette habitude possède "
                    "un brouillon de modification.\n"
                    "L'acceptation directe est bloquée "
                    "pour éviter de perdre les modifications "
                    "du brouillon."
                )
            )

        return accept_habit(
            int(
                target
            )
        )

    if action == "reject_habit":

        return reject_habit(
            int(
                target
            )
        )

    return (
        False,
        (
            "Action autorisée mais aucun exécuteur "
            "n'est défini : "
            f"{action}"
        )
    )


# ============================================================
# ACTION APPRENABLE AUTORISEE ?
# ============================================================

def is_action_learnable(
    action,
    target
):
    """
    Une application réservée aux commandes manuelles
    ne doit pas devenir automatiquement une habitude.

    Les sites web restent apprenables.
    """

    if action == "open_website":
        return True

    if action != "open_application":
        return False

    application_config = get_application_config(
        target
    )

    if not isinstance(
        application_config,
        dict
    ):
        return False

    return bool(
        application_config.get(
            "enabled",
            False
        )
        and
        application_config.get(
            "allow_from_habit",
            False
        )
    )


# ============================================================
# EXECUTION DE PLUSIEURS ACTIONS
# ============================================================

def execute_actions(
    actions,
    user_message=None
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
                    "Je n'ai pas exécuté cette action : "
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

        success, message = (
            execute_action(
                action_data,
                user_message=user_message
            )
        )

        if success:

            display_results.append(
                message
            )

        else:

            display_results.append(
                (
                    "Je n'ai pas exécuté cette action : "
                    f"{message}"
                )
            )

        # ----------------------------------------------------
        # Les actions fichiers ne sont jamais apprises.
        # ----------------------------------------------------

        if (
            action in LEARNABLE_AGENT_ACTIONS
            and
            is_action_learnable(
                action,
                target
            )
        ):

            activity_results.append(
                {
                    "action": action,
                    "target": target,
                    "success": bool(
                        success
                    ),
                }
            )

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
            habit[
                "id"
            ]
            for habit in previous_pending
        }

        recorded, result = (
            record_session(
                activity_results,
                source="manual"
            )
        )

        if DEBUG:

            if recorded:

                print(
                    (
                        "[APPRENTISSAGE] "
                        "Session manuelle enregistrée."
                    )
                )

            else:

                print(
                    (
                        "[APPRENTISSAGE] "
                        f"{result}"
                    )
                )

        if not recorded:
            return []

        current_pending = (
            get_pending_habits()
        )

        return [
            habit
            for habit in current_pending
            if habit[
                "id"
            ] not in previous_ids
        ]

    except Exception as error:

        if DEBUG:

            print(
                (
                    "[APPRENTISSAGE] "
                    "Erreur non bloquante : "
                    f"{error}"
                )
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

from action_suggestions import (
    build_suggestions,
    clear_pending_suggestion,
    format_suggestions,
    get_pending_suggestions,
    is_accept_suggestion_message,
    is_reject_suggestion_message,
    resolve_suggestion_message,
    set_pending_suggestions,
)
from session_context import (
    clear_pending_choice,
    get_last_entity,
    resolve_pending_choice,
    set_last_entity,
    set_pending_choice,
)

from command_sequences import (
    split_explicit_sequence,
    remember_sequence,
    describe_last_sequence,
)

from interaction_guard import route_user_input

# V12.5.2 : une sequence est volontairement limitee aux consultations
# et ouvertures sans ecriture. Les operations sensibles restent unitaires.
SAFE_SEQUENCE_ACTIONS = frozenset({
    "open_application", "check_application", "open_website",
    "list_directory", "list_directory_auto", "find_filesystem_item",
    "advanced_file_search", "read_system_info", "read_process_info",
    "read_power_info", "read_network_info", "read_audio_state",
    "list_browser_tabs", "check_browser_site", "read_weather",
    "read_news", "read_daily_briefing", "check_online_updates",
})

_SEQUENCE_HISTORY_QUESTIONS = frozenset({
    "explique ce que tu viens de faire et ce que tu n as pas reussi",
    "explique ce que tu viens de faire", "qu as tu fait et qu est ce qui a echoue",
    "resume les dernieres etapes", "resume la derniere sequence",
    "quelles etapes as tu executees", "quelles etapes as tu faites",
    "ou en est la derniere tache", "qu as tu fait dans la derniere tache",
})


def _execute_explicit_sequence(steps):
    """Valide toute la sequence avant d'effectuer sa premiere action.

    Chaque etape est reverifiee avec le parseur deterministe strict ; le LLM
    ne peut ni ajouter d'actions ni contourner le contrat et les permissions.
    """
    # Meme une tentative refusee remplace l'ancien resume de sequence.
    remember_sequence(steps, [], completed=False)
    planned = []
    for index, step in enumerate(steps, start=1):
        result = interpret_instruction(step)
        actions = result.get("actions", []) if isinstance(result, dict) else []
        if not isinstance(actions, list) or len(actions) != 1:
            return (
                f"Aucune action lancee : l'etape {index}/{len(steps)} "
                "n'est pas une commande unique suffisamment precise."
            )
        action_data = actions[0]
        if not isinstance(action_data, dict):
            return f"Aucune action lancee : format invalide a l'etape {index}."
        action = str(action_data.get("action", "")).strip().lower()
        if action not in SAFE_SEQUENCE_ACTIONS:
            return (
                f"Aucune action lancee : l'etape {index}/{len(steps)} "
                f"({action or 'inconnue'}) necessite une commande separee. "
                "Les modifications, suppressions et autres actions sensibles "
                "ne sont pas automatisees dans une sequence."
            )
        valid, reason = validate_action(action_data)
        if not valid:
            return f"Aucune action lancee : etape {index} invalide : {reason}"
        try:
            strict = interpret_deterministic_for_proof(step)
            candidates = strict.get("actions", []) if isinstance(strict, dict) else []
        except Exception:
            candidates = []
        if not any(isinstance(candidate, dict) and candidate == action_data for candidate in candidates):
            return (
                f"Aucune action lancee : l'etape {index} n'est pas "
                "confirmee par le moteur de securite local."
            )
        planned.append((step, action_data))

    lines = []
    outcomes = []
    activities = []
    for index, (step, action_data) in enumerate(planned, start=1):
        try:
            success, message = execute_action(action_data, user_message=step)
        except Exception as error:
            success, message = False, f"Erreur de l'outil : {type(error).__name__}"
        success = bool(success)
        outcomes.append(success)
        lines.append(
            f"Etape {index}/{len(planned)} "
            + ("reussie" if success else "en echec")
            + f" : {message}"
        )
        if success:
            _remember_last_entity([action_data], [str(message)])
            _register_browser_tab_number_choices([action_data], [str(message)])
            action = str(action_data.get("action", "")).lower()
            target = str(action_data.get("target", "")).lower()
            if action in LEARNABLE_AGENT_ACTIONS and is_action_learnable(action, target):
                activities.append({"action": action, "target": target, "success": True})
        else:
            break
    remember_sequence(steps, outcomes, completed=(len(outcomes) == len(steps) and all(outcomes)))
    if activities:
        learn_from_actions(activities)
    if len(outcomes) < len(steps):
        lines.append(f"{len(steps) - len(outcomes)} etape(s) non executee(s) apres cet echec.")
    return "\n\n".join(lines)


def _normalize_session_phrase(value):
    text = str(value or "").strip().lower().replace("’", "'")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\s+", " ", text).strip(" .!?")
    return text


def _resolve_session_reference_command(user_message):
    """Résout quelques pronoms sûrs vers la dernière entité explicitement manipulée."""
    text = _normalize_session_phrase(user_message).replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()
    entity = get_last_entity()
    if not entity:
        return None
    kind = str(entity.get("kind", "")).strip().lower()
    target = str(entity.get("target", "")).strip()
    if not target:
        return None

    if text in {"ferme ca", "ferme cela", "ferme le", "ferme lui", "ferme cette application", "ferme cette appli"}:
        if kind == "application":
            return f"ferme {target}"
        if kind in {"website", "browser_tab"}:
            return f"ferme {target}"

    if text in {"ouvre le", "ouvre la", "ouvre ca", "ouvre cela", "rouvre le", "rouvre la", "relance le", "relance la", "relance ca"}:
        if kind in {"application", "website"}:
            return f"ouvre {target}"

    if text in {"retourne dessus", "repasse dessus", "passe dessus", "mets ca devant", "ramene ca devant", "reviens dessus", "reviens sur ca"}:
        if kind in {"website", "browser_tab"}:
            return f"passe sur {target}"
        if kind == "application":
            return f"mets {target} au premier plan"
    return None


def _remember_last_entity(actions, display_results):
    """Mémorise seulement une cible déjà autorisée et exécutée avec succès."""
    if not isinstance(actions, list) or not isinstance(display_results, list):
        return
    for action_data, display in zip(actions, display_results):
        if not isinstance(action_data, dict):
            continue
        text = str(display or "").strip().lower()
        if text.startswith("je n'ai pas exécuté") or text.startswith("je n'ai pas execute") or text.startswith("erreur"):
            continue
        action = str(action_data.get("action", "")).strip().lower()
        target = str(action_data.get("target", "")).strip()
        if not target:
            continue
        if action in {"open_application", "check_application", "manage_window"}:
            set_last_entity("application", target, action)
        elif action in {"open_website", "close_website", "check_browser_site", "open_browser_site_existing_edge"}:
            set_last_entity("website", target, action)
        elif action == "activate_browser_tab":
            set_last_entity("browser_tab", target, action)


def _register_conversation_choices(user_message, reply):
    """Transforme les questions de clarification connues en vrais choix actionnables."""
    text = _normalize_session_phrase(user_message)
    answer = str(reply or "")
    items = []
    choices = {}

    if text in {"je veux faire un tableau", "ouvre le truc pour faire un tableau"}:
        items = [
            ("excel", "Ouvrir Excel pour le tableau de données", "ouvre excel"),
            ("word", "Ouvrir Word pour un tableau dans un document", "ouvre word"),
        ]
        choices = {"excel": "ouvre excel", "word": "ouvre word"}
    elif text in {"je veux ecrire quelque chose", "je veux ecrire un texte", "je veux taper un texte", "ouvre le truc pour ecrire", "ouvre ce qu'il faut pour ecrire"}:
        items = [
            ("notepad", "Ouvrir Bloc-notes pour du texte rapide", "ouvre bloc-notes"),
            ("word", "Ouvrir Word pour un document", "ouvre word"),
        ]
        choices = {"bloc-notes": "ouvre bloc-notes", "bloc notes": "ouvre bloc-notes", "word": "ouvre word"}
    elif text in {"ouvre note", "ouvre notes", "lance note", "lance notes", "ouvre mes notes", "lance mes notes"}:
        items = [
            ("notepad", "Ouvrir Bloc-notes", "ouvre bloc-notes"),
            ("onenote", "Ouvrir OneNote", "ouvre onenote"),
        ]
        choices = {"bloc-notes": "ouvre bloc-notes", "bloc notes": "ouvre bloc-notes", "onenote": "ouvre onenote", "one note": "ouvre onenote"}

    if items:
        set_pending_suggestions(items)
        set_pending_choice("clarification", choices)
        return True
    return False


def get_pending_action_suggestions():
    """API légère destinée au GUI : aucune exécution, uniquement des métadonnées de session."""
    return [
        {"id": s.suggestion_id, "label": s.label, "command": s.command}
        for s in get_pending_suggestions()
    ]


def _register_browser_tab_number_choices(actions, display_results):
    """Permet « 5 » après une liste d'onglets, sans confondre avec les suggestions 1..3.

    Seuls les hôtes déjà connus d'AgentLocal sont convertis en commandes sûres.
    """
    if not actions or len(actions) != 1 or not display_results:
        return
    action = actions[0] if isinstance(actions[0], dict) else {}
    if str(action.get("action", "")).strip().lower() != "list_browser_tabs":
        return
    text = str(display_results[0] or "")
    host_aliases = {
        "chatgpt.com": "chatgpt",
        "web.whatsapp.com": "whatsapp",
        "whatsapp.com": "whatsapp",
        "www.youtube.com": "youtube",
        "youtube.com": "youtube",
        "github.com": "github",
        "teams.microsoft.com": "teams",
        "outlook.office365.com": "outlook",
        "outlook.live.com": "outlook-perso",
        "web.descript.com": "descript",
        "foad.udmci-enligne.ci": "udmci",
    }
    choices = {}
    for line in text.splitlines():
        match = re.match(r"^(\d+)\. .*? — ([^ ]+)(?: \[actif\])?$", line.strip())
        if not match:
            continue
        alias = host_aliases.get(match.group(2).strip().lower())
        if alias:
            choices[match.group(1)] = f"passe sur {alias}"
    if choices:
        set_pending_choice("browser_tab_number", choices)


def process_instruction(
    user_message,
    _depth=0,
):
    # Evite les cycles entre expressions apprises, suggestions et references.
    if _depth >= 6:
        return "Je m'arrete : trop de reformulations successives. Precise ta demande."

    # V11.8 : refus/annulation d'une proposition ou d'un choix en attente.
    if is_reject_suggestion_message(user_message):
        clear_pending_suggestion()
        clear_pending_choice()
        return "Ça marche, je laisse tomber la suggestion."

    # Une suggestion concrète peut être choisie par clic, numéro, libellé ou
    # validation courte (oui/vas-y). La commande canonique repasse ensuite
    # dans toutes les validations normales.
    suggestion_command = resolve_suggestion_message(user_message)
    if suggestion_command:
        clear_pending_suggestion()
        clear_pending_choice()
        return process_instruction(suggestion_command, _depth=_depth + 1)

    if is_accept_suggestion_message(user_message):
        return "Je n’ai aucune suggestion en attente pour le moment."

    choice_command = resolve_pending_choice(user_message)
    if choice_command:
        clear_pending_suggestion()
        return process_instruction(choice_command, _depth=_depth + 1)

    if re.sub(r"\s+", " ", _normalize_session_phrase(user_message).replace("-", " ").replace("'", " ")).strip() in _SEQUENCE_HISTORY_QUESTIONS:
        return describe_last_sequence()

    contextual_command = _resolve_session_reference_command(user_message)
    if contextual_command:
        return process_instruction(contextual_command, _depth=_depth + 1)

    # Comprehension V1.5 : correction de quelques erreurs terrain, sans
    # nouvelle permission. Une commande normalisee repasse par le parseur
    # local de securite. Les explications ne declenchent aucun outil.
    if _depth == 0:
        guarded = route_user_input(user_message)
        if guarded is not None:
            kind, value = guarded
            if kind == "reply":
                clear_pending_suggestion()
                clear_pending_choice()
                return value
            if kind == "command":
                return process_instruction(value, _depth=_depth + 1)

    # V12.5.2 : la commande composee est analysee avant tout appel LLM global.
    # Une etape invalide bloque l'ensemble, sans effet de bord.
    steps, sequence_error = split_explicit_sequence(user_message)
    if sequence_error:
        return "Aucune action lancee : " + sequence_error
    if steps:
        clear_pending_suggestion()
        clear_pending_choice()
        return _execute_explicit_sequence(steps)

    # V12.5 : une expression explicitement apprise par cet hôte repasse par
    # toutes les validations normales. Elle ne contourne jamais le moteur.
    if resolve_learned_expression is not None:
        try:
            learned_command = resolve_learned_expression(user_message)
        except Exception:
            learned_command = None
        if learned_command and _normalize_session_phrase(learned_command) != _normalize_session_phrase(user_message):
            return process_instruction(learned_command, _depth=_depth + 1)

    # Une nouvelle demande sans rapport invalide les anciennes suggestions.
    clear_pending_suggestion()
    clear_pending_choice()

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
            and
            reply.strip()
        ):

            reply = reply.strip()
            if _register_conversation_choices(user_message, reply):
                suggestions = get_pending_suggestions()
                if suggestions:
                    return reply + "\n\n" + format_suggestions(suggestions)
            return reply

        error = result.get(
            "error"
        )

        if error:

            return (
                "ERREUR D'INTERPRETATION : "
                f"{error}"
            )

        try:
            should_store = bool(user_preference("understanding.store_unrecognized", True)) if user_preference is not None else False
            if should_store and record_unrecognized is not None:
                record_unrecognized(user_message)
        except Exception:
            pass
        return (
            "Je n’ai pas capté exactement ce que tu veux faire. "
            "Dis-moi juste l’action et la cible, par exemple : « ouvre Formation JS », "
            "« retrouve mon rapport dans Documents » ou « montre mes Téléchargements »."
        )

    display_results, activity_results = (
        execute_actions(
            actions,
            user_message=user_message
        )
    )

    _remember_last_entity(actions, display_results)
    _register_browser_tab_number_choices(actions, display_results)

    new_habits = learn_from_actions(
        activity_results
    )

    for habit in new_habits:

        display_results.append(
            format_habit_notification(
                habit
            )
        )

    suggestions = build_suggestions(
        user_message,
        actions,
        display_results,
    )
    if suggestions:
        display_results.append(format_suggestions(suggestions))

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
        (
            "Multi-backend + routines + "
            "apprentissage + sécurité fichiers"
        )
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
            else
            "désactivé"
        )
    )

    print()

    print(
        (
            "Zones fichiers autorisées : "
            "Bureau, Documents, Téléchargements, "
            "Images, Vidéos, Musique"
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
        "  liste mes images"
    )

    print(
        "  liste mes vidéos"
    )

    print(
        "  liste ma musique"
    )

    print(
        "  crée un dossier Factures dans Documents"
    )

    print(
        "  déplace facture.pdf dans Factures"
    )

    print(
        (
            "  déplace photo.jpg "
            "de Téléchargements vers Images"
        )
    )

    print(
        "  prépare mon environnement de travail"
    )

    print(
        "  affiche mes habitudes"
    )

    print()

    print(
        "Tape 'sort' ou 'arrête' pour arrêter l'agent."
    )

    print()

    # ========================================================
    # BOUCLE PRINCIPALE
    # ========================================================

    while True:

        try:

            user_message = input(
                "Que veux-tu faire ? > "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError
        ):

            print()

            print(
                "Agent Local arrêté."
            )

            break

        if not user_message:
            continue

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

            print()

            print(
                "Agent Local arrêté."
            )

            break

        print()

        print(
            "Je regarde..."
        )

        print()

        result = process_instruction(
            user_message
        )

        print(
            "Agent Local >"
        )

        print(
            result
        )

        print()



# ============================================================
# ACCES RECURSIF CONTROLE AUX SOUS-DOSSIERS
# ============================================================

from recursive_file_tools import (
    advanced_search_files as recursive_advanced_search_files,
    copy_file_between_roots as recursive_copy_file_between_roots,
    create_file_with_content as recursive_create_file_with_content,
    create_folder as recursive_create_folder,
    delete_file_auto as recursive_delete_file_auto,
    delete_file_to_recycle_bin as recursive_delete_file_to_recycle_bin,
    find_filesystem_item as recursive_find_filesystem_item,
    list_directory as recursive_list_directory,
    list_directory_auto as recursive_list_directory_auto,
    modify_file_content as recursive_modify_file_content,
    move_file_between_roots as recursive_move_file_between_roots,
    move_file_within_root as recursive_move_file_within_root,
    read_file_auto as recursive_read_file_auto,
    read_file_content as recursive_read_file_content,
    rename_file as recursive_rename_file,
    rename_file_auto as recursive_rename_file_auto,
)

from controlled_open_tools import (
    open_directory as controlled_open_directory,
    open_directory_auto as controlled_open_directory_auto,
    close_directory_auto as controlled_close_directory_auto,
    open_file as controlled_open_file,
    open_file_auto as controlled_open_file_auto,
)

from backends.deterministic_backend import (
    interpret as deterministic_proof_interpret,
)


RECURSIVE_FILE_ACTIONS = {
    "list_directory",
    "list_directory_auto",
    "find_filesystem_item",
    "create_folder",
    "create_file_with_content",
    "modify_file_content",
    "move_file_within_root",
    "move_file_between_roots",
    "copy_file_between_roots",
    "rename_file",
    "rename_file_auto",
    "delete_file",
    "delete_file_auto",
    "read_file_content",
    "read_file_auto",
    "open_directory",
    "open_directory_auto",
    "close_directory_auto",
    "open_file",
    "open_file_auto",
    "advanced_file_search",
}

SUPPORTED_ACTIONS.update(
    {
        "list_directory_auto",
        "find_filesystem_item",
        "delete_file_auto",
        "read_file_auto",
        "open_directory",
        "open_directory_auto",
        "close_directory_auto",
        "open_file",
        "open_file_auto",
        "advanced_file_search",
    }
)

FILE_ACTIONS_REQUIRING_EXPLICIT_PROOF.update(
    {
        "list_directory_auto",
        "find_filesystem_item",
        "delete_file_auto",
        "read_file_auto",
        "open_directory",
        "open_directory_auto",
        "close_directory_auto",
        "open_file",
        "open_file_auto",
        "advanced_file_search",
    }
)


_VAGUE_FILE_REFERENCES_FOR_VALIDATION = {
    "fichier", "le fichier", "la fichier", "un fichier", "ce fichier", "mon fichier",
    "document", "le document", "un document", "ce document", "mon document",
    "dossier", "le dossier", "un dossier", "ce dossier", "mon dossier",
    "quelque chose", "un truc", "le truc", "ce truc", "ca", "cela",
    "celui ci", "celui la", "le dernier fichier", "le dernier document",
    "le dernier dossier", "lui",
}


def _contract_is_vague_reference(value):
    if not isinstance(value, str):
        return False
    normalized = unicodedata.normalize("NFKD", value.lower().replace("’", "'"))
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.replace("-", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip(" .!?")
    return normalized in _VAGUE_FILE_REFERENCES_FOR_VALIDATION


def _contract_relative_path_ok(value, allow_empty=False, simple_only=False):
    if value is None:
        return allow_empty
    if not isinstance(value, str):
        return False
    value = value.strip()
    if not value:
        return allow_empty
    if _contract_is_vague_reference(value):
        return False
    if len(value) > 1024:
        return False
    if value.startswith(("\\\\", "//", "\\", "/")):
        return False
    if ":" in value or "*" in value or "?" in value:
        return False
    if simple_only and ("\\" in value or "/" in value):
        return False
    parts = value.replace("/", "\\").split("\\")
    if not parts or len(parts) > 10:
        return False
    for part in parts:
        if not part or part in {".", ".."} or ".." in part:
            return False
        if re.search(r'[<>:"/\\|?*\x00-\x1f]', part):
            return False
        if part.endswith((" ", ".")):
            return False
    return True


def _validate_recursive_file_action(action_data):
    if not isinstance(action_data, dict):
        return False, "Format d'action invalide."
    if action_data.get("schema_version") != SCHEMA_VERSION:
        return False, "Version du contrat non supportée."

    action = str(action_data.get("action", "")).strip().lower()
    target = str(action_data.get("target", "")).strip().lower()
    params = action_data.get("params", {})
    if not isinstance(params, dict):
        return False, "Paramètres invalides."

    if action not in RECURSIVE_FILE_ACTIONS:
        return False, "Action fichier inconnue."

    auto_actions = {
        "list_directory_auto",
        "find_filesystem_item",
        "rename_file_auto",
        "delete_file_auto",
        "read_file_auto",
        "open_directory_auto",
        "open_file_auto",
        "advanced_file_search",
    }

    if action in auto_actions:
        if action in {"find_filesystem_item", "advanced_file_search"}:
            if target != "auto" and target not in ALLOWED_FILE_ROOTS:
                return False, "Racine de recherche invalide."
        elif target != "auto":
            return False, "Cible automatique invalide."
    elif target not in ALLOWED_FILE_ROOTS:
        return False, "Racine de fichiers interdite ou inconnue."

    if action == "list_directory":
        relative = params.get("relative_path", "")
        if not _contract_relative_path_ok(relative, allow_empty=True):
            return False, "Chemin de dossier invalide."

    elif action == "list_directory_auto":
        if not _contract_relative_path_ok(params.get("directory_name"), simple_only=True):
            return False, "Nom de dossier à rechercher invalide."

    elif action == "find_filesystem_item":
        if not _contract_relative_path_ok(params.get("name"), simple_only=True):
            return False, "Nom à rechercher invalide."
        if str(params.get("item_type", "any")).strip().lower() not in {"any", "file", "dir"}:
            return False, "Type de recherche invalide."
        root_name = params.get("root_name")
        if root_name is not None and str(root_name).strip().lower() not in ALLOWED_FILE_ROOTS:
            return False, "Racine de recherche invalide."

    elif action == "advanced_file_search":
        expected = {
            "file_kind", "date_filter", "date_field", "size_operator",
            "size_bytes", "sort", "limit", "count_only",
        }
        if set(params) != expected:
            return False, "Paramètres de recherche avancée invalides."
        if str(params.get("file_kind", "")).strip().lower() not in {
            "any", "pdf", "word", "excel", "powerpoint", "image", "video", "audio", "text"
        }:
            return False, "Type de fichier de recherche invalide."
        if str(params.get("date_filter", "")).strip().lower() not in {
            "any", "today", "yesterday", "this_week", "last_7_days"
        }:
            return False, "Filtre de date invalide."
        if str(params.get("date_field", "")).strip().lower() not in {"modified", "created"}:
            return False, "Champ de date invalide."
        if str(params.get("size_operator", "")).strip().lower() not in {"any", "gt", "lt"}:
            return False, "Filtre de taille invalide."
        if str(params.get("sort", "")).strip().lower() not in {
            "modified_desc", "created_desc", "size_desc", "name_asc"
        }:
            return False, "Tri de recherche invalide."
        size_bytes = params.get("size_bytes")
        limit = params.get("limit")
        count_only = params.get("count_only")
        if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 0 or size_bytes > 10 * 1024**4:
            return False, "Taille de recherche invalide."
        if isinstance(limit, bool) or not isinstance(limit, int) or not (1 <= limit <= 20):
            return False, "Limite de résultats invalide."
        if not isinstance(count_only, bool):
            return False, "Mode de comptage invalide."

    elif action == "create_folder":
        if not _contract_relative_path_ok(params.get("name")):
            return False, "Chemin du dossier à créer invalide."

    elif action == "create_file_with_content":
        if not _contract_relative_path_ok(params.get("file_name")):
            return False, "Chemin du fichier à créer invalide."
        content = params.get("content")
        if not isinstance(content, str) or "\x00" in content or len(content) > 65536:
            return False, "Contenu du fichier à créer invalide ou trop volumineux."

    elif action == "modify_file_content":
        if not _contract_relative_path_ok(params.get("file_name")):
            return False, "Chemin du fichier à modifier invalide."
        mode = str(params.get("mode", "")).strip().lower()
        if mode not in {"replace_content", "append_content", "append_line"}:
            return False, "Mode de modification invalide."
        content = params.get("content")
        if not isinstance(content, str) or "\x00" in content or len(content) > 65536:
            return False, "Contenu de modification invalide ou trop volumineux."
        if mode == "append_line" and ("\n" in content or "\r" in content):
            return False, "Une seule ligne est autorisée avec ce mode."

    elif action == "move_file_within_root":
        if not _contract_relative_path_ok(params.get("file_name")):
            return False, "Chemin du fichier source invalide."
        if not _contract_relative_path_ok(params.get("destination_folder"), allow_empty=False):
            return False, "Chemin du dossier destination invalide."

    elif action in {"move_file_between_roots", "copy_file_between_roots"}:
        source_root = str(params.get("source_root", "")).strip().lower()
        destination_root = str(params.get("destination_root", "")).strip().lower()
        if source_root not in ALLOWED_FILE_ROOTS or destination_root not in ALLOWED_FILE_ROOTS:
            return False, "Racine source ou destination invalide."
        if source_root != target:
            return False, "Incohérence entre la cible et la racine source."
        if source_root == destination_root:
            return False, "Les racines source et destination doivent être différentes."
        if not _contract_relative_path_ok(params.get("file_name")):
            return False, "Chemin du fichier source invalide."
        destination_folder = params.get("destination_folder")
        if destination_folder is not None and not _contract_relative_path_ok(destination_folder, allow_empty=True):
            return False, "Chemin du dossier destination invalide."

    elif action == "rename_file":
        if not _contract_relative_path_ok(params.get("old_name")):
            return False, "Chemin de l'ancien fichier invalide."
        if not _contract_relative_path_ok(params.get("new_name"), simple_only=True):
            return False, "Nouveau nom de fichier invalide."

    elif action == "rename_file_auto":
        if not _contract_relative_path_ok(params.get("old_name"), simple_only=True):
            return False, "Ancien nom de fichier invalide."
        if not _contract_relative_path_ok(params.get("new_name"), simple_only=True):
            return False, "Nouveau nom de fichier invalide."

    elif action in {"delete_file", "read_file_content"}:
        if not _contract_relative_path_ok(params.get("file_name")):
            return False, "Chemin du fichier invalide."

    elif action in {"delete_file_auto", "read_file_auto"}:
        if not _contract_relative_path_ok(params.get("file_name"), simple_only=True):
            return False, "Nom de fichier à rechercher invalide."

    elif action == "open_directory":
        if not _contract_relative_path_ok(params.get("relative_path", ""), allow_empty=True):
            return False, "Chemin de dossier à ouvrir invalide."

    elif action in {"open_directory_auto", "close_directory_auto"}:
        if not _contract_relative_path_ok(params.get("directory_name"), simple_only=True):
            return False, "Nom de dossier invalide."

    elif action == "open_file":
        if not _contract_relative_path_ok(params.get("file_name")):
            return False, "Chemin de fichier à ouvrir invalide."

    elif action == "open_file_auto":
        if not _contract_relative_path_ok(params.get("file_name"), simple_only=True):
            return False, "Nom de fichier à ouvrir invalide."
        allow_directory_fallback = params.get("allow_directory_fallback", False)
        if not isinstance(allow_directory_fallback, bool):
            return False, "Option d'ouverture fichier/dossier invalide."

    return True, None


_validate_action_before_recursive_access = validate_action


def validate_action(action_data):
    action = ""
    if isinstance(action_data, dict):
        action = str(action_data.get("action", "")).strip().lower()
    if action in RECURSIVE_FILE_ACTIONS:
        return _validate_recursive_file_action(action_data)
    return _validate_action_before_recursive_access(action_data)


def _canonical_contract_value(value):
    if isinstance(value, dict):
        return {
            key: _canonical_contract_value(value[key])
            for key in sorted(value)
        }
    if isinstance(value, list):
        return [_canonical_contract_value(item) for item in value]
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value).strip()
    return value


def verify_explicit_file_action(user_message, action_data):
    """
    Preuve indépendante du backend choisi : la phrase brute doit être
    comprise par le parseur déterministe local et produire exactement
    le même contrat fichier.
    """
    if not isinstance(user_message, str) or not user_message.strip():
        return False, "Aucune commande utilisateur explicite n'a été fournie."

    proof = deterministic_proof_interpret(user_message)
    actions = proof.get("actions", []) if isinstance(proof, dict) else []
    wanted = _canonical_contract_value(action_data)

    for candidate in actions:
        if _canonical_contract_value(candidate) == wanted:
            return True, None

    return False, (
        "La manipulation de fichiers a été refusée : la commande utilisateur "
        "ne correspond pas exactement à l'action déterministe autorisée."
    )


_execute_action_before_recursive_access = execute_action


def execute_action(action_data, user_message=None):
    action = ""
    if isinstance(action_data, dict):
        action = str(action_data.get("action", "")).strip().lower()

    if action not in RECURSIVE_FILE_ACTIONS:
        return _execute_action_before_recursive_access(action_data, user_message=user_message)

    valid, error = validate_action(action_data)
    if not valid:
        return False, error

    explicit, proof_error = verify_explicit_file_action(user_message, action_data)
    if not explicit:
        return False, proof_error

    target = str(action_data.get("target", "")).strip().lower()
    params = action_data.get("params", {})

    if action == "find_filesystem_item":
        return recursive_find_filesystem_item(
            params["name"],
            root_name=params.get("root_name"),
            item_type=params.get("item_type", "any"),
            explicit_user_command=True,
            source="manual",
        )

    if action == "advanced_file_search":
        return recursive_advanced_search_files(
            root_name=None if target == "auto" else target,
            file_kind=params["file_kind"],
            date_filter=params["date_filter"],
            date_field=params["date_field"],
            size_operator=params["size_operator"],
            size_bytes=params["size_bytes"],
            sort=params["sort"],
            limit=params["limit"],
            count_only=params["count_only"],
            explicit_user_command=True,
            source="manual",
        )

    if action == "list_directory":
        return recursive_list_directory(
            target,
            relative_path=params.get("relative_path", ""),
            explicit_user_command=True,
            source="manual",
        )

    if action == "list_directory_auto":
        return recursive_list_directory_auto(
            params["directory_name"],
            explicit_user_command=True,
            source="manual",
        )

    if action == "create_folder":
        return recursive_create_folder(
            target,
            params["name"],
            explicit_user_command=True,
        )

    if action == "create_file_with_content":
        return recursive_create_file_with_content(
            target,
            params["file_name"],
            params["content"],
            explicit_user_command=True,
            source="manual",
        )

    if action == "modify_file_content":
        return recursive_modify_file_content(
            target,
            params["file_name"],
            params["content"],
            params["mode"],
            explicit_user_command=True,
            source="manual",
        )

    if action == "move_file_within_root":
        return recursive_move_file_within_root(
            target,
            params["file_name"],
            params["destination_folder"],
            explicit_user_command=True,
        )

    if action == "move_file_between_roots":
        return recursive_move_file_between_roots(
            params["source_root"],
            params["destination_root"],
            params["file_name"],
            destination_folder_name=params.get("destination_folder"),
            explicit_user_command=True,
        )

    if action == "copy_file_between_roots":
        return recursive_copy_file_between_roots(
            params["source_root"],
            params["destination_root"],
            params["file_name"],
            destination_folder_name=params.get("destination_folder"),
            explicit_user_command=True,
            source="manual",
        )

    if action == "rename_file":
        return recursive_rename_file(
            target,
            params["old_name"],
            params["new_name"],
            explicit_user_command=True,
        )

    if action == "rename_file_auto":
        return recursive_rename_file_auto(
            params["old_name"],
            params["new_name"],
            explicit_user_command=True,
        )

    if action == "delete_file":
        return recursive_delete_file_to_recycle_bin(
            target,
            params["file_name"],
            explicit_user_command=True,
        )

    if action == "delete_file_auto":
        return recursive_delete_file_auto(
            params["file_name"],
            explicit_user_command=True,
        )

    if action == "read_file_content":
        return recursive_read_file_content(
            target,
            params["file_name"],
            explicit_user_command=True,
            source="manual",
        )

    if action == "read_file_auto":
        return recursive_read_file_auto(
            params["file_name"],
            explicit_user_command=True,
            source="manual",
        )

    if action == "open_directory":
        return controlled_open_directory(
            target,
            relative_path=params.get("relative_path", ""),
            explicit_user_command=True,
            source="manual",
        )

    if action == "open_directory_auto":
        return controlled_open_directory_auto(
            params["directory_name"],
            explicit_user_command=True,
            source="manual",
        )

    if action == "close_directory_auto":
        return controlled_close_directory_auto(
            params["directory_name"],
            explicit_user_command=True,
            source="manual",
        )

    if action == "open_file":
        return controlled_open_file(
            target,
            params["file_name"],
            explicit_user_command=True,
            source="manual",
        )

    if action == "open_file_auto":
        return controlled_open_file_auto(
            params["file_name"],
            explicit_user_command=True,
            source="manual",
            allow_directory_fallback=params.get("allow_directory_fallback", False),
        )

    return False, "Action fichier récursive non implémentée."


# ============================================================
# ACTIONS LOCALES V1 - ACCÈS CONTRÔLÉ
# ============================================================

from controlled_local_tools import (
    activate_browser_tab as controlled_activate_browser_tab,
    check_browser_site_open as controlled_check_browser_site_open,
    copy_file_path as controlled_copy_file_path,
    copy_last_reference_path as controlled_copy_last_reference_path,
    list_browser_tabs as controlled_list_browser_tabs,
    open_browser_site_existing_window as controlled_open_browser_site_existing_window,
    open_last_reference as controlled_open_last_reference,
    read_clipboard_text as controlled_read_clipboard_text,
    read_last_reference as controlled_read_last_reference,
    read_system_info as controlled_read_system_info,
    read_process_info as controlled_read_process_info,
    read_power_info as controlled_read_power_info,
    read_network_info as controlled_read_network_info,
    read_audio_state as controlled_read_audio_state,
    set_audio_volume as controlled_set_audio_volume,
    change_audio_volume as controlled_change_audio_volume,
    set_audio_mute as controlled_set_audio_mute,
    create_zip_archive as controlled_create_zip_archive,
    extract_zip_archive as controlled_extract_zip_archive,
    undo_last_file_action as controlled_undo_last_file_action,
    inspect_file_metadata as controlled_inspect_file_metadata,
    inspect_file_metadata_auto as controlled_inspect_file_metadata_auto,
    calculate_file_sha256 as controlled_calculate_file_sha256,
    compare_files_sha256 as controlled_compare_files_sha256,
    find_duplicate_files as controlled_find_duplicate_files,
    take_screenshot as controlled_take_screenshot,
    validate_controlled_action_policy,
    write_clipboard_text as controlled_write_clipboard_text,
)
from recursive_file_tools import get_unique_reference_for_context
from session_context import clear_session_context, set_last_reference
from session_undo import clear_last_file_undo


CONTROLLED_LOCAL_ACTIONS = {
    "read_system_info",
    "read_process_info",
    "read_power_info",
    "read_network_info",
    "read_clipboard",
    "write_clipboard",
    "copy_file_path",
    "list_browser_tabs",
    "activate_browser_tab",
    "check_browser_site",
    "open_browser_site_existing_edge",
    "open_last_reference",
    "read_last_reference",
    "copy_last_reference_path",
    "take_screenshot",
    "read_audio_state",
    "set_audio_volume",
    "change_audio_volume",
    "set_audio_mute",
    "create_zip_archive",
    "extract_zip_archive",
    "undo_last_file_action",
    "inspect_file_metadata",
    "inspect_file_metadata_auto",
    "calculate_file_sha256",
    "compare_files_sha256",
    "find_duplicate_files",
}

SUPPORTED_ACTIONS.update(CONTROLLED_LOCAL_ACTIONS)


def _validate_controlled_local_contract(action_data):
    if not isinstance(action_data, dict):
        return False, "Format d'action invalide."
    if action_data.get("schema_version") != SCHEMA_VERSION:
        return False, "Version du contrat non supportée."

    action = str(action_data.get("action", "")).strip().lower()
    target = str(action_data.get("target", "")).strip().lower()
    params = action_data.get("params")

    if action not in CONTROLLED_LOCAL_ACTIONS:
        return False, "Action locale contrôlée inconnue."

    policy_ok, policy_error = validate_controlled_action_policy(action)
    if not policy_ok:
        return False, policy_error

    no_params_actions = {
        "read_system_info",
        "read_process_info",
        "read_power_info",
        "read_network_info",
        "read_clipboard",
        "list_browser_tabs",
        "activate_browser_tab",
        "check_browser_site",
        "open_browser_site_existing_edge",
        "open_last_reference",
        "read_last_reference",
        "copy_last_reference_path",
        "take_screenshot",
        "read_audio_state",
        "undo_last_file_action",
        "find_duplicate_files",
    }
    if action in no_params_actions and params not in (None, {}):
        return False, "Paramètres supplémentaires interdits pour cette action."

    if action == "read_system_info":
        if target not in {"memory", "disk", "cpu", "uptime", "summary", "performance", "agent", "windows"}:
            return False, "Information système non autorisée."

    elif action == "read_process_info":
        if target not in {"summary", "top", "top_cpu", "top_memory"}:
            return False, "Information processus non autorisée."

    elif action == "read_power_info":
        if target not in {"battery", "power"}:
            return False, "Information d'alimentation non autorisée."

    elif action == "read_network_info":
        if target not in {"status", "local_ip", "interfaces", "link_speed", "traffic_speed", "internet_speed"}:
            return False, "Information réseau non autorisée."

    elif action == "read_clipboard":
        if target != "clipboard":
            return False, "Cible du presse-papiers invalide."

    elif action == "write_clipboard":
        if target != "clipboard" or not isinstance(params, dict):
            return False, "Contrat du presse-papiers invalide."
        if set(params) != {"text"}:
            return False, "Seul le texte explicitement demandé peut être copié."
        text = params.get("text")
        if not isinstance(text, str) or not text or "\x00" in text or len(text) > 8192:
            return False, "Texte du presse-papiers invalide ou trop long."

    elif action == "copy_file_path":
        if target not in ALLOWED_FILE_ROOTS or not isinstance(params, dict):
            return False, "Racine du fichier invalide."
        if set(params) != {"file_name"}:
            return False, "Paramètres de copie de chemin invalides."
        if not _contract_relative_path_ok(params.get("file_name"), simple_only=True):
            return False, "Nom de fichier à résoudre invalide."

    elif action == "list_browser_tabs":
        if target != "edge":
            return False, "Seuls les onglets Edge sont autorisés."

    elif action in {"activate_browser_tab", "check_browser_site", "open_browser_site_existing_edge"}:
        if not target or len(target) > 120:
            return False, "Cible web invalide."
        if any(token in target for token in ("\\", "/", ":", "*", "?", "\x00")):
            return False, "Cible web invalide."

    elif action in {"open_last_reference", "read_last_reference", "copy_last_reference_path"}:
        if target != "session":
            return False, "Cible de mémoire de session invalide."

    elif action == "take_screenshot":
        if target not in {"full_screen", "active_window"}:
            return False, "Mode de capture d'écran non autorisé."

    elif action == "read_audio_state":
        if target != "master":
            return False, "Cible audio invalide."

    elif action == "set_audio_volume":
        if target != "master" or not isinstance(params, dict) or set(params) != {"percent"}:
            return False, "Contrat de volume invalide."
        percent = params.get("percent")
        if isinstance(percent, bool) or not isinstance(percent, int) or not 0 <= percent <= 100:
            return False, "Pourcentage de volume invalide."

    elif action == "change_audio_volume":
        if target != "master" or not isinstance(params, dict) or set(params) != {"delta"}:
            return False, "Contrat de variation audio invalide."
        delta = params.get("delta")
        if isinstance(delta, bool) or not isinstance(delta, int) or delta == 0 or abs(delta) > 25:
            return False, "Variation de volume invalide ou trop importante."

    elif action == "set_audio_mute":
        if target != "master" or not isinstance(params, dict) or set(params) != {"muted"}:
            return False, "Contrat du mode muet invalide."
        if not isinstance(params.get("muted"), bool):
            return False, "État du mode muet invalide."

    elif action in {"inspect_file_metadata", "calculate_file_sha256"}:
        if target not in ALLOWED_FILE_ROOTS or not isinstance(params, dict):
            return False, "Racine d'analyse de fichier invalide."
        if set(params) != {"file_name"}:
            return False, "Paramètres d'analyse de fichier invalides."
        if not _contract_relative_path_ok(params.get("file_name")):
            return False, "Nom de fichier à analyser invalide."

    elif action == "inspect_file_metadata_auto":
        if target != "auto" or not isinstance(params, dict):
            return False, "Cible d'analyse automatique invalide."
        if set(params) != {"file_name"}:
            return False, "Paramètres d'analyse de fichier invalides."
        if not _contract_relative_path_ok(params.get("file_name"), simple_only=True):
            return False, "Nom de fichier à analyser invalide."

    elif action == "compare_files_sha256":
        if target not in ALLOWED_FILE_ROOTS or not isinstance(params, dict):
            return False, "Racine de comparaison invalide."
        if set(params) != {"left_name", "right_name"}:
            return False, "Paramètres de comparaison invalides."
        if not _contract_relative_path_ok(params.get("left_name")) or not _contract_relative_path_ok(params.get("right_name")):
            return False, "Nom de fichier à comparer invalide."

    elif action == "find_duplicate_files":
        if target not in ALLOWED_FILE_ROOTS:
            return False, "Racine de recherche de doublons invalide."

    elif action == "create_zip_archive":
        if target not in ALLOWED_FILE_ROOTS or not isinstance(params, dict):
            return False, "Racine ZIP invalide."
        if set(params) != {"source_name", "archive_name"}:
            return False, "Contrat de création ZIP invalide."
        if not _contract_relative_path_ok(params.get("source_name")):
            return False, "Source à compresser invalide."
        archive_name = params.get("archive_name")
        if not _contract_relative_path_ok(archive_name, simple_only=True) or not str(archive_name).lower().endswith(".zip"):
            return False, "Nom de ZIP invalide."

    elif action == "undo_last_file_action":
        if target != "session":
            return False, "Cible d'annulation invalide."

    elif action == "extract_zip_archive":
        if target not in ALLOWED_FILE_ROOTS or not isinstance(params, dict):
            return False, "Racine ZIP invalide."
        if set(params) != {"archive_name", "destination_folder"}:
            return False, "Contrat d'extraction ZIP invalide."
        if not _contract_relative_path_ok(params.get("archive_name")) or not str(params.get("archive_name", "")).lower().endswith(".zip"):
            return False, "Archive ZIP invalide."
        if not _contract_relative_path_ok(params.get("destination_folder", ""), allow_empty=True):
            return False, "Dossier de destination ZIP invalide."

    return True, None


_validate_action_before_controlled_local_v1 = validate_action


def validate_action(action_data):
    action = ""
    if isinstance(action_data, dict):
        action = str(action_data.get("action", "")).strip().lower()
    if action in CONTROLLED_LOCAL_ACTIONS:
        return _validate_controlled_local_contract(action_data)
    return _validate_action_before_controlled_local_v1(action_data)


def verify_explicit_controlled_action(user_message, action_data):
    """La phrase brute doit produire exactement le même contrat déterministe."""
    if not isinstance(user_message, str) or not user_message.strip():
        return False, "Une commande utilisateur explicite est requise."

    try:
        proof = deterministic_proof_interpret(user_message)
    except Exception:
        return False, "Impossible de vérifier localement la commande utilisateur."

    actions = proof.get("actions", []) if isinstance(proof, dict) else []
    wanted = _canonical_contract_value(action_data)
    for candidate in actions:
        if _canonical_contract_value(candidate) == wanted:
            return True, None
    return False, (
        "Commande refusée : l'action locale proposée ne correspond pas exactement "
        "à la phrase écrite par l'utilisateur."
    )


def _remember_reference_from_successful_action(action_data):
    """Mémorise au plus une référence déjà validée, uniquement en RAM."""
    if not isinstance(action_data, dict):
        return
    action = str(action_data.get("action", "")).strip().lower()
    target = str(action_data.get("target", "")).strip().lower()
    params = action_data.get("params", {})
    if not isinstance(params, dict):
        params = {}

    try:
        if action == "find_filesystem_item":
            ok, ref = get_unique_reference_for_context(
                params.get("name"),
                root_name=params.get("root_name"),
                item_type=params.get("item_type", "any"),
            )
            if ok:
                set_last_reference(ref["root_name"], ref["relative_path"], ref["item_type"])
            return

        if action in {"open_file", "read_file_content", "modify_file_content"}:
            ok, ref = get_unique_reference_for_context(
                params.get("file_name"), root_name=target, item_type="file"
            )
            if ok:
                set_last_reference(ref["root_name"], ref["relative_path"], "file")
            return

        if action in {"open_file_auto", "read_file_auto"}:
            item_type = "any" if (action == "open_file_auto" and params.get("allow_directory_fallback", False)) else "file"
            ok, ref = get_unique_reference_for_context(
                params.get("file_name"), root_name=None, item_type=item_type
            )
            if ok:
                set_last_reference(ref["root_name"], ref["relative_path"], ref.get("item_type", "file"))
            return

        if action == "create_file_with_content":
            set_last_reference(target, params.get("file_name"), "file")
            return

        if action == "open_directory":
            relative_path = str(params.get("relative_path", "")).strip()
            if relative_path:
                set_last_reference(target, relative_path, "dir")
            return

        if action == "open_directory_auto":
            ok, ref = get_unique_reference_for_context(
                params.get("directory_name"), root_name=None, item_type="dir"
            )
            if ok:
                set_last_reference(ref["root_name"], ref["relative_path"], "dir")
            return

        if action == "create_folder":
            set_last_reference(target, params.get("name"), "dir")
            return

        # Après une opération qui peut déplacer, renommer ou supprimer la
        # dernière référence, on préfère oublier plutôt que viser un chemin périmé.
        if action in {
            "move_file_within_root", "move_file_between_roots", "rename_file",
            "rename_file_auto", "delete_file", "delete_file_auto",
        }:
            clear_session_context()
    except Exception:
        # La mémoire de session est un confort : elle ne doit jamais faire
        # échouer une action déjà autorisée.
        return


_execute_action_before_controlled_local_v1 = execute_action


def execute_action(action_data, user_message=None):
    action = ""
    if isinstance(action_data, dict):
        action = str(action_data.get("action", "")).strip().lower()

    if action not in CONTROLLED_LOCAL_ACTIONS:
        result = _execute_action_before_controlled_local_v1(
            action_data, user_message=user_message
        )
        try:
            success = bool(result[0])
        except Exception:
            success = False
        if success:
            _remember_reference_from_successful_action(action_data)
            if action in {
                "create_folder", "create_file_with_content", "modify_file_content",
                "delete_file", "delete_file_auto",
            }:
                clear_last_file_undo()
        return result

    valid, error = validate_action(action_data)
    if not valid:
        return False, error

    explicit, proof_error = verify_explicit_controlled_action(user_message, action_data)
    if not explicit:
        return False, proof_error

    target = str(action_data.get("target", "")).strip().lower()
    params = action_data.get("params", {})
    if not isinstance(params, dict):
        params = {}

    if action == "read_system_info":
        return controlled_read_system_info(
            target, explicit_user_command=True, source="manual"
        )
    if action == "read_process_info":
        return controlled_read_process_info(
            target, explicit_user_command=True, source="manual"
        )
    if action == "read_power_info":
        return controlled_read_power_info(
            target, explicit_user_command=True, source="manual"
        )
    if action == "read_network_info":
        return controlled_read_network_info(
            target, explicit_user_command=True, source="manual"
        )
    if action == "read_clipboard":
        return controlled_read_clipboard_text(
            explicit_user_command=True, source="manual"
        )
    if action == "write_clipboard":
        return controlled_write_clipboard_text(
            params["text"], explicit_user_command=True, source="manual"
        )
    if action == "copy_file_path":
        return controlled_copy_file_path(
            target, params["file_name"], explicit_user_command=True, source="manual"
        )
    if action == "list_browser_tabs":
        return controlled_list_browser_tabs(
            explicit_user_command=True, source="manual"
        )
    if action == "activate_browser_tab":
        return controlled_activate_browser_tab(
            target, explicit_user_command=True, source="manual"
        )
    if action == "check_browser_site":
        return controlled_check_browser_site_open(
            target, explicit_user_command=True, source="manual"
        )
    if action == "open_browser_site_existing_edge":
        return controlled_open_browser_site_existing_window(
            target, explicit_user_command=True, source="manual"
        )
    if action == "open_last_reference":
        return controlled_open_last_reference(
            explicit_user_command=True, source="manual"
        )
    if action == "read_last_reference":
        return controlled_read_last_reference(
            explicit_user_command=True, source="manual"
        )
    if action == "copy_last_reference_path":
        return controlled_copy_last_reference_path(
            explicit_user_command=True, source="manual"
        )
    if action == "take_screenshot":
        return controlled_take_screenshot(
            target, explicit_user_command=True, source="manual"
        )
    if action == "read_audio_state":
        return controlled_read_audio_state(
            explicit_user_command=True, source="manual"
        )
    if action == "set_audio_volume":
        return controlled_set_audio_volume(
            params["percent"], explicit_user_command=True, source="manual"
        )
    if action == "change_audio_volume":
        return controlled_change_audio_volume(
            params["delta"], explicit_user_command=True, source="manual"
        )
    if action == "set_audio_mute":
        return controlled_set_audio_mute(
            params["muted"], explicit_user_command=True, source="manual"
        )
    if action == "inspect_file_metadata":
        return controlled_inspect_file_metadata(
            target, params["file_name"], explicit_user_command=True, source="manual"
        )
    if action == "calculate_file_sha256":
        return controlled_calculate_file_sha256(
            target, params["file_name"], explicit_user_command=True, source="manual"
        )
    if action == "compare_files_sha256":
        return controlled_compare_files_sha256(
            target, params["left_name"], params["right_name"],
            explicit_user_command=True, source="manual"
        )
    if action == "find_duplicate_files":
        return controlled_find_duplicate_files(
            target, explicit_user_command=True, source="manual"
        )
    if action == "create_zip_archive":
        result = controlled_create_zip_archive(
            target, params["source_name"], params["archive_name"],
            explicit_user_command=True, source="manual"
        )
        if result and result[0]:
            clear_last_file_undo()
        return result
    if action == "extract_zip_archive":
        result = controlled_extract_zip_archive(
            target, params["archive_name"], params["destination_folder"],
            explicit_user_command=True, source="manual"
        )
        if result and result[0]:
            clear_last_file_undo()
        return result
    if action == "undo_last_file_action":
        return controlled_undo_last_file_action(
            explicit_user_command=True, source="manual"
        )

    return False, "Action locale contrôlée non implémentée."



# ============================================================
# V12 - SERVICES INTERNET OPTIONNELS EN LECTURE SEULE
# ============================================================

from connected_services import (
    build_daily_briefing as connected_build_daily_briefing,
    check_agentlocal_update as connected_check_agentlocal_update,
    format_daily_briefing as connected_format_daily_briefing,
    format_news as connected_format_news,
    format_update_status as connected_format_update_status,
    format_weather as connected_format_weather,
    get_news as connected_get_news,
    get_weather as connected_get_weather,
)

CONNECTED_ACTIONS = {
    "read_weather",
    "read_news",
    "read_daily_briefing",
    "check_online_updates",
}
SUPPORTED_ACTIONS.update(CONNECTED_ACTIONS)

_validate_action_before_connected_v12 = validate_action
_execute_action_before_connected_v12 = execute_action


def _validate_connected_contract(action_data):
    if not isinstance(action_data, dict):
        return False, "Format d'action connectee invalide."
    if action_data.get("schema_version") != SCHEMA_VERSION:
        return False, "Version du contrat non supportee."
    action = str(action_data.get("action", "")).strip().lower()
    target = str(action_data.get("target", "")).strip().lower()
    params = action_data.get("params")
    if action not in CONNECTED_ACTIONS:
        return False, "Action connectee inconnue."
    if params not in (None, {}):
        return False, "Parametres Internet supplementaires interdits."
    if action in {"read_weather", "read_news", "read_daily_briefing"} and target != "today":
        return False, "Cible connectee non autorisee."
    if action == "check_online_updates" and target != "agentlocal":
        return False, "Seule la verification AgentLocal est autorisee."
    return True, None


def validate_action(action_data):
    action = ""
    if isinstance(action_data, dict):
        action = str(action_data.get("action", "")).strip().lower()
    if action in CONNECTED_ACTIONS:
        return _validate_connected_contract(action_data)
    return _validate_action_before_connected_v12(action_data)


def _verify_explicit_connected_action(user_message, action_data):
    if not isinstance(user_message, str) or not user_message.strip():
        return False, "Une commande utilisateur explicite est requise."
    try:
        proof = deterministic_proof_interpret(user_message)
    except Exception:
        return False, "Impossible de verifier localement la commande Internet."
    wanted = _canonical_contract_value(action_data)
    for candidate in proof.get("actions", []) if isinstance(proof, dict) else []:
        if _canonical_contract_value(candidate) == wanted:
            return True, None
    return False, "Commande connectee refusee : la demande ne correspond pas exactement a une action Internet autorisee."


def execute_action(action_data, user_message=None):
    action = ""
    if isinstance(action_data, dict):
        action = str(action_data.get("action", "")).strip().lower()
    if action not in CONNECTED_ACTIONS:
        return _execute_action_before_connected_v12(action_data, user_message=user_message)

    valid, error = validate_action(action_data)
    if not valid:
        return False, error
    explicit, proof_error = _verify_explicit_connected_action(user_message, action_data)
    if not explicit:
        return False, proof_error

    if action == "read_weather":
        ok, data = connected_get_weather()
        return (True, connected_format_weather(data)) if ok else (False, str(data))
    if action == "read_news":
        ok, data = connected_get_news()
        return (True, connected_format_news(data)) if ok else (False, str(data))
    if action == "read_daily_briefing":
        data = connected_build_daily_briefing()
        # Le briefing peut etre partiel : une panne Internet ne casse jamais l'agent local.
        return True, connected_format_daily_briefing(data)
    if action == "check_online_updates":
        ok, data = connected_check_agentlocal_update()
        return (True, connected_format_update_status(data)) if ok else (False, str(data))

    return False, "Action connectee non implementee."

# ============================================================
# V12.1 - PLANIFICATION LOCALE CONTROLEE
# ============================================================

from scheduler import (
    confirm_schedule as scheduler_confirm_schedule,
    create_draft as scheduler_create_draft,
    delete_schedule as scheduler_delete_schedule,
    format_schedule as scheduler_format_schedule,
    format_schedule_list as scheduler_format_schedule_list,
    resolve_schedule_ref as scheduler_resolve_schedule_ref,
    set_enabled as scheduler_set_enabled,
)

SCHEDULE_ACTIONS = {
    "create_schedule_draft",
    "list_schedules",
    "confirm_schedule",
    "enable_schedule",
    "disable_schedule",
    "delete_schedule",
}
SUPPORTED_ACTIONS.update(SCHEDULE_ACTIONS)

_validate_action_before_scheduler_v121 = validate_action
_execute_action_before_scheduler_v121 = execute_action


def _validate_schedule_contract(action_data):
    if not isinstance(action_data, dict):
        return False, "Format de planification invalide."
    if action_data.get("schema_version") != SCHEMA_VERSION:
        return False, "Version du contrat non supportée."
    action = str(action_data.get("action", "")).strip().lower()
    target = str(action_data.get("target", "")).strip().lower()
    params = action_data.get("params")
    if action not in SCHEDULE_ACTIONS:
        return False, "Action de planification inconnue."

    if action == "list_schedules":
        if target != "all" or params not in (None, {}):
            return False, "Contrat de liste des planifications invalide."
        return True, None

    if action == "create_schedule_draft":
        if target not in {"routine", "briefing", "habit_summary"} or not isinstance(params, dict):
            return False, "Type de planification interdit."
        if set(params) != {"kind", "scheduled_target", "trigger"}:
            return False, "Paramètres de planification invalides."
        if str(params.get("kind", "")).strip().lower() != target:
            return False, "Type de planification incohérent."
        trigger = params.get("trigger")
        if not isinstance(trigger, dict) or set(trigger) != {"type", "time", "days"}:
            return False, "Déclencheur de planification invalide."
        if trigger.get("type") != "weekly":
            return False, "Seul le déclencheur hebdomadaire local est autorisé."
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", str(trigger.get("time", ""))):
            return False, "Heure de planification invalide."
        days = trigger.get("days")
        if not isinstance(days, list) or not days or any(not isinstance(day, int) or day < 0 or day > 6 for day in days):
            return False, "Jours de planification invalides."
        scheduled_target = str(params.get("scheduled_target", "")).strip().lower()
        if target == "routine" and not re.fullmatch(r"[a-z0-9_-]+", scheduled_target):
            return False, "Routine planifiée invalide."
        if target in {"briefing", "habit_summary"} and scheduled_target != "today":
            return False, "Cible de planification invalide."
        return True, None

    if params not in (None, {}):
        return False, "Paramètres supplémentaires interdits."
    if not (target.isdigit() or re.fullmatch(r"p-[0-9a-f]{8}", target)):
        return False, "Référence de planification invalide."
    return True, None


def validate_action(action_data):
    action = ""
    if isinstance(action_data, dict):
        action = str(action_data.get("action", "")).strip().lower()
    if action in SCHEDULE_ACTIONS:
        return _validate_schedule_contract(action_data)
    return _validate_action_before_scheduler_v121(action_data)


def _verify_explicit_schedule_action(user_message, action_data):
    if not isinstance(user_message, str) or not user_message.strip():
        return False, "Une commande utilisateur explicite est requise."
    try:
        proof = deterministic_proof_interpret(user_message)
    except Exception:
        return False, "Impossible de vérifier localement la planification."
    wanted = _canonical_contract_value(action_data)
    for candidate in proof.get("actions", []) if isinstance(proof, dict) else []:
        if _canonical_contract_value(candidate) == wanted:
            return True, None
    return False, "Planification refusée : la demande ne correspond pas exactement à l'action autorisée."


def execute_action(action_data, user_message=None):
    action = ""
    if isinstance(action_data, dict):
        action = str(action_data.get("action", "")).strip().lower()
    if action not in SCHEDULE_ACTIONS:
        return _execute_action_before_scheduler_v121(action_data, user_message=user_message)

    valid, error = validate_action(action_data)
    if not valid:
        return False, error
    explicit, proof_error = _verify_explicit_schedule_action(user_message, action_data)
    if not explicit:
        return False, proof_error

    target = str(action_data.get("target", "")).strip().lower()
    params = action_data.get("params") or {}

    if action == "list_schedules":
        return True, scheduler_format_schedule_list()

    if action == "create_schedule_draft":
        try:
            item = scheduler_create_draft(
                params["kind"],
                params["scheduled_target"],
                params["trigger"],
            )
        except Exception as exc:
            return False, f"Impossible de préparer cette planification : {exc}"
        detail = scheduler_format_schedule(item)
        return True, (
            "Brouillon de planification créé, mais encore désactivé.\n"
            f"{detail}\n\n"
            f"Pour l'activer, dis : « confirme la planification {item['id']} »."
        )

    schedule_id = scheduler_resolve_schedule_ref(target)
    if not schedule_id:
        return False, "Planification introuvable. Utilise « liste mes planifications » pour voir les identifiants."
    if action == "confirm_schedule":
        return scheduler_confirm_schedule(schedule_id)
    if action == "enable_schedule":
        return scheduler_set_enabled(schedule_id, True)
    if action == "disable_schedule":
        return scheduler_set_enabled(schedule_id, False)
    if action == "delete_schedule":
        return scheduler_delete_schedule(schedule_id)

    return False, "Action de planification non implémentée."


# ============================================================
# DEMARRAGE
# ============================================================

if __name__ == "__main__":
    main()
