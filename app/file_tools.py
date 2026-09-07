import ctypes
import json
import os
import re
import uuid

from ctypes import wintypes
from datetime import datetime
from pathlib import Path


# ============================================================
# CHEMINS DU PROJET
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]

AGENT_CONFIG_FILE = ROOT_DIR / "config" / "agent.json"
PERMISSIONS_FILE = ROOT_DIR / "config" / "permissions.json"


# ============================================================
# DOSSIERS WINDOWS AUTORISES
# ============================================================

KNOWN_FOLDER_GUIDS = {
    "desktop": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
    "documents": "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}",
    "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
    "pictures": "{33E28130-4E1E-4676-835A-98395C3BC3BB}",
    "videos": "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}",
    "music": "{4BD8D571-6D19-48D3-BE97-422220080E}",
}


DISPLAY_NAMES = {
    "desktop": "Bureau",
    "documents": "Documents",
    "downloads": "Téléchargements",
    "pictures": "Images",
    "videos": "Vidéos",
    "music": "Musique",
}


# ============================================================
# SECURITE WINDOWS
# ============================================================

FILE_ATTRIBUTE_HIDDEN = 0x00000002
FILE_ATTRIBUTE_SYSTEM = 0x00000004
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400


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


# Même si permissions.json est accidentellement modifié,
# ces extensions restent interdites.
HARD_BLOCKED_EXTENSIONS = {
    ".exe",
    ".com",
    ".bat",
    ".cmd",
    ".ps1",
    ".psm1",
    ".vbs",
    ".vbe",
    ".js",
    ".jse",
    ".wsf",
    ".wsh",
    ".scr",
    ".msi",
    ".msp",
    ".msc",
    ".cpl",
    ".dll",
    ".sys",
    ".reg",
    ".lnk",
    ".url",
    ".hta",
    ".jar",
}


# ============================================================
# JSON SECURISE
# ============================================================

def load_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

    except (
        OSError,
        json.JSONDecodeError,
    ):
        pass

    return {}


# ============================================================
# INTERRUPTEUR GENERAL
# ============================================================

def is_filesystem_globally_enabled():
    config = load_json_file(AGENT_CONFIG_FILE)

    return bool(
        config
        .get("security", {})
        .get("allow_filesystem", False)
    )


def get_filesystem_config():
    permissions = load_json_file(PERMISSIONS_FILE)

    filesystem = permissions.get(
        "filesystem",
        {}
    )

    if not isinstance(filesystem, dict):
        return {}

    return filesystem


def is_filesystem_enabled():
    if not is_filesystem_globally_enabled():
        return False

    return bool(
        get_filesystem_config()
        .get("enabled", False)
    )


# ============================================================
# PERMISSIONS PAR RACINE
# ============================================================

def get_root_permissions(root_name):
    filesystem = get_filesystem_config()

    roots = filesystem.get(
        "roots",
        {}
    )

    if not isinstance(roots, dict):
        return {}

    permission = roots.get(
        root_name,
        {}
    )

    if not isinstance(permission, dict):
        return {}

    return permission


def has_root_permission(
    root_name,
    permission_name
):
    if not is_filesystem_enabled():
        return False

    permission = get_root_permissions(
        root_name
    )

    return bool(
        permission.get("enabled", False)
        and
        permission.get(
            permission_name,
            False
        )
    )


# ============================================================
# POLITIQUES
# ============================================================

def get_creation_policy():
    policy = (
        get_filesystem_config()
        .get("creation_policy", {})
    )

    if not isinstance(policy, dict):
        return {}

    return policy


def get_move_policy():
    policy = (
        get_filesystem_config()
        .get("move_policy", {})
    )

    if not isinstance(policy, dict):
        return {}

    return policy


def get_cross_root_move_policy():
    policy = (
        get_filesystem_config()
        .get(
            "cross_root_move_policy",
            {}
        )
    )

    if not isinstance(policy, dict):
        return {}

    return policy


def get_security_policy():
    policy = (
        get_filesystem_config()
        .get(
            "security_policy",
            {}
        )
    )

    if not isinstance(policy, dict):
        return {}

    return policy


# ============================================================
# BARRIERES DURES DU SYSTEME
# ============================================================

def normalized_path_string(path):
    return os.path.normcase(
        os.path.abspath(
            str(path)
        )
    )


def is_same_path(
    path_a,
    path_b
):
    try:
        return (
            normalized_path_string(path_a)
            ==
            normalized_path_string(path_b)
        )

    except (
        OSError,
        ValueError,
    ):
        return False


def is_same_or_descendant(
    path,
    parent
):
    try:
        child_value = normalized_path_string(
            path
        )

        parent_value = normalized_path_string(
            parent
        )

        return (
            os.path.commonpath(
                [
                    child_value,
                    parent_value,
                ]
            )
            ==
            parent_value
        )

    except (
        OSError,
        ValueError,
    ):
        return False


