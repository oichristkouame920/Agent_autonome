import ctypes
import json
import os
import posixpath
import re
import stat
import uuid
import zipfile
import zlib
import xml.etree.ElementTree as ET

from ctypes import wintypes
from datetime import datetime
from email import policy as email_policy
from email.parser import BytesParser
from html.parser import HTMLParser
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


# ============================================================
# EXTENSIONS BLOQUEES EN DUR
# ============================================================

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
# FORMATS DE LECTURE SUPPORTES EN DUR
# ============================================================

PLAIN_TEXT_READ_EXTENSIONS = {
    ".txt", ".md", ".csv", ".tsv", ".json",
    ".xml", ".yaml", ".yml", ".log", ".ini",
    ".cfg", ".conf", ".toml", ".ics", ".vcf",
}

HTML_READ_EXTENSIONS = {".html", ".htm"}
RTF_READ_EXTENSIONS = {".rtf"}
OFFICE_XML_READ_EXTENSIONS = {".docx", ".xlsx", ".pptx"}
OPEN_DOCUMENT_READ_EXTENSIONS = {".odt", ".ods", ".odp"}
EPUB_READ_EXTENSIONS = {".epub"}
EMAIL_READ_EXTENSIONS = {".eml"}
PDF_READ_EXTENSIONS = {".pdf"}

HARD_SUPPORTED_READ_EXTENSIONS = (
    PLAIN_TEXT_READ_EXTENSIONS
    | HTML_READ_EXTENSIONS
    | RTF_READ_EXTENSIONS
    | OFFICE_XML_READ_EXTENSIONS
    | OPEN_DOCUMENT_READ_EXTENSIONS
    | EPUB_READ_EXTENSIONS
    | EMAIL_READ_EXTENSIONS
    | PDF_READ_EXTENSIONS
)

HARD_BLOCKED_DOCUMENT_READ_EXTENSIONS = {
    ".doc", ".xls", ".ppt",
    ".docm", ".xlsm", ".pptm",
    ".dotm", ".xltm", ".potm", ".ppsm",
}

HARD_MAX_READ_FILE_BYTES = 20 * 1024 * 1024
HARD_MAX_READ_OUTPUT_CHARACTERS = 50000
HARD_MAX_ARCHIVE_ENTRIES = 5000
HARD_MAX_ARCHIVE_RELEVANT_BYTES = 32 * 1024 * 1024
HARD_MAX_ARCHIVE_SINGLE_ENTRY_BYTES = 8 * 1024 * 1024
HARD_MAX_PDF_PAGES = 100


# ============================================================
# FORMATS D'ECRITURE SUPPORTES EN DUR
# ============================================================

HARD_WRITABLE_TEXT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".tsv", ".json",
    ".xml", ".yaml", ".yml", ".log", ".ini",
    ".cfg", ".conf", ".toml", ".ics", ".vcf",
    ".html", ".htm", ".rtf", ".eml",
}

HARD_MAX_CREATE_FILE_CONTENT_BYTES = 1024 * 1024


# ============================================================
# MODIFICATION DE FICHIERS TEXTE SUPPORTES EN DUR
# ============================================================

HARD_MODIFIABLE_TEXT_EXTENSIONS = set(
    HARD_WRITABLE_TEXT_EXTENSIONS
)

HARD_APPEND_SAFE_EXTENSIONS = {
    ".txt", ".md", ".csv", ".tsv", ".log",
}

HARD_MAX_MODIFY_EXISTING_BYTES = 1024 * 1024
HARD_MAX_MODIFY_ADDED_BYTES = 256 * 1024
HARD_MAX_MODIFY_RESULT_BYTES = 1024 * 1024



# ============================================================
# CORBEILLE WINDOWS
# ============================================================

FO_DELETE = 0x0003

FOF_SILENT = 0x0004
FOF_NOCONFIRMATION = 0x0010
FOF_ALLOWUNDO = 0x0040
FOF_FILESONLY = 0x0080
FOF_NOERRORUI = 0x0400

DRIVE_FIXED = 3


class SHFILEOPSTRUCTW(ctypes.Structure):

    _fields_ = [
        (
            "hwnd",
            wintypes.HWND
        ),
        (
            "wFunc",
            wintypes.UINT
        ),
        (
            "pFrom",
            wintypes.LPCWSTR
        ),
        (
            "pTo",
            wintypes.LPCWSTR
        ),
        (
            "fFlags",
            wintypes.WORD
        ),
        (
            "fAnyOperationsAborted",
            wintypes.BOOL
        ),
        (
            "hNameMappings",
            ctypes.c_void_p
        ),
        (
            "lpszProgressTitle",
            wintypes.LPCWSTR
        ),
    ]


# ============================================================
# JSON SECURISE
# ============================================================

def load_json_file(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        if isinstance(
            data,
            dict
        ):

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

    config = load_json_file(
        AGENT_CONFIG_FILE
    )

    return bool(
        config
        .get(
            "security",
            {}
        )
        .get(
            "allow_filesystem",
            False
        )
    )


def get_filesystem_config():

    permissions = load_json_file(
        PERMISSIONS_FILE
    )

    filesystem = permissions.get(
        "filesystem",
        {}
    )

    if not isinstance(
        filesystem,
        dict
    ):

        return {}

    return filesystem


def is_filesystem_enabled():

    if not is_filesystem_globally_enabled():

        return False

    return bool(
        get_filesystem_config()
        .get(
            "enabled",
            False
        )
    )


def has_filesystem_permission(
    permission_name
):

    if not is_filesystem_enabled():

        return False

    return bool(
        get_filesystem_config()
        .get(
            permission_name,
            False
        )
    )


# ============================================================
# PERMISSIONS PAR RACINE
# ============================================================

def get_root_permissions(
    root_name
):

    filesystem = get_filesystem_config()

    roots = filesystem.get(
        "roots",
        {}
    )

    if not isinstance(
        roots,
        dict
    ):

        return {}

    permission = roots.get(
        root_name,
        {}
    )

    if not isinstance(
        permission,
        dict
    ):

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
        permission.get(
            "enabled",
            False
        )
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
        .get(
            "creation_policy",
            {}
        )
    )

    if not isinstance(
        policy,
        dict
    ):

        return {}

    return policy


def get_move_policy():

    policy = (
        get_filesystem_config()
        .get(
            "move_policy",
            {}
        )
    )

    if not isinstance(
        policy,
        dict
    ):

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

    if not isinstance(
        policy,
        dict
    ):

        return {}

    return policy


def get_copy_policy():

    policy = (
        get_filesystem_config()
        .get(
            "copy_policy",
            {}
        )
    )

    if not isinstance(
        policy,
        dict
    ):

        return {}

    return policy


def get_rename_policy():

    policy = (
        get_filesystem_config()
        .get(
            "rename_policy",
            {}
        )
    )

    if not isinstance(
        policy,
        dict
    ):

        return {}

    return policy


def get_delete_policy():

    policy = (
        get_filesystem_config()
        .get(
            "delete_policy",
            {}
        )
    )

    if not isinstance(
        policy,
        dict
    ):

        return {}

    return policy




def get_read_content_policy():

    policy = (
        get_filesystem_config()
        .get(
            "read_content_policy",
            {}
        )
    )

    if not isinstance(
        policy,
        dict
    ):

        return {}

    return policy


def get_create_file_policy():

    policy = (
        get_filesystem_config()
        .get(
            "create_file_policy",
            {}
        )
    )

    if not isinstance(
        policy,
        dict
    ):

        return {}

    return policy


def get_modify_file_policy():

    policy = (
        get_filesystem_config()
        .get(
            "modify_file_policy",
            {}
        )
    )

    if not isinstance(
        policy,
        dict
    ):

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

    if not isinstance(
        policy,
        dict
    ):

        return {}

    return policy


# ============================================================
# BARRIERES DURES DU SYSTEME
# ============================================================

def normalized_path_string(
    path
):

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
            normalized_path_string(
                path_a
            )
            ==
            normalized_path_string(
                path_b
            )
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

        child_value = (
            normalized_path_string(
                path
            )
        )

        parent_value = (
            normalized_path_string(
                parent
            )
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

        value = os.environ.get(
            variable
        )

        if value:

            protected.append(
                Path(
                    value
                )
            )

    user_profile = os.environ.get(
        "USERPROFILE"
    )

    if user_profile:

        user_profile_path = Path(
            user_profile
        )

        protected.append(
            user_profile_path
            /
            "AppData"
        )

    # --------------------------------------------------------
    # Projet AgentLocal toujours protégé
    # --------------------------------------------------------

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
        drive_root
        /
        "$Recycle.Bin"
    )

    protected.append(
        drive_root
        /
        "System Volume Information"
    )

    return protected


def is_hard_protected_path(
    path
):
    """
    Protection indépendante de permissions.json.
    """

    try:

        path = Path(
            path
        )

    except TypeError:

        return True

    # --------------------------------------------------------
    # Racine du disque
    # --------------------------------------------------------

    try:

        if (
            path.anchor
            and
            is_same_path(
                path,
                Path(
                    path.anchor
                )
            )
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
            Path(
                user_profile
            )
        ):

            return True

    # --------------------------------------------------------
    # Zones système
    # --------------------------------------------------------

    for protected_path in (
        get_hard_protected_paths()
    ):

        if is_same_or_descendant(
            path,
            protected_path
        ):

            return True

    return False


# ============================================================
# ATTRIBUTS WINDOWS
# ============================================================

def get_file_attributes(
    path
):

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


def is_reparse_point(
    path
):
    """
    Bloque :
    - liens symboliques ;
    - junctions ;
    - autres reparse points Windows.
    """

    try:

        if Path(
            path
        ).is_symlink():

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


def is_hidden_or_system(
    path
):

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

    if isinstance(
        configured,
        list
    ):

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

            if not extension.startswith(
                "."
            ):

                extension = (
                    "."
                    +
                    extension
                )

            blocked.add(
                extension
            )

    return blocked


def is_blocked_file_type(
    file_name
):

    try:

        extension = (
            Path(
                file_name
            )
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
# CHAINE D'EXTENSIONS
# ============================================================

def get_extension_chain(
    file_name
):
    """
    Exemple :

    archive.tar.gz
    -> .tar.gz

    Évite de considérer seulement .gz lors
    d'un renommage contrôlé.
    """

    try:

        suffixes = Path(
            file_name
        ).suffixes

    except TypeError:

        return ""

    return "".join(
        suffix.casefold()
        for suffix in suffixes
    )


# ============================================================
# CATEGORIES MEDIA
# ============================================================

def get_media_category(
    file_name
):

    extension = (
        Path(
            file_name
        )
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

    for category, extensions in (
        categories.items()
    ):

        if not isinstance(
            extensions,
            list
        ):

            continue

        normalized_extensions = {
            str(
                item
            )
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
        (
            "Data1",
            wintypes.DWORD
        ),
        (
            "Data2",
            wintypes.WORD
        ),
        (
            "Data3",
            wintypes.WORD
        ),
        (
            "Data4",
            ctypes.c_ubyte * 8
        ),
    ]


def guid_from_string(
    guid_string
):

    value = uuid.UUID(
        guid_string.strip(
            "{}"
        )
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

    for index in range(
        8
    ):

        guid.Data4[
            index
        ] = bytes_le[
            8 + index
        ]

    return guid


# ============================================================
# KNOWN FOLDERS WINDOWS
# ============================================================

def get_windows_known_folder(
    root_name
):

    guid_string = (
        KNOWN_FOLDER_GUIDS.get(
            root_name
        )
    )

    if not guid_string:

        return None

    try:

        shell32 = (
            ctypes
            .windll
            .shell32
        )

        ole32 = (
            ctypes
            .windll
            .ole32
        )

        guid = guid_from_string(
            guid_string
        )

        path_pointer = (
            ctypes
            .c_void_p()
        )

        shell32.SHGetKnownFolderPath.argtypes = [
            ctypes.POINTER(
                GUID
            ),
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
                ctypes.byref(
                    guid
                ),
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

            folder_path = (
                ctypes
                .wstring_at(
                    path_pointer.value
                )
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
        "desktop": (
            base
            /
            "Desktop"
        ),
        "documents": (
            base
            /
            "Documents"
        ),
        "downloads": (
            base
            /
            "Downloads"
        ),
        "pictures": (
            base
            /
            "Pictures"
        ),
        "videos": (
            base
            /
            "Videos"
        ),
        "music": (
            base
            /
            "Music"
        ),
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

    # --------------------------------------------------------
    # Jamais de chemin arbitraire
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Barrière système indépendante du JSON
    # --------------------------------------------------------

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

    if len(
        value
    ) > 180:

        return (
            False,
            "Le nom est trop long."
        )

    # --------------------------------------------------------
    # Aucun chemin
    # --------------------------------------------------------

    if (
        "/"
        in
        value
        or
        "\\"
        in
        value
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

    if (
        "*"
        in
        value
        or
        "?"
        in
        value
    ):

        return (
            False,
            "Les jokers sont interdits."
        )

    # --------------------------------------------------------
    # Caractères Windows interdits
    #
    # ':' bloque également Alternate Data Streams
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
        value.endswith(
            " "
        )
        or
        value.endswith(
            "."
        )
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
        .split(
            "."
        )[0]
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

    valid, result = (
        validate_simple_name(
            file_name
        )
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
                f"Le type de fichier "
                f"'{Path(result).suffix}' "
                "est protégé et ne peut pas "
                "être manipulé."
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
            Path(
                root_path
            )
            .resolve()
        )

        resolved_target = (
            Path(
                target_path
            )
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
# DISQUE LOCAL FIXE ?
# ============================================================

def is_local_fixed_drive(
    path
):
    """
    La suppression contrôlée est refusée
    sur :
    - lecteur réseau ;
    - clé USB ;
    - chemin UNC ;
    - média amovible.

    Cela évite les comportements de Corbeille
    différents selon le support.
    """

    try:

        path = Path(
            path
        )

        anchor = path.anchor

        if not anchor:

            return False

        if anchor.startswith(
            "\\\\"
        ):

            return False

        drive_type = (
            ctypes
            .windll
            .kernel32
            .GetDriveTypeW(
                anchor
            )
        )

        return (
            drive_type
            ==
            DRIVE_FIXED
        )

    except Exception:

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
        str(
            source_root
        )
        .strip()
        .lower()
    )

    destination_root = (
        str(
            destination_root
        )
        .strip()
        .lower()
    )

    if (
        source_root
        ==
        destination_root
    ):

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
    # Toutes les racines utilisateur activées
    # peuvent communiquer entre elles.
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
    # Compatibilité avec ancien allowed_transfers
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
# COPIE ENTRE RACINES AUTORISEE ?
# ============================================================

def is_cross_root_copy_allowed(
    source_root,
    destination_root
):

    if not is_filesystem_enabled():
        return False

    if not has_filesystem_permission(
        "can_copy"
    ):
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

    policy = get_copy_policy()

    if not policy.get(
        "enabled",
        False
    ):
        return False

    if not policy.get(
        "allow_between_enabled_user_roots",
        False
    ):
        return False

    if not has_root_permission(
        source_root,
        "can_copy_out"
    ):
        return False

    if not has_root_permission(
        destination_root,
        "can_receive_copy"
    ):
        return False

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


# ============================================================
# LISTER UN DOSSIER
# ============================================================

def list_directory(
    root_name
):

    root_name = (
        str(
            root_name
        )
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

        if is_hard_protected_path(
            item
        ):

            protected_count += 1
            continue

        if is_reparse_point(
            item
        ):

            protected_count += 1
            continue

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
                item_type
                ==
                "fichier"
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

        lines.append(
            ""
        )

        lines.append(
            (
                f"{protected_count} élément(s) "
                "protégé(s) ont été ignorés."
            )
        )

    return (
        True,
        "\n".join(
            lines
        )
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
        str(
            root_name
        )
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
        str(
            root_name
        )
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

        resolved_root = (
            root_path
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
        str(
            source_root
        )
        .strip()
        .lower()
    )

    destination_root = (
        str(
            destination_root
        )
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
            str(
                destination_folder_name
            )
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

            validated_destination_folder = (
                result
            )

    source_root_path = (
        resolve_allowed_root(
            source_root
        )
    )

    destination_root_path = (
        resolve_allowed_root(
            destination_root
        )
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

    # ========================================================
    # DESTINATION
    # ========================================================

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
                (
                    "Le sous-dossier destination "
                    "est interdit."
                )
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

    # ========================================================
    # VERIFICATION FINALE
    # ========================================================

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
                (
                    "La destination sort "
                    "de la zone autorisée."
                )
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

    # ========================================================
    # DEPLACEMENT
    # ========================================================

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
# COPIE CONTROLEE ENTRE DEUX RACINES
# ============================================================

def copy_file_between_roots(
    source_root,
    destination_root,
    file_name,
    destination_folder_name=None,
    explicit_user_command=False,
    source="unspecified"
):
    """
    Copie UN fichier utilisateur entre deux racines autorisées.

    Garanties :
    - commande manuelle explicite obligatoire ;
    - un seul fichier ;
    - aucun chemin arbitraire ;
    - aucun joker ;
    - aucun dossier ;
    - pas de lien, junction ou reparse point ;
    - pas de fichier caché ou système ;
    - pas de type exécutable/script/raccourci protégé ;
    - aucun écrasement ;
    - nom du fichier conservé ;
    - source jamais supprimée ;
    - copie par flux, sans charger le fichier entier en mémoire.
    """

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

    normalized_source = (
        str(source)
        .strip()
        .lower()
    )

    # ========================================================
    # INTERRUPTEURS ET POLITIQUE
    # ========================================================

    if not is_filesystem_enabled():
        return (
            False,
            "L'accès au système de fichiers est désactivé."
        )

    if not has_filesystem_permission(
        "can_copy"
    ):
        return (
            False,
            "La copie de fichiers est désactivée."
        )

    policy = get_copy_policy()

    if not policy.get(
        "enabled",
        False
    ):
        return (
            False,
            "La politique de copie est désactivée."
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
            "La copie nécessite une commande explicite de l'utilisateur."
        )

    # La première version de la copie reste exclusivement manuelle.
    if normalized_source != "manual":
        return (
            False,
            (
                "La copie de fichiers n'est autorisée que depuis "
                "une commande manuelle explicite."
            )
        )

    if source_root == destination_root:
        return (
            False,
            "Les deux racines doivent être différentes."
        )

    if policy.get(
        "maximum_items_per_command",
        1
    ) != 1:
        return (
            False,
            (
                "La politique de copie n'est pas assez restrictive : "
                "un seul fichier doit être autorisé par commande."
            )
        )

    if not policy.get(
        "preserve_original_filename",
        True
    ):
        return (
            False,
            "La copie doit conserver le nom d'origine du fichier."
        )

    if policy.get(
        "allow_rename_during_copy",
        False
    ):
        return (
            False,
            "Le renommage pendant la copie est interdit."
        )

    if policy.get(
        "allow_overwrite",
        False
    ):
        return (
            False,
            (
                "Configuration dangereuse détectée : "
                "l'écrasement doit rester interdit."
            )
        )

    if not is_cross_root_copy_allowed(
        source_root,
        destination_root
    ):
        return (
            False,
            "Cette copie entre dossiers n'est pas autorisée."
        )

    # ========================================================
    # NOM DU FICHIER
    # ========================================================

    valid, validated_file = validate_file_name(
        file_name
    )

    if not valid:
        return (
            False,
            validated_file
        )

    # ========================================================
    # SOUS-DOSSIER DESTINATION FACULTATIF
    # ========================================================

    validated_destination_folder = None

    if destination_folder_name is not None:

        destination_folder_name = (
            str(destination_folder_name)
            .strip()
        )

        if destination_folder_name:

            if not policy.get(
                "destination_subfolder_optional",
                True
            ):
                return (
                    False,
                    "Les sous-dossiers de destination sont désactivés."
                )

            valid, result = validate_folder_name(
                destination_folder_name
            )

            if not valid:
                return (
                    False,
                    result
                )

            validated_destination_folder = result

    # ========================================================
    # RACINES
    # ========================================================

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
            "Une racine est protégée, inconnue ou introuvable."
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

    # ========================================================
    # SOURCE
    # ========================================================

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
                "Le fichier source doit se trouver directement "
                "dans la racine autorisée."
            )
        )

    if not source_path.exists():
        return (
            False,
            (
                f"Le fichier '{validated_file}' n'existe pas dans "
                f"{DISPLAY_NAMES.get(source_root, source_root)}."
            )
        )

    if is_reparse_point(
        source_path
    ):
        return (
            False,
            "Les liens, junctions et reparse points sont protégés."
        )

    if is_hidden_or_system(
        source_path
    ):
        return (
            False,
            "Les fichiers cachés ou système sont protégés."
        )

    if not source_path.is_file():
        return (
            False,
            "La source n'est pas un fichier autorisé."
        )

    if is_blocked_file_type(
        validated_file
    ):
        return (
            False,
            "Ce type de fichier est protégé et ne peut pas être copié."
        )

    # ========================================================
    # DESTINATION
    # ========================================================

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
                    f"Le dossier '{validated_destination_folder}' "
                    f"n'existe pas dans "
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
        destination_folder = destination_root_path

    destination_path = (
        destination_folder
        /
        validated_file
    )

    # os.path.lexists bloque aussi un lien cassé déjà présent.
    if os.path.lexists(
        str(destination_path)
    ):
        return (
            False,
            (
                f"'{validated_file}' existe déjà dans la destination. "
                "Aucun écrasement n'est autorisé."
            )
        )

    # ========================================================
    # VERIFICATION FINALE DES CHEMINS
    # ========================================================

    try:
        resolved_source_root = source_root_path.resolve(
            strict=True
        )

        resolved_destination_root = destination_root_path.resolve(
            strict=True
        )

        resolved_source = source_path.resolve(
            strict=True
        )

        resolved_destination_folder = destination_folder.resolve(
            strict=True
        )

    except (
        OSError,
        RuntimeError,
    ):
        return (
            False,
            "Impossible de vérifier les chemins."
        )

    if resolved_source.parent != resolved_source_root:
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
            "Une zone système ou protégée a été détectée."
        )

    # Vérification immédiate avant ouverture pour réduire
    # la fenêtre de remplacement de la source.
    if (
        is_reparse_point(source_path)
        or
        is_hidden_or_system(source_path)
    ):
        return (
            False,
            "Le fichier source a changé pendant la vérification."
        )

    try:
        source_before = os.stat(
            source_path,
            follow_symlinks=False
        )
    except OSError as error:
        return (
            False,
            f"Impossible de vérifier le fichier source : {error}"
        )

    # ========================================================
    # COPIE PAR FLUX AVEC CREATION EXCLUSIVE
    # ========================================================

    source_fd = None
    destination_fd = None
    destination_created = False

    read_flags = (
        os.O_RDONLY
        |
        getattr(
            os,
            "O_BINARY",
            0
        )
    )

    write_flags = (
        os.O_WRONLY
        |
        os.O_CREAT
        |
        os.O_EXCL
        |
        getattr(
            os,
            "O_BINARY",
            0
        )
    )

    try:
        source_fd = os.open(
            source_path,
            read_flags
        )

        opened_source = os.fstat(
            source_fd
        )

        if not stat.S_ISREG(
            opened_source.st_mode
        ):
            raise OSError(
                "La source ouverte n'est plus un fichier ordinaire."
            )

        # Défense contre un remplacement entre stat() et open().
        if (
            getattr(source_before, "st_dev", None)
            !=
            getattr(opened_source, "st_dev", None)
            or
            getattr(source_before, "st_ino", None)
            !=
            getattr(opened_source, "st_ino", None)
        ):
            raise OSError(
                "Le fichier source a changé avant la copie."
            )

        destination_fd = os.open(
            destination_path,
            write_flags,
            0o600
        )

        destination_created = True

        buffer_size = 1024 * 1024

        while True:
            chunk = os.read(
                source_fd,
                buffer_size
            )

            if not chunk:
                break

            offset = 0

            while offset < len(chunk):
                written = os.write(
                    destination_fd,
                    chunk[offset:]
                )

                if written <= 0:
                    raise OSError(
                        "Écriture interrompue pendant la copie."
                    )

                offset += written

        os.fsync(
            destination_fd
        )

        source_after_open = os.fstat(
            source_fd
        )

        if policy.get(
            "verify_source_unchanged_after_copy",
            True
        ):
            if (
                source_after_open.st_size
                !=
                source_before.st_size
                or
                getattr(source_after_open, "st_mtime_ns", 0)
                !=
                getattr(source_before, "st_mtime_ns", 0)
            ):
                raise OSError(
                    "Le fichier source a été modifié pendant la copie."
                )

    except (
        OSError,
        PermissionError,
    ) as error:

        if destination_fd is not None:
            try:
                os.close(
                    destination_fd
                )
            except OSError:
                pass
            destination_fd = None

        if source_fd is not None:
            try:
                os.close(
                    source_fd
                )
            except OSError:
                pass
            source_fd = None

        # Nettoyage uniquement du fichier que CETTE opération
        # vient de créer de manière exclusive.
        if destination_created:
            try:
                os.remove(
                    destination_path
                )
            except OSError:
                pass

        return (
            False,
            f"Impossible de copier le fichier : {error}"
        )

    finally:
        if destination_fd is not None:
            try:
                os.close(
                    destination_fd
                )
            except OSError:
                pass

        if source_fd is not None:
            try:
                os.close(
                    source_fd
                )
            except OSError:
                pass

    # ========================================================
    # VALIDATION DU RESULTAT
    # ========================================================

    try:
        destination_stats = os.stat(
            destination_path,
            follow_symlinks=False
        )
    except OSError as error:
        return (
            False,
            (
                "La copie a été effectuée mais son résultat "
                f"ne peut pas être vérifié : {error}"
            )
        )

    if not stat.S_ISREG(
        destination_stats.st_mode
    ):
        return (
            False,
            "Le résultat de la copie n'est pas un fichier ordinaire."
        )

    if destination_stats.st_size != source_before.st_size:
        return (
            False,
            "La taille du fichier copié ne correspond pas à la source."
        )

    if validated_destination_folder:
        destination_description = (
            f"{DISPLAY_NAMES.get(destination_root, destination_root)}"
            f"\\{validated_destination_folder}"
        )
    else:
        destination_description = DISPLAY_NAMES.get(
            destination_root,
            destination_root
        )

    return (
        True,
        (
            f"Le fichier '{validated_file}' a été copié de "
            f"{DISPLAY_NAMES.get(source_root, source_root)} vers "
            f"{destination_description}. "
            "Le fichier source a été conservé."
        )
    )


# ============================================================
# RECHERCHE CONTROLEE POUR RENOMMAGE SANS RACINE
# ============================================================

def find_rename_candidates(
    file_name
):
    """
    Recherche un nom de fichier uniquement dans les six
    racines utilisateur autorisées.

    Règles :
    - nom simple uniquement ;
    - enfant direct de la racine ;
    - fichier normal uniquement ;
    - aucune traversée de chemin ;
    - aucun lien / junction / reparse point ;
    - aucun fichier caché ou système ;
    - uniquement dans une racine où le renommage est autorisé.

    Retourne une liste de tuples :
        (root_name, full_path)
    """

    if not is_filesystem_enabled():
        return []

    if not has_filesystem_permission(
        "can_rename"
    ):
        return []

    valid, validated_file = (
        validate_file_name(
            file_name
        )
    )

    if not valid:
        return []

    policy = get_rename_policy()

    if not policy.get(
        "enabled",
        False
    ):
        return []

    if not policy.get(
        "allow_auto_root_discovery",
        False
    ):
        return []

    # Barrière dure : même si le JSON est modifié, la recherche
    # ne peut jamais sortir de ces six racines.
    hard_allowed_roots = (
        "desktop",
        "documents",
        "downloads",
        "pictures",
        "videos",
        "music",
    )

    configured_roots = policy.get(
        "auto_root_discovery_roots",
        list(hard_allowed_roots)
    )

    if not isinstance(
        configured_roots,
        list
    ):
        configured_roots = list(
            hard_allowed_roots
        )

    search_roots = [
        root
        for root in hard_allowed_roots
        if root in configured_roots
    ]

    matches = []

    for root_name in search_roots:

        if not has_root_permission(
            root_name,
            "can_rename"
        ):
            continue

        root_path = resolve_allowed_root(
            root_name
        )

        if root_path is None:
            continue

        if not root_path.exists():
            continue

        candidate = (
            root_path
            /
            validated_file
        )

        if not is_direct_child(
            root_path,
            candidate
        ):
            continue

        try:
            if not candidate.exists():
                continue

            if not candidate.is_file():
                continue

        except OSError:
            continue

        if is_hard_protected_path(
            candidate
        ):
            continue

        if is_reparse_point(
            candidate
        ):
            continue

        if is_hidden_or_system(
            candidate
        ):
            continue

        try:
            resolved_root = root_path.resolve(
                strict=True
            )

            resolved_candidate = candidate.resolve(
                strict=True
            )

        except (
            OSError,
            RuntimeError,
        ):
            continue

        if (
            resolved_candidate.parent
            !=
            resolved_root
        ):
            continue

        matches.append(
            (
                root_name,
                resolved_candidate
            )
        )

    return matches


def rename_file_auto(
    old_name,
    new_name,
    explicit_user_command=False
):
    """
    Renommage avec recherche automatique de la racine.

    La racine peut être omise par l'utilisateur. AgentLocal
    recherche alors le fichier uniquement dans les six dossiers
    utilisateur autorisés.

    - 0 correspondance : refus ;
    - 1 correspondance : renommage dans cette racine ;
    - 2+ correspondances : refus et demande de préciser la racine.
    """

    if not is_filesystem_enabled():
        return (
            False,
            (
                "L'accès au système de fichiers "
                "est désactivé."
            )
        )

    if not has_filesystem_permission(
        "can_rename"
    ):
        return (
            False,
            "Le renommage de fichiers est désactivé."
        )

    policy = get_rename_policy()

    if not policy.get(
        "enabled",
        False
    ):
        return (
            False,
            "La politique de renommage est désactivée."
        )

    if not policy.get(
        "allow_auto_root_discovery",
        False
    ):
        return (
            False,
            (
                "La recherche automatique de l'emplacement "
                "du fichier est désactivée."
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
                "Le renommage nécessite une commande "
                "explicite de l'utilisateur."
            )
        )

    # La politique doit rester stricte : une seule correspondance
    # est nécessaire pour agir automatiquement.
    if policy.get(
        "maximum_auto_root_matches",
        1
    ) != 1:
        return (
            False,
            (
                "La politique de recherche automatique n'est "
                "pas assez restrictive."
            )
        )

    valid, validated_old_name = (
        validate_file_name(
            old_name
        )
    )

    if not valid:
        return (
            False,
            validated_old_name
        )

    valid, validated_new_name = (
        validate_file_name(
            new_name
        )
    )

    if not valid:
        return (
            False,
            validated_new_name
        )

    if (
        validated_old_name.casefold()
        ==
        validated_new_name.casefold()
    ):
        return (
            False,
            (
                "L'ancien et le nouveau nom sont identiques "
                "ou ne diffèrent que par la casse."
            )
        )

    if not policy.get(
        "allow_extension_change",
        False
    ):
        if (
            get_extension_chain(
                validated_old_name
            )
            !=
            get_extension_chain(
                validated_new_name
            )
        ):
            return (
                False,
                "Le changement d'extension est interdit."
            )

    matches = find_rename_candidates(
        validated_old_name
    )

    if not matches:
        return (
            False,
            (
                f"Le fichier '{validated_old_name}' n'a pas été trouvé "
                "directement dans Bureau, Documents, Téléchargements, "
                "Images, Vidéos ou Musique."
            )
        )

    if len(matches) > 1:
        locations = ", ".join(
            DISPLAY_NAMES.get(
                root_name,
                root_name
            )
            for root_name, _ in matches
        )

        return (
            False,
            (
                f"Plusieurs fichiers nommés '{validated_old_name}' "
                f"ont été trouvés : {locations}. "
                "Précise le dossier pour éviter de renommer "
                "le mauvais fichier."
            )
        )

    resolved_root, _ = matches[0]

    return rename_file(
        resolved_root,
        validated_old_name,
        validated_new_name,
        explicit_user_command=True
    )


# ============================================================
# RENOMMAGE ULTRA CONTROLE
# ============================================================

def rename_file(
    root_name,
    old_name,
    new_name,
    explicit_user_command=False
):
    """
    Renomme UN fichier directement présent dans
    une racine utilisateur autorisée.

    Protections :
    - commande explicite obligatoire ;
    - un seul fichier ;
    - aucun chemin ;
    - aucun joker ;
    - aucun dossier ;
    - pas de lien/reparse point ;
    - pas de fichier caché/système ;
    - aucune modification d'extension ;
    - aucun écrasement ;
    - aucune extension dangereuse ;
    - aucune automatisation.
    """

    root_name = (
        str(
            root_name
        )
        .strip()
        .lower()
    )

    # ========================================================
    # SYSTEME FICHIERS
    # ========================================================

    if not is_filesystem_enabled():

        return (
            False,
            (
                "L'accès au système de fichiers "
                "est désactivé."
            )
        )

    # ========================================================
    # PERMISSION GLOBALE
    # ========================================================

    if not has_filesystem_permission(
        "can_rename"
    ):

        return (
            False,
            (
                "Le renommage de fichiers "
                "est désactivé."
            )
        )

    # ========================================================
    # PERMISSION RACINE
    # ========================================================

    if not has_root_permission(
        root_name,
        "can_rename"
    ):

        return (
            False,
            (
                "Le renommage n'est pas autorisé dans "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    # ========================================================
    # POLITIQUE
    # ========================================================

    policy = get_rename_policy()

    if not policy.get(
        "enabled",
        False
    ):

        return (
            False,
            (
                "La politique de renommage "
                "est désactivée."
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
                "Le renommage nécessite une commande "
                "explicite de l'utilisateur."
            )
        )

    # ========================================================
    # VALIDATION DES DEUX NOMS
    # ========================================================

    valid, validated_old_name = (
        validate_file_name(
            old_name
        )
    )

    if not valid:

        return (
            False,
            validated_old_name
        )

    valid, validated_new_name = (
        validate_file_name(
            new_name
        )
    )

    if not valid:

        return (
            False,
            validated_new_name
        )

    # ========================================================
    # MEME NOM / CHANGEMENT DE CASSE
    # ========================================================

    if (
        validated_old_name.casefold()
        ==
        validated_new_name.casefold()
    ):

        if (
            validated_old_name
            ==
            validated_new_name
        ):

            return (
                False,
                (
                    "L'ancien et le nouveau nom "
                    "sont identiques."
                )
            )

        return (
            False,
            (
                "Le renommage qui modifie uniquement "
                "les majuscules/minuscules est interdit."
            )
        )

    # ========================================================
    # EXTENSION STRICTEMENT IDENTIQUE
    # ========================================================

    if not policy.get(
        "allow_extension_change",
        False
    ):

        old_extension = (
            get_extension_chain(
                validated_old_name
            )
        )

        new_extension = (
            get_extension_chain(
                validated_new_name
            )
        )

        if (
            old_extension
            !=
            new_extension
        ):

            return (
                False,
                (
                    "Le changement d'extension "
                    "est interdit."
                )
            )

    # ========================================================
    # RACINE
    # ========================================================

    root_path = resolve_allowed_root(
        root_name
    )

    if root_path is None:

        return (
            False,
            (
                "Dossier racine protégé "
                "ou introuvable."
            )
        )

    if not root_path.exists():

        return (
            False,
            (
                "Le dossier racine "
                "n'existe pas."
            )
        )

    source_path = (
        root_path
        /
        validated_old_name
    )

    destination_path = (
        root_path
        /
        validated_new_name
    )

    # ========================================================
    # ENFANTS DIRECTS UNIQUEMENT
    # ========================================================

    if not is_direct_child(
        root_path,
        source_path
    ):

        return (
            False,
            (
                "Le fichier source doit se trouver "
                "directement dans la racine autorisée."
            )
        )

    if not is_direct_child(
        root_path,
        destination_path
    ):

        return (
            False,
            (
                "Le nouveau nom sort "
                "de la zone autorisée."
            )
        )

    # ========================================================
    # EXISTENCE SOURCE
    # ========================================================

    if not source_path.exists():

        return (
            False,
            (
                f"Le fichier '{validated_old_name}' "
                "n'existe pas dans "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    # ========================================================
    # FICHIERS UNIQUEMENT
    # ========================================================

    if not source_path.is_file():

        return (
            False,
            (
                "Le renommage des dossiers "
                "n'est pas autorisé."
            )
        )

    # ========================================================
    # REPARSE / SYMLINK / JUNCTION
    # ========================================================

    if is_reparse_point(
        source_path
    ):

        return (
            False,
            (
                "Les liens, junctions et reparse points "
                "ne peuvent pas être renommés."
            )
        )

    # ========================================================
    # CACHE / SYSTEME
    # ========================================================

    if is_hidden_or_system(
        source_path
    ):

        return (
            False,
            (
                "Les fichiers cachés ou système "
                "ne peuvent pas être renommés."
            )
        )

    # ========================================================
    # AUCUN ECRASEMENT
    # ========================================================

    if destination_path.exists():

        return (
            False,
            (
                f"'{validated_new_name}' existe déjà. "
                "Aucun écrasement n'est autorisé."
            )
        )

    # ========================================================
    # RESOLUTION FINALE
    # ========================================================

    try:

        resolved_root = (
            root_path
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

    except (
        OSError,
        RuntimeError,
    ):

        return (
            False,
            (
                "Impossible de vérifier "
                "le fichier source."
            )
        )

    if (
        resolved_source.parent
        !=
        resolved_root
    ):

        return (
            False,
            (
                "Le fichier source sort "
                "de la zone autorisée."
            )
        )

    if is_hard_protected_path(
        resolved_source
    ):

        return (
            False,
            (
                "Le fichier appartient "
                "à une zone protégée."
            )
        )

    if is_hard_protected_path(
        destination_path
    ):

        return (
            False,
            (
                "La destination appartient "
                "à une zone protégée."
            )
        )

    # ========================================================
    # RENOMMAGE
    # ========================================================

    try:

        os.rename(
            source_path,
            destination_path
        )

    except (
        OSError,
        PermissionError,
    ) as error:

        return (
            False,
            (
                "Impossible de renommer le fichier : "
                f"{error}"
            )
        )

    return (
        True,
        (
            f"Le fichier '{validated_old_name}' "
            "a été renommé en "
            f"'{validated_new_name}' dans "
            f"{DISPLAY_NAMES.get(root_name, root_name)}."
        )
    )


# ============================================================
# ENVOI VERS LA CORBEILLE WINDOWS
# ============================================================

def send_file_to_recycle_bin(
    file_path
):
    """
    Demande au Shell Windows d'envoyer le fichier
    vers la Corbeille.

    Cette fonction :
    - n'utilise pas os.remove ;
    - n'utilise pas Path.unlink ;
    - n'utilise pas PowerShell ;
    - n'utilise pas CMD ;
    - ne possède aucune fonction de suppression définitive.
    """

    try:

        file_path = (
            Path(
                file_path
            )
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
                "Impossible de résoudre "
                "le chemin du fichier."
            )
        )

    if not file_path.exists():

        return (
            False,
            (
                "Le fichier n'existe plus."
            )
        )

    if not file_path.is_file():

        return (
            False,
            (
                "Seuls les fichiers peuvent "
                "être envoyés à la Corbeille."
            )
        )

    # --------------------------------------------------------
    # Par sécurité, uniquement disque local fixe.
    # --------------------------------------------------------

    if not is_local_fixed_drive(
        file_path
    ):

        return (
            False,
            (
                "La suppression contrôlée est limitée "
                "aux disques locaux fixes. "
                "Les lecteurs réseau et supports "
                "amovibles sont refusés."
            )
        )

    try:

        shell32 = (
            ctypes
            .windll
            .shell32
        )

        shell32.SHFileOperationW.argtypes = [
            ctypes.POINTER(
                SHFILEOPSTRUCTW
            )
        ]

        shell32.SHFileOperationW.restype = (
            ctypes.c_int
        )

        # ----------------------------------------------------
        # SHFileOperation attend une liste de chemins
        # terminée par deux caractères NULL.
        # --------------------------------------------------------

        source_buffer = (
            ctypes
            .create_unicode_buffer(
                str(
                    file_path
                )
                +
                "\0\0"
            )
        )

        operation = SHFILEOPSTRUCTW()

        operation.hwnd = None
        operation.wFunc = FO_DELETE

        operation.pFrom = ctypes.cast(
            source_buffer,
            wintypes.LPCWSTR
        )

        operation.pTo = None

        operation.fFlags = (
            FOF_ALLOWUNDO
            |
            FOF_FILESONLY
            |
            FOF_NOCONFIRMATION
            |
            FOF_SILENT
            |
            FOF_NOERRORUI
        )

        operation.fAnyOperationsAborted = False
        operation.hNameMappings = None
        operation.lpszProgressTitle = None

        result = (
            shell32
            .SHFileOperationW(
                ctypes.byref(
                    operation
                )
            )
        )

    except Exception as error:

        return (
            False,
            (
                "Impossible de contacter "
                "la Corbeille Windows : "
                f"{error}"
            )
        )

    if result != 0:

        return (
            False,
            (
                "Windows a refusé l'envoi "
                "vers la Corbeille. "
                f"Code Windows : {result}"
            )
        )

    if operation.fAnyOperationsAborted:

        return (
            False,
            (
                "L'opération a été annulée "
                "par Windows."
            )
        )

    # --------------------------------------------------------
    # Le fichier ne doit plus exister à son emplacement
    # d'origine après une opération réussie.
    # --------------------------------------------------------

    if file_path.exists():

        return (
            False,
            (
                "Windows indique une opération terminée, "
                "mais le fichier est toujours présent. "
                "La suppression est considérée comme échouée."
            )
        )

    return (
        True,
        None
    )


# ============================================================
# SUPPRESSION CONTROLEE
# ============================================================

def delete_file_to_recycle_bin(
    root_name,
    file_name,
    explicit_user_command=False
):
    """
    Suppression contrôlée.

    Important :
    "supprimer" signifie ici uniquement
    "envoyer vers la Corbeille Windows".

    Aucune suppression définitive n'est implémentée.
    """

    root_name = (
        str(
            root_name
        )
        .strip()
        .lower()
    )

    # ========================================================
    # SYSTEME DE FICHIERS
    # ========================================================

    if not is_filesystem_enabled():

        return (
            False,
            (
                "L'accès au système de fichiers "
                "est désactivé."
            )
        )

    # ========================================================
    # PERMISSION GLOBALE
    # ========================================================

    if not has_filesystem_permission(
        "can_delete"
    ):

        return (
            False,
            (
                "La suppression contrôlée "
                "est désactivée."
            )
        )

    # ========================================================
    # PERMISSION RACINE
    # ========================================================

    if not has_root_permission(
        root_name,
        "can_delete"
    ):

        return (
            False,
            (
                "La suppression n'est pas autorisée dans "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    # ========================================================
    # POLITIQUE
    # ========================================================

    policy = get_delete_policy()

    if not policy.get(
        "enabled",
        False
    ):

        return (
            False,
            (
                "La politique de suppression "
                "est désactivée."
            )
        )

    # --------------------------------------------------------
    # Mode imposé en dur
    # --------------------------------------------------------

    if (
        str(
            policy.get(
                "mode",
                ""
            )
        )
        .strip()
        .lower()
        !=
        "recycle_bin_only"
    ):

        return (
            False,
            (
                "Mode de suppression refusé. "
                "Seule la Corbeille Windows "
                "est autorisée."
            )
        )

    # --------------------------------------------------------
    # Même si le JSON était modifié,
    # cette implémentation ne possède aucune
    # suppression définitive.
    # --------------------------------------------------------

    if policy.get(
        "allow_permanent_delete",
        False
    ):

        return (
            False,
            (
                "Configuration de suppression dangereuse "
                "détectée. La suppression définitive "
                "reste interdite par AgentLocal."
            )
        )

    # ========================================================
    # PREUVE EXPLICITE
    # ========================================================

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
                "La suppression nécessite une commande "
                "explicite de l'utilisateur."
            )
        )

    # ========================================================
    # UN SEUL FICHIER
    # ========================================================

    maximum_items = policy.get(
        "maximum_items_per_command",
        1
    )

    if maximum_items != 1:

        return (
            False,
            (
                "La politique de suppression n'est pas "
                "assez restrictive. "
                "Un seul fichier doit être autorisé."
            )
        )

    # ========================================================
    # VALIDATION DU NOM
    # ========================================================

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

    # ========================================================
    # RACINE
    # ========================================================

    root_path = resolve_allowed_root(
        root_name
    )

    if root_path is None:

        return (
            False,
            (
                "Dossier racine protégé "
                "ou introuvable."
            )
        )

    if not root_path.exists():

        return (
            False,
            (
                "Le dossier racine "
                "n'existe pas."
            )
        )

    source_path = (
        root_path
        /
        validated_file
    )

    # ========================================================
    # FICHIER DIRECT UNIQUEMENT
    # ========================================================

    if not is_direct_child(
        root_path,
        source_path
    ):

        return (
            False,
            (
                "Le fichier doit se trouver directement "
                "dans la racine autorisée."
            )
        )

    # ========================================================
    # EXISTENCE
    # ========================================================

    if not source_path.exists():

        return (
            False,
            (
                f"Le fichier '{validated_file}' "
                "n'existe pas dans "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    # ========================================================
    # PAS DE DOSSIER
    # ========================================================

    if not source_path.is_file():

        return (
            False,
            (
                "La suppression des dossiers "
                "n'est pas autorisée."
            )
        )

    # ========================================================
    # REPARSE / LIEN / JUNCTION
    # ========================================================

    if is_reparse_point(
        source_path
    ):

        return (
            False,
            (
                "Les liens, junctions et reparse points "
                "ne peuvent pas être supprimés."
            )
        )

    # ========================================================
    # CACHE / SYSTEME
    # ========================================================

    if is_hidden_or_system(
        source_path
    ):

        return (
            False,
            (
                "Les fichiers cachés ou système "
                "ne peuvent pas être supprimés."
            )
        )

    # ========================================================
    # TYPE DANGEREUX
    # ========================================================

    if is_blocked_file_type(
        validated_file
    ):

        return (
            False,
            (
                "Ce type de fichier est protégé "
                "et ne peut pas être supprimé."
            )
        )

    # ========================================================
    # RESOLUTION FINALE
    # ========================================================

    try:

        resolved_root = (
            root_path
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

    except (
        OSError,
        RuntimeError,
    ):

        return (
            False,
            (
                "Impossible de vérifier "
                "le chemin du fichier."
            )
        )

    if (
        resolved_source.parent
        !=
        resolved_root
    ):

        return (
            False,
            (
                "Le fichier sort "
                "de la zone autorisée."
            )
        )

    if is_hard_protected_path(
        resolved_source
    ):

        return (
            False,
            (
                "Le fichier appartient "
                "à une zone protégée."
            )
        )

    # ========================================================
    # CORBEILLE WINDOWS
    # ========================================================

    success, error = (
        send_file_to_recycle_bin(
            resolved_source
        )
    )

    if not success:

        return (
            False,
            error
        )

    return (
        True,
        (
            f"Le fichier '{validated_file}' "
            "a été envoyé dans la Corbeille Windows "
            "depuis "
            f"{DISPLAY_NAMES.get(root_name, root_name)}."
        )
    )




# ============================================================
# LECTURE CONTROLEE DU CONTENU D'UN FICHIER
# ============================================================

def get_allowed_read_extensions():
    """
    Retourne uniquement les formats explicitement autorisés
    dans permissions.json ET supportés en dur par AgentLocal.
    """

    policy = get_read_content_policy()

    configured = policy.get(
        "allowed_extensions",
        []
    )

    if not isinstance(
        configured,
        list
    ):
        return set()

    allowed = set()

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
            extension = "." + extension

        if extension in get_blocked_extensions():
            continue

        if extension in HARD_BLOCKED_DOCUMENT_READ_EXTENSIONS:
            continue

        if extension not in HARD_SUPPORTED_READ_EXTENSIONS:
            continue

        allowed.add(
            extension
        )

    return allowed


def get_allowed_read_encodings():
    """
    Liste fermée d'encodages textuels simples.
    """

    policy = get_read_content_policy()

    configured = policy.get(
        "allowed_encodings",
        []
    )

    if not isinstance(
        configured,
        list
    ):
        return []

    allowed = []

    for encoding in configured:

        if not isinstance(
            encoding,
            str
        ):
            continue

        encoding = (
            encoding
            .strip()
            .lower()
        )

        if encoding not in {
            "utf-8",
            "utf-8-sig",
            "cp1252",
        }:
            continue

        if encoding not in allowed:
            allowed.append(
                encoding
            )

    return allowed


def get_positive_read_limit(
    policy,
    key,
    hard_maximum
):
    value = policy.get(
        key,
        0
    )

    if not isinstance(
        value,
        int
    ):
        return None

    if value <= 0:
        return None

    if value > hard_maximum:
        return None

    return value


def looks_like_binary_data(
    data
):
    """
    Détecte un contenu binaire pour les formats qui doivent
    être lus comme texte brut. Les documents structurés connus
    (.docx, .xlsx, .pptx, PDF...) utilisent leur propre lecteur.
    """

    if not isinstance(
        data,
        (bytes, bytearray)
    ):
        return True

    if not data:
        return False

    if b"\x00" in data:
        return True

    allowed_controls = {
        8,
        9,
        10,
        12,
        13,
    }

    suspicious = 0

    for value in data:

        if (
            value < 32
            and
            value not in allowed_controls
        ):
            suspicious += 1

    return (
        suspicious
        / len(data)
        > 0.01
    )


class BoundedTextCollector:
    """
    Construit une sortie sans dépasser la limite imposée.
    """

    def __init__(
        self,
        maximum_characters
    ):
        self.maximum_characters = maximum_characters
        self.parts = []
        self.length = 0
        self.truncated = False

    def add(
        self,
        value,
        separator="\n"
    ):
        if value is None:
            return False

        value = str(
            value
        )

        if not value:
            return True

        prefix = (
            separator
            if self.parts
            else ""
        )

        available = (
            self.maximum_characters
            - self.length
        )

        if available <= 0:
            self.truncated = True
            return False

        combined = prefix + value

        if len(combined) > available:
            self.parts.append(
                combined[:available]
            )
            self.length += available
            self.truncated = True
            return False

        self.parts.append(
            combined
        )
        self.length += len(
            combined
        )
        return True

    def text(self):
        return "".join(
            self.parts
        )


def decode_text_bytes(
    data
):
    encodings = get_allowed_read_encodings()

    if not encodings:
        return (
            False,
            "Aucun encodage de texte autorisé n'est configuré.",
            None
        )

    for encoding in encodings:

        try:
            content = data.decode(
                encoding,
                errors="strict"
            )

            if content.startswith("\ufeff"):
                content = content[1:]

            return (
                True,
                content,
                encoding
            )

        except UnicodeDecodeError:
            continue

    return (
        False,
        (
            "Le fichier n'utilise aucun des encodages "
            "textuels autorisés."
        ),
        None
    )


def normalize_extracted_text(
    value
):
    value = str(
        value or ""
    )

    value = value.replace(
        "\r\n",
        "\n"
    ).replace(
        "\r",
        "\n"
    )

    value = re.sub(
        r"[ \t]+\n",
        "\n",
        value
    )

    value = re.sub(
        r"\n[ \t]+",
        "\n",
        value
    )

    value = re.sub(
        r"\n{3,}",
        "\n\n",
        value
    )

    return value.strip()


def xml_local_name(
    tag
):
    if not isinstance(
        tag,
        str
    ):
        return ""

    return tag.rsplit(
        "}",
        1
    )[-1]


def natural_sort_key(
    value
):
    return [
        int(part)
        if part.isdigit()
        else part.casefold()
        for part in re.split(
            r"(\d+)",
            str(value)
        )
    ]


def get_archive_limits(
    policy
):
    maximum_entries = get_positive_read_limit(
        policy,
        "maximum_archive_entries",
        HARD_MAX_ARCHIVE_ENTRIES
    )

    maximum_relevant_bytes = get_positive_read_limit(
        policy,
        "maximum_archive_relevant_uncompressed_bytes",
        HARD_MAX_ARCHIVE_RELEVANT_BYTES
    )

    maximum_single_entry = get_positive_read_limit(
        policy,
        "maximum_archive_single_entry_bytes",
        HARD_MAX_ARCHIVE_SINGLE_ENTRY_BYTES
    )

    if (
        maximum_entries is None
        or
        maximum_relevant_bytes is None
        or
        maximum_single_entry is None
    ):
        return None

    return (
        maximum_entries,
        maximum_relevant_bytes,
        maximum_single_entry
    )


def validate_zip_entries(
    archive,
    relevant_names,
    policy
):
    limits = get_archive_limits(
        policy
    )

    if limits is None:
        return (
            False,
            "Les limites de sécurité des documents compressés sont invalides."
        )

    (
        maximum_entries,
        maximum_relevant_bytes,
        maximum_single_entry,
    ) = limits

    infos = archive.infolist()

    if len(infos) > maximum_entries:
        return (
            False,
            "Le document contient trop d'éléments internes."
        )

    info_map = {
        info.filename: info
        for info in infos
    }

    total = 0

    for name in relevant_names:
        info = info_map.get(
            name
        )

        if info is None:
            continue

        if info.is_dir():
            continue

        if info.file_size > maximum_single_entry:
            return (
                False,
                (
                    "Une partie interne du document dépasse "
                    "la limite de sécurité."
                )
            )

        total += info.file_size

        if total > maximum_relevant_bytes:
            return (
                False,
                (
                    "Le contenu textuel interne du document "
                    "est trop volumineux."
                )
            )

        if (
            info.file_size > 1024 * 1024
            and
            info.compress_size > 0
            and
            info.file_size > info.compress_size * 1000
        ):
            return (
                False,
                "Un taux de compression anormal a été détecté."
            )

    return (
        True,
        None
    )


def read_zip_entry(
    archive,
    name,
    policy
):
    try:
        info = archive.getinfo(
            name
        )
    except KeyError:
        return (
            False,
            None,
            "Une partie nécessaire du document est absente."
        )

    limits = get_archive_limits(
        policy
    )

    if limits is None:
        return (
            False,
            None,
            "Les limites des archives sont invalides."
        )

    maximum_single_entry = limits[2]

    if info.file_size > maximum_single_entry:
        return (
            False,
            None,
            "Une partie interne du document est trop volumineuse."
        )

    try:
        data = archive.read(
            info
        )
    except (
        OSError,
        RuntimeError,
        zipfile.BadZipFile,
        zlib.error,
    ) as error:
        return (
            False,
            None,
            f"Impossible de lire le document compressé : {error}"
        )

    if len(data) > maximum_single_entry:
        return (
            False,
            None,
            "Une partie interne dépasse la limite après décompression."
        )

    return (
        True,
        data,
        None
    )


def extract_paragraphs_from_xml(
    data
):
    try:
        root = ET.fromstring(
            data
        )
    except ET.ParseError:
        return []

    lines = []

    for element in root.iter():

        if xml_local_name(
            element.tag
        ) not in {
            "p",
            "h",
        }:
            continue

        pieces = []

        for child in element.iter():
            name = xml_local_name(
                child.tag
            )

            if name == "t":
                if child.text:
                    pieces.append(
                        child.text
                    )

            elif name == "tab":
                pieces.append(
                    "\t"
                )

            elif name in {
                "br",
                "cr",
            }:
                pieces.append(
                    "\n"
                )

        line = normalize_extracted_text(
            "".join(pieces)
        )

        if line:
            lines.append(
                line
            )

    return lines


def extract_odf_paragraphs_from_xml(
    data
):
    try:
        root = ET.fromstring(
            data
        )
    except ET.ParseError:
        return []

    lines = []

    for element in root.iter():
        if xml_local_name(
            element.tag
        ) not in {
            "p",
            "h",
        }:
            continue

        text = normalize_extracted_text(
            "".join(
                element.itertext()
            )
        )

        if text:
            lines.append(
                text
            )

    return lines


def extract_all_text_nodes_from_xml(
    data
):
    try:
        root = ET.fromstring(
            data
        )
    except ET.ParseError:
        return []

    values = []

    for element in root.iter():
        if (
            xml_local_name(
                element.tag
            ) == "t"
            and
            element.text
        ):
            values.append(
                element.text
            )

    return values


def extract_docx_content(
    path,
    policy,
    maximum_output
):
    try:
        with zipfile.ZipFile(
            path,
            "r"
        ) as archive:
            names = set(
                archive.namelist()
            )

            relevant = [
                name
                for name in names
                if (
                    name == "word/document.xml"
                    or
                    re.fullmatch(
                        r"word/(?:header|footer)\d+\.xml",
                        name
                    )
                    or
                    name in {
                        "word/footnotes.xml",
                        "word/endnotes.xml",
                        "word/comments.xml",
                    }
                )
            ]

            if "word/document.xml" not in names:
                return (
                    False,
                    None,
                    "Le fichier DOCX ne contient pas de document Word valide.",
                    False
                )

            valid, error = validate_zip_entries(
                archive,
                relevant,
                policy
            )

            if not valid:
                return (
                    False,
                    None,
                    error,
                    False
                )

            relevant.sort(
                key=natural_sort_key
            )

            collector = BoundedTextCollector(
                maximum_output
            )

            for name in relevant:
                ok, data, error = read_zip_entry(
                    archive,
                    name,
                    policy
                )

                if not ok:
                    return (
                        False,
                        None,
                        error,
                        False
                    )

                for line in extract_paragraphs_from_xml(
                    data
                ):
                    if not collector.add(
                        line
                    ):
                        break

                if collector.truncated:
                    break

            return (
                True,
                collector.text(),
                "DOCX",
                collector.truncated
            )

    except zipfile.BadZipFile:
        return (
            False,
            None,
            "Le fichier DOCX est endommagé ou invalide.",
            False
        )

    except OSError as error:
        return (
            False,
            None,
            f"Impossible de lire le DOCX : {error}",
            False
        )


def get_xml_child_text(
    element,
    child_name
):
    for child in element:
        if xml_local_name(
            child.tag
        ) == child_name:
            return child.text or ""

    return ""


def extract_xlsx_content(
    path,
    policy,
    maximum_output
):
    try:
        with zipfile.ZipFile(
            path,
            "r"
        ) as archive:
            names = set(
                archive.namelist()
            )

            worksheet_names = sorted(
                [
                    name
                    for name in names
                    if re.fullmatch(
                        r"xl/worksheets/sheet\d+\.xml",
                        name
                    )
                ],
                key=natural_sort_key
            )

            relevant = list(
                worksheet_names
            )

            for fixed in (
                "xl/sharedStrings.xml",
                "xl/workbook.xml",
                "xl/_rels/workbook.xml.rels",
            ):
                if fixed in names:
                    relevant.append(
                        fixed
                    )

            if not worksheet_names:
                return (
                    False,
                    None,
                    "Le classeur XLSX ne contient aucune feuille lisible.",
                    False
                )

            valid, error = validate_zip_entries(
                archive,
                relevant,
                policy
            )

            if not valid:
                return (
                    False,
                    None,
                    error,
                    False
                )

            shared_strings = []

            if "xl/sharedStrings.xml" in names:
                ok, data, error = read_zip_entry(
                    archive,
                    "xl/sharedStrings.xml",
                    policy
                )

                if not ok:
                    return (
                        False,
                        None,
                        error,
                        False
                    )

                try:
                    root = ET.fromstring(
                        data
                    )

                    for item in root.iter():
                        if xml_local_name(
                            item.tag
                        ) != "si":
                            continue

                        text = "".join(
                            child.text or ""
                            for child in item.iter()
                            if xml_local_name(
                                child.tag
                            ) == "t"
                        )

                        shared_strings.append(
                            text
                        )

                except ET.ParseError:
                    return (
                        False,
                        None,
                        "La table de chaînes XLSX est invalide.",
                        False
                    )

            collector = BoundedTextCollector(
                maximum_output
            )

            for index, sheet_name in enumerate(
                worksheet_names,
                start=1
            ):
                if not collector.add(
                    f"Feuille {index}",
                    separator="\n\n"
                ):
                    break

                ok, data, error = read_zip_entry(
                    archive,
                    sheet_name,
                    policy
                )

                if not ok:
                    return (
                        False,
                        None,
                        error,
                        False
                    )

                try:
                    root = ET.fromstring(
                        data
                    )
                except ET.ParseError:
                    return (
                        False,
                        None,
                        "Une feuille XLSX est invalide.",
                        False
                    )

                for row in root.iter():
                    if xml_local_name(
                        row.tag
                    ) != "row":
                        continue

                    cells = []

                    for cell in row:
                        if xml_local_name(
                            cell.tag
                        ) != "c":
                            continue

                        reference = cell.attrib.get(
                            "r",
                            ""
                        )

                        cell_type = cell.attrib.get(
                            "t",
                            ""
                        )

                        value = get_xml_child_text(
                            cell,
                            "v"
                        )

                        formula = get_xml_child_text(
                            cell,
                            "f"
                        )

                        if cell_type == "s":
                            try:
                                shared_index = int(
                                    value
                                )
                                value = shared_strings[
                                    shared_index
                                ]
                            except (
                                ValueError,
                                IndexError,
                            ):
                                value = ""

                        elif cell_type == "inlineStr":
                            value = "".join(
                                child.text or ""
                                for child in cell.iter()
                                if xml_local_name(
                                    child.tag
                                ) == "t"
                            )

                        elif cell_type == "b":
                            value = (
                                "VRAI"
                                if value == "1"
                                else "FAUX"
                            )

                        if formula:
                            if value:
                                value = (
                                    f"={formula} -> {value}"
                                )
                            else:
                                value = f"={formula}"

                        value = normalize_extracted_text(
                            value
                        )

                        if value:
                            if reference:
                                cells.append(
                                    f"{reference}={value}"
                                )
                            else:
                                cells.append(
                                    value
                                )

                    if cells:
                        if not collector.add(
                            " | ".join(cells)
                        ):
                            break

                if collector.truncated:
                    break

            return (
                True,
                collector.text(),
                "XLSX",
                collector.truncated
            )

    except zipfile.BadZipFile:
        return (
            False,
            None,
            "Le fichier XLSX est endommagé ou invalide.",
            False
        )

    except OSError as error:
        return (
            False,
            None,
            f"Impossible de lire le XLSX : {error}",
            False
        )


def extract_pptx_content(
    path,
    policy,
    maximum_output
):
    try:
        with zipfile.ZipFile(
            path,
            "r"
        ) as archive:
            slides = sorted(
                [
                    name
                    for name in archive.namelist()
                    if re.fullmatch(
                        r"ppt/slides/slide\d+\.xml",
                        name
                    )
                ],
                key=natural_sort_key
            )

            if not slides:
                return (
                    False,
                    None,
                    "Le fichier PPTX ne contient aucune diapositive lisible.",
                    False
                )

            valid, error = validate_zip_entries(
                archive,
                slides,
                policy
            )

            if not valid:
                return (
                    False,
                    None,
                    error,
                    False
                )

            collector = BoundedTextCollector(
                maximum_output
            )

            for index, slide_name in enumerate(
                slides,
                start=1
            ):
                ok, data, error = read_zip_entry(
                    archive,
                    slide_name,
                    policy
                )

                if not ok:
                    return (
                        False,
                        None,
                        error,
                        False
                    )

                values = extract_all_text_nodes_from_xml(
                    data
                )

                text = normalize_extracted_text(
                    " ".join(values)
                )

                if text:
                    if not collector.add(
                        f"Diapositive {index} : {text}",
                        separator="\n\n"
                    ):
                        break

            return (
                True,
                collector.text(),
                "PPTX",
                collector.truncated
            )

    except zipfile.BadZipFile:
        return (
            False,
            None,
            "Le fichier PPTX est endommagé ou invalide.",
            False
        )

    except OSError as error:
        return (
            False,
            None,
            f"Impossible de lire le PPTX : {error}",
            False
        )


def extract_open_document_content(
    path,
    extension,
    policy,
    maximum_output
):
    try:
        with zipfile.ZipFile(
            path,
            "r"
        ) as archive:
            relevant = [
                "content.xml"
            ]

            if "content.xml" not in archive.namelist():
                return (
                    False,
                    None,
                    "Le document OpenDocument ne contient pas content.xml.",
                    False
                )

            valid, error = validate_zip_entries(
                archive,
                relevant,
                policy
            )

            if not valid:
                return (
                    False,
                    None,
                    error,
                    False
                )

            ok, data, error = read_zip_entry(
                archive,
                "content.xml",
                policy
            )

            if not ok:
                return (
                    False,
                    None,
                    error,
                    False
                )

            collector = BoundedTextCollector(
                maximum_output
            )

            for line in extract_odf_paragraphs_from_xml(
                data
            ):
                if not collector.add(
                    line
                ):
                    break

            labels = {
                ".odt": "ODT",
                ".ods": "ODS",
                ".odp": "ODP",
            }

            return (
                True,
                collector.text(),
                labels.get(extension, "OpenDocument"),
                collector.truncated
            )

    except zipfile.BadZipFile:
        return (
            False,
            None,
            "Le document OpenDocument est endommagé ou invalide.",
            False
        )

    except OSError as error:
        return (
            False,
            None,
            f"Impossible de lire le document OpenDocument : {error}",
            False
        )


class SafeHTMLTextExtractor(HTMLParser):

    BLOCK_TAGS = {
        "address", "article", "aside", "blockquote", "br", "div",
        "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header",
        "hr", "li", "main", "nav", "ol", "p", "pre", "section",
        "table", "tr", "ul",
    }

    SKIP_TAGS = {
        "script",
        "style",
        "noscript",
        "template",
    }

    def __init__(
        self,
        maximum_output
    ):
        super().__init__(
            convert_charrefs=True
        )
        self.collector = BoundedTextCollector(
            maximum_output
        )
        self.skip_depth = 0

    def handle_starttag(
        self,
        tag,
        attrs
    ):
        tag = tag.lower()

        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return

        if (
            self.skip_depth == 0
            and
            tag in self.BLOCK_TAGS
        ):
            self.collector.add(
                "\n",
                separator=""
            )

    def handle_endtag(
        self,
        tag
    ):
        tag = tag.lower()

        if tag in self.SKIP_TAGS:
            if self.skip_depth > 0:
                self.skip_depth -= 1
            return

        if (
            self.skip_depth == 0
            and
            tag in self.BLOCK_TAGS
        ):
            self.collector.add(
                "\n",
                separator=""
            )

    def handle_data(
        self,
        data
    ):
        if self.skip_depth:
            return

        value = re.sub(
            r"\s+",
            " ",
            data
        )

        if value.strip():
            self.collector.add(
                value.strip(),
                separator=" "
            )

    def result(self):
        return (
            normalize_extracted_text(
                self.collector.text()
            ),
            self.collector.truncated
        )


def html_to_text(
    content,
    maximum_output
):
    parser = SafeHTMLTextExtractor(
        maximum_output
    )

    try:
        parser.feed(
            content
        )
        parser.close()
    except Exception:
        pass

    return parser.result()


def rtf_to_text(
    content,
    maximum_output
):
    """
    Extraction RTF locale : aucun objet embarqué ni commande
    n'est exécuté. Le parseur récupère uniquement le texte.
    """

    destinations = {
        "fonttbl", "colortbl", "datastore", "themedata", "stylesheet",
        "info", "pict", "object", "filetbl", "revtbl", "rsidtbl",
        "generator", "xmlnstbl", "listtable", "listoverridetable",
    }

    special = {
        "par": "\n",
        "line": "\n",
        "tab": "\t",
        "page": "\n\n",
        "sect": "\n\n",
        "emdash": "—",
        "endash": "–",
        "bullet": "•",
        "lquote": "‘",
        "rquote": "’",
        "ldblquote": "“",
        "rdblquote": "”",
    }

    token_pattern = re.compile(
        r"\\([a-zA-Z]+)(-?\d+)? ?|"
        r"\\'([0-9a-fA-F]{2})|"
        r"\\([^a-zA-Z])|"
        r"([{}])|"
        r"([\r\n]+)|"
        r"(.)",
        re.DOTALL
    )

    collector = BoundedTextCollector(
        maximum_output
    )

    stack = []
    ignorable = False
    unicode_skip = 1
    skip_characters = 0

    for match in token_pattern.finditer(
        content
    ):
        word = match.group(1)
        argument = match.group(2)
        hex_value = match.group(3)
        escaped = match.group(4)
        brace = match.group(5)
        plain = match.group(7)

        if brace:
            if brace == "{":
                stack.append(
                    (
                        ignorable,
                        unicode_skip,
                    )
                )
            elif stack:
                ignorable, unicode_skip = stack.pop()
            continue

        if word:
            lower_word = word.lower()

            if lower_word in destinations:
                ignorable = True
                continue

            if lower_word == "uc":
                try:
                    unicode_skip = max(
                        0,
                        int(argument or 1)
                    )
                except ValueError:
                    unicode_skip = 1
                continue

            if lower_word == "u":
                if ignorable:
                    continue

                try:
                    codepoint = int(
                        argument or 0
                    )
                    if codepoint < 0:
                        codepoint += 65536
                    collector.add(
                        chr(codepoint),
                        separator=""
                    )
                    skip_characters = unicode_skip
                except (
                    ValueError,
                    OverflowError,
                ):
                    pass
                continue

            if (
                not ignorable
                and
                lower_word in special
            ):
                collector.add(
                    special[lower_word],
                    separator=""
                )

            continue

        if hex_value:
            if ignorable:
                continue

            try:
                character = bytes(
                    [int(hex_value, 16)]
                ).decode(
                    "cp1252",
                    errors="replace"
                )
                collector.add(
                    character,
                    separator=""
                )
            except Exception:
                pass
            continue

        if escaped:
            if (
                not ignorable
                and
                escaped in {
                    "\\", "{", "}"
                }
            ):
                collector.add(
                    escaped,
                    separator=""
                )
            continue

        if plain and not ignorable:
            if skip_characters > 0:
                skip_characters -= 1
                continue

            collector.add(
                plain,
                separator=""
            )

        if collector.truncated:
            break

    return (
        normalize_extracted_text(
            collector.text()
        ),
        collector.truncated
    )


def extract_epub_content(
    path,
    policy,
    maximum_output
):
    try:
        with zipfile.ZipFile(
            path,
            "r"
        ) as archive:
            html_names = sorted(
                [
                    name
                    for name in archive.namelist()
                    if (
                        name.lower().endswith(
                            (".xhtml", ".html", ".htm")
                        )
                        and
                        not name.upper().startswith(
                            "META-INF/"
                        )
                    )
                ],
                key=natural_sort_key
            )

            if not html_names:
                return (
                    False,
                    None,
                    "Le fichier EPUB ne contient aucun chapitre HTML lisible.",
                    False
                )

            valid, error = validate_zip_entries(
                archive,
                html_names,
                policy
            )

            if not valid:
                return (
                    False,
                    None,
                    error,
                    False
                )

            collector = BoundedTextCollector(
                maximum_output
            )

            for index, name in enumerate(
                html_names,
                start=1
            ):
                ok, data, error = read_zip_entry(
                    archive,
                    name,
                    policy
                )

                if not ok:
                    return (
                        False,
                        None,
                        error,
                        False
                    )

                decoded = None

                for encoding in (
                    "utf-8",
                    "utf-8-sig",
                    "cp1252",
                ):
                    try:
                        decoded = data.decode(
                            encoding,
                            errors="strict"
                        )
                        break
                    except UnicodeDecodeError:
                        continue

                if decoded is None:
                    continue

                text, truncated = html_to_text(
                    decoded,
                    maximum_output
                )

                if text:
                    if not collector.add(
                        f"Chapitre {index}\n{text}",
                        separator="\n\n"
                    ):
                        break

                if truncated:
                    collector.truncated = True
                    break

            return (
                True,
                collector.text(),
                "EPUB",
                collector.truncated
            )

    except zipfile.BadZipFile:
        return (
            False,
            None,
            "Le fichier EPUB est endommagé ou invalide.",
            False
        )

    except OSError as error:
        return (
            False,
            None,
            f"Impossible de lire l'EPUB : {error}",
            False
        )


def extract_eml_content(
    path,
    maximum_output
):
    try:
        with open(
            path,
            "rb"
        ) as file:
            message = BytesParser(
                policy=email_policy.default
            ).parse(
                file
            )
    except (
        OSError,
        ValueError,
    ) as error:
        return (
            False,
            None,
            f"Impossible de lire le fichier EML : {error}",
            False
        )

    collector = BoundedTextCollector(
        maximum_output
    )

    for label, header in (
        ("Sujet", "subject"),
        ("De", "from"),
        ("À", "to"),
        ("Date", "date"),
    ):
        value = message.get(
            header
        )
        if value:
            collector.add(
                f"{label} : {value}"
            )

    part_count = 0

    for part in message.walk():
        part_count += 1

        if part_count > 200:
            return (
                False,
                None,
                "Le message contient trop de parties MIME.",
                False
            )

        if part.is_multipart():
            continue

        if part.get_content_disposition() == "attachment":
            continue

        content_type = part.get_content_type()

        if content_type not in {
            "text/plain",
            "text/html",
        }:
            continue

        try:
            value = part.get_content()
        except Exception:
            continue

        if content_type == "text/html":
            value, html_truncated = html_to_text(
                str(value),
                maximum_output
            )
        else:
            html_truncated = False
            value = normalize_extracted_text(
                value
            )

        if value:
            if not collector.add(
                value,
                separator="\n\n"
            ):
                break

        if html_truncated:
            collector.truncated = True
            break

    return (
        True,
        collector.text(),
        "EML",
        collector.truncated
    )


def extract_pdf_content(
    path,
    policy,
    maximum_output
):
    try:
        from pypdf import PdfReader
    except ImportError:
        return (
            False,
            None,
            (
                "Le support PDF nécessite le module local 'pypdf'. "
                "Installez-le avec : python -m pip install pypdf"
            ),
            False
        )

    maximum_pages = get_positive_read_limit(
        policy,
        "maximum_pdf_pages",
        HARD_MAX_PDF_PAGES
    )

    if maximum_pages is None:
        return (
            False,
            None,
            "La limite de pages PDF est invalide.",
            False
        )

    try:
        reader = PdfReader(
            str(path),
            strict=False
        )

        if reader.is_encrypted:
            if not policy.get(
                "allow_encrypted_documents",
                False
            ):
                return (
                    False,
                    None,
                    "Les PDF chiffrés ou protégés par mot de passe sont refusés.",
                    False
                )

            return (
                False,
                None,
                "La lecture des PDF chiffrés n'est pas implémentée.",
                False
            )

        total_pages = len(
            reader.pages
        )

        pages_to_read = min(
            total_pages,
            maximum_pages
        )

        collector = BoundedTextCollector(
            maximum_output
        )

        for index in range(
            pages_to_read
        ):
            try:
                text = reader.pages[
                    index
                ].extract_text() or ""
            except Exception:
                text = ""

            text = normalize_extracted_text(
                text
            )

            if text:
                if not collector.add(
                    f"Page {index + 1}\n{text}",
                    separator="\n\n"
                ):
                    break

        truncated = (
            collector.truncated
            or
            total_pages > maximum_pages
        )

        if not collector.text():
            return (
                True,
                (
                    "[Aucun texte extractible. Le PDF peut être scanné "
                    "ou constitué principalement d'images.]"
                ),
                "PDF",
                truncated
            )

        return (
            True,
            collector.text(),
            "PDF",
            truncated
        )

    except Exception as error:
        return (
            False,
            None,
            f"Impossible de lire le PDF : {error}",
            False
        )


def extract_plain_text_content(
    path,
    maximum_file_size,
    maximum_output
):
    try:
        with open(
            path,
            "rb"
        ) as file:
            data = file.read(
                maximum_file_size + 1
            )
    except (
        OSError,
        PermissionError,
    ) as error:
        return (
            False,
            None,
            f"Impossible de lire le fichier : {error}",
            False
        )

    if len(data) > maximum_file_size:
        return (
            False,
            None,
            "Le fichier a dépassé la limite de taille pendant la lecture.",
            False
        )

    if looks_like_binary_data(
        data
    ):
        return (
            False,
            None,
            "Le fichier ressemble à un contenu binaire non autorisé.",
            False
        )

    ok, decoded, encoding = decode_text_bytes(
        data
    )

    if not ok:
        return (
            False,
            None,
            decoded,
            False
        )

    truncated = len(decoded) > maximum_output

    if truncated:
        decoded = decoded[
            :maximum_output
        ]

    return (
        True,
        decoded,
        f"texte ({encoding})",
        truncated
    )


def extract_html_file_content(
    path,
    maximum_file_size,
    maximum_output
):
    try:
        with open(
            path,
            "rb"
        ) as file:
            data = file.read(
                maximum_file_size + 1
            )
    except OSError as error:
        return (
            False,
            None,
            f"Impossible de lire le HTML : {error}",
            False
        )

    if len(data) > maximum_file_size:
        return (
            False,
            None,
            "Le fichier HTML dépasse la limite pendant la lecture.",
            False
        )

    ok, decoded, encoding = decode_text_bytes(
        data
    )

    if not ok:
        return (
            False,
            None,
            decoded,
            False
        )

    text, truncated = html_to_text(
        decoded,
        maximum_output
    )

    return (
        True,
        text,
        f"HTML ({encoding})",
        truncated
    )


def extract_rtf_file_content(
    path,
    maximum_file_size,
    maximum_output
):
    try:
        with open(
            path,
            "rb"
        ) as file:
            data = file.read(
                maximum_file_size + 1
            )
    except OSError as error:
        return (
            False,
            None,
            f"Impossible de lire le RTF : {error}",
            False
        )

    if len(data) > maximum_file_size:
        return (
            False,
            None,
            "Le fichier RTF dépasse la limite pendant la lecture.",
            False
        )

    ok, decoded, encoding = decode_text_bytes(
        data
    )

    if not ok:
        return (
            False,
            None,
            decoded,
            False
        )

    text, truncated = rtf_to_text(
        decoded,
        maximum_output
    )

    return (
        True,
        text,
        f"RTF ({encoding})",
        truncated
    )


def read_file_content(
    root_name,
    file_name,
    explicit_user_command=False,
    source="unspecified"
):
    """
    Lit le contenu d'UN fichier utilisateur explicitement demandé.

    Les formats structurés sont parsés en lecture seule : aucune
    macro, application Office, pièce jointe, script HTML ou contenu
    embarqué n'est exécuté.
    """

    root_name = (
        str(root_name)
        .strip()
        .lower()
    )

    source = (
        str(source)
        .strip()
        .lower()
    )

    if not is_filesystem_enabled():
        return (
            False,
            "L'accès au système de fichiers est désactivé."
        )

    if not has_filesystem_permission(
        "can_read_content"
    ):
        return (
            False,
            "La lecture du contenu des fichiers est désactivée."
        )

    if not has_root_permission(
        root_name,
        "can_read_content"
    ):
        return (
            False,
            (
                "La lecture du contenu n'est pas autorisée dans "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    policy = get_read_content_policy()

    if not policy.get(
        "enabled",
        False
    ):
        return (
            False,
            "La politique de lecture du contenu est désactivée."
        )

    if source != "manual":
        return (
            False,
            (
                "La lecture du contenu est réservée aux commandes "
                "manuelles explicites."
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
                "La lecture d'un fichier nécessite une commande "
                "explicite de l'utilisateur."
            )
        )

    if (
        policy.get("allow_from_routine", False)
        or
        policy.get("allow_from_habit", False)
        or
        policy.get("allow_automatic_read", False)
    ):
        return (
            False,
            (
                "Configuration de lecture dangereuse détectée : "
                "routine, habitude et lecture automatique doivent rester désactivées."
            )
        )

    if policy.get(
        "maximum_items_per_command",
        1
    ) != 1:
        return (
            False,
            "Un seul fichier doit être autorisé par commande."
        )

    valid, validated_file = validate_file_name(
        file_name
    )

    if not valid:
        return (
            False,
            validated_file
        )

    extension = Path(
        validated_file
    ).suffix.lower()

    allowed_extensions = get_allowed_read_extensions()

    if extension not in allowed_extensions:
        if extension in HARD_BLOCKED_DOCUMENT_READ_EXTENSIONS:
            return (
                False,
                (
                    f"Le format '{extension}' reste volontairement bloqué. "
                    "Utilisez si possible un format moderne non macro comme "
                    ".docx, .xlsx ou .pptx."
                )
            )

        return (
            False,
            (
                f"Le type de fichier '{extension or '(sans extension)'}' "
                "n'est pas autorisé pour la lecture."
            )
        )

    is_structured = (
        extension
        not in PLAIN_TEXT_READ_EXTENSIONS
    )

    if (
        is_structured
        and
        not policy.get(
            "allow_structured_documents",
            False
        )
    ):
        return (
            False,
            "La lecture des documents structurés est désactivée."
        )

    if policy.get(
        "allow_macro_enabled_documents",
        False
    ):
        return (
            False,
            (
                "Configuration dangereuse détectée : les documents "
                "Office avec macros doivent rester interdits."
            )
        )

    if policy.get(
        "allow_legacy_binary_office",
        False
    ):
        return (
            False,
            (
                "Configuration dangereuse détectée : les anciens formats "
                "Office binaires doivent rester interdits."
            )
        )

    root_path = resolve_allowed_root(
        root_name
    )

    if root_path is None:
        return (
            False,
            "Dossier racine protégé, inconnu ou introuvable."
        )

    if not root_path.exists():
        return (
            False,
            "Le dossier racine n'existe pas."
        )

    source_path = root_path / validated_file

    if not is_direct_child(
        root_path,
        source_path
    ):
        return (
            False,
            (
                "Le fichier doit se trouver directement "
                "dans la racine autorisée."
            )
        )

    if not source_path.exists():
        return (
            False,
            (
                f"Le fichier '{validated_file}' n'existe pas dans "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    if not source_path.is_file():
        return (
            False,
            "La source n'est pas un fichier autorisé."
        )

    if is_reparse_point(
        source_path
    ):
        return (
            False,
            (
                "Les liens, junctions et reparse points "
                "ne peuvent pas être lus."
            )
        )

    if is_hidden_or_system(
        source_path
    ):
        return (
            False,
            "Les fichiers cachés ou système ne peuvent pas être lus."
        )

    try:
        resolved_root = root_path.resolve(
            strict=True
        )
        resolved_source = source_path.resolve(
            strict=True
        )
    except (
        OSError,
        RuntimeError,
    ):
        return (
            False,
            "Impossible de vérifier le chemin du fichier."
        )

    if resolved_source.parent != resolved_root:
        return (
            False,
            "Le fichier sort de la zone autorisée."
        )

    if is_hard_protected_path(
        resolved_source
    ):
        return (
            False,
            "Le fichier appartient à une zone protégée."
        )

    if (
        is_reparse_point(resolved_source)
        or
        is_hidden_or_system(resolved_source)
    ):
        return (
            False,
            "Le fichier a changé d'état pendant la vérification."
        )

    try:
        stats = resolved_source.stat(
            follow_symlinks=False
        )
    except (
        OSError,
        PermissionError,
    ) as error:
        return (
            False,
            f"Impossible de lire les métadonnées du fichier : {error}"
        )

    maximum_file_size = get_positive_read_limit(
        policy,
        "maximum_file_size_bytes",
        HARD_MAX_READ_FILE_BYTES
    )

    if maximum_file_size is None:
        return (
            False,
            "La limite de taille de lecture est invalide."
        )

    if stats.st_size > maximum_file_size:
        return (
            False,
            (
                f"Le fichier est trop volumineux ({format_size(stats.st_size)}). "
                f"La limite actuelle est {format_size(maximum_file_size)}."
            )
        )

    maximum_output = get_positive_read_limit(
        policy,
        "maximum_output_characters",
        HARD_MAX_READ_OUTPUT_CHARACTERS
    )

    if maximum_output is None:
        return (
            False,
            "La limite de sortie de lecture est invalide."
        )

    if extension in PLAIN_TEXT_READ_EXTENSIONS:
        success, content, format_name, truncated = extract_plain_text_content(
            resolved_source,
            maximum_file_size,
            maximum_output
        )

    elif extension in HTML_READ_EXTENSIONS:
        success, content, format_name, truncated = extract_html_file_content(
            resolved_source,
            maximum_file_size,
            maximum_output
        )

    elif extension in RTF_READ_EXTENSIONS:
        success, content, format_name, truncated = extract_rtf_file_content(
            resolved_source,
            maximum_file_size,
            maximum_output
        )

    elif extension == ".docx":
        success, content, format_name, truncated = extract_docx_content(
            resolved_source,
            policy,
            maximum_output
        )

    elif extension == ".xlsx":
        success, content, format_name, truncated = extract_xlsx_content(
            resolved_source,
            policy,
            maximum_output
        )

    elif extension == ".pptx":
        success, content, format_name, truncated = extract_pptx_content(
            resolved_source,
            policy,
            maximum_output
        )

    elif extension in OPEN_DOCUMENT_READ_EXTENSIONS:
        success, content, format_name, truncated = extract_open_document_content(
            resolved_source,
            extension,
            policy,
            maximum_output
        )

    elif extension in EPUB_READ_EXTENSIONS:
        success, content, format_name, truncated = extract_epub_content(
            resolved_source,
            policy,
            maximum_output
        )

    elif extension in EMAIL_READ_EXTENSIONS:
        success, content, format_name, truncated = extract_eml_content(
            resolved_source,
            maximum_output
        )

    elif extension in PDF_READ_EXTENSIONS:
        success, content, format_name, truncated = extract_pdf_content(
            resolved_source,
            policy,
            maximum_output
        )

    else:
        return (
            False,
            "Le format demandé n'a aucun lecteur local autorisé."
        )

    if not success:
        return (
            False,
            content if content else format_name
        )

    content = content or ""

    display_name = DISPLAY_NAMES.get(
        root_name,
        root_name
    )

    header = (
        f"Contenu de '{validated_file}' dans {display_name} "
        f"(format : {format_name}) :"
    )

    if content:
        message = header + "\n\n" + content
    else:
        message = header + "\n\n[Document vide ou sans texte extractible]"

    if truncated:
        message += (
            "\n\n"
            "[Contenu tronqué : une limite de sécurité ou de sortie a été atteinte.]"
        )

    return (
        True,
        message
    )


# ============================================================
# CREER UN FICHIER TEXTE CONTROLE
# ============================================================

def get_allowed_create_file_extensions():
    """
    Intersection entre la politique JSON et la liste dure.

    Même si permissions.json est élargi par erreur, AgentLocal
    ne peut créer que des formats texte explicitement supportés.
    """

    policy = get_create_file_policy()

    configured = policy.get(
        "allowed_extensions",
        []
    )

    if not isinstance(
        configured,
        list
    ):
        return set()

    normalized = set()

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
            extension = "." + extension

        normalized.add(
            extension
        )

    return (
        normalized
        &
        HARD_WRITABLE_TEXT_EXTENSIONS
    )


def create_file_with_content(
    root_name,
    file_name,
    content,
    explicit_user_command=False,
    source="unspecified"
):
    """
    Crée UN nouveau fichier texte dans une racine autorisée.

    Garanties principales :
    - commande utilisateur explicite ;
    - source manuelle uniquement ;
    - un seul fichier ;
    - aucun chemin arbitraire ;
    - aucun écrasement ;
    - aucune création dans une zone système ;
    - aucune extension exécutable ou script ;
    - UTF-8 uniquement ;
    - taille bornée ;
    - aucune exécution du contenu.
    """

    root_name = (
        str(root_name)
        .strip()
        .lower()
    )

    source = (
        str(source)
        .strip()
        .lower()
    )

    # ========================================================
    # SYSTEME DE FICHIERS
    # ========================================================

    if not is_filesystem_enabled():
        return (
            False,
            "L'accès au système de fichiers est désactivé."
        )

    if not has_filesystem_permission(
        "can_write_content"
    ):
        return (
            False,
            "La création de fichiers avec contenu est désactivée."
        )

    if not has_root_permission(
        root_name,
        "can_create_file"
    ):
        return (
            False,
            (
                "La création de fichiers n'est pas autorisée dans "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    # ========================================================
    # POLITIQUE
    # ========================================================

    policy = get_create_file_policy()

    if not policy.get(
        "enabled",
        False
    ):
        return (
            False,
            "La politique de création de fichiers est désactivée."
        )

    if source != "manual":
        return (
            False,
            (
                "La création de fichiers est limitée aux commandes "
                "manuelles explicites."
            )
        )

    if policy.get(
        "allow_from_routine",
        False
    ):
        return (
            False,
            "Configuration dangereuse détectée pour les routines."
        )

    if policy.get(
        "allow_from_habit",
        False
    ):
        return (
            False,
            "Configuration dangereuse détectée pour les habitudes."
        )

    if policy.get(
        "allow_automatic_write",
        False
    ):
        return (
            False,
            "L'écriture automatique reste interdite."
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
                "La création du fichier nécessite une commande "
                "explicite de l'utilisateur."
            )
        )

    if policy.get(
        "maximum_items_per_command",
        1
    ) != 1:
        return (
            False,
            (
                "La politique de création n'est pas assez restrictive : "
                "un seul fichier doit être autorisé."
            )
        )

    if policy.get(
        "allow_overwrite",
        False
    ):
        return (
            False,
            "La configuration d'écrasement est refusée par AgentLocal."
        )

    # ========================================================
    # NOM DU FICHIER
    # ========================================================

    valid, validated_file = validate_file_name(
        file_name
    )

    if not valid:
        return (
            False,
            validated_file
        )

    extension = (
        Path(validated_file)
        .suffix
        .lower()
    )

    allowed_extensions = (
        get_allowed_create_file_extensions()
    )

    if extension not in allowed_extensions:
        return (
            False,
            (
                f"L'extension '{extension or '(aucune)'}' n'est pas "
                "autorisée pour la création de fichiers."
            )
        )

    # ========================================================
    # CONTENU
    # ========================================================

    if not isinstance(
        content,
        str
    ):
        return (
            False,
            "Le contenu du fichier est invalide."
        )

    if "\x00" in content:
        return (
            False,
            "Le contenu binaire ou contenant un octet NUL est interdit."
        )

    encoding = (
        str(
            policy.get(
                "encoding",
                "utf-8"
            )
        )
        .strip()
        .lower()
    )

    # Barrière dure : écriture UTF-8 uniquement.
    if encoding != "utf-8":
        return (
            False,
            "Seul l'encodage UTF-8 est autorisé pour l'écriture."
        )

    try:
        encoded_content = content.encode(
            "utf-8"
        )
    except UnicodeEncodeError:
        return (
            False,
            "Le contenu ne peut pas être encodé en UTF-8."
        )

    configured_limit = policy.get(
        "maximum_content_bytes",
        0
    )

    try:
        configured_limit = int(
            configured_limit
        )
    except (
        TypeError,
        ValueError,
    ):
        return (
            False,
            "La limite de taille d'écriture est invalide."
        )

    if (
        configured_limit <= 0
        or
        configured_limit > HARD_MAX_CREATE_FILE_CONTENT_BYTES
    ):
        return (
            False,
            "La limite de taille d'écriture est invalide ou trop élevée."
        )

    if len(encoded_content) > configured_limit:
        return (
            False,
            (
                "Le contenu est trop volumineux. "
                f"Limite : {format_size(configured_limit)}."
            )
        )

    # ========================================================
    # RACINE ET DESTINATION
    # ========================================================

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

    if not root_path.is_dir():
        return (
            False,
            "La racine autorisée n'est pas un dossier."
        )

    destination_path = (
        root_path
        /
        validated_file
    )

    if not is_direct_child(
        root_path,
        destination_path
    ):
        return (
            False,
            "Le fichier demandé sort de la zone autorisée."
        )

    if is_hard_protected_path(
        destination_path
    ):
        return (
            False,
            "La destination appartient à une zone protégée."
        )

    # os.path.lexists détecte aussi un lien symbolique cassé.
    if os.path.lexists(
        str(destination_path)
    ):
        return (
            False,
            (
                f"'{validated_file}' existe déjà. "
                "Aucun écrasement n'est autorisé."
            )
        )

    # ========================================================
    # VERIFICATION FINALE DE LA RACINE
    # ========================================================

    try:
        resolved_root = root_path.resolve(
            strict=True
        )
    except (
        OSError,
        RuntimeError,
    ):
        return (
            False,
            "Impossible de vérifier la racine de destination."
        )

    if is_hard_protected_path(
        resolved_root
    ):
        return (
            False,
            "La racine de destination est protégée."
        )

    if destination_path.parent.resolve(
        strict=True
    ) != resolved_root:
        return (
            False,
            "La destination sort de la racine autorisée."
        )

    # ========================================================
    # CREATION ATOMIQUE SANS ECRASEMENT
    # ========================================================

    flags = (
        os.O_WRONLY
        |
        os.O_CREAT
        |
        os.O_EXCL
    )

    fd = None

    try:
        fd = os.open(
            str(destination_path),
            flags,
            0o600
        )

        with os.fdopen(
            fd,
            "wb"
        ) as file:
            fd = None
            file.write(
                encoded_content
            )
            file.flush()
            os.fsync(
                file.fileno()
            )

    except FileExistsError:
        return (
            False,
            (
                f"'{validated_file}' existe déjà. "
                "Aucun écrasement n'est autorisé."
            )
        )

    except (
        OSError,
        PermissionError,
    ) as error:
        if fd is not None:
            try:
                os.close(
                    fd
                )
            except OSError:
                pass

        return (
            False,
            (
                "Impossible de créer le fichier : "
                f"{error}"
            )
        )

    # ========================================================
    # VERIFICATION APRES CREATION
    # ========================================================

    try:
        if not destination_path.exists():
            return (
                False,
                "Le fichier n'est pas visible après sa création."
            )

        if not destination_path.is_file():
            return (
                False,
                "L'élément créé n'est pas un fichier normal."
            )

        if is_reparse_point(
            destination_path
        ):
            return (
                False,
                "Un reparse point inattendu a été détecté."
            )

        if is_hidden_or_system(
            destination_path
        ):
            return (
                False,
                "Le fichier créé possède un attribut protégé inattendu."
            )

        stats = destination_path.stat(
            follow_symlinks=False
        )

        if stats.st_size != len(encoded_content):
            return (
                False,
                (
                    "La taille du fichier créé ne correspond pas "
                    "au contenu demandé."
                )
            )

    except OSError as error:
        return (
            False,
            (
                "Le fichier a été créé mais sa vérification a échoué : "
                f"{error}"
            )
        )

    return (
        True,
        (
            f"Le fichier '{validated_file}' a été créé dans "
            f"{DISPLAY_NAMES.get(root_name, root_name)} "
            "avec le contenu demandé."
        )
    )



# ============================================================
# MODIFIER UN FICHIER TEXTE EXISTANT DE FAÇON CONTROLEE
# ============================================================

def get_allowed_modify_file_extensions():
    """
    Intersection entre permissions.json et la liste dure.

    Même si la configuration est élargie par erreur, AgentLocal
    ne modifie que les formats textuels explicitement supportés.
    """

    policy = get_modify_file_policy()

    configured = policy.get(
        "allowed_extensions",
        []
    )

    if not isinstance(
        configured,
        list
    ):
        return set()

    normalized = set()

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
            extension = "." + extension

        if extension in get_blocked_extensions():
            continue

        normalized.add(
            extension
        )

    return (
        normalized
        &
        HARD_MODIFIABLE_TEXT_EXTENSIONS
    )


def get_append_safe_modify_extensions():
    policy = get_modify_file_policy()

    configured = policy.get(
        "append_safe_extensions",
        []
    )

    if not isinstance(
        configured,
        list
    ):
        return set()

    normalized = set()

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
            extension = "." + extension

        normalized.add(
            extension
        )

    return (
        normalized
        &
        HARD_APPEND_SAFE_EXTENSIONS
        &
        get_allowed_modify_file_extensions()
    )


def get_allowed_modify_encodings():
    policy = get_modify_file_policy()

    configured = policy.get(
        "allowed_encodings",
        []
    )

    if not isinstance(
        configured,
        list
    ):
        return []

    allowed = []

    for encoding in configured:

        if not isinstance(
            encoding,
            str
        ):
            continue

        encoding = (
            encoding
            .strip()
            .lower()
        )

        if encoding not in {
            "utf-8",
            "utf-8-sig",
            "cp1252",
        }:
            continue

        if encoding not in allowed:
            allowed.append(
                encoding
            )

    return allowed


def decode_text_bytes_for_modification(
    data
):
    """
    Décode le texte en conservant autant que possible l'encodage
    réellement utilisé par le fichier.
    """

    if not isinstance(
        data,
        (bytes, bytearray)
    ):
        return (
            False,
            "Contenu de fichier invalide.",
            None
        )

    encodings = get_allowed_modify_encodings()

    if not encodings:
        return (
            False,
            "Aucun encodage autorisé pour la modification.",
            None
        )

    # BOM UTF-8 : il doit rester présent après modification.
    if (
        data.startswith(b"\xef\xbb\xbf")
        and
        "utf-8-sig" in encodings
    ):
        try:
            return (
                True,
                data.decode(
                    "utf-8-sig",
                    errors="strict"
                ),
                "utf-8-sig"
            )
        except UnicodeDecodeError:
            return (
                False,
                "Le fichier possède un BOM UTF-8 invalide.",
                None
            )

    for encoding in (
        "utf-8",
        "cp1252",
    ):

        if encoding not in encodings:
            continue

        try:
            return (
                True,
                data.decode(
                    encoding,
                    errors="strict"
                ),
                encoding
            )
        except UnicodeDecodeError:
            continue

    return (
        False,
        (
            "Le fichier n'utilise aucun des encodages "
            "autorisés pour la modification."
        ),
        None
    )


def get_file_fingerprint(
    path
):
    """
    Empreinte légère permettant de détecter un changement du fichier
    entre la lecture et l'écriture atomique.
    """

    try:
        stats = os.stat(
            path,
            follow_symlinks=False
        )

        return (
            int(stats.st_size),
            int(getattr(stats, "st_mtime_ns", 0)),
            int(getattr(stats, "st_ino", 0)),
        )

    except OSError:
        return None


def write_existing_file_atomically(
    source_path,
    encoded_content,
    expected_fingerprint
):
    """
    Écrit d'abord dans un fichier temporaire du même dossier puis
    remplace atomiquement le fichier d'origine avec os.replace().

    Aucun fichier temporaire n'est laissé volontairement en place.
    """

    source_path = Path(
        source_path
    )

    temp_path = (
        source_path.parent
        /
        (
            ".agentlocal_tmp_"
            + uuid.uuid4().hex
            + ".tmp"
        )
    )

    fd = None

    try:
        fd = os.open(
            str(temp_path),
            (
                os.O_WRONLY
                |
                os.O_CREAT
                |
                os.O_EXCL
            ),
            0o600
        )

        with os.fdopen(
            fd,
            "wb"
        ) as file:
            fd = None
            file.write(
                encoded_content
            )
            file.flush()
            os.fsync(
                file.fileno()
            )

        # Revalidation juste avant le remplacement.
        if not source_path.exists():
            return (
                False,
                "Le fichier source a disparu pendant la modification."
            )

        if not source_path.is_file():
            return (
                False,
                "La source n'est plus un fichier normal."
            )

        if is_reparse_point(
            source_path
        ):
            return (
                False,
                "Le fichier source est devenu un reparse point."
            )

        if is_hidden_or_system(
            source_path
        ):
            return (
                False,
                "Le fichier source est devenu caché ou système."
            )

        current_fingerprint = get_file_fingerprint(
            source_path
        )

        if (
            expected_fingerprint is None
            or
            current_fingerprint != expected_fingerprint
        ):
            return (
                False,
                (
                    "Le fichier a changé depuis sa lecture. "
                    "La modification est annulée pour éviter d'écraser "
                    "une modification concurrente."
                )
            )

        os.replace(
            temp_path,
            source_path
        )

        temp_path = None

        return (
            True,
            None
        )

    except FileExistsError:
        return (
            False,
            "Un fichier temporaire inattendu existe déjà."
        )

    except (
        OSError,
        PermissionError,
    ) as error:
        return (
            False,
            (
                "Impossible d'enregistrer atomiquement le fichier : "
                f"{error}"
            )
        )

    finally:
        if fd is not None:
            try:
                os.close(
                    fd
                )
            except OSError:
                pass

        if temp_path is not None:
            try:
                Path(temp_path).unlink(
                    missing_ok=True
                )
            except OSError:
                pass


def modify_file_content(
    root_name,
    file_name,
    content,
    mode,
    explicit_user_command=False,
    source="unspecified"
):
    """
    Modifie UN fichier texte existant.

    Modes fermés :
    - replace_content : remplace tout le contenu ;
    - append_content  : ajoute exactement le contenu à la fin ;
    - append_line     : ajoute une seule nouvelle ligne.

    La modification est limitée aux commandes manuelles explicites.
    """

    root_name = (
        str(root_name)
        .strip()
        .lower()
    )

    source = (
        str(source)
        .strip()
        .lower()
    )

    mode = (
        str(mode)
        .strip()
        .lower()
    )

    if not is_filesystem_enabled():
        return (
            False,
            "L'accès au système de fichiers est désactivé."
        )

    if not has_filesystem_permission(
        "can_write_content"
    ):
        return (
            False,
            "L'écriture de contenu est désactivée."
        )

    if not has_filesystem_permission(
        "can_modify_content"
    ):
        return (
            False,
            "La modification de fichiers existants est désactivée."
        )

    if not has_root_permission(
        root_name,
        "can_modify_file"
    ):
        return (
            False,
            (
                "La modification de fichiers n'est pas autorisée dans "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    policy = get_modify_file_policy()

    if not policy.get(
        "enabled",
        False
    ):
        return (
            False,
            "La politique de modification de fichiers est désactivée."
        )

    if source != "manual":
        return (
            False,
            (
                "La modification de fichiers est limitée aux commandes "
                "manuelles explicites."
            )
        )

    if policy.get(
        "allow_from_routine",
        False
    ):
        return (
            False,
            "Configuration dangereuse détectée pour les routines."
        )

    if policy.get(
        "allow_from_habit",
        False
    ):
        return (
            False,
            "Configuration dangereuse détectée pour les habitudes."
        )

    if policy.get(
        "allow_automatic_write",
        False
    ):
        return (
            False,
            "La modification automatique reste interdite."
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
                "La modification du fichier nécessite une commande "
                "explicite de l'utilisateur."
            )
        )

    if policy.get(
        "maximum_items_per_command",
        1
    ) != 1:
        return (
            False,
            (
                "La politique de modification n'est pas assez restrictive : "
                "un seul fichier doit être autorisé."
            )
        )

    allowed_modes = policy.get(
        "allowed_modes",
        []
    )

    if not isinstance(
        allowed_modes,
        list
    ):
        return (
            False,
            "La liste des modes de modification est invalide."
        )

    allowed_modes = {
        str(item).strip().lower()
        for item in allowed_modes
        if isinstance(item, str)
    }

    hard_modes = {
        "replace_content",
        "append_content",
        "append_line",
    }

    if (
        mode not in hard_modes
        or
        mode not in allowed_modes
    ):
        return (
            False,
            "Mode de modification interdit ou inconnu."
        )

    if policy.get(
        "allow_create_if_missing",
        False
    ):
        return (
            False,
            (
                "Configuration dangereuse détectée : la modification "
                "ne doit jamais créer automatiquement un fichier manquant."
            )
        )

    if not policy.get(
        "atomic_replace_required",
        True
    ):
        return (
            False,
            "L'écriture atomique est obligatoire."
        )

    if not policy.get(
        "verify_source_unchanged_before_commit",
        True
    ):
        return (
            False,
            "La vérification anti-écrasement concurrent est obligatoire."
        )

    valid, validated_file = validate_file_name(
        file_name
    )

    if not valid:
        return (
            False,
            validated_file
        )

    extension = (
        Path(validated_file)
        .suffix
        .lower()
    )

    if extension not in get_allowed_modify_file_extensions():
        return (
            False,
            (
                f"L'extension '{extension or '(aucune)'}' n'est pas "
                "autorisée pour la modification."
            )
        )

    if (
        mode in {
            "append_content",
            "append_line",
        }
        and
        extension not in get_append_safe_modify_extensions()
    ):
        return (
            False,
            (
                "L'ajout à la fin est limité aux formats textuels "
                "simples afin d'éviter de corrompre un format structuré."
            )
        )

    if not isinstance(
        content,
        str
    ):
        return (
            False,
            "Le nouveau contenu est invalide."
        )

    if "\x00" in content:
        return (
            False,
            "Le contenu binaire ou contenant un octet NUL est interdit."
        )

    if (
        mode == "append_line"
        and
        ("\n" in content or "\r" in content)
    ):
        return (
            False,
            "Le mode 'ajoute une ligne' accepte une seule ligne de texte."
        )

    try:
        content_utf8_bytes = content.encode(
            "utf-8"
        )
    except UnicodeEncodeError:
        return (
            False,
            "Le contenu demandé n'est pas un texte Unicode valide."
        )

    def validated_positive_limit(
        key,
        hard_maximum
    ):
        value = policy.get(
            key,
            0
        )

        try:
            value = int(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        if (
            value <= 0
            or
            value > hard_maximum
        ):
            return None

        return value

    maximum_existing = validated_positive_limit(
        "maximum_existing_file_bytes",
        HARD_MAX_MODIFY_EXISTING_BYTES
    )

    maximum_added = validated_positive_limit(
        "maximum_added_content_bytes",
        HARD_MAX_MODIFY_ADDED_BYTES
    )

    maximum_result = validated_positive_limit(
        "maximum_result_bytes",
        HARD_MAX_MODIFY_RESULT_BYTES
    )

    if (
        maximum_existing is None
        or
        maximum_added is None
        or
        maximum_result is None
    ):
        return (
            False,
            "Une limite de taille de modification est invalide."
        )

    if len(content_utf8_bytes) > maximum_added:
        return (
            False,
            (
                "Le contenu demandé est trop volumineux. "
                f"Limite d'ajout : {format_size(maximum_added)}."
            )
        )

    root_path = resolve_allowed_root(
        root_name
    )

    if root_path is None:
        return (
            False,
            "Dossier racine protégé ou introuvable."
        )

    if (
        not root_path.exists()
        or
        not root_path.is_dir()
    ):
        return (
            False,
            "La racine autorisée n'est pas disponible."
        )

    source_path = (
        root_path
        /
        validated_file
    )

    if not is_direct_child(
        root_path,
        source_path
    ):
        return (
            False,
            "Le fichier doit se trouver directement dans la racine autorisée."
        )

    if is_hard_protected_path(
        source_path
    ):
        return (
            False,
            "Le fichier appartient à une zone protégée."
        )

    if not os.path.lexists(
        str(source_path)
    ):
        return (
            False,
            (
                f"Le fichier '{validated_file}' n'existe pas dans "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    if is_reparse_point(
        source_path
    ):
        return (
            False,
            "Les liens, junctions et reparse points sont interdits."
        )

    if is_hidden_or_system(
        source_path
    ):
        return (
            False,
            "Les fichiers cachés ou système sont protégés."
        )

    if not source_path.is_file():
        return (
            False,
            "La source n'est pas un fichier normal autorisé."
        )

    try:
        resolved_root = root_path.resolve(
            strict=True
        )

        resolved_source = source_path.resolve(
            strict=True
        )

    except (
        OSError,
        RuntimeError,
    ):
        return (
            False,
            "Impossible de vérifier le chemin du fichier."
        )

    if resolved_source.parent != resolved_root:
        return (
            False,
            "Le fichier sort de la racine autorisée."
        )

    original_fingerprint = get_file_fingerprint(
        source_path
    )

    if original_fingerprint is None:
        return (
            False,
            "Impossible d'obtenir l'empreinte du fichier."
        )

    if original_fingerprint[0] > maximum_existing:
        return (
            False,
            (
                "Le fichier existant est trop volumineux pour être modifié. "
                f"Limite : {format_size(maximum_existing)}."
            )
        )

    try:
        with open(
            source_path,
            "rb"
        ) as file:
            original_bytes = file.read(
                maximum_existing + 1
            )

    except (
        OSError,
        PermissionError,
    ) as error:
        return (
            False,
            (
                "Impossible de lire le fichier avant modification : "
                f"{error}"
            )
        )

    if len(original_bytes) > maximum_existing:
        return (
            False,
            "Le fichier a dépassé la limite pendant sa lecture."
        )

    if looks_like_binary_data(
        original_bytes
    ):
        return (
            False,
            "Le fichier ressemble à un contenu binaire non autorisé."
        )

    after_read_fingerprint = get_file_fingerprint(
        source_path
    )

    if after_read_fingerprint != original_fingerprint:
        return (
            False,
            (
                "Le fichier a changé pendant sa lecture. "
                "La modification est annulée."
            )
        )

    ok, original_text, detected_encoding = (
        decode_text_bytes_for_modification(
            original_bytes
        )
    )

    if not ok:
        return (
            False,
            original_text
        )

    if mode == "replace_content":
        result_text = content

    elif mode == "append_content":
        result_text = (
            original_text
            +
            content
        )

    else:
        if "\r\n" in original_text:
            newline = "\r\n"
        else:
            newline = "\n"

        if not original_text:
            result_text = content
        elif original_text.endswith(("\n", "\r")):
            result_text = (
                original_text
                +
                content
            )
        else:
            result_text = (
                original_text
                +
                newline
                +
                content
            )

    try:
        result_bytes = result_text.encode(
            detected_encoding,
            errors="strict"
        )
    except UnicodeEncodeError:
        return (
            False,
            (
                "Le nouveau contenu ne peut pas être enregistré dans "
                f"l'encodage existant '{detected_encoding}' sans perte."
            )
        )

    if len(result_bytes) > maximum_result:
        return (
            False,
            (
                "Le résultat serait trop volumineux. "
                f"Limite : {format_size(maximum_result)}."
            )
        )

    success, error = write_existing_file_atomically(
        source_path,
        result_bytes,
        original_fingerprint
    )

    if not success:
        return (
            False,
            error
        )

    try:
        if not source_path.exists():
            return (
                False,
                "Le fichier n'est plus visible après la modification."
            )

        if not source_path.is_file():
            return (
                False,
                "Le résultat n'est pas un fichier normal."
            )

        if is_reparse_point(
            source_path
        ):
            return (
                False,
                "Un reparse point inattendu a été détecté après écriture."
            )

        if is_hidden_or_system(
            source_path
        ):
            return (
                False,
                "Le fichier possède un attribut protégé inattendu."
            )

        stats = source_path.stat(
            follow_symlinks=False
        )

        if stats.st_size != len(result_bytes):
            return (
                False,
                (
                    "La taille du fichier modifié ne correspond pas "
                    "au résultat attendu."
                )
            )

    except OSError as error:
        return (
            False,
            (
                "Le fichier a été modifié mais sa vérification a échoué : "
                f"{error}"
            )
        )

    mode_labels = {
        "replace_content": "contenu remplacé",
        "append_content": "contenu ajouté",
        "append_line": "ligne ajoutée",
    }

    return (
        True,
        (
            f"Le fichier '{validated_file}' dans "
            f"{DISPLAY_NAMES.get(root_name, root_name)} a été modifié "
            f"({mode_labels[mode]})."
        )
    )


# ============================================================
# TEST DIRECT
# ============================================================

if __name__ == "__main__":

    print()

    print(
        "=" * 65
    )

    print(
        "TEST SECURITE FILE_TOOLS"
    )

    print(
        "=" * 65
    )

    print()

    print(
        "Accès fichiers :",
        is_filesystem_enabled()
    )

    print()

    # ========================================================
    # RACINES
    # ========================================================

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
            (
                f"- {DISPLAY_NAMES[root]} : "
                f"{path}"
            )
        )

    print()

    # ========================================================
    # PROTECTION SYSTEME
    # ========================================================

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

    # ========================================================
    # EXTENSIONS
    # ========================================================

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
            (
                f"- {name} : "
                f"{'BLOQUÉ' if is_blocked_file_type(name) else 'autorisé'}"
            )
        )

    print()

    # ========================================================
    # TRANSFERTS
    # ========================================================

    print(
        "Communication entre racines :"
    )

    tests = [
        (
            "desktop",
            "documents"
        ),
        (
            "documents",
            "downloads"
        ),
        (
            "downloads",
            "pictures"
        ),
        (
            "pictures",
            "videos"
        ),
        (
            "videos",
            "music"
        ),
        (
            "music",
            "desktop"
        ),
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

    # ========================================================
    # RENOMMAGE
    # ========================================================

    rename_policy = (
        get_rename_policy()
    )

    print(
        "Renommage contrôlé :"
    )

    print(
        (
            "- Permission globale : "
            f"{has_filesystem_permission('can_rename')}"
        )
    )

    print(
        (
            "- Politique active : "
            f"{rename_policy.get('enabled', False)}"
        )
    )

    print(
        (
            "- Changement extension : "
            f"{rename_policy.get('allow_extension_change', False)}"
        )
    )

    print(
        (
            "- Écrasement : "
            f"{rename_policy.get('allow_overwrite', False)}"
        )
    )

    print()

    # ========================================================
    # SUPPRESSION
    # ========================================================

    delete_policy = (
        get_delete_policy()
    )

    print(
        "Suppression contrôlée :"
    )

    print(
        (
            "- Permission globale : "
            f"{has_filesystem_permission('can_delete')}"
        )
    )

    print(
        (
            "- Politique active : "
            f"{delete_policy.get('enabled', False)}"
        )
    )

    print(
        (
            "- Mode : "
            f"{delete_policy.get('mode', 'non défini')}"
        )
    )

    print(
        (
            "- Suppression définitive : "
            f"{delete_policy.get('allow_permanent_delete', False)}"
        )
    )

    print(
        (
            "- Maximum fichiers par commande : "
            f"{delete_policy.get('maximum_items_per_command', 0)}"
        )
    )

    print()


    # ========================================================
    # LECTURE CONTROLEE
    # ========================================================

    read_policy = (
        get_read_content_policy()
    )

    print(
        "Lecture contrôlée :"
    )

    print(
        (
            "- Permission globale : "
            f"{has_filesystem_permission('can_read_content')}"
        )
    )

    print(
        (
            "- Politique active : "
            f"{read_policy.get('enabled', False)}"
        )
    )

    print(
        (
            "- Taille maximale : "
            f"{format_size(read_policy.get('maximum_file_size_bytes', 0))}"
        )
    )

    print(
        (
            "- Sortie maximale : "
            f"{read_policy.get('maximum_output_characters', 0)} caractères"
        )
    )

    print(
        (
            "- Extensions autorisées : "
            f"{', '.join(sorted(get_allowed_read_extensions())) or 'aucune'}"
        )
    )

    print()

    # ========================================================
    # CREATION DE FICHIER CONTROLEE
    # ========================================================

    create_file_policy = (
        get_create_file_policy()
    )

    print(
        "Création de fichier contrôlée :"
    )

    print(
        (
            "- Permission globale : "
            f"{has_filesystem_permission('can_write_content')}"
        )
    )

    print(
        (
            "- Politique active : "
            f"{create_file_policy.get('enabled', False)}"
        )
    )

    print(
        (
            "- Taille maximale du contenu : "
            f"{format_size(create_file_policy.get('maximum_content_bytes', 0))}"
        )
    )

    print(
        (
            "- Extensions autorisées : "
            f"{', '.join(sorted(get_allowed_create_file_extensions())) or 'aucune'}"
        )
    )

    print()

    # ========================================================
    # MODIFICATION DE FICHIER CONTROLEE
    # ========================================================

    modify_file_policy = (
        get_modify_file_policy()
    )

    print(
        "Modification de fichier contrôlée :"
    )

    print(
        (
            "- Permission globale : "
            f"{has_filesystem_permission('can_modify_content')}"
        )
    )

    print(
        (
            "- Politique active : "
            f"{modify_file_policy.get('enabled', False)}"
        )
    )

    print(
        (
            "- Extensions modifiables : "
            f"{', '.join(sorted(get_allowed_modify_file_extensions())) or 'aucune'}"
        )
    )

    print(
        (
            "- Extensions autorisées pour ajout : "
            f"{', '.join(sorted(get_append_safe_modify_extensions())) or 'aucune'}"
        )
    )

    print()

    print(
        (
            "Aucun fichier n'a été créé, lu, exécuté, "
            "déplacé, copié, renommé, modifié ou supprimé pendant ce test."
        )
    )

    print()