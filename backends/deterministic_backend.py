import json
import re
import unicodedata
from pathlib import Path


# ============================================================
# VERSION
# ============================================================

SCHEMA_VERSION = 1


# ============================================================
# CHEMINS
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]

SITES_FILE = (
    ROOT_DIR
    / "config"
    / "sites.json"
)

ROUTINES_FILE = (
    ROOT_DIR
    / "config"
    / "routines.json"
)


# ============================================================
# APPLICATIONS
# ============================================================

APPLICATION_ALIASES = {
    # Edge
    "edge": "edge",
    "microsoft edge": "edge",
    "ms edge": "edge",

    # VS Code
    "vscode": "vscode",
    "vs code": "vscode",
    "visual studio code": "vscode",
    "code": "vscode",

    # Explorateur Windows
    "explorateur": "explorer",
    "explorateur de fichiers": "explorer",
    "explorateur de fichier": "explorer",
    "explorateur windows": "explorer",

    "l'explorateur": "explorer",
    "l'explorateur de fichiers": "explorer",
    "l'explorateur de fichier": "explorer",

    "mes fichiers": "explorer",
    "fichiers": "explorer",

    "explorer": "explorer",
    "file explorer": "explorer",
    "windows explorer": "explorer",
}


# ============================================================
# DOSSIERS UTILISATEUR
# ============================================================

FILE_ROOT_ALIASES = {
    # Bureau
    "bureau": "desktop",
    "mon bureau": "desktop",
    "desktop": "desktop",

    # Documents
    "document": "documents",
    "documents": "documents",
    "mes documents": "documents",

    # Téléchargements
    "telechargement": "downloads",
    "telechargements": "downloads",
    "mes telechargements": "downloads",
    "download": "downloads",
    "downloads": "downloads",

    # Images
    "image": "pictures",
    "images": "pictures",
    "mes images": "pictures",
    "photo": "pictures",
    "photos": "pictures",
    "mes photos": "pictures",
    "picture": "pictures",
    "pictures": "pictures",

    # Vidéos
    "video": "videos",
    "videos": "videos",
    "mes videos": "videos",

    # Musique
    "musique": "music",
    "musiques": "music",
    "ma musique": "music",
    "mes musiques": "music",
    "music": "music",
}


# ============================================================
# SITES
# ============================================================

WEBSITE_ALIASES = {
    "teams": "teams",
    "microsoft teams": "teams",
    "ms teams": "teams",

    "outlook": "outlook",
    "microsoft outlook": "outlook",

    "outlook perso": "outlook-perso",
    "outlook personnel": "outlook-perso",

    "onedrive": "onedrive",
    "one drive": "onedrive",

    "microsoft 365": "microsoft365",
    "office 365": "microsoft365",
    "m365": "microsoft365",

    "office": "office",

    "word": "word",
    "excel": "excel",

    "powerpoint": "powerpoint",
    "power point": "powerpoint",

    "onenote": "onenote",
    "one note": "onenote",

    "microsoft forms": "microsoftforms",

    "todo": "todo",
    "to do": "todo",

    "planner": "planner",
    "copilot": "copilot",

    "gmail": "gmail",

    "google drive": "googledrive",
    "drive": "googledrive",

    "google docs": "docs",
    "docs": "docs",

    "google sheets": "sheets",
    "sheets": "sheets",

    "google slides": "slides",
    "slides": "slides",

    "google meet": "meet",
    "meet": "meet",

    "google calendar": "calendar",
    "google chat": "googlechat",
    "google forms": "googleforms",
    "google contacts": "contacts",
    "google keep": "keep",

    "google classroom": "classroom",
    "classroom": "classroom",

    "google photos": "photos",
    "google maps": "maps",
    "google translate": "translate",

    "gemini": "gemini",
    "google gemini": "gemini",

    "github": "github",

    "chatgpt": "chatgpt",
    "chat gpt": "chatgpt",

    "youtube": "youtube",

    "whatsapp": "whatsapp",
    "whats app": "whatsapp",

    "udmci": "udmci",
}


# ============================================================
# NORMALISATION
# ============================================================