def get_hard_protected_paths():
    protected = []

    environment_names = [
        "WINDIR",
        "SystemRoot",
        "ProgramFiles",
        "ProgramFiles(x86)",
        "ProgramData",
    ]

    for variable in environment_names:
        value = os.environ.get(variable)

        if value:
            protected.append(
                Path(value)
            )

    user_profile = os.environ.get(
        "USERPROFILE"
    )

    if user_profile:
        user_profile_path = Path(
            user_profile
        )

        protected.append(
            user_profile_path / "AppData"
        )

    # Le projet de l'agent lui-même est toujours protégé.
    protected.append(
        ROOT_DIR
    )

    system_drive = os.environ.get(
        "SystemDrive",
        "C:"
    )

    drive_root = Path(
        system_drive + "\\"
    )

    protected.append(
        drive_root / "$Recycle.Bin"
    )

    protected.append(
        drive_root / "System Volume Information"
    )

    return protected


def is_hard_protected_path(path):
    """
    Protection indépendante de permissions.json.

    Même si la configuration est mal modifiée,
    les dossiers système restent inaccessibles.
    """

    try:
        path = Path(path)

    except TypeError:
        return True

    # --------------------------------------------------------
    # Racine du disque
    # --------------------------------------------------------

    try:
        if path.anchor and is_same_path(
            path,
            Path(path.anchor)
        ):
            return True

    except OSError:
        return True

    # --------------------------------------------------------
    # Racine du profil utilisateur
    # --------------------------------------------------------

    user_profile = os.environ.get(
        "USERPROFILE"
    )

    if user_profile:

        if is_same_path(
            path,
            Path(user_profile)
        ):
            return True

    # --------------------------------------------------------
    # Zones système
    # --------------------------------------------------------

    for protected_path in get_hard_protected_paths():

        if is_same_or_descendant(
            path,
            protected_path
        ):
            return True

    return False


# ============================================================
# ATTRIBUTS WINDOWS
# ============================================================

def get_file_attributes(path):
    try:
        stats = os.lstat(
            path
        )

        return getattr(
            stats,
            "st_file_attributes",
            0
        )

    except (
        OSError,
        PermissionError,
    ):
        return None


def is_reparse_point(path):
    """
    Bloque :
    - liens symboliques ;
    - junctions ;
    - autres reparse points Windows.
    """

    try:
        if Path(path).is_symlink():
            return True

    except OSError:
        return True

    attributes = get_file_attributes(
        path
    )

    if attributes is None:
        return True

    return bool(
        attributes
        &
        FILE_ATTRIBUTE_REPARSE_POINT
    )


def is_hidden_or_system(path):
    attributes = get_file_attributes(
        path
    )

    if attributes is None:
        return True

    return bool(
        attributes
        &
        (
            FILE_ATTRIBUTE_HIDDEN
            |
            FILE_ATTRIBUTE_SYSTEM
        )
    )


# ============================================================
# EXTENSIONS DANGEREUSES
# ============================================================

def get_blocked_extensions():
    blocked = set(
        HARD_BLOCKED_EXTENSIONS
    )

    configured = (
        get_filesystem_config()
        .get(
            "blocked_extensions",
            []
        )
    )

    if isinstance(configured, list):

        for extension in configured:

            if not isinstance(
                extension,
                str
            ):
                continue

            extension = (
                extension
                .strip()
                .lower()
            )

            if not extension:
                continue

            if not extension.startswith("."):
                extension = (
                    "."
                    + extension
                )

            blocked.add(
                extension
            )

    return blocked


def is_blocked_file_type(file_name):
    try:
        extension = (
            Path(file_name)
            .suffix
            .lower()
        )

    except TypeError:
        return True

    if not extension:
        return False

    return (
        extension
        in
        get_blocked_extensions()
    )


# ============================================================
# CATEGORIES MEDIA
# ============================================================

def get_media_category(file_name):
    extension = (
        Path(file_name)
        .suffix
        .lower()
    )

    categories = (
        get_filesystem_config()
        .get(
            "media_categories",
            {}
        )
    )

    if not isinstance(
        categories,
        dict
    ):
        return None

    labels = {
        "images": "image",
        "videos": "vidéo",
        "audio": "audio",
    }

    for category, extensions in categories.items():

        if not isinstance(
            extensions,
            list
        ):
            continue

        normalized_extensions = {
            str(item)
            .strip()
            .lower()
            for item in extensions
        }

        if extension in normalized_extensions:

            return labels.get(
                category,
                category
            )

    return None


