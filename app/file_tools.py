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

AGENT_CONFIG_FILE = (
    ROOT_DIR
    / "config"
    / "agent.json"
)

PERMISSIONS_FILE = (
    ROOT_DIR
    / "config"
    / "permissions.json"
)


# ============================================================
# DOSSIERS WINDOWS AUTORISES
# ============================================================

KNOWN_FOLDER_GUIDS = {
    "desktop": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
    "documents": "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}",
    "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
}


DISPLAY_NAMES = {
    "desktop": "Bureau",
    "documents": "Documents",
    "downloads": "Téléchargements",
}


# ============================================================
# NOMS RESERVES SOUS WINDOWS
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


# ============================================================
# CHARGEMENT JSON SECURISE
# ============================================================

def load_json_file(path):
    """
    Charge un fichier JSON.

    En cas d'erreur, retourne un dictionnaire vide.
    Le comportement par défaut est donc le refus.
    """

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(
            data,
            dict
        ):
            return data

    except (
        OSError,
        json.JSONDecodeError
    ):
        pass

    return {}


# ============================================================
# INTERRUPTEUR GENERAL
# ============================================================

def is_filesystem_globally_enabled():
    """
    Vérifie l'interrupteur général
    config/agent.json.
    """

    config = load_json_file(
        AGENT_CONFIG_FILE
    )

    return bool(
        config
        .get("security", {})
        .get(
            "allow_filesystem",
            False
        )
    )