def remove_accents(text):

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


def normalize_text(text):

    if not isinstance(
        text,
        str
    ):
        return ""

    text = (
        text
        .lower()
        .strip()
    )

    text = remove_accents(
        text
    )

    text = text.replace(
        "’",
        "'"
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# ACTION
# ============================================================

def make_action(
    action,
    target,
    params=None
):

    result = {
        "schema_version": SCHEMA_VERSION,
        "action": action,
        "target": str(
            target
        ),
    }

    if params is not None:

        result[
            "params"
        ] = params

    return result


# ============================================================
# SITES CONFIGURES
# ============================================================

def load_site_names():

    if not SITES_FILE.exists():
        return set()

    try:

        with open(
            SITES_FILE,
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

        return set()

    websites = data.get(
        "websites",
        {}
    )

    if not isinstance(
        websites,
        dict
    ):

        return set()

    names = set()

    for name, config in websites.items():

        if not isinstance(
            config,
            dict
        ):
            continue

        if not config.get(
            "enabled",
            False
        ):
            continue

        normalized = normalize_text(
            name
        )

        if normalized:

            names.add(
                normalized
            )

    return names


# ============================================================
# ROUTINES
# ============================================================

def load_routine_triggers():

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

    except (
        OSError,
        json.JSONDecodeError
    ):

        return {}

    routines = data.get(
        "routines",
        {}
    )

    if not isinstance(
        routines,
        dict
    ):

        return {}

    trigger_map = {}

    for routine_id, routine in routines.items():

        if not isinstance(
            routine,
            dict
        ):
            continue

        if not routine.get(
            "enabled",
            False
        ):
            continue

        if not routine.get(
            "confirmed",
            False
        ):
            continue

        triggers = routine.get(
            "triggers",
            []
        )

        if not isinstance(
            triggers,
            list
        ):
            continue

        for trigger in triggers:

            if not isinstance(
                trigger,
                str
            ):
                continue

            normalized = normalize_text(
                trigger
            )

            if normalized:

                trigger_map[
                    normalized
                ] = (
                    routine_id
                    .lower()
                    .strip()
                )

    return trigger_map


# ============================================================
# NORMALISATION DES CIBLES
# ============================================================

def normalize_application_target(
    value
):

    return APPLICATION_ALIASES.get(
        normalize_text(
            value
        )
    )


def normalize_file_root(
    value
):

    return FILE_ROOT_ALIASES.get(
        normalize_text(
            value
        )
    )


def normalize_website_target(
    value
):

    value = normalize_text(
        value
    )

    if not value:
        return None

    alias = WEBSITE_ALIASES.get(
        value
    )

    if alias:
        return alias

    if value in load_site_names():
        return value

    if re.fullmatch(
        r"[a-z0-9][a-z0-9.-]*\.[a-z]{2,63}",
        value
    ):

        return value

    if re.fullmatch(
        r"[a-z0-9][a-z0-9-]{0,62}",
        value
    ):

        return value

    return None


def resolve_learnable_target(
    value
):

    application = (
        normalize_application_target(
            value
        )
    )

    if application:

        return (
            "open_application",
            application
        )

    website = (
        normalize_website_target(
            value
        )
    )

    if website:

        return (
            "open_website",
            website
        )

    return (
        None,
        None
    )


# ============================================================
# HABITUDES
# ============================================================

def parse_habit_command(
    user_message
):

    text = normalize_text(
        user_message
    )

    # --------------------------------------------------------
    # Liste
    # --------------------------------------------------------

    if text in {
        "affiche mes habitudes",
        "afficher mes habitudes",
        "montre mes habitudes",
        "liste mes habitudes",
        "voir mes habitudes",
        "mes habitudes",
    }:

        return [
            make_action(
                "list_habits",
                "pending"
            )
        ]

    # --------------------------------------------------------
    # Confirmer
    # --------------------------------------------------------

    confirm_patterns = [
        (
            r"^(?:confirme|confirmer|valide|valider) "
            r"la modification de l'?habitude (\d+)$"
        ),
        (
            r"^(?:confirme|confirmer|valide|valider) "
            r"le brouillon de l'?habitude (\d+)$"
        ),
    ]

    for pattern in confirm_patterns:

        match = re.fullmatch(
            pattern,
            text
        )

        if match:

            return [
                make_action(
                    "confirm_habit_draft",
                    match.group(1)
                )
            ]

    # --------------------------------------------------------
    # Afficher brouillon
    # --------------------------------------------------------

    match = re.fullmatch(
        (
            r"(?:affiche|afficher|montre|montrer|voir) "
            r"le brouillon de l'?habitude (\d+)"
        ),
        text
    )

    if match:

        return [
            make_action(
                "show_habit_draft",
                match.group(1)
            )
        ]

    # --------------------------------------------------------
    # Annuler
    # --------------------------------------------------------

    match = re.fullmatch(
        (
            r"(?:annule|annuler) "
            r"la modification de l'?habitude (\d+)"
        ),
        text
    )

    if match:

        return [
            make_action(
                "cancel_habit_draft",
                match.group(1)
            )
        ]

    # --------------------------------------------------------
    # Renommer
    # --------------------------------------------------------

    rename_match = re.match(
        (
            r"^\s*(?:renomme|renommer)\s+"
            r"l[’']?habitude\s+"
            r"(\d+)\s+en\s+"
            r"(.+?)\s*$"
        ),
        user_message,
        flags=re.IGNORECASE
    )

    if rename_match:

        return [
            make_action(
                "rename_habit_draft",
                rename_match.group(1),
                {
                    "name": (
                        rename_match
                        .group(2)
                        .strip()
                    )
                }
            )
        ]

    # --------------------------------------------------------
    # Changer nom
    # --------------------------------------------------------

    rename_match = re.match(
        (
            r"^\s*(?:change|changer)\s+"
            r"le\s+nom\s+de\s+"
            r"l[’']?habitude\s+"
            r"(\d+)\s+en\s+"
            r"(.+?)\s*$"
        ),
        user_message,
        flags=re.IGNORECASE
    )

    if rename_match:

        return [
            make_action(
                "rename_habit_draft",
                rename_match.group(1),
                {
                    "name": (
                        rename_match
                        .group(2)
                        .strip()
                    )
                }
            )
        ]

    # --------------------------------------------------------
    # Déclencheur
    # --------------------------------------------------------

    trigger_match = re.match(
        (
            r"^\s*(?:change|changer|modifie|modifier)\s+"
            r"le\s+d[ée]clencheur\s+de\s+"
            r"l[’']?habitude\s+"
            r"(\d+)\s+en\s+"
            r"(.+?)\s*$"
        ),
        user_message,
        flags=re.IGNORECASE
    )

    if trigger_match:

        return [
            make_action(
                "set_habit_draft_trigger",
                trigger_match.group(1),
                {
                    "trigger": (
                        trigger_match
                        .group(2)
                        .strip()
                    )
                }
            )
        ]

    # --------------------------------------------------------
    # Ajouter action
    # --------------------------------------------------------

    add_match = re.match(
        (
            r"^\s*(?:ajoute|ajouter)\s+"
            r"(.+?)\s+[àa]\s+"
            r"l[’']?habitude\s+"
            r"(\d+)\s*$"
        ),
        user_message,
        flags=re.IGNORECASE
    )

    if add_match:

        raw_target = (
            add_match
            .group(1)
            .strip()
        )

        habit_id = (
            add_match
            .group(2)
        )

        action, target = (
            resolve_learnable_target(
                raw_target
            )
        )

        if action and target:

            return [
                make_action(
                    "add_habit_draft_action",
                    habit_id,
                    {
                        "action": action,
                        "target": target,
                    }
                )
            ]

    # --------------------------------------------------------
    # Retirer action
    # --------------------------------------------------------

    remove_match = re.match(
        (
            r"^\s*(?:retire|retirer|supprime|supprimer)\s+"
            r"(.+?)\s+de\s+"
            r"l[’']?habitude\s+"
            r"(\d+)\s*$"
        ),
        user_message,
        flags=re.IGNORECASE
    )

    if remove_match:

        raw_target = (
            remove_match
            .group(1)
            .strip()
        )

        habit_id = (
            remove_match
            .group(2)
        )

        action, target = (
            resolve_learnable_target(
                raw_target
            )
        )

        if action and target:

            return [
                make_action(
                    "remove_habit_draft_action",
                    habit_id,
                    {
                        "action": action,
                        "target": target,
                    }
                )
            ]

    # --------------------------------------------------------
    # Modifier
    # --------------------------------------------------------

    for pattern in [
        r"^(?:modifie|modifier) l'?habitude (\d+)$",
        r"^(?:modifie|modifier) habitude (\d+)$",
        r"^(?:edite|editer) l'?habitude (\d+)$",
    ]:

        match = re.fullmatch(
            pattern,
            text
        )

        if match:

            return [
                make_action(
                    "modify_habit",
                    match.group(1)
                )
            ]

    # --------------------------------------------------------
    # Accepter
    # --------------------------------------------------------

    for pattern in [
        r"^(?:accepte|accepter) l'?habitude (\d+)$",
        r"^(?:accepte|accepter) habitude (\d+)$",
    ]:

        match = re.fullmatch(
            pattern,
            text
        )

        if match:

            return [
                make_action(
                    "accept_habit",
                    match.group(1)
                )
            ]

    # --------------------------------------------------------
    # Refuser
    # --------------------------------------------------------

    for pattern in [
        r"^(?:refuse|refuser) l'?habitude (\d+)$",
        r"^(?:refuse|refuser) habitude (\d+)$",
    ]:

        match = re.fullmatch(
            pattern,
            text
        )

        if match:

            return [
                make_action(
                    "reject_habit",
                    match.group(1)
                )
            ]

    return []


# ============================================================
# ROUTINE
# ============================================================

def parse_run_routine(
    text
):

    routine_id = (
        load_routine_triggers()
        .get(
            text
        )
    )

    if not routine_id:
        return []

    return [
        make_action(
            "run_routine",
            routine_id
        )
    ]


# ============================================================
# VERIFICATION APPLICATION
# ============================================================

def parse_check_application(
    text
):

    patterns = [
        r"^verifie si (.+?) est ouvert$",
        r"^verifie si (.+?) est ouverte$",
        r"^verifie (.+)$",
        r"^est ce que (.+?) est ouvert$",
        r"^est ce que (.+?) est ouverte$",
    ]

    for pattern in patterns:

        match = re.fullmatch(
            pattern,
            text
        )

        if not match:
            continue

        target = (
            normalize_application_target(
                match.group(1)
            )
        )

        if target:

            return [
                make_action(
                    "check_application",
                    target
                )
            ]

    return []


# ============================================================
# PLUSIEURS CIBLES
# ============================================================

def split_targets(
    value
):

    value = normalize_text(
        value
    )

    value = value.replace(
        " et ",
        ","
    )

    value = value.replace(
        " + ",
        ","
    )

    value = value.replace(
        ";",
        ","
    )

    return [
        item
        .strip()
        .strip(".!?")
        for item in value.split(",")
        if item.strip()
    ]


# ============================================================
# LISTER UN DOSSIER
# ============================================================

def parse_list_directory(
    user_message
):

    text = normalize_text(
        user_message
    )

    patterns = [
        r"^(?:liste|lister) (.+)$",
        r"^(?:affiche|afficher) (.+)$",
        r"^(?:montre|montrer) (.+)$",
        r"^voir (.+)$",
    ]

    for pattern in patterns:

        match = re.fullmatch(
            pattern,
            text
        )

        if not match:
            continue

        raw_target = (
            match
            .group(1)
            .strip()
        )

        for prefix in [
            "le contenu de ",
            "le contenu du ",
            "le contenu des ",
        ]:

            if raw_target.startswith(
                prefix
            ):

                raw_target = (
                    raw_target[
                        len(prefix):
                    ]
                    .strip()
                )

                break

        target = normalize_file_root(
            raw_target
        )

        if target:

            return [
                make_action(
                    "list_directory",
                    target
                )
            ]

    return []


# ============================================================
# CREER UN DOSSIER
# ============================================================

def parse_create_folder(
    user_message
):

    root_pattern = (
        r"bureau|desktop|"
        r"documents?|"
        r"téléchargements?|telechargements?|downloads?|"
        r"images?|photos?|pictures?|"
        r"vidéos?|videos?|"
        r"musiques?|music"
    )

    pattern = (
        r"^\s*"
        r"(?:crée|cree|créer|creer)"
        r"\s+"
        r"(?:(?:un|le)\s+)?"
        r"dossier"
        r"\s+"
        r"(.+?)"
        r"\s+dans\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"("
        + root_pattern
        + r")"
        r"\s*[.!?]?\s*$"
    )

    match = re.fullmatch(
        pattern,
        user_message,
        flags=re.IGNORECASE
    )

    if not match:
        return []

    folder_name = (
        match
        .group(1)
        .strip()
    )

    root_name = (
        normalize_file_root(
            match.group(2)
        )
    )

    if not folder_name:
        return []

    if not root_name:
        return []

    return [
        make_action(
            "create_folder",
            root_name,
            {
                "name": folder_name
            }
        )
    ]


# ============================================================
# DEPLACER ENTRE RACINES
# ============================================================

def parse_move_file_between_roots(
    user_message
):

    root_pattern = (
        r"bureau|desktop|"
        r"documents?|"
        r"téléchargements?|telechargements?|downloads?|"
        r"images?|photos?|pictures?|"
        r"vidéos?|videos?|"
        r"musiques?|music"
    )

    # ========================================================
    # AVEC SOUS-DOSSIER
    # ========================================================

    pattern_with_folder = (
        r"^\s*"
        r"(?:déplace|deplace|déplacer|deplacer)"
        r"\s+"
        r"(?:(?:le|la)\s+fichier\s+)?"
        r"(.+?)"
        r"\s+"
        r"(?:de|du|des)"
        r"\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"("
        + root_pattern
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
        + root_pattern
        + r")"
        r"\s*[.!?]?\s*$"
    )

    match = re.fullmatch(
        pattern_with_folder,
        user_message,
        flags=re.IGNORECASE
    )

    if match:

        file_name = (
            match
            .group(1)
            .strip()
        )

        source_root = (
            normalize_file_root(
                match.group(2)
            )
        )

        destination_folder = (
            match
            .group(3)
            .strip()
        )

        destination_root = (
            normalize_file_root(
                match.group(4)
            )
        )

        if (
            file_name
            and
            source_root
            and
            destination_folder
            and
            destination_root
            and
            source_root != destination_root
        ):

            return [
                make_action(
                    "move_file_between_roots",
                    source_root,
                    {
                        "source_root": source_root,
                        "destination_root": destination_root,
                        "file_name": file_name,
                        "destination_folder": destination_folder,
                    }
                )
            ]

    # ========================================================
    # DIRECTEMENT VERS UNE AUTRE RACINE
    # ========================================================

    pattern_direct = (
        r"^\s*"
        r"(?:déplace|deplace|déplacer|deplacer)"
        r"\s+"
        r"(?:(?:le|la)\s+fichier\s+)?"
        r"(.+?)"
        r"\s+"
        r"(?:de|du|des)"
        r"\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"("
        + root_pattern
        + r")"
        r"\s+"
        r"(?:vers|dans)"
        r"\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"("
        + root_pattern
        + r")"
        r"\s*[.!?]?\s*$"
    )

    match = re.fullmatch(
        pattern_direct,
        user_message,
        flags=re.IGNORECASE
    )

    if not match:
        return []

    file_name = (
        match
        .group(1)
        .strip()
    )

    source_root = (
        normalize_file_root(
            match.group(2)
        )
    )

    destination_root = (
        normalize_file_root(
            match.group(3)
        )
    )

    if not file_name:
        return []

    if not source_root:
        return []

    if not destination_root:
        return []

    if source_root == destination_root:
        return []

    return [
        make_action(
            "move_file_between_roots",
            source_root,
            {
                "source_root": source_root,
                "destination_root": destination_root,
                "file_name": file_name,
                "destination_folder": None,
            }
        )
    ]


# ============================================================
# DEPLACEMENT INTERNE DANS DOCUMENTS
# ============================================================

def parse_move_file(
    user_message
):

    pattern = (
        r"^\s*"
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
        user_message,
        flags=re.IGNORECASE
    )

    if not match:
        return []

    file_name = (
        match
        .group(1)
        .strip()
    )

    destination_folder = (
        match
        .group(2)
        .strip()
    )

    if not file_name:
        return []

    if not destination_folder:
        return []

    # Ne pas confondre avec un déplacement
    # vers une racine utilisateur.
    if normalize_file_root(
        destination_folder
    ):
        return []

    return [
        make_action(
            "move_file_within_root",
            "documents",
            {
                "file_name": file_name,
                "destination_folder": destination_folder,
            }
        )
    ]


# ============================================================
# OUVERTURE
# ============================================================

def parse_open(
    text
):

    prefixes = [
        "ouvre ",
        "ouvrir ",
        "lance ",
        "lancer ",
        "demarre ",
        "demarrer ",
        "va sur ",
        "aller sur ",
    ]

    content = None

    for prefix in prefixes:

        if text.startswith(
            prefix
        ):

            content = (
                text[
                    len(prefix):
                ]
                .strip()
            )

            break

    if not content:
        return []

    for prefix in [
        "le site ",
        "site ",
        "l'application ",
        "application ",
        "appli ",
    ]:

        if content.startswith(
            prefix
        ):

            content = (
                content[
                    len(prefix):
                ]
                .strip()
            )

            break

    actions = []

    seen = set()

    for raw_target in split_targets(
        content
    ):

        action, target = (
            resolve_learnable_target(
                raw_target
            )
        )

        if not action:
            continue

        key = (
            action,
            target
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        actions.append(
            make_action(
                action,
                target
            )
        )

    return actions


# ============================================================
# INTERPRETATION
# ============================================================

def interpret(
    user_message
):

    text = normalize_text(
        user_message
    )

    if not text:

        return {
            "schema_version": SCHEMA_VERSION,
            "backend": "deterministic",
            "understood": False,
            "actions": [],
        }

    # --------------------------------------------------------
    # Habitudes
    # --------------------------------------------------------

    actions = parse_habit_command(
        user_message
    )

    # --------------------------------------------------------
    # Routines
    # --------------------------------------------------------

    if not actions:

        actions = parse_run_routine(
            text
        )

    # --------------------------------------------------------
    # Vérification application
    # --------------------------------------------------------

    if not actions:

        actions = parse_check_application(
            text
        )

    # --------------------------------------------------------
    # Création dossier
    # --------------------------------------------------------

    if not actions:

        actions = parse_create_folder(
            user_message
        )

    # --------------------------------------------------------
    # Liste dossier
    # --------------------------------------------------------

    if not actions:

        actions = parse_list_directory(
            user_message
        )

    # --------------------------------------------------------
    # Déplacement entre racines
    # --------------------------------------------------------

    if not actions:

        actions = parse_move_file_between_roots(
            user_message
        )

    # --------------------------------------------------------
    # Déplacement interne Documents
    # --------------------------------------------------------

    if not actions:

        actions = parse_move_file(
            user_message
        )

    # --------------------------------------------------------
    # Application / site
    # --------------------------------------------------------

    if not actions:

        actions = parse_open(
            text
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "backend": "deterministic",
        "understood": bool(
            actions
        ),
        "actions": actions,
    }


# ============================================================
# TEST
# ============================================================

def main():

    print()

    print(
        "BACKEND DETERMINISTE - AgentLocal"
    )

    print(
        "Interprétation uniquement."
    )

    print()

    while True:

        try:

            message = input(
                "Vous > "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError
        ):

            break

        if message.lower() in {
            "quit",
            "exit",
            "quitter",
            "stop",
        }:

            break

        print(
            json.dumps(
                interpret(
                    message
                ),
                ensure_ascii=False,
                indent=2
            )
        )


if __name__ == "__main__":

    main()