# ============================================================
# API WINDOWS : GUID
# ============================================================

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def guid_from_string(
    guid_string
):
    value = uuid.UUID(
        guid_string.strip("{}")
    )

    bytes_le = value.bytes_le

    guid = GUID()

    guid.Data1 = int.from_bytes(
        bytes_le[0:4],
        "little"
    )

    guid.Data2 = int.from_bytes(
        bytes_le[4:6],
        "little"
    )

    guid.Data3 = int.from_bytes(
        bytes_le[6:8],
        "little"
    )

    for index in range(8):
        guid.Data4[index] = (
            bytes_le[
                8 + index
            ]
        )

    return guid


# ============================================================
# KNOWN FOLDERS WINDOWS
# ============================================================

def get_windows_known_folder(
    root_name
):
    guid_string = KNOWN_FOLDER_GUIDS.get(
        root_name
    )

    if not guid_string:
        return None

    try:
        shell32 = ctypes.windll.shell32
        ole32 = ctypes.windll.ole32

        guid = guid_from_string(
            guid_string
        )

        path_pointer = ctypes.c_void_p()

        shell32.SHGetKnownFolderPath.argtypes = [
            ctypes.POINTER(GUID),
            wintypes.DWORD,
            wintypes.HANDLE,
            ctypes.POINTER(
                ctypes.c_void_p
            ),
        ]

        shell32.SHGetKnownFolderPath.restype = (
            ctypes.c_long
        )

        result = (
            shell32
            .SHGetKnownFolderPath(
                ctypes.byref(guid),
                0,
                None,
                ctypes.byref(
                    path_pointer
                )
            )
        )

        if result != 0:
            return None

        if not path_pointer.value:
            return None

        try:
            folder_path = ctypes.wstring_at(
                path_pointer.value
            )

        finally:
            ole32.CoTaskMemFree.argtypes = [
                ctypes.c_void_p
            ]

            ole32.CoTaskMemFree(
                path_pointer
            )

        if not folder_path:
            return None

        return Path(
            folder_path
        )

    except Exception:
        return None


# ============================================================
# FALLBACK WINDOWS
# ============================================================

def get_fallback_folder(
    root_name
):
    user_profile = os.environ.get(
        "USERPROFILE"
    )

    if not user_profile:
        return None

    base = Path(
        user_profile
    )

    fallback = {
        "desktop": base / "Desktop",
        "documents": base / "Documents",
        "downloads": base / "Downloads",
        "pictures": base / "Pictures",
        "videos": base / "Videos",
        "music": base / "Music",
    }

    return fallback.get(
        root_name
    )


# ============================================================
# RESOLUTION D'UNE RACINE AUTORISEE
# ============================================================

def resolve_allowed_root(
    root_name
):
    if not isinstance(
        root_name,
        str
    ):
        return None

    root_name = (
        root_name
        .strip()
        .lower()
    )

    # Jamais de chemin arbitraire.
    if root_name not in KNOWN_FOLDER_GUIDS:
        return None

    folder = get_windows_known_folder(
        root_name
    )

    if folder is None:
        folder = get_fallback_folder(
            root_name
        )

    if folder is None:
        return None

    try:
        folder = folder.resolve()

    except (
        OSError,
        RuntimeError,
    ):
        folder = folder.absolute()

    # Barrière système indépendante du JSON.
    if is_hard_protected_path(
        folder
    ):
        return None

    return folder


# ============================================================
# VALIDATION D'UN NOM SIMPLE
# ============================================================

def validate_simple_name(
    value
):
    if not isinstance(
        value,
        str
    ):
        return (
            False,
            "Le nom est invalide."
        )

    value = value.strip()

    if not value:
        return (
            False,
            "Le nom est vide."
        )

    if len(value) > 180:
        return (
            False,
            "Le nom est trop long."
        )

    # --------------------------------------------------------
    # Aucun chemin
    # --------------------------------------------------------

    if (
        "/" in value
        or
        "\\" in value
    ):
        return (
            False,
            (
                "Les chemins sont interdits. "
                "Un seul nom est autorisé."
            )
        )

    # --------------------------------------------------------
    # Traversée de répertoire
    # --------------------------------------------------------

    if value in {
        ".",
        "..",
    }:
        return (
            False,
            "Ce nom est interdit."
        )

    if ".." in value:
        return (
            False,
            (
                "Les séquences '..' "
                "ne sont pas autorisées."
            )
        )

    # --------------------------------------------------------
    # Jokers
    # --------------------------------------------------------

    if "*" in value or "?" in value:
        return (
            False,
            "Les jokers sont interdits."
        )

    # --------------------------------------------------------
    # Caractères Windows interdits
    # Le ':' bloque aussi les Alternate Data Streams.
    # --------------------------------------------------------

    if re.search(
        r'[<>:"/\\|?*\x00-\x1f]',
        value
    ):
        return (
            False,
            (
                "Le nom contient un caractère "
                "interdit par Windows."
            )
        )

    if (
        value.endswith(" ")
        or
        value.endswith(".")
    ):
        return (
            False,
            (
                "Le nom ne peut pas finir "
                "par un espace ou un point."
            )
        )

    base_name = (
        value
        .split(".")[0]
        .upper()
    )

    if base_name in WINDOWS_RESERVED_NAMES:
        return (
            False,
            (
                f"Le nom '{value}' "
                "est réservé par Windows."
            )
        )

    return (
        True,
        value
    )


