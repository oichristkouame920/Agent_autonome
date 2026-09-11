import subprocess
from pathlib import Path

import file_tools as base
import recursive_file_tools as recursive
import windows_tools


# Closed mapping: a validated file type is always sent to one approved app.
# No Windows default association and no user-provided executable are used.
FILE_APP_BY_EXTENSION = {
    # Microsoft Office
    ".docx": "word",
    ".odt": "word",
    ".xlsx": "excel",
    ".ods": "excel",
    ".pptx": "powerpoint",
    ".odp": "powerpoint",

    # PDF / web documents
    ".pdf": "edge",
    ".html": "edge",
    ".htm": "edge",

    # Text and structured text
    ".txt": "notepad",
    ".md": "notepad",
    ".csv": "notepad",
    ".tsv": "notepad",
    ".json": "notepad",
    ".xml": "notepad",
    ".yaml": "notepad",
    ".yml": "notepad",
    ".log": "notepad",
    ".ini": "notepad",
    ".cfg": "notepad",
    ".conf": "notepad",
    ".toml": "notepad",
    ".ics": "notepad",
    ".vcf": "notepad",
    ".rtf": "notepad",
    ".eml": "notepad",

    # Images: Paint is a Win32-approved target that accepts a file path.
    ".jpg": "paint",
    ".jpeg": "paint",
    ".png": "paint",
    ".webp": "paint",
    ".gif": "paint",
    ".bmp": "paint",
    ".tif": "paint",
    ".tiff": "paint",

    # Media: use the approved Win32 media player when available.
    ".mp4": "media_player",
    ".mkv": "media_player",
    ".mov": "media_player",
    ".avi": "media_player",
    ".webm": "media_player",
    ".m4v": "media_player",
    ".mp3": "media_player",
    ".wav": "media_player",
    ".flac": "media_player",
    ".m4a": "media_player",
    ".aac": "media_player",
    ".ogg": "media_player",
    ".wma": "media_player",
}


HARD_OPEN_BLOCKED_EXTENSIONS = set(base.HARD_BLOCKED_EXTENSIONS) | {
    ".doc",
    ".xls",
    ".ppt",
    ".docm",
    ".xlsm",
    ".pptm",
    ".dotm",
    ".xltm",
    ".potm",
    ".ppsm",
}


def get_open_existing_policy():
    config = base.get_filesystem_config()
    policy = config.get("open_existing_policy", {})
    return policy if isinstance(policy, dict) else {}


def _manual_open_allowed(explicit_user_command, source="manual"):
    policy = get_open_existing_policy()
    filesystem = base.get_filesystem_config()

    if not filesystem.get("can_open_existing", False):
        return False, "L'ouverture de fichiers et dossiers est d\u00e9sactiv\u00e9e globalement."

    if not policy.get("enabled", False):
        return False, "L'ouverture contr\u00f4l\u00e9e de fichiers et dossiers est d\u00e9sactiv\u00e9e."

    if str(source).strip().lower() != "manual":
        return False, "Cette ouverture est r\u00e9serv\u00e9e aux commandes manuelles explicites."

    if policy.get("require_explicit_user_command", True) and not explicit_user_command:
        return False, "Cette ouverture n\u00e9cessite une commande utilisateur explicite."

    if policy.get("allow_from_routine", False) or policy.get("allow_from_habit", False):
        return False, "Configuration dangereuse d\u00e9tect\u00e9e : routines et habitudes doivent rester d\u00e9sactiv\u00e9es."

    if policy.get("maximum_items_per_command", 1) != 1:
        return False, "Un seul fichier ou dossier doit \u00eatre ouvert par commande."

    if policy.get("allow_windows_default_association", False):
        return False, "Configuration dangereuse d\u00e9tect\u00e9e : l'association Windows par d\u00e9faut doit rester d\u00e9sactiv\u00e9e."

    return True, None


def _root_can_open(root_name, kind):
    permission = "can_open_directory" if kind == "dir" else "can_open_file"
    return bool(base.get_root_permissions(root_name).get(permission, False))


def _launch_validated(executable, argument):
    executable = windows_tools.validate_trusted_executable(executable)
    if executable is None:
        return False, "L'application approuv\u00e9e est introuvable ou non fiable."

    windows_info = windows_tools.get_windows_info()
    if not windows_info.get("supported", False):
        return False, "AgentLocal prend en charge Windows 10 et Windows 11."

    argument = Path(argument)
    try:
        argument = argument.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return False, "Impossible de v\u00e9rifier la cible \u00e0 ouvrir."

    creation_flags = (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "DETACHED_PROCESS", 0)
    )

    try:
        subprocess.Popen(
            [str(executable), str(argument)],
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=creation_flags,
        )
    except OSError as exc:
        return False, f"Impossible d'ouvrir la cible : {exc}"

    return True, None


