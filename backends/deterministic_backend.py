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

    # Android Studio
    "android studio": "android_studio",
    "androidstudio": "android_studio",

    # Bloc-notes
    "bloc notes": "notepad",
    "bloc-notes": "notepad",
    "bloc note": "notepad",
    "notepad": "notepad",

    # Calculatrice
    "calculatrice": "calculator",
    "calculator": "calculator",
    "calc": "calculator",

    # Paint
    "paint": "paint",
    "microsoft paint": "paint",

    # Outil Capture
    "outil capture": "snipping_tool",
    "outil de capture": "snipping_tool",
    "outil capture d'ecran": "snipping_tool",
    "capture d'ecran": "snipping_tool",
    "snipping tool": "snipping_tool",

    # Photos
    "photos": "photos",
    "microsoft photos": "photos",
    "application photos": "photos",

    # Lecteur multimédia
    "lecteur multimedia": "media_player",
    "lecteur media": "media_player",
    "media player": "media_player",
    "windows media player": "media_player",

    # Caméra
    "camera": "camera",
    "camera windows": "camera",

    # Horloge
    "horloge": "clock",
    "clock": "clock",

    # Enregistreur audio
    "enregistreur audio": "sound_recorder",
    "magnetophone": "sound_recorder",
    "sound recorder": "sound_recorder",
    "voice recorder": "sound_recorder",

    # Pense-bêtes
    "pense betes": "sticky_notes",
    "pense-betes": "sticky_notes",
    "sticky notes": "sticky_notes",

    # Clipchamp
    "clipchamp": "clipchamp",

    # Mobile connecté
    "mobile connecte": "phone_link",
    "phone link": "phone_link",
    "votre telephone": "phone_link",
    "your phone": "phone_link",

    # Teams
    "teams": "teams",
    "microsoft teams": "teams",
    "ms teams": "teams",

    # Microsoft Office
    "word": "word",
    "microsoft word": "word",

    "excel": "excel",
    "microsoft excel": "excel",

    "powerpoint": "powerpoint",
    "power point": "powerpoint",
    "microsoft powerpoint": "powerpoint",

    "outlook": "outlook",
    "microsoft outlook": "outlook",

    "onenote": "onenote",
    "one note": "onenote",
    "microsoft onenote": "onenote",
}


# ============================================================
# APPLICATIONS POUVANT ETRE APPRISES
# ============================================================