def validate_folder_name(
    folder_name
):
    return validate_simple_name(
        folder_name
    )


def validate_file_name(
    file_name
):
    valid, result = validate_simple_name(
        file_name
    )

    if not valid:
        return (
            False,
            result
        )

    if is_blocked_file_type(
        result
    ):
        return (
            False,
            (
                f"Le type de fichier '{Path(result).suffix}' "
                "est protégé et ne peut pas être manipulé."
            )
        )

    return (
        True,
        result
    )


# ============================================================
# SECURITE DES CHEMINS
# ============================================================

def is_direct_child(
    root_path,
    target_path
):
    try:
        resolved_root = (
            Path(root_path)
            .resolve()
        )

        resolved_target = (
            Path(target_path)
            .resolve(
                strict=False
            )
        )

        if is_hard_protected_path(
            resolved_target
        ):
            return False

        return (
            resolved_target.parent
            ==
            resolved_root
        )

    except (
        OSError,
        RuntimeError,
    ):
        return False


# ============================================================
# FORMAT DES TAILLES
# ============================================================

def format_size(
    size
):
    size = float(
        size
    )

    units = [
        "o",
        "Ko",
        "Mo",
        "Go",
        "To",
    ]

    for unit in units:

        if size < 1024:

            if unit == "o":
                return (
                    f"{int(size)} {unit}"
                )

            return (
                f"{size:.1f} {unit}"
            )

        size /= 1024

    return (
        f"{size:.1f} Po"
    )


# ============================================================
# TRANSFERTS ENTRE RACINES
# ============================================================

def is_cross_root_transfer_allowed(
    source_root,
    destination_root
):
    if not is_filesystem_enabled():
        return False

    source_root = (
        str(source_root)
        .strip()
        .lower()
    )

    destination_root = (
        str(destination_root)
        .strip()
        .lower()
    )

    if source_root == destination_root:
        return False

    if source_root not in KNOWN_FOLDER_GUIDS:
        return False

    if destination_root not in KNOWN_FOLDER_GUIDS:
        return False

    policy = get_cross_root_move_policy()

    if not policy.get(
        "enabled",
        False
    ):
        return False

    if not has_root_permission(
        source_root,
        "can_move_out"
    ):
        return False

    if not has_root_permission(
        destination_root,
        "can_receive_move"
    ):
        return False

    # --------------------------------------------------------
    # Nouveau mode :
    # toutes les racines utilisateur activées peuvent
    # communiquer entre elles.
    # --------------------------------------------------------

    if policy.get(
        "allow_between_enabled_user_roots",
        False
    ):

        source_enabled = (
            get_root_permissions(
                source_root
            )
            .get(
                "enabled",
                False
            )
        )

        destination_enabled = (
            get_root_permissions(
                destination_root
            )
            .get(
                "enabled",
                False
            )
        )

        return bool(
            source_enabled
            and
            destination_enabled
        )

    # --------------------------------------------------------
    # Compatibilité avec l'ancien système allowed_transfers
    # --------------------------------------------------------

    transfers = policy.get(
        "allowed_transfers",
        []
    )

    if not isinstance(
        transfers,
        list
    ):
        return False

    for transfer in transfers:

        if not isinstance(
            transfer,
            dict
        ):
            continue

        configured_source = (
            str(
                transfer.get(
                    "source",
                    ""
                )
            )
            .strip()
            .lower()
        )

        configured_destination = (
            str(
                transfer.get(
                    "destination",
                    ""
                )
            )
            .strip()
            .lower()
        )

        if (
            configured_source
            ==
            source_root
            and
            configured_destination
            ==
            destination_root
        ):
            return True

    return False


# ============================================================
# LISTER UN DOSSIER
# ============================================================