def _approved_application_for_file(path):
    extension = path.suffix.lower()

    if extension in HARD_OPEN_BLOCKED_EXTENSIONS or base.is_blocked_file_type(path.name):
        return False, "Ce type de fichier est prot\u00e9g\u00e9 et ne peut pas \u00eatre ouvert par AgentLocal."

    app_name = FILE_APP_BY_EXTENSION.get(extension)
    if app_name is None:
        return False, (
            f"Aucune application approuv\u00e9e n'est configur\u00e9e pour le type '{extension or 'sans extension'}'."
        )

    policy = get_open_existing_policy()

    allowed_extensions = policy.get("allowed_extensions", [])
    if not isinstance(allowed_extensions, list) or extension not in {str(item).lower() for item in allowed_extensions}:
        return False, "Ce type de fichier n'est pas autoris\u00e9 par la politique locale d'ouverture."

    configured_blocked = {
        str(item).lower()
        for item in policy.get("blocked_extensions", [])
        if isinstance(item, str)
    }
    if extension in configured_blocked:
        return False, "Ce type de fichier est explicitement bloqu\u00e9 pour l'ouverture."

    allowed_apps = policy.get("allowed_applications", [])
    if not isinstance(allowed_apps, list) or app_name not in allowed_apps:
        return False, "L'application pr\u00e9vue pour ce type de fichier n'est pas autoris\u00e9e par la politique locale."

    if not windows_tools.get_application_permission(app_name, "can_open"):
        return False, f"L'ouverture avec {windows_tools.DISPLAY_NAMES.get(app_name, app_name)} est interdite."

    if not windows_tools.is_application_source_allowed(
        app_name,
        source="manual",
        explicit_user_command=True,
    ):
        return False, "Cette application ne peut pas \u00eatre utilis\u00e9e pour cette commande manuelle."

    executable = windows_tools.find_application(app_name)
    if executable is None:
        return False, (
            f"{windows_tools.DISPLAY_NAMES.get(app_name, app_name)} n'a pas \u00e9t\u00e9 trouv\u00e9 sous une forme approuv\u00e9e."
        )

    return True, (app_name, executable)


def open_directory(root_name, relative_path="", explicit_user_command=False, source="manual"):
    allowed, error = _manual_open_allowed(explicit_user_command, source)
    if not allowed:
        return False, error

    root_name = str(root_name).strip().lower()
    if not _root_can_open(root_name, "dir"):
        return False, "L'ouverture de dossiers n'est pas autoris\u00e9e dans cette racine."

    ok, directory = recursive.resolve_existing_directory(root_name, relative_path)
    if not ok:
        return False, directory

    explorer = windows_tools.find_application("explorer")
    if explorer is None:
        return False, "L'Explorateur Windows approuv\u00e9 n'a pas \u00e9t\u00e9 trouv\u00e9."

    launched, launch_error = _launch_validated(explorer, directory)
    if not launched:
        return False, launch_error

    if str(relative_path or "").strip():
        display_path = recursive.relative_display(root_name, directory)
    else:
        display_path = base.DISPLAY_NAMES.get(root_name, root_name)

    return True, f"Dossier ouvert : {display_path}"


def open_directory_auto(directory_name, explicit_user_command=False, source="manual"):
    allowed, error = _manual_open_allowed(explicit_user_command, source)
    if not allowed:
        return False, error

    ok, candidate = recursive._unique_directory_candidate(directory_name)
    if not ok:
        return False, candidate

    root_name, directory = candidate
    root_path, root_error = recursive._root_path(root_name)
    if root_path is None:
        return False, root_error

    relative_path = str(directory.relative_to(root_path))
    return open_directory(
        root_name,
        relative_path,
        explicit_user_command=True,
        source="manual",
    )


def open_file(root_name, file_name, explicit_user_command=False, source="manual"):
    allowed, error = _manual_open_allowed(explicit_user_command, source)
    if not allowed:
        return False, error

    root_name = str(root_name).strip().lower()
    if not _root_can_open(root_name, "file"):
        return False, "L'ouverture de fichiers n'est pas autoris\u00e9e dans cette racine."

    ok, file_path = recursive.resolve_file_reference_inside_root(
        root_name,
        file_name,
    )
    if not ok:
        return False, file_path

    ok, app_data = _approved_application_for_file(file_path)
    if not ok:
        return False, app_data

    app_name, executable = app_data
    launched, launch_error = _launch_validated(executable, file_path)
    if not launched:
        return False, launch_error

    display = windows_tools.DISPLAY_NAMES.get(app_name, app_name)
    return True, f"Fichier ouvert avec {display} : {recursive.relative_display(root_name, file_path)}"


def open_file_auto(file_name, explicit_user_command=False, source="manual"):
    allowed, error = _manual_open_allowed(explicit_user_command, source)
    if not allowed:
        return False, error

    ok, candidate = recursive._unique_file_candidate(file_name)
    if not ok:
        return False, candidate

    root_name, file_path = candidate
    root_path, root_error = recursive._root_path(root_name)
    if root_path is None:
        return False, root_error

    relative_path = str(file_path.relative_to(root_path))
    return open_file(
        root_name,
        relative_path,
        explicit_user_command=True,
        source="manual",
    )