CORE_LEARNABLE_APPLICATIONS = {
    "edge",
    "vscode",
    "explorer",
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
# SECURITE DES NOMS DE FICHIERS
# ============================================================

WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


MASS_DELETE_TERMS = {
    "tout",
    "tous",
    "toutes",
    "tout le contenu",
    "tous les fichiers",
    "toutes les fichiers",
    "tous les documents",
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


MASS_READ_TERMS = set(MASS_DELETE_TERMS)
MASS_COPY_TERMS = set(MASS_DELETE_TERMS)


WRITABLE_TEXT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".tsv", ".json",
    ".xml", ".yaml", ".yml", ".log", ".ini",
    ".cfg", ".conf", ".toml", ".ics", ".vcf",
    ".html", ".htm", ".rtf", ".eml",
}


def is_safe_simple_file_name(
    value
):
    """
    Filtre syntaxique de défense en profondeur.

    La validation finale reste effectuée par agent.py
    puis file_tools.py.
    """

    if not isinstance(
        value,
        str
    ):
        return False

    value = value.strip()

    if not value:
        return False

    if len(value) > 180:
        return False

    # --------------------------------------------------------
    # Aucun chemin
    # --------------------------------------------------------

    if (
        "/" in value
        or
        "\\" in value
    ):
        return False

    # --------------------------------------------------------
    # Pas de traversée
    # --------------------------------------------------------

    if value in {
        ".",
        "..",
    }:
        return False

    if ".." in value:
        return False

    # --------------------------------------------------------
    # Aucun joker
    # --------------------------------------------------------

    if (
        "*" in value
        or
        "?" in value
    ):
        return False

    # --------------------------------------------------------
    # Caractères Windows interdits
    # ':' bloque également les ADS.
    # --------------------------------------------------------

    if re.search(
        r'[<>:"/\\|?*\x00-\x1f]',
        value
    ):
        return False

    if (
        value.endswith(" ")
        or
        value.endswith(".")
    ):
        return False

    base_name = (
        value
        .split(".")[0]
        .upper()
    )

    if base_name in WINDOWS_RESERVED_NAMES:
        return False

    return True


def get_extension_chain(
    file_name
):
    """
    Exemple :

        archive.tar.gz
        -> .tar.gz
    """

    try:

        return "".join(
            suffix.casefold()
            for suffix in Path(
                file_name
            ).suffixes
        )

    except TypeError:

        return ""


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


def normalize_text(
    text
):

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

    # --------------------------------------------------------
    # Sites présents dans sites.json.
    #
    # Descript reste donc supporté s'il est présent
    # et activé dans sites.json.
    # --------------------------------------------------------

    if value in load_site_names():

        return value

    # --------------------------------------------------------
    # Domaine explicite
    # --------------------------------------------------------

    if re.fullmatch(
        r"[a-z0-9][a-z0-9.-]*\.[a-z]{2,63}",
        value
    ):

        return value

    # --------------------------------------------------------
    # Nom de site simple
    # --------------------------------------------------------

    if re.fullmatch(
        r"[a-z0-9][a-z0-9-]{0,62}",
        value
    ):

        return value

    return None


# ============================================================
# RESOLUTION OUVERTURE
# ============================================================

def resolve_open_target(
    value,
    forced_kind=None
):
    """
    Résout une cible pour une ouverture manuelle.

    forced_kind :

        application
            application locale uniquement

        website
            site uniquement

        None
            application d'abord, puis site
    """

    # ========================================================
    # APPLICATION FORCEE
    # ========================================================

    if forced_kind == "application":

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

        return (
            None,
            None
        )

    # ========================================================
    # SITE FORCE
    # ========================================================

    if forced_kind == "website":

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

    # ========================================================
    # APPLICATION EN PRIORITE
    # ========================================================

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

    # ========================================================
    # SITE
    # ========================================================

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
# CIBLES APPRENABLES
# ============================================================

def resolve_learnable_target(
    value
):
    """
    Les applications étendues restent manuelles.

    Seules Edge, VS Code et l'Explorateur
    peuvent être ajoutés automatiquement
    à une habitude.

    Les sites restent apprenables.
    """

    application = (
        normalize_application_target(
            value
        )
    )

    if (
        application
        and
        application in CORE_LEARNABLE_APPLICATIONS
    ):

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
    # Renommer habitude
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
# COPIER ENTRE RACINES
# ============================================================

def parse_copy_file_between_roots(
    user_message
):
    """
    Interprète la copie explicite d'UN fichier entre deux
    racines utilisateur autorisées.

    Formes acceptées :
        copie rapport.pdf de Documents vers Bureau
        copier rapport.pdf de Documents vers Téléchargements
        copie rapport.pdf de Documents vers le dossier Archives dans Bureau

    Aucun chemin arbitraire, joker ou copie de masse n'est accepté.
    """

    root_pattern = (
        r"bureau|desktop|"
        r"documents?|"
        r"téléchargements?|telechargements?|downloads?|"
        r"images?|photos?|pictures?|"
        r"vidéos?|videos?|"
        r"musiques?|music"
    )

    # ========================================================
    # AVEC SOUS-DOSSIER DESTINATION
    # ========================================================

    pattern_with_folder = (
        r"^\s*"
        r"(?:copie|copier)"
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

        source_root = normalize_file_root(
            match.group(2)
        )

        destination_folder = (
            match
            .group(3)
            .strip()
        )

        destination_root = normalize_file_root(
            match.group(4)
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
            and
            is_safe_simple_file_name(file_name)
            and
            is_safe_simple_file_name(destination_folder)
            and
            normalize_text(file_name) not in MASS_COPY_TERMS
        ):
            return [
                make_action(
                    "copy_file_between_roots",
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
        r"(?:copie|copier)"
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

    source_root = normalize_file_root(
        match.group(2)
    )

    destination_root = normalize_file_root(
        match.group(3)
    )

    if not file_name:
        return []

    if not source_root:
        return []

    if not destination_root:
        return []

    if source_root == destination_root:
        return []

    if not is_safe_simple_file_name(
        file_name
    ):
        return []

    if normalize_text(
        file_name
    ) in MASS_COPY_TERMS:
        return []

    return [
        make_action(
            "copy_file_between_roots",
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

    # --------------------------------------------------------
    # Ne pas confondre avec une racine utilisateur.
    # --------------------------------------------------------

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
# RENOMMER UN FICHIER
# ============================================================

def parse_rename_file(
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
        r"(?:renomme|renommer)"
        r"\s+"
        r"(?:(?:le|la)\s+fichier\s+)?"
        r"(.+?)"
        r"\s+en\s+"
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

    old_name = (
        match
        .group(1)
        .strip()
    )

    new_name = (
        match
        .group(2)
        .strip()
    )

    root_name = (
        normalize_file_root(
            match.group(3)
        )
    )

    if not root_name:

        return []

    # --------------------------------------------------------
    # Noms simples uniquement
    # --------------------------------------------------------

    if not is_safe_simple_file_name(
        old_name
    ):

        return []

    if not is_safe_simple_file_name(
        new_name
    ):

        return []

    # --------------------------------------------------------
    # Même nom ou simple changement de casse
    # --------------------------------------------------------

    if (
        old_name.casefold()
        ==
        new_name.casefold()
    ):

        return []

    # --------------------------------------------------------
    # Aucun changement d'extension
    # --------------------------------------------------------

    if (
        get_extension_chain(
            old_name
        )
        !=
        get_extension_chain(
            new_name
        )
    ):

        return []

    return [
        make_action(
            "rename_file",
            root_name,
            {
                "old_name": old_name,
                "new_name": new_name,
            }
        )
    ]


# ============================================================
# SUPPRIMER UN FICHIER
# ============================================================

def parse_delete_file(
    user_message
):
    """
    Interprète uniquement une suppression de fichier
    explicitement rattachée à une racine utilisateur.

    L'exécution réelle correspond uniquement
    à un envoi vers la Corbeille Windows.
    """

    normalized = normalize_text(
        user_message
    )

    # ========================================================
    # INTENTIONS INTERDITES
    # ========================================================

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
        fragment in normalized
        for fragment in forbidden_fragments
    ):

        return []

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
        r"(?:supprime|supprimer)"
        r"\s+"
        r"(?:(?:le|la)\s+fichier\s+)?"
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

    root_name = (
        normalize_file_root(
            match.group(2)
        )
    )

    if not root_name:

        return []

    # ========================================================
    # NOM SIMPLE UNIQUEMENT
    # ========================================================

    if not is_safe_simple_file_name(
        file_name
    ):

        return []

    # ========================================================
    # AUCUNE FORMULATION DE MASSE
    # ========================================================

    if normalize_text(
        file_name
    ) in MASS_DELETE_TERMS:

        return []

    return [
        make_action(
            "delete_file",
            root_name,
            {
                "file_name": file_name
            }
        )
    ]


# ============================================================
# LIRE LE CONTENU D'UN FICHIER
# ============================================================

def parse_read_file_content(
    user_message
):
    """
    Interprète uniquement la lecture explicite d'UN fichier
    situé directement dans une racine utilisateur autorisée.

    Formes acceptées :
        lis rapport.txt dans Documents
        lis le fichier rapport.txt dans Documents
        lire notes.md dans Bureau
        affiche le contenu de config.json dans Téléchargements

    La validation des extensions, de la taille, de l'encodage
    et du contenu binaire reste assurée par file_tools.py.
    """

    root_pattern = (
        r"bureau|desktop|"
        r"documents?|"
        r"téléchargements?|telechargements?|downloads?|"
        r"images?|photos?|pictures?|"
        r"vidéos?|videos?|"
        r"musiques?|music"
    )

    patterns = [
        (
            r"^\s*"
            r"(?:lis|lire)"
            r"\s+"
            r"(?:(?:le|la)\s+fichier\s+)?"
            r"(.+?)"
            r"\s+dans\s+"
            r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
            r"(" + root_pattern + r")"
            r"\s*[.!?]?\s*$"
        ),
        (
            r"^\s*"
            r"(?:affiche|afficher|montre|montrer)"
            r"\s+le\s+contenu\s+(?:de|du)\s+"
            r"(.+?)"
            r"\s+dans\s+"
            r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
            r"(" + root_pattern + r")"
            r"\s*[.!?]?\s*$"
        ),
    ]

    match = None

    for pattern in patterns:

        match = re.fullmatch(
            pattern,
            user_message,
            flags=re.IGNORECASE
        )

        if match:
            break

    if not match:
        return []

    file_name = (
        match
        .group(1)
        .strip()
    )

    root_name = (
        normalize_file_root(
            match.group(2)
        )
    )

    if not root_name:
        return []

    if not is_safe_simple_file_name(
        file_name
    ):
        return []

    if normalize_text(
        file_name
    ) in MASS_READ_TERMS:
        return []

    return [
        make_action(
            "read_file_content",
            root_name,
            {
                "file_name": file_name
            }
        )
    ]


# ============================================================
# CREER UN FICHIER AVEC CONTENU
# ============================================================

def parse_create_file_with_content(
    user_message
):
    """
    Interprète une création explicite d'UN nouveau fichier texte.

    Formes acceptées :
        crée notes.txt dans Documents avec le contenu Réunion à 14h
        crée le fichier todo.md dans Bureau contenant Acheter du lait
        créer config.json dans Téléchargements avec le contenu {"mode":"local"}

    La validation finale des permissions, de la taille et de
    l'absence d'écrasement reste assurée par agent.py/file_tools.py.
    """

    root_pattern = (
        r"bureau|desktop|"
        r"documents?|"
        r"téléchargements?|telechargements?|downloads?|"
        r"images?|photos?|pictures?|"
        r"vidéos?|videos?|"
        r"musiques?|music"
    )

    patterns = [
        (
            r"^\s*"
            r"(?:crée|cree|créer|creer)"
            r"\s+"
            r"(?:(?:le|un)\s+fichier\s+)?"
            r"(.+?)"
            r"\s+dans\s+"
            r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
            r"(" + root_pattern + r")"
            r"\s+avec\s+le\s+contenu"
            r"\s*:?[ \t]*"
            r"(.+?)"
            r"\s*$"
        ),
        (
            r"^\s*"
            r"(?:crée|cree|créer|creer)"
            r"\s+"
            r"(?:(?:le|un)\s+fichier\s+)?"
            r"(.+?)"
            r"\s+dans\s+"
            r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
            r"(" + root_pattern + r")"
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
            user_message,
            flags=re.IGNORECASE
        )

        if match:
            break

    if not match:
        return []

    file_name = (
        match
        .group(1)
        .strip()
    )

    root_name = normalize_file_root(
        match.group(2)
    )

    content = (
        match
        .group(3)
        .strip()
    )

    if not root_name:
        return []

    if not is_safe_simple_file_name(
        file_name
    ):
        return []

    extension = (
        Path(file_name)
        .suffix
        .lower()
    )

    if extension not in WRITABLE_TEXT_EXTENSIONS:
        return []

    if not content:
        return []

    # Le backend applique une borne prudente. La borne finale
    # en octets est imposée par file_tools.py.
    if len(content) > 65536:
        return []

    return [
        make_action(
            "create_file_with_content",
            root_name,
            {
                "file_name": file_name,
                "content": content,
            }
        )
    ]


# ============================================================
# FERMETURE APPLICATION / SITE
# ============================================================

def parse_close(
    text
):
    """
    Exemples :

        ferme Word
        ferme Edge
        ferme l'application Android Studio
        ferme le site GitHub
        ferme la fenêtre du site ChatGPT
        ferme Word et Excel

    Sans précision, une application connue est prioritaire,
    sinon la cible est interprétée comme un site.
    """

    prefixes = [
        "ferme ",
        "fermer ",
        "quitte ",
        "quitter ",
        "arrete ",
        "arreter ",
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

    forced_kind = None

    site_prefixes = [
        "la fenetre du site ",
        "fenetre du site ",
        "le site ",
        "site ",
    ]

    application_prefixes = [
        "la fenetre de l'application ",
        "fenetre de l'application ",
        "la fenetre de l'appli ",
        "fenetre de l'appli ",
        "l'application ",
        "application ",
        "l'appli ",
        "appli ",
    ]

    for prefix in site_prefixes:
        if content.startswith(
            prefix
        ):
            forced_kind = "website"
            content = (
                content[
                    len(prefix):
                ]
                .strip()
            )
            break

    if forced_kind is None:
        for prefix in application_prefixes:
            if content.startswith(
                prefix
            ):
                forced_kind = "application"
                content = (
                    content[
                        len(prefix):
                    ]
                    .strip()
                )
                break

    if forced_kind is None:
        for prefix in [
            "la fenetre de ",
            "fenetre de ",
            "la fenetre ",
            "fenetre ",
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

    if not content:
        return []

    actions = []
    seen = set()

    for raw_target in split_targets(
        content
    ):
        open_action, target = resolve_open_target(
            raw_target,
            forced_kind=forced_kind
        )

        if not open_action:
            continue

        if open_action == "open_application":
            action = "close_application"
        elif open_action == "open_website":
            action = "close_website"
        else:
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

    # ========================================================
    # PRECISION SITE / APPLICATION
    # ========================================================

    forced_kind = None

    website_prefixes = [
        "le site ",
        "site ",
    ]

    application_prefixes = [
        "l'application ",
        "application ",
        "l'appli ",
        "appli ",
    ]

    # --------------------------------------------------------
    # Site explicitement demandé
    # --------------------------------------------------------

    for prefix in website_prefixes:

        if content.startswith(
            prefix
        ):

            forced_kind = "website"

            content = (
                content[
                    len(prefix):
                ]
                .strip()
            )

            break

    # --------------------------------------------------------
    # Application explicitement demandée
    # --------------------------------------------------------

    if forced_kind is None:

        for prefix in application_prefixes:

            if content.startswith(
                prefix
            ):

                forced_kind = "application"

                content = (
                    content[
                        len(prefix):
                    ]
                    .strip()
                )

                break

    if not content:

        return []

    actions = []

    seen = set()

    for raw_target in split_targets(
        content
    ):

        action, target = (
            resolve_open_target(
                raw_target,
                forced_kind=forced_kind
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
    # Création contrôlée de fichier avec contenu
    # --------------------------------------------------------

    if not actions:

        actions = parse_create_file_with_content(
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
    # Renommage contrôlé
    # --------------------------------------------------------

    if not actions:

        actions = parse_rename_file(
            user_message
        )

    # --------------------------------------------------------
    # Suppression contrôlée
    # --------------------------------------------------------

    if not actions:

        actions = parse_delete_file(
            user_message
        )

    # --------------------------------------------------------
    # Lecture contrôlée
    # --------------------------------------------------------

    if not actions:

        actions = parse_read_file_content(
            user_message
        )

    # --------------------------------------------------------
    # Copie contrôlée entre racines
    # --------------------------------------------------------

    if not actions:

        actions = parse_copy_file_between_roots(
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
    # Fermeture application / site
    # --------------------------------------------------------

    if not actions:

        actions = parse_close(
            text
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

        if normalize_text(
            message
        ) in {
            "quit",
            "exit",
            "quitte",
            "stop",
            "sort",
            "ferme"
            "arrête",
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