def list_directory(
    root_name
):
    root_name = (
        str(root_name)
        .strip()
        .lower()
    )

    if not is_filesystem_enabled():
        return (
            False,
            (
                "L'accès au système de fichiers "
                "est désactivé."
            )
        )

    if not has_root_permission(
        root_name,
        "can_list"
    ):
        return (
            False,
            (
                "La consultation de ce dossier "
                "n'est pas autorisée."
            )
        )

    root_path = resolve_allowed_root(
        root_name
    )

    if root_path is None:
        return (
            False,
            (
                "Ce dossier est inconnu, "
                "protégé ou non autorisé."
            )
        )

    if not root_path.exists():
        return (
            False,
            (
                f"Le dossier "
                f"{DISPLAY_NAMES.get(root_name, root_name)} "
                "n'existe pas."
            )
        )

    metadata_allowed = (
        has_root_permission(
            root_name,
            "can_read_metadata"
        )
    )

    try:
        entries = list(
            root_path.iterdir()
        )

    except (
        OSError,
        PermissionError,
    ) as error:
        return (
            False,
            (
                "Impossible de consulter "
                f"le dossier : {error}"
            )
        )

    visible_entries = []

    protected_count = 0

    for item in entries:

        # ----------------------------------------------------
        # Zone système / projet
        # ----------------------------------------------------

        if is_hard_protected_path(
            item
        ):
            protected_count += 1
            continue

        # ----------------------------------------------------
        # Liens, junctions, reparse points
        # ----------------------------------------------------

        if is_reparse_point(
            item
        ):
            protected_count += 1
            continue

        # ----------------------------------------------------
        # Fichiers cachés / système
        # ----------------------------------------------------

        if is_hidden_or_system(
            item
        ):
            protected_count += 1
            continue

        visible_entries.append(
            item
        )

    try:
        visible_entries.sort(
            key=lambda item: (
                not item.is_dir(),
                item.name.casefold()
            )
        )

    except OSError:
        visible_entries.sort(
            key=lambda item: (
                item.name.casefold()
            )
        )

    display_name = DISPLAY_NAMES.get(
        root_name,
        root_name
    )

    if not visible_entries:

        if protected_count:
            return (
                True,
                (
                    f"{display_name} ne contient aucun "
                    "élément utilisateur affichable. "
                    f"{protected_count} élément(s) "
                    "protégé(s) ont été ignorés."
                )
            )

        return (
            True,
            f"{display_name} est vide."
        )

    lines = [
        f"Contenu de {display_name} :"
    ]

    for item in visible_entries:

        try:
            if item.is_dir():
                item_type = "dossier"

            elif item.is_file():
                item_type = "fichier"

            else:
                item_type = "élément"

            line = (
                f"- [{item_type}] "
                f"{item.name}"
            )

            if (
                item_type == "fichier"
                and
                is_blocked_file_type(
                    item.name
                )
            ):
                line += " | protégé"

            else:
                media_category = (
                    get_media_category(
                        item.name
                    )
                )

                if media_category:
                    line += (
                        f" | {media_category}"
                    )

            if metadata_allowed:

                try:
                    stats = item.stat(
                        follow_symlinks=False
                    )

                    modified = (
                        datetime
                        .fromtimestamp(
                            stats.st_mtime
                        )
                        .strftime(
                            "%d/%m/%Y %H:%M"
                        )
                    )

                    if item_type == "fichier":
                        line += (
                            f" | {format_size(stats.st_size)}"
                            f" | modifié le {modified}"
                        )

                    else:
                        line += (
                            f" | modifié le {modified}"
                        )

                except OSError:
                    pass

            lines.append(
                line
            )

        except OSError:
            continue

    if protected_count:
        lines.append("")
        lines.append(
            (
                f"{protected_count} élément(s) "
                "protégé(s) ont été ignorés."
            )
        )

    return (
        True,
        "\n".join(lines)
    )


# ============================================================
# CREER UN DOSSIER
# ============================================================

def create_folder(
    root_name,
    folder_name,
    explicit_user_command=False
):
    root_name = (
        str(root_name)
        .strip()
        .lower()
    )

    if not is_filesystem_enabled():
        return (
            False,
            (
                "L'accès au système de fichiers "
                "est désactivé."
            )
        )

    creation_policy = (
        get_creation_policy()
    )

    if (
        creation_policy.get(
            "require_explicit_user_command",
            True
        )
        and
        not explicit_user_command
    ):
        return (
            False,
            (
                "La création d'un dossier nécessite "
                "une commande explicite de l'utilisateur."
            )
        )

    if not has_root_permission(
        root_name,
        "can_create_folder"
    ):
        return (
            False,
            (
                "La création de dossiers n'est pas "
                "autorisée dans "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    valid, validated_name = (
        validate_folder_name(
            folder_name
        )
    )

    if not valid:
        return (
            False,
            validated_name
        )

    root_path = resolve_allowed_root(
        root_name
    )

    if root_path is None:
        return (
            False,
            "Dossier racine protégé ou introuvable."
        )

    if not root_path.exists():
        return (
            False,
            "Le dossier racine n'existe pas."
        )

    target_path = (
        root_path
        /
        validated_name
    )

    if not is_direct_child(
        root_path,
        target_path
    ):
        return (
            False,
            (
                "Le chemin demandé sort "
                "de la zone autorisée."
            )
        )

    if target_path.exists():

        if target_path.is_dir():
            return (
                True,
                (
                    f"Le dossier '{validated_name}' "
                    "existe déjà dans "
                    f"{DISPLAY_NAMES.get(root_name, root_name)}."
                )
            )

        return (
            False,
            (
                f"Un fichier nommé '{validated_name}' "
                "existe déjà à cet emplacement."
            )
        )

    try:
        target_path.mkdir(
            parents=False,
            exist_ok=False
        )

        return (
            True,
            (
                f"Le dossier '{validated_name}' "
                "a été créé dans "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    except (
        OSError,
        PermissionError,
    ) as error:
        return (
            False,
            (
                "Impossible de créer le dossier : "
                f"{error}"
            )
        )


# ============================================================
# DEPLACER DANS LA MEME RACINE
# ============================================================

def move_file_within_root(
    root_name,
    file_name,
    destination_folder_name,
    explicit_user_command=False
):
    root_name = (
        str(root_name)
        .strip()
        .lower()
    )

    if not is_filesystem_enabled():
        return (
            False,
            (
                "L'accès au système de fichiers "
                "est désactivé."
            )
        )

    if not has_root_permission(
        root_name,
        "can_move_within_root"
    ):
        return (
            False,
            (
                "Le déplacement interne n'est pas "
                "autorisé dans "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    policy = get_move_policy()

    if (
        policy.get(
            "require_explicit_user_command",
            True
        )
        and
        not explicit_user_command
    ):
        return (
            False,
            (
                "Le déplacement nécessite "
                "une commande explicite."
            )
        )

    valid, validated_file = (
        validate_file_name(
            file_name
        )
    )

    if not valid:
        return (
            False,
            validated_file
        )

    valid, validated_destination = (
        validate_folder_name(
            destination_folder_name
        )
    )

    if not valid:
        return (
            False,
            validated_destination
        )

    root_path = resolve_allowed_root(
        root_name
    )

    if root_path is None:
        return (
            False,
            "Dossier racine protégé ou introuvable."
        )

    source_path = (
        root_path
        /
        validated_file
    )

    destination_folder = (
        root_path
        /
        validated_destination
    )

    destination_path = (
        destination_folder
        /
        validated_file
    )

    if not is_direct_child(
        root_path,
        source_path
    ):
        return (
            False,
            "Le fichier source n'est pas autorisé."
        )

    if not is_direct_child(
        root_path,
        destination_folder
    ):
        return (
            False,
            "Le dossier destination n'est pas autorisé."
        )

    if not source_path.exists():
        return (
            False,
            (
                f"Le fichier '{validated_file}' "
                "n'existe pas dans "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    if is_reparse_point(
        source_path
    ):
        return (
            False,
            (
                "Les liens, junctions et reparse points "
                "ne peuvent pas être déplacés."
            )
        )

    if is_hidden_or_system(
        source_path
    ):
        return (
            False,
            (
                "Les fichiers cachés ou système "
                "sont protégés."
            )
        )

    if not source_path.is_file():
        return (
            False,
            "La source n'est pas un fichier autorisé."
        )

    if not destination_folder.exists():
        return (
            False,
            (
                f"Le dossier '{validated_destination}' "
                "n'existe pas."
            )
        )

    if is_reparse_point(
        destination_folder
    ):
        return (
            False,
            (
                "La destination est un lien, "
                "une junction ou un reparse point."
            )
        )

    if is_hidden_or_system(
        destination_folder
    ):
        return (
            False,
            "Le dossier destination est protégé."
        )

    if not destination_folder.is_dir():
        return (
            False,
            "La destination n'est pas un dossier."
        )

    if destination_path.exists():
        return (
            False,
            (
                f"'{validated_file}' existe déjà "
                "dans la destination. "
                "Aucun écrasement n'est autorisé."
            )
        )

    try:
        resolved_root = root_path.resolve(
            strict=True
        )

        resolved_source = source_path.resolve(
            strict=True
        )

        resolved_destination = (
            destination_folder
            .resolve(
                strict=True
            )
        )

    except (
        OSError,
        RuntimeError,
    ):
        return (
            False,
            (
                "Impossible de vérifier "
                "les chemins."
            )
        )

    if (
        resolved_source.parent
        !=
        resolved_root
    ):
        return (
            False,
            "La source sort de la zone autorisée."
        )

    if (
        resolved_destination.parent
        !=
        resolved_root
    ):
        return (
            False,
            "La destination sort de la zone autorisée."
        )

    if (
        is_hard_protected_path(
            resolved_source
        )
        or
        is_hard_protected_path(
            resolved_destination
        )
    ):
        return (
            False,
            "Une zone protégée a été détectée."
        )

    try:
        os.rename(
            source_path,
            destination_path
        )

        return (
            True,
            (
                f"Le fichier '{validated_file}' "
                "a été déplacé dans "
                f"'{validated_destination}'."
            )
        )

    except (
        OSError,
        PermissionError,
    ) as error:
        return (
            False,
            (
                "Impossible de déplacer le fichier : "
                f"{error}"
            )
        )


# ============================================================
# DEPLACER ENTRE DEUX RACINES
# ============================================================

def move_file_between_roots(
    source_root,
    destination_root,
    file_name,
    destination_folder_name=None,
    explicit_user_command=False
):
    source_root = (
        str(source_root)
        .strip()
        .lower()
    )

    destination_root = (
        str(destination_root)
        .strip()
        .lower()
    )

    if not is_filesystem_enabled():
        return (
            False,
            (
                "L'accès au système de fichiers "
                "est désactivé."
            )
        )

    if source_root == destination_root:
        return (
            False,
            (
                "Les deux racines doivent "
                "être différentes."
            )
        )

    policy = get_cross_root_move_policy()

    if not policy.get(
        "enabled",
        False
    ):
        return (
            False,
            (
                "Les déplacements entre dossiers "
                "sont désactivés."
            )
        )

    if (
        policy.get(
            "require_explicit_user_command",
            True
        )
        and
        not explicit_user_command
    ):
        return (
            False,
            (
                "Le déplacement nécessite "
                "une commande explicite."
            )
        )

    if not is_cross_root_transfer_allowed(
        source_root,
        destination_root
    ):
        return (
            False,
            (
                "Ce transfert entre dossiers "
                "n'est pas autorisé."
            )
        )

    valid, validated_file = (
        validate_file_name(
            file_name
        )
    )

    if not valid:
        return (
            False,
            validated_file
        )

    validated_destination_folder = None

    if destination_folder_name is not None:

        destination_folder_name = (
            str(destination_folder_name)
            .strip()
        )

        if destination_folder_name:

            valid, result = (
                validate_folder_name(
                    destination_folder_name
                )
            )

            if not valid:
                return (
                    False,
                    result
                )

            validated_destination_folder = result

    source_root_path = resolve_allowed_root(
        source_root
    )

    destination_root_path = resolve_allowed_root(
        destination_root
    )

    if (
        source_root_path is None
        or
        destination_root_path is None
    ):
        return (
            False,
            (
                "Une racine est protégée, "
                "inconnue ou introuvable."
            )
        )

    if (
        not source_root_path.exists()
        or
        not destination_root_path.exists()
    ):
        return (
            False,
            "Une racine Windows n'existe pas."
        )

    source_path = (
        source_root_path
        /
        validated_file
    )

    if not is_direct_child(
        source_root_path,
        source_path
    ):
        return (
            False,
            (
                "Le fichier source doit se trouver "
                "directement dans la racine autorisée."
            )
        )

    if not source_path.exists():
        return (
            False,
            (
                f"Le fichier '{validated_file}' "
                "n'existe pas dans "
                f"{DISPLAY_NAMES.get(source_root, source_root)}."
            )
        )

    if is_reparse_point(
        source_path
    ):
        return (
            False,
            (
                "Les liens, junctions et reparse points "
                "sont protégés."
            )
        )

    if is_hidden_or_system(
        source_path
    ):
        return (
            False,
            (
                "Les fichiers cachés ou système "
                "sont protégés."
            )
        )

    if not source_path.is_file():
        return (
            False,
            "La source n'est pas un fichier autorisé."
        )

    # --------------------------------------------------------
    # Destination
    # --------------------------------------------------------

    if validated_destination_folder:

        destination_folder = (
            destination_root_path
            /
            validated_destination_folder
        )

        if not is_direct_child(
            destination_root_path,
            destination_folder
        ):
            return (
                False,
                "Le sous-dossier destination est interdit."
            )

        if not destination_folder.exists():
            return (
                False,
                (
                    f"Le dossier "
                    f"'{validated_destination_folder}' "
                    "n'existe pas dans "
                    f"{DISPLAY_NAMES.get(destination_root, destination_root)}."
                )
            )

        if is_reparse_point(
            destination_folder
        ):
            return (
                False,
                (
                    "Le dossier destination est un lien, "
                    "une junction ou un reparse point."
                )
            )

        if is_hidden_or_system(
            destination_folder
        ):
            return (
                False,
                "Le dossier destination est protégé."
            )

        if not destination_folder.is_dir():
            return (
                False,
                "La destination n'est pas un dossier."
            )

    else:
        destination_folder = (
            destination_root_path
        )

    destination_path = (
        destination_folder
        /
        validated_file
    )

    if destination_path.exists():
        return (
            False,
            (
                f"'{validated_file}' existe déjà "
                "dans la destination. "
                "Aucun écrasement n'est autorisé."
            )
        )

    # --------------------------------------------------------
    # Vérification finale
    # --------------------------------------------------------

    try:
        resolved_source_root = (
            source_root_path
            .resolve(
                strict=True
            )
        )

        resolved_destination_root = (
            destination_root_path
            .resolve(
                strict=True
            )
        )

        resolved_source = (
            source_path
            .resolve(
                strict=True
            )
        )

        resolved_destination_folder = (
            destination_folder
            .resolve(
                strict=True
            )
        )

    except (
        OSError,
        RuntimeError,
    ):
        return (
            False,
            (
                "Impossible de vérifier "
                "les chemins."
            )
        )

    if (
        resolved_source.parent
        !=
        resolved_source_root
    ):
        return (
            False,
            "La source sort de la zone autorisée."
        )

    if validated_destination_folder:

        if (
            resolved_destination_folder.parent
            !=
            resolved_destination_root
        ):
            return (
                False,
                "La destination sort de la zone autorisée."
            )

    else:

        if (
            resolved_destination_folder
            !=
            resolved_destination_root
        ):
            return (
                False,
                "La destination est invalide."
            )

    if (
        is_hard_protected_path(
            resolved_source
        )
        or
        is_hard_protected_path(
            resolved_destination_folder
        )
    ):
        return (
            False,
            (
                "Une zone système ou protégée "
                "a été détectée."
            )
        )

    # --------------------------------------------------------
    # Déplacement
    # --------------------------------------------------------

    try:
        os.rename(
            source_path,
            destination_path
        )

    except OSError as error:
        return (
            False,
            (
                "Impossible de déplacer le fichier. "
                "Aucune copie automatique n'est utilisée, "
                "afin de respecter les permissions actuelles. "
                f"Détail : {error}"
            )
        )

    if validated_destination_folder:

        destination_description = (
            f"{DISPLAY_NAMES.get(destination_root, destination_root)}"
            f"\\{validated_destination_folder}"
        )

    else:

        destination_description = (
            DISPLAY_NAMES.get(
                destination_root,
                destination_root
            )
        )

    return (
        True,
        (
            f"Le fichier '{validated_file}' "
            "a été déplacé de "
            f"{DISPLAY_NAMES.get(source_root, source_root)} "
            "vers "
            f"{destination_description}."
        )
    )


# ============================================================
# TEST DIRECT
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 65)
    print("TEST SECURITE FILE_TOOLS")
    print("=" * 65)
    print()

    print(
        "Accès fichiers :",
        is_filesystem_enabled()
    )

    print()

    print(
        "Racines utilisateur :"
    )

    for root in (
        "desktop",
        "documents",
        "downloads",
        "pictures",
        "videos",
        "music",
    ):

        path = resolve_allowed_root(
            root
        )

        print(
            f"- {DISPLAY_NAMES[root]} : {path}"
        )

    print()

    print(
        "Protection système :"
    )

    windows_path = Path(
        os.environ.get(
            "WINDIR",
            "C:\\Windows"
        )
    )

    print(
        "Windows protégé :",
        is_hard_protected_path(
            windows_path
        )
    )

    print(
        "AgentLocal protégé :",
        is_hard_protected_path(
            ROOT_DIR
        )
    )

    print()

    print(
        "Extensions dangereuses :"
    )

    for name in (
        "photo.jpg",
        "video.mp4",
        "musique.mp3",
        "programme.exe",
        "script.ps1",
        "commande.bat",
        "raccourci.lnk",
    ):

        print(
            f"- {name} :",
            (
                "BLOQUÉ"
                if is_blocked_file_type(name)
                else "autorisé"
            )
        )

    print()

    print(
        "Communication entre racines :"
    )

    tests = [
        ("desktop", "documents"),
        ("documents", "downloads"),
        ("downloads", "pictures"),
        ("pictures", "videos"),
        ("videos", "music"),
        ("music", "desktop"),
    ]

    for source, destination in tests:

        print(
            (
                f"- {DISPLAY_NAMES[source]} "
                f"-> {DISPLAY_NAMES[destination]} : "
                f"{is_cross_root_transfer_allowed(source, destination)}"
            )
        )

    print()

    print(
        "Aucun fichier n'a été créé, lu, exécuté, "
        "déplacé ou supprimé pendant ce test."
    )

    print()