# ============================================================
# CONFIGURATION FILESYSTEM
# ============================================================

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
    """
    Deux niveaux doivent être actifs :

    agent.json
        allow_filesystem = true

    permissions.json
        filesystem.enabled = true
    """

    if not is_filesystem_globally_enabled():
        return False

    filesystem = get_filesystem_config()

    return bool(
        filesystem.get(
            "enabled",
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

    return (
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

    filesystem = get_filesystem_config()

    policy = filesystem.get(
        "creation_policy",
        {}
    )

    if not isinstance(
        policy,
        dict
    ):
        return {}

    return policy


def get_move_policy():

    filesystem = get_filesystem_config()

    policy = filesystem.get(
        "move_policy",
        {}
    )

    if not isinstance(
        policy,
        dict
    ):
        return {}

    return policy


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
# DOSSIERS CONNUS WINDOWS
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
            shell32.SHGetKnownFolderPath(
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
        "desktop": (
            base / "Desktop"
        ),

        "documents": (
            base / "Documents"
        ),

        "downloads": (
            base / "Downloads"
        ),
    }

    return fallback.get(
        root_name
    )


# ============================================================
# RESOLUTION D'UNE RACINE
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

        return folder.resolve()

    except OSError:

        return folder.absolute()


# ============================================================
# VALIDATION D'UN NOM SIMPLE
# ============================================================

def validate_simple_name(
    value
):
    """
    Valide uniquement un nom simple.

    Aucun chemin n'est accepté.

    Autorisé :
        Factures
        cours.pdf
        Rapport 2026.docx

    Interdit :
        ../Windows
        C:\\Windows
        dossier/fichier.pdf
    """

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
    # Chemins interdits
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

    if value in {
        ".",
        "..",
    }:

        return (
            False,
            "Ce nom est interdit."
        )

    # --------------------------------------------------------
    # Caractères interdits Windows
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

    # --------------------------------------------------------
    # Fin de nom interdite
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Noms Windows réservés
    # --------------------------------------------------------

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

    return validate_simple_name(
        file_name
    )


# ============================================================
# VERIFICATION ENFANT DIRECT
# ============================================================

def is_direct_child(
    root_path,
    target_path
):

    try:

        resolved_root = (
            root_path.resolve()
        )

        resolved_target = (
            target_path.resolve(
                strict=False
            )
        )

        return (
            resolved_target.parent
            ==
            resolved_root
        )

    except OSError:
        return False


# ============================================================
# FORMATAGE TAILLE
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

    # --------------------------------------------------------
    # Interrupteur général
    # --------------------------------------------------------

    if not is_filesystem_enabled():

        return (
            False,
            (
                "L'accès au système de fichiers "
                "est désactivé."
            )
        )

    # --------------------------------------------------------
    # Permission
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Racine Windows
    # --------------------------------------------------------

    root_path = resolve_allowed_root(
        root_name
    )

    if root_path is None:

        return (
            False,
            "Dossier Windows introuvable."
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

    # --------------------------------------------------------
    # Métadonnées
    # --------------------------------------------------------

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
        PermissionError
    ) as error:

        return (
            False,
            (
                "Impossible de consulter "
                f"le dossier : {error}"
            )
        )

    # --------------------------------------------------------
    # Tri
    # --------------------------------------------------------

    try:

        entries.sort(
            key=lambda item: (
                not item.is_dir(),
                item.name.casefold()
            )
        )

    except OSError:

        entries.sort(
            key=lambda item: (
                item.name.casefold()
            )
        )

    display_name = DISPLAY_NAMES.get(
        root_name,
        root_name
    )

    if not entries:

        return (
            True,
            f"{display_name} est vide."
        )

    lines = [
        f"Contenu de {display_name} :"
    ]

    # --------------------------------------------------------
    # Affichage
    # --------------------------------------------------------

    for item in entries:

        try:

            if item.is_symlink():

                item_type = "lien"

            elif item.is_dir():

                item_type = "dossier"

            elif item.is_file():

                item_type = "fichier"

            else:

                item_type = "élément"

            line = (
                f"- [{item_type}] "
                f"{item.name}"
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
                            f" | "
                            f"{format_size(stats.st_size)}"
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

            lines.append(
                (
                    "- [inaccessible] "
                    f"{item.name}"
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
        str(root_name)
        .strip()
        .lower()
    )

    # --------------------------------------------------------
    # Interrupteur général
    # --------------------------------------------------------

    if not is_filesystem_enabled():

        return (
            False,
            (
                "L'accès au système de fichiers "
                "est désactivé."
            )
        )

    # --------------------------------------------------------
    # Politique de création
    # --------------------------------------------------------

    creation_policy = (
        get_creation_policy()
    )

    require_explicit = bool(
        creation_policy.get(
            "require_explicit_user_command",
            True
        )
    )

    if (
        require_explicit
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

    # --------------------------------------------------------
    # Permission racine
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Validation nom
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Racine
    # --------------------------------------------------------

    root_path = resolve_allowed_root(
        root_name
    )

    if root_path is None:

        return (
            False,
            "Dossier Windows introuvable."
        )

    if not root_path.exists():

        return (
            False,
            (
                "Le dossier racine autorisé "
                "n'existe pas."
            )
        )

    # --------------------------------------------------------
    # Construction chemin
    # --------------------------------------------------------

    target_path = (
        root_path
        / validated_name
    )

    # --------------------------------------------------------
    # Anti-évasion
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Existe déjà
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Création
    # --------------------------------------------------------

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
        PermissionError
    ) as error:

        return (
            False,
            (
                "Impossible de créer le dossier : "
                f"{error}"
            )
        )


# ============================================================
# DEPLACER UN FICHIER DANS LA MEME RACINE
# ============================================================

def move_file_within_root(
    root_name,
    file_name,
    destination_folder_name,
    explicit_user_command=False
):
    """
    Déplace un fichier présent directement dans une racine
    vers un sous-dossier existant de cette même racine.

    Exemple autorisé :

        Documents\\facture.pdf
        ->
        Documents\\Factures\\facture.pdf

    Le fichier source doit être un fichier normal.
    Les liens symboliques sont refusés.
    Le dossier destination doit exister.
    Aucun écrasement n'est autorisé.
    """

    root_name = (
        str(root_name)
        .strip()
        .lower()
    )

    # --------------------------------------------------------
    # Interrupteur général
    # --------------------------------------------------------

    if not is_filesystem_enabled():

        return (
            False,
            (
                "L'accès au système de fichiers "
                "est désactivé."
            )
        )

    # --------------------------------------------------------
    # Permission de déplacement
    # --------------------------------------------------------

    if not has_root_permission(
        root_name,
        "can_move_within_root"
    ):

        return (
            False,
            (
                "Le déplacement de fichiers "
                "n'est pas autorisé dans "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    # --------------------------------------------------------
    # Politique
    # --------------------------------------------------------

    move_policy = get_move_policy()

    require_explicit = bool(
        move_policy.get(
            "require_explicit_user_command",
            True
        )
    )

    if (
        require_explicit
        and
        not explicit_user_command
    ):

        return (
            False,
            (
                "Le déplacement d'un fichier nécessite "
                "une commande explicite de l'utilisateur."
            )
        )

    # --------------------------------------------------------
    # Même racine uniquement
    # --------------------------------------------------------

    if not bool(
        move_policy.get(
            "same_root_only",
            True
        )
    ):

        return (
            False,
            (
                "La politique de déplacement "
                "n'autorise pas cette opération."
            )
        )

    # --------------------------------------------------------
    # Validation du nom du fichier
    # --------------------------------------------------------

    valid, validated_file_name = (
        validate_file_name(
            file_name
        )
    )

    if not valid:

        return (
            False,
            validated_file_name
        )

    # --------------------------------------------------------
    # Validation du dossier destination
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Racine réelle
    # --------------------------------------------------------

    root_path = resolve_allowed_root(
        root_name
    )

    if root_path is None:

        return (
            False,
            "Dossier Windows introuvable."
        )

    if not root_path.exists():

        return (
            False,
            (
                "Le dossier racine autorisé "
                "n'existe pas."
            )
        )

    # --------------------------------------------------------
    # Construction des chemins
    # --------------------------------------------------------

    source_path = (
        root_path
        / validated_file_name
    )

    destination_folder = (
        root_path
        / validated_destination
    )

    destination_path = (
        destination_folder
        / validated_file_name
    )

    # --------------------------------------------------------
    # La source doit être directement dans la racine
    # --------------------------------------------------------

    if bool(
        move_policy.get(
            "source_must_be_direct_child",
            True
        )
    ):

        if not is_direct_child(
            root_path,
            source_path
        ):

            return (
                False,
                (
                    "Le fichier source doit se trouver "
                    "directement dans "
                    f"{DISPLAY_NAMES.get(root_name, root_name)}."
                )
            )

    # --------------------------------------------------------
    # Destination également directement sous la racine
    # --------------------------------------------------------

    if not is_direct_child(
        root_path,
        destination_folder
    ):

        return (
            False,
            (
                "Le dossier destination doit être "
                "un sous-dossier direct de "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    # --------------------------------------------------------
    # Source existante
    # --------------------------------------------------------

    if not source_path.exists():

        return (
            False,
            (
                f"Le fichier '{validated_file_name}' "
                "n'existe pas dans "
                f"{DISPLAY_NAMES.get(root_name, root_name)}."
            )
        )

    # --------------------------------------------------------
    # Refus des liens symboliques
    # --------------------------------------------------------

    if source_path.is_symlink():

        return (
            False,
            (
                "Le déplacement d'un lien symbolique "
                "n'est pas autorisé."
            )
        )

    # --------------------------------------------------------
    # Uniquement des fichiers
    # --------------------------------------------------------

    if not source_path.is_file():

        return (
            False,
            (
                f"'{validated_file_name}' "
                "n'est pas un fichier autorisé."
            )
        )

    # --------------------------------------------------------
    # Destination existante obligatoire
    # --------------------------------------------------------

    destination_required = bool(
        move_policy.get(
            "destination_must_be_existing_subfolder",
            True
        )
    )

    if destination_required:

        if not destination_folder.exists():

            return (
                False,
                (
                    f"Le dossier '{validated_destination}' "
                    "n'existe pas dans "
                    f"{DISPLAY_NAMES.get(root_name, root_name)}."
                )
            )

    # --------------------------------------------------------
    # Destination doit être un dossier
    # --------------------------------------------------------

    if not destination_folder.is_dir():

        return (
            False,
            (
                f"'{validated_destination}' "
                "n'est pas un dossier."
            )
        )

    # --------------------------------------------------------
    # Pas de lien symbolique destination
    # --------------------------------------------------------

    if destination_folder.is_symlink():

        return (
            False,
            (
                "Le dossier destination est un lien "
                "symbolique et n'est pas autorisé."
            )
        )

    # --------------------------------------------------------
    # Vérification finale après résolution
    # --------------------------------------------------------

    try:

        resolved_root = (
            root_path.resolve(
                strict=True
            )
        )

        resolved_source = (
            source_path.resolve(
                strict=True
            )
        )

        resolved_destination_folder = (
            destination_folder.resolve(
                strict=True
            )
        )

    except OSError:

        return (
            False,
            (
                "Impossible de vérifier les chemins "
                "du déplacement."
            )
        )

    # La source doit rester dans Documents
    if resolved_source.parent != resolved_root:

        return (
            False,
            (
                "Le fichier source sort de "
                "la zone autorisée."
            )
        )

    # Le dossier destination doit rester sous Documents
    if resolved_destination_folder.parent != resolved_root:

        return (
            False,
            (
                "Le dossier destination sort de "
                "la zone autorisée."
            )
        )

    # --------------------------------------------------------
    # Pas d'écrasement
    # --------------------------------------------------------

    allow_overwrite = bool(
        move_policy.get(
            "allow_overwrite",
            False
        )
    )

    if (
        destination_path.exists()
        and
        not allow_overwrite
    ):

        return (
            False,
            (
                f"Un élément nommé "
                f"'{validated_file_name}' "
                "existe déjà dans "
                f"'{validated_destination}'. "
                "Aucun écrasement n'est autorisé."
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

        return (
            True,
            (
                f"Le fichier '{validated_file_name}' "
                "a été déplacé dans le dossier "
                f"'{validated_destination}'."
            )
        )

    except (
        OSError,
        PermissionError
    ) as error:

        return (
            False,
            (
                "Impossible de déplacer le fichier : "
                f"{error}"
            )
        )


# ============================================================
# TEST DIRECT
# ============================================================

if __name__ == "__main__":

    print()

    print(
        "=" * 60
    )

    print(
        "TEST FILE_TOOLS"
    )

    print(
        "=" * 60
    )

    print()

    print(
        "Accès fichiers :",
        is_filesystem_enabled()
    )

    print()

    for root in (
        "desktop",
        "documents",
        "downloads"
    ):

        path = resolve_allowed_root(
            root
        )

        print(
            f"{DISPLAY_NAMES[root]} :",
            path
        )

    print()

    print(
        "Permissions création :"
    )

    print(
        "Bureau :",
        has_root_permission(
            "desktop",
            "can_create_folder"
        )
    )

    print(
        "Documents :",
        has_root_permission(
            "documents",
            "can_create_folder"
        )
    )

    print(
        "Téléchargements :",
        has_root_permission(
            "downloads",
            "can_create_folder"
        )
    )

    print()

    print(
        "Permissions déplacement :"
    )

    print(
        "Bureau :",
        has_root_permission(
            "desktop",
            "can_move_within_root"
        )
    )

    print(
        "Documents :",
        has_root_permission(
            "documents",
            "can_move_within_root"
        )
    )

    print(
        "Téléchargements :",
        has_root_permission(
            "downloads",
            "can_move_within_root"
        )
    )

    print()

    print(
        "Aucun fichier n'a été déplacé "
        "pendant ce test."
    )

    print()