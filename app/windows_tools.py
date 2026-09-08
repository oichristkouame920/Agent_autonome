import ctypes
import json
import os
import platform
import subprocess
import sys
import time
import uuid

from ctypes import wintypes
from pathlib import Path

import psutil


# ============================================================
# CHEMINS DU PROJET
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]

PERMISSIONS_FILE = (
    ROOT_DIR
    / "config"
    / "permissions.json"
)


# ============================================================
# WINDOWS 10 / WINDOWS 11
# ============================================================

def get_windows_info():
    """
    Détecte Windows 10 ou Windows 11
    sans utiliser de commande externe.
    """

    if platform.system().lower() != "windows":

        return {
            "supported": False,
            "family": "unsupported",
            "build": 0,
            "label": (
                platform.system()
                or
                "Système inconnu"
            ),
        }

    try:

        version = sys.getwindowsversion()

        build = int(
            version.build
        )

    except Exception:

        build = 0

    # Windows 11 : build >= 22000
    if build >= 22000:

        family = "windows_11"
        label = "Windows 11"

    # Windows 10 : build >= 10240
    elif build >= 10240:

        family = "windows_10"
        label = "Windows 10"

    else:

        family = "unsupported"

        label = (
            "Version Windows non prise en charge"
        )

    return {
        "supported": (
            family
            in
            {
                "windows_10",
                "windows_11",
            }
        ),

        "family": family,

        "build": build,

        "label": label,
    }


# ============================================================
# APPLICATIONS CONNUES
# ============================================================

PROCESS_MAP = {
    "edge": (
        "msedge.exe",
    ),

    "vscode": (
        "code.exe",
    ),

    "explorer": (
        "explorer.exe",
    ),

    "android_studio": (
        "studio64.exe",
        "studio.exe",
    ),

    "notepad": (
        "notepad.exe",
    ),

    "calculator": (
        "calculatorapp.exe",
        "calculator.exe",
        "calc.exe",
    ),

    "paint": (
        "mspaint.exe",
        "paintstudio.view.exe",
    ),

    "snipping_tool": (
        "snippingtool.exe",
        "screensketch.exe",
    ),

    "photos": (
        "photos.exe",
        "microsoft.photos.exe",
    ),

    "media_player": (
        "microsoft.media.player.exe",
        "music.ui.exe",
        "video.ui.exe",
        "wmplayer.exe",
    ),

    "camera": (
        "windowscamera.exe",
    ),

    "clock": (
        "time.exe",
        "windowsalarms.exe",
    ),

    "sound_recorder": (
        "soundrecorder.exe",
        "voicerecorder.exe",
    ),

    "sticky_notes": (
        "microsoft.notes.exe",
        "stickynotes.exe",
    ),

    "clipchamp": (
        "clipchamp.exe",
    ),

    "phone_link": (
        "phoneexperiencehost.exe",
        "yourphone.exe",
    ),

    "teams": (
        "ms-teams.exe",
        "teams.exe",
    ),

    "word": (
        "winword.exe",
    ),

    "excel": (
        "excel.exe",
    ),

    "powerpoint": (
        "powerpnt.exe",
    ),

    "outlook": (
        "outlook.exe",
        "olk.exe",
    ),

    "onenote": (
        "onenote.exe",
    ),
}


# ============================================================
# NOMS D'AFFICHAGE
# ============================================================

DISPLAY_NAMES = {
    "edge": "Microsoft Edge",

    "vscode": (
        "Visual Studio Code"
    ),

    "explorer": (
        "Explorateur de fichiers"
    ),

    "android_studio": (
        "Android Studio"
    ),

    "notepad": (
        "Bloc-notes"
    ),

    "calculator": (
        "Calculatrice"
    ),

    "paint": (
        "Paint"
    ),

    "snipping_tool": (
        "Outil Capture d'écran"
    ),

    "photos": (
        "Photos"
    ),

    "media_player": (
        "Lecteur multimédia"
    ),

    "camera": (
        "Caméra"
    ),

    "clock": (
        "Horloge"
    ),

    "sound_recorder": (
        "Enregistreur audio"
    ),

    "sticky_notes": (
        "Pense-bêtes"
    ),

    "clipchamp": (
        "Clipchamp"
    ),

    "phone_link": (
        "Mobile connecté"
    ),

    "teams": (
        "Microsoft Teams"
    ),

    "word": (
        "Microsoft Word"
    ),

    "excel": (
        "Microsoft Excel"
    ),

    "powerpoint": (
        "Microsoft PowerPoint"
    ),

    "outlook": (
        "Microsoft Outlook"
    ),

    "onenote": (
        "Microsoft OneNote"
    ),
}


# ============================================================
# APPLICATIONS SYSTEME INTERDITES
# ============================================================

HARD_BLOCKED_APPLICATIONS = {
    "cmd",
    "command_prompt",

    "powershell",
    "pwsh",

    "windows_terminal",
    "terminal",

    "regedit",
    "registry_editor",

    "msconfig",

    "services",
    "services_msc",

    "task_scheduler",

    "device_manager",

    "disk_management",

    "computer_management",

    "local_security_policy",

    "group_policy",
    "gpedit",
    "secpol",
}


# ============================================================
# APPLICATIONS WINDOWS PACKAGÉES
# ============================================================
#
# Ces identifiants viennent uniquement du catalogue interne.
#
# Aucun AUMID fourni par l'utilisateur ou le LLM
# n'est accepté.
#
# ============================================================

PACKAGED_APP_IDS = {
    "notepad": (
        "Microsoft.WindowsNotepad_8wekyb3d8bbwe!App",
    ),

    "calculator": (
        "Microsoft.WindowsCalculator_8wekyb3d8bbwe!App",
    ),

    "paint": (
        "Microsoft.Paint_8wekyb3d8bbwe!App",
    ),

    "snipping_tool": (
        "Microsoft.ScreenSketch_8wekyb3d8bbwe!App",
    ),

    "photos": (
        "Microsoft.Windows.Photos_8wekyb3d8bbwe!App",
    ),

    "media_player": (
        # Windows 10 / 11
        "Microsoft.ZuneMusic_8wekyb3d8bbwe!Microsoft.ZuneMusic",

        # Films et TV
        "Microsoft.ZuneVideo_8wekyb3d8bbwe!Microsoft.ZuneVideo",
    ),

    "camera": (
        "Microsoft.WindowsCamera_8wekyb3d8bbwe!App",
    ),

    "clock": (
        "Microsoft.WindowsAlarms_8wekyb3d8bbwe!App",
    ),

    "sound_recorder": (
        "Microsoft.WindowsSoundRecorder_8wekyb3d8bbwe!App",
    ),

    "sticky_notes": (
        "Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe!App",
    ),

    "clipchamp": (
        "Clipchamp.Clipchamp_yxz26nhyzhsrt!App",
    ),

    "phone_link": (
        "Microsoft.YourPhone_8wekyb3d8bbwe!App",
    ),

    "teams": (
        "MSTeams_8wekyb3d8bbwe!MSTeams",
    ),

    "outlook": (
        "Microsoft.OutlookForWindows_8wekyb3d8bbwe!"
        "Microsoft.OutlookforWindows",
    ),
}


# ============================================================
# PERMISSIONS
# ============================================================

def load_permissions():
    """
    Charge permissions.json.

    En cas d'erreur :
    aucune permission n'est accordée.
    """

    try:

        with open(
            PERMISSIONS_FILE,
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
        json.JSONDecodeError
    ):

        pass

    return {}


# ============================================================
# POLITIQUE APPLICATIONS
# ============================================================

def get_application_policy():

    permissions = load_permissions()

    policy = permissions.get(
        "application_policy",
        {}
    )

    if not isinstance(
        policy,
        dict
    ):

        return {}

    return policy


# ============================================================
# CONFIGURATION D'UNE APPLICATION
# ============================================================

def get_application_config(
    app_name
):

    permissions = load_permissions()

    applications = permissions.get(
        "applications",
        {}
    )

    if not isinstance(
        applications,
        dict
    ):

        return {}

    config = applications.get(
        app_name,
        {}
    )

    if not isinstance(
        config,
        dict
    ):

        return {}

    return config


# ============================================================
# PERMISSION D'UNE APPLICATION
# ============================================================

def get_application_permission(
    app_name,
    permission
):
    """
    Fonction utilisée également par web_tools.py.

    Exemple :
        get_application_permission(
            "edge",
            "can_open"
        )
    """

    policy = get_application_policy()

    if not policy.get(
        "enabled",
        False
    ):

        return False

    application = (
        get_application_config(
            app_name
        )
    )

    return bool(
        application.get(
            "enabled",
            False
        )
        and
        application.get(
            permission,
            False
        )
    )


# ============================================================
# APPLICATION PROTEGEE ?
# ============================================================

def is_hard_blocked_application(
    app_name
):

    app_name = (
        str(app_name)
        .strip()
        .lower()
    )

    # --------------------------------------------------------
    # Blocage codé en dur
    # --------------------------------------------------------

    if app_name in HARD_BLOCKED_APPLICATIONS:

        return True

    # --------------------------------------------------------
    # Blocage configurable
    # --------------------------------------------------------

    policy = get_application_policy()

    configured = policy.get(
        "hard_blocked_targets",
        []
    )

    if isinstance(
        configured,
        list
    ):

        for value in configured:

            if not isinstance(
                value,
                str
            ):

                continue

            if (
                value
                .strip()
                .lower()
                ==
                app_name
            ):

                return True

    return False


# ============================================================
# SOURCE AUTORISEE ?
# ============================================================

def is_application_source_allowed(
    app_name,
    source="unspecified",
    explicit_user_command=False
):
    """
    source :

        manual
            demande utilisateur

        routine
            routine confirmée

        habit
            habitude confirmée

        unspecified
            compatibilité avec ancien code
    """

    application = (
        get_application_config(
            app_name
        )
    )

    if not application:

        return False

    source = (
        str(source)
        .strip()
        .lower()
    )

    scope = (
        str(
            application.get(
                "scope",
                "manual"
            )
        )
        .strip()
        .lower()
    )

    policy = get_application_policy()

    # ========================================================
    # COMMANDE MANUELLE
    # ========================================================

    if source == "manual":

        if (
            scope != "core"
            and
            policy.get(
                "extended_apps_require_explicit_user_command",
                True
            )
            and
            not explicit_user_command
        ):

            return False

        return True

    # ========================================================
    # ROUTINE
    # ========================================================

    if source == "routine":

        return bool(
            application.get(
                "allow_from_routine",
                False
            )
        )

    # ========================================================
    # HABITUDE
    # ========================================================

    if source == "habit":

        return bool(
            application.get(
                "allow_from_habit",
                False
            )
        )

    # ========================================================
    # COMPATIBILITE ANCIENNE
    # ========================================================

    return (
        scope
        ==
        "core"
    )


# ============================================================
# DOSSIER WINDOWS
# ============================================================

def get_windows_directory():

    try:

        buffer = (
            ctypes
            .create_unicode_buffer(
                32768
            )
        )

        length = (
            ctypes
            .windll
            .kernel32
            .GetWindowsDirectoryW(
                buffer,
                len(buffer)
            )
        )

        if length:

            return Path(
                buffer.value
            )

    except Exception:

        pass

    value = (
        os.environ.get(
            "WINDIR"
        )
        or
        os.environ.get(
            "SystemRoot"
        )
    )

    if value:

        return Path(
            value
        )

    return None


# ============================================================
# DOSSIERS SPECIAUX WINDOWS
# ============================================================

def get_shell_folder(
    csidl
):

    try:

        buffer = (
            ctypes
            .create_unicode_buffer(
                32768
            )
        )

        result = (
            ctypes
            .windll
            .shell32
            .SHGetFolderPathW(
                None,
                csidl,
                None,
                0,
                buffer
            )
        )

        if (
            result == 0
            and
            buffer.value
        ):

            return Path(
                buffer.value
            )

    except Exception:

        pass

    return None


# ============================================================
# PROGRAM FILES
# ============================================================

def get_program_files_directory():

    # CSIDL_PROGRAM_FILES

    path = get_shell_folder(
        0x0026
    )

    if path:

        return path

    value = os.environ.get(
        "ProgramFiles"
    )

    if value:

        return Path(
            value
        )

    return None


# ============================================================
# PROGRAM FILES X86
# ============================================================

def get_program_files_x86_directory():

    # CSIDL_PROGRAM_FILESX86

    path = get_shell_folder(
        0x002A
    )

    if path:

        return path

    value = os.environ.get(
        "ProgramFiles(x86)"
    )

    if value:

        return Path(
            value
        )

    return None


# ============================================================
# LOCAL APP DATA
# ============================================================

def get_local_app_data_directory():

    # CSIDL_LOCAL_APPDATA

    path = get_shell_folder(
        0x001C
    )

    if path:

        return path

    value = os.environ.get(
        "LOCALAPPDATA"
    )

    if value:

        return Path(
            value
        )

    return None


# ============================================================
# REPARSE POINT
# ============================================================

def is_reparse_point(
    path
):

    try:

        stats = os.lstat(
            path
        )

        attributes = getattr(
            stats,
            "st_file_attributes",
            0
        )

        # FILE_ATTRIBUTE_REPARSE_POINT

        return bool(
            attributes
            &
            0x00000400
        )

    except OSError:

        return True


# ============================================================
# VALIDATION D'UN EXECUTABLE APPROUVE
# ============================================================

def validate_trusted_executable(
    path
):
    """
    Le chemin doit provenir du catalogue interne.

    Aucun chemin donné par l'utilisateur
    ne doit arriver ici.
    """

    if path is None:

        return None

    try:

        path = Path(
            path
        )

        # ----------------------------------------------------
        # Extension obligatoire
        # ----------------------------------------------------

        if (
            path
            .suffix
            .lower()
            !=
            ".exe"
        ):

            return None

        # ----------------------------------------------------
        # Existence
        # ----------------------------------------------------

        if not path.exists():

            return None

        # ----------------------------------------------------
        # Fichier normal
        # ----------------------------------------------------

        if not path.is_file():

            return None

        # ----------------------------------------------------
        # Aucun lien symbolique
        # ----------------------------------------------------

        if path.is_symlink():

            return None

        # ----------------------------------------------------
        # Aucun reparse point
        # ----------------------------------------------------

        if is_reparse_point(
            path
        ):

            return None

        return path.resolve(
            strict=True
        )

    except (
        OSError,
        RuntimeError,
        ValueError
    ):

        return None


# ============================================================
# AJOUT D'UN CHEMIN CANDIDAT
# ============================================================

def add_candidate(
    candidates,
    base,
    *parts
):

    if base is None:

        return

    candidates.append(
        Path(base)
        .joinpath(
            *parts
        )
    )


# ============================================================
# CATALOGUE DE CHEMINS
# ============================================================

def get_application_candidates(
    app_name
):
    """
    Catalogue fermé.

    Aucun scan récursif.
    Aucun PATH utilisateur.
    Aucun chemin provenant du LLM.
    """

    windows_dir = (
        get_windows_directory()
    )

    program_files = (
        get_program_files_directory()
    )

    program_files_x86 = (
        get_program_files_x86_directory()
    )

    local_app_data = (
        get_local_app_data_directory()
    )

    candidates = []

    # ========================================================
    # EXPLORATEUR
    # ========================================================

    if app_name == "explorer":

        add_candidate(
            candidates,
            windows_dir,
            "explorer.exe"
        )

    # ========================================================
    # BLOC-NOTES
    # ========================================================

    elif app_name == "notepad":

        add_candidate(
            candidates,
            windows_dir,
            "System32",
            "notepad.exe"
        )

        add_candidate(
            candidates,
            windows_dir,
            "notepad.exe"
        )

    # ========================================================
    # CALCULATRICE
    # ========================================================

    elif app_name == "calculator":

        add_candidate(
            candidates,
            windows_dir,
            "System32",
            "calc.exe"
        )

    # ========================================================
    # PAINT
    # ========================================================

    elif app_name == "paint":

        add_candidate(
            candidates,
            windows_dir,
            "System32",
            "mspaint.exe"
        )

    # ========================================================
    # CAPTURE D'ECRAN
    # ========================================================

    elif app_name == "snipping_tool":

        add_candidate(
            candidates,
            windows_dir,
            "System32",
            "SnippingTool.exe"
        )

    # ========================================================
    # EDGE
    # ========================================================

    elif app_name == "edge":

        for base in (
            program_files,
            program_files_x86,
        ):

            add_candidate(
                candidates,
                base,
                "Microsoft",
                "Edge",
                "Application",
                "msedge.exe"
            )

        add_candidate(
            candidates,
            local_app_data,
            "Microsoft",
            "Edge",
            "Application",
            "msedge.exe"
        )

    # ========================================================
    # VS CODE
    # ========================================================

    elif app_name == "vscode":

        add_candidate(
            candidates,
            local_app_data,
            "Programs",
            "Microsoft VS Code",
            "Code.exe"
        )

        for base in (
            program_files,
            program_files_x86,
        ):

            add_candidate(
                candidates,
                base,
                "Microsoft VS Code",
                "Code.exe"
            )

    # ========================================================
    # ANDROID STUDIO
    # ========================================================

    elif app_name == "android_studio":

        for base in (
            program_files,
            program_files_x86,
        ):

            add_candidate(
                candidates,
                base,
                "Android",
                "Android Studio",
                "bin",
                "studio64.exe"
            )

            add_candidate(
                candidates,
                base,
                "Android",
                "Android Studio",
                "bin",
                "studio.exe"
            )

        add_candidate(
            candidates,
            local_app_data,
            "Programs",
            "Android Studio",
            "bin",
            "studio64.exe"
        )

        add_candidate(
            candidates,
            local_app_data,
            "Programs",
            "Android Studio",
            "bin",
            "studio.exe"
        )

    # ========================================================
    # MICROSOFT OFFICE
    # ========================================================

    elif app_name in {
        "word",
        "excel",
        "powerpoint",
        "outlook",
        "onenote",
    }:

        executable_names = {
            "word": "WINWORD.EXE",
            "excel": "EXCEL.EXE",
            "powerpoint": "POWERPNT.EXE",
            "outlook": "OUTLOOK.EXE",
            "onenote": "ONENOTE.EXE",
        }

        executable_name = (
            executable_names[
                app_name
            ]
        )

        for base in (
            program_files,
            program_files_x86,
        ):

            for office_folder in (
                "Office16",
                "Office15",
                "Office14",
            ):

                # Microsoft 365 / Office moderne

                add_candidate(
                    candidates,
                    base,
                    "Microsoft Office",
                    "root",
                    office_folder,
                    executable_name
                )

                # Anciennes installations Office

                add_candidate(
                    candidates,
                    base,
                    "Microsoft Office",
                    office_folder,
                    executable_name
                )

    # ========================================================
    # WINDOWS MEDIA PLAYER
    # ========================================================

    elif app_name == "media_player":

        for base in (
            program_files,
            program_files_x86,
        ):

            add_candidate(
                candidates,
                base,
                "Windows Media Player",
                "wmplayer.exe"
            )

    return candidates


# ============================================================
# RECHERCHE SECURISEE D'UNE APPLICATION
# ============================================================

def find_application(
    app_name
):
    """
    Recherche uniquement dans le catalogue
    interne de chemins autorisés.
    """

    if not isinstance(
        app_name,
        str
    ):

        return None

    app_name = (
        app_name
        .strip()
        .lower()
    )

    if is_hard_blocked_application(
        app_name
    ):

        return None

    if app_name not in PROCESS_MAP:

        return None

    for candidate in (
        get_application_candidates(
            app_name
        )
    ):

        validated = (
            validate_trusted_executable(
                candidate
            )
        )

        if validated is not None:

            return validated

    return None


# ============================================================
# COMPATIBILITE AVEC WEB_TOOLS ET ANCIENS MODULES
# ============================================================

def find_edge():
    """
    Compatibilité avec web_tools.py.

    web_tools.py importe :
        find_edge
        get_application_permission

    La recherche d'Edge reste soumise
    au catalogue sécurisé.
    """

    return find_application(
        "edge"
    )


def find_vscode():
    """
    Wrapper de compatibilité.
    """

    return find_application(
        "vscode"
    )


def find_explorer():
    """
    Wrapper de compatibilité.
    """

    return find_application(
        "explorer"
    )


# ============================================================
# PROCESSUS WINDOWS
# ============================================================

def get_process_ids(
    process_names
):

    if isinstance(
        process_names,
        str
    ):

        process_names = (
            process_names,
        )

    expected = {
        str(name)
        .lower()
        for name in process_names
    }

    process_ids = []

    for process in psutil.process_iter(
        [
            "pid",
            "name",
        ]
    ):

        try:

            name = process.info[
                "name"
            ]

            if (
                name
                and
                name.lower()
                in
                expected
            ):

                process_ids.append(
                    process.info[
                        "pid"
                    ]
                )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied
        ):

            continue

    return process_ids


# ============================================================
# FENETRES VISIBLES
# ============================================================

def has_visible_window(
    process_ids,
    app_name
):

    if not process_ids:

        return False

    user32 = ctypes.windll.user32

    try:

        dwmapi = ctypes.windll.dwmapi

    except Exception:

        dwmapi = None

    found = ctypes.c_bool(
        False
    )

    EnumWindowsProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM
    )

    @EnumWindowsProc
    def callback(
        hwnd,
        lparam
    ):

        # ----------------------------------------------------
        # Visible ?
        # ----------------------------------------------------

        if not user32.IsWindowVisible(
            hwnd
        ):

            return True

        # ----------------------------------------------------
        # PID
        # ----------------------------------------------------

        pid = wintypes.DWORD()

        user32.GetWindowThreadProcessId(
            hwnd,
            ctypes.byref(
                pid
            )
        )

        if pid.value not in process_ids:

            return True

        # ----------------------------------------------------
        # Fenêtre masquée par DWM ?
        # ----------------------------------------------------

        if dwmapi is not None:

            cloaked = wintypes.DWORD(
                0
            )

            try:

                dwmapi.DwmGetWindowAttribute(
                    hwnd,
                    14,
                    ctypes.byref(
                        cloaked
                    ),
                    ctypes.sizeof(
                        cloaked
                    )
                )

                if cloaked.value != 0:

                    return True

            except Exception:

                pass

        # ====================================================
        # EXPLORATEUR
        # ====================================================

        if app_name == "explorer":

            class_buffer = (
                ctypes
                .create_unicode_buffer(
                    256
                )
            )

            user32.GetClassNameW(
                hwnd,
                class_buffer,
                256
            )

            window_class = (
                class_buffer
                .value
                .strip()
            )

            if window_class in {
                "CabinetWClass",
                "ExploreWClass",
            }:

                found.value = True

                return False

            return True

        # ----------------------------------------------------
        # Titre
        # ----------------------------------------------------

        title_length = (
            user32
            .GetWindowTextLengthW(
                hwnd
            )
        )

        if title_length <= 0:

            return True

        buffer = (
            ctypes
            .create_unicode_buffer(
                title_length + 1
            )
        )

        user32.GetWindowTextW(
            hwnd,
            buffer,
            title_length + 1
        )

        title = (
            buffer
            .value
            .strip()
            .lower()
        )

        if not title:

            return True

        # ====================================================
        # EDGE
        # ====================================================

        if app_name == "edge":

            if (
                "microsoft edge"
                in
                title
                or
                title.endswith(
                    " - edge"
                )
            ):

                found.value = True

                return False

            return True

        # ====================================================
        # VS CODE
        # ====================================================

        if app_name == "vscode":

            if (
                "visual studio code"
                in
                title
                or
                title.endswith(
                    " - code"
                )
            ):

                found.value = True

                return False

            return True

        # ----------------------------------------------------
        # Pour les autres applications approuvées,
        # une fenêtre visible du bon processus suffit.
        # ----------------------------------------------------

        found.value = True

        return False

    user32.EnumWindows(
        callback,
        0
    )

    return found.value


# ============================================================
# APPLICATION OUVERTE ?
# ============================================================

def is_application_running(
    app_name,
    source="unspecified"
):

    if not isinstance(
        app_name,
        str
    ):

        return (
            False,
            "Nom d'application invalide."
        )

    app_name = (
        app_name
        .lower()
        .strip()
    )

    # ========================================================
    # BLOCAGE SYSTEME
    # ========================================================

    if is_hard_blocked_application(
        app_name
    ):

        return (
            False,
            (
                "Cette application est protégée "
                "et ne peut pas être contrôlée."
            )
        )

    # ========================================================
    # CATALOGUE
    # ========================================================

    if app_name not in PROCESS_MAP:

        return (
            False,
            (
                "Application inconnue ou "
                f"non autorisée : {app_name}"
            )
        )

    # ========================================================
    # PERMISSION
    # ========================================================

    if not get_application_permission(
        app_name,
        "can_check"
    ):

        return (
            False,
            (
                "Vérification interdite "
                f"pour : {app_name}"
            )
        )

    # ========================================================
    # SOURCE
    # ========================================================

    if not is_application_source_allowed(
        app_name,
        source=source,
        explicit_user_command=(
            source
            ==
            "manual"
        )
    ):

        return (
            False,
            (
                "Vérification non autorisée "
                "dans ce contexte."
            )
        )

    # ========================================================
    # PROCESSUS
    # ========================================================

    process_ids = (
        get_process_ids(
            PROCESS_MAP[
                app_name
            ]
        )
    )

    display_name = (
        DISPLAY_NAMES.get(
            app_name,
            app_name
        )
    )

    if not process_ids:

        return (
            False,
            (
                f"{display_name} "
                "est fermé."
            )
        )

    # ========================================================
    # FENETRE VISIBLE
    # ========================================================

    if has_visible_window(
        process_ids,
        app_name
    ):

        return (
            True,
            (
                f"{display_name} "
                "est ouvert."
            )
        )

    return (
        False,
        (
            f"{display_name} n'a aucune fenêtre "
            "ouverte "
            "(processus en arrière-plan uniquement)."
        )
    )


# ============================================================
# LANCEMENT DETACHE D'UN EXECUTABLE
# ============================================================

def launch_detached(
    executable
):
    """
    Lance uniquement un exécutable déjà validé.

    Aucun :
        shell=True
        PowerShell
        cmd
        argument utilisateur
    """

    executable = (
        validate_trusted_executable(
            executable
        )
    )

    if executable is None:

        raise OSError(
            (
                "Exécutable non fiable "
                "ou introuvable."
            )
        )

    creation_flags = (
        subprocess
        .CREATE_NEW_PROCESS_GROUP
        |
        subprocess
        .DETACHED_PROCESS
    )

    subprocess.Popen(
        [
            str(
                executable
            )
        ],

        shell=False,

        stdin=(
            subprocess
            .DEVNULL
        ),

        stdout=(
            subprocess
            .DEVNULL
        ),

        stderr=(
            subprocess
            .DEVNULL
        ),

        close_fds=True,

        creationflags=(
            creation_flags
        )
    )


# ============================================================
# GUID WINDOWS
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
    value
):

    parsed = uuid.UUID(
        value.strip(
            "{}"
        )
    )

    raw = parsed.bytes_le

    result = GUID()

    result.Data1 = int.from_bytes(
        raw[0:4],
        "little"
    )

    result.Data2 = int.from_bytes(
        raw[4:6],
        "little"
    )

    result.Data3 = int.from_bytes(
        raw[6:8],
        "little"
    )

    for index in range(8):

        result.Data4[
            index
        ] = (
            raw[
                8 + index
            ]
        )

    return result


# ============================================================
# ACTIVATION APPLICATION WINDOWS PACKAGÉE
# ============================================================

def activate_packaged_app(
    aumid
):
    """
    Active une application UWP/MSIX
    uniquement si son AUMID appartient
    à notre catalogue interne.
    """

    if not isinstance(
        aumid,
        str
    ):

        return False

    allowed_aumids = {
        item
        for values
        in PACKAGED_APP_IDS.values()
        for item
        in values
    }

    if aumid not in allowed_aumids:

        return False

    try:

        ole32 = ctypes.windll.ole32

    except Exception:

        return False

    # --------------------------------------------------------
    # COM
    # --------------------------------------------------------

    coinit_result = (
        ole32
        .CoInitializeEx(
            None,
            0x2
        )
    )

    should_uninitialize = (
        coinit_result
        in
        {
            0,
            1,
        }
    )

    try:

        clsid = guid_from_string(
            (
                "{45BA127D-10A8-46EA-"
                "8AB7-56EA9078943C}"
            )
        )

        iid = guid_from_string(
            (
                "{2E941141-7F97-4756-"
                "BA1D-9DECDE894A3D}"
            )
        )

        instance = (
            ctypes
            .c_void_p()
        )

        # CLSCTX_LOCAL_SERVER = 4

        result = (
            ole32
            .CoCreateInstance(
                ctypes.byref(
                    clsid
                ),
                None,
                0x4,
                ctypes.byref(
                    iid
                ),
                ctypes.byref(
                    instance
                )
            )
        )

        if (
            result != 0
            or
            not instance.value
        ):

            return False

        try:

            vtable_pointer = (
                ctypes.cast(
                    instance,
                    ctypes.POINTER(
                        ctypes.POINTER(
                            ctypes.c_void_p
                        )
                    )
                )
            )

            vtable = (
                vtable_pointer
                .contents
            )

            ActivateApplicationPrototype = (
                ctypes.WINFUNCTYPE(
                    ctypes.c_long,
                    ctypes.c_void_p,
                    wintypes.LPCWSTR,
                    wintypes.LPCWSTR,
                    wintypes.DWORD,
                    ctypes.POINTER(
                        wintypes.DWORD
                    )
                )
            )

            activate_application = (
                ActivateApplicationPrototype(
                    vtable[3]
                )
            )

            process_id = (
                wintypes.DWORD(
                    0
                )
            )

            # AO_NONE = 0

            result = (
                activate_application(
                    instance,
                    aumid,
                    None,
                    0,
                    ctypes.byref(
                        process_id
                    )
                )
            )

            return (
                result
                ==
                0
            )

        finally:

            try:

                ReleasePrototype = (
                    ctypes.WINFUNCTYPE(
                        ctypes.c_ulong,
                        ctypes.c_void_p
                    )
                )

                vtable_pointer = (
                    ctypes.cast(
                        instance,
                        ctypes.POINTER(
                            ctypes.POINTER(
                                ctypes.c_void_p
                            )
                        )
                    )
                )

                release = (
                    ReleasePrototype(
                        vtable_pointer
                        .contents[2]
                    )
                )

                release(
                    instance
                )

            except Exception:

                pass

    except Exception:

        return False

    finally:

        if should_uninitialize:

            try:

                ole32.CoUninitialize()

            except Exception:

                pass


# ============================================================
# LANCEMENT APPLICATION PACKAGÉE
# ============================================================

def launch_packaged_application(
    app_name
):

    identifiers = (
        PACKAGED_APP_IDS.get(
            app_name,
            ()
        )
    )

    for aumid in identifiers:

        if activate_packaged_app(
            aumid
        ):

            return True

    return False


# ============================================================
# OUVERTURE D'UNE APPLICATION
# ============================================================

def open_application(
    app_name,
    source="unspecified",
    explicit_user_command=False
):
    """
    Ouvre uniquement une application
    appartenant au catalogue approuvé.

    app_name n'est jamais interprété
    comme un chemin.
    """

    # ========================================================
    # WINDOWS
    # ========================================================

    windows_info = (
        get_windows_info()
    )

    if not windows_info[
        "supported"
    ]:

        return (
            False,
            (
                "AgentLocal prend en charge "
                "Windows 10 et Windows 11."
            )
        )

    # ========================================================
    # NOM
    # ========================================================

    if not isinstance(
        app_name,
        str
    ):

        return (
            False,
            (
                "Nom d'application "
                "invalide."
            )
        )

    app_name = (
        app_name
        .lower()
        .strip()
    )

    # ========================================================
    # OUTILS SYSTEME
    # ========================================================

    if is_hard_blocked_application(
        app_name
    ):

        return (
            False,
            (
                "Cette application appartient "
                "aux outils système protégés "
                "et ne peut pas être ouverte "
                "par AgentLocal."
            )
        )

    # ========================================================
    # CATALOGUE FERME
    # ========================================================

    if app_name not in PROCESS_MAP:

        return (
            False,
            (
                "Application inconnue ou "
                f"non autorisée : {app_name}"
            )
        )

    # ========================================================
    # PERMISSION
    # ========================================================

    if not get_application_permission(
        app_name,
        "can_open"
    ):

        return (
            False,
            (
                "Ouverture interdite "
                f"pour : {app_name}"
            )
        )

    # ========================================================
    # SOURCE
    # ========================================================

    if not is_application_source_allowed(
        app_name,
        source=source,
        explicit_user_command=(
            explicit_user_command
        )
    ):

        return (
            False,
            (
                "Cette application ne peut pas "
                "être ouverte dans ce contexte. "
                "Une commande utilisateur explicite "
                "peut être requise."
            )
        )

    display_name = (
        DISPLAY_NAMES.get(
            app_name,
            app_name
        )
    )

    # ========================================================
    # DEJA OUVERTE ?
    # ========================================================

    if get_application_permission(
        app_name,
        "can_check"
    ):

        running, _ = (
            is_application_running(
                app_name,
                source=source
            )
        )

        if running:

            return (
                True,
                (
                    f"{display_name} "
                    "est déjà ouvert."
                )
            )

    # ========================================================
    # WIN32
    # ========================================================

    executable = (
        find_application(
            app_name
        )
    )

    if executable is not None:

        try:

            launch_detached(
                executable
            )

            return (
                True,
                (
                    f"{display_name} "
                    "a été lancé."
                )
            )

        except OSError as error:

            return (
                False,
                (
                    f"Impossible de lancer "
                    f"{display_name} : "
                    f"{error}"
                )
            )

    # ========================================================
    # APPLICATION PACKAGÉE
    # ========================================================

    if app_name in PACKAGED_APP_IDS:

        if launch_packaged_application(
            app_name
        ):

            return (
                True,
                (
                    f"{display_name} "
                    "a été lancé."
                )
            )

    # ========================================================
    # INTROUVABLE
    # ========================================================

    return (
        False,
        (
            f"{display_name} n'a pas été trouvé "
            "ou n'est pas installé sous une forme "
            "approuvée sur "
            f"{windows_info['label']}."
        )
    )


# ============================================================
# AUDIT DU CATALOGUE
# ============================================================

def audit_application_catalog():
    """
    Vérifie les applications sans en ouvrir.
    """

    results = []

    windows_info = (
        get_windows_info()
    )

    for app_name in PROCESS_MAP:

        config = (
            get_application_config(
                app_name
            )
        )

        executable = (
            find_application(
                app_name
            )
        )

        packaged = (
            app_name
            in
            PACKAGED_APP_IDS
        )

        results.append(
            {
                "app": app_name,

                "display_name": (
                    DISPLAY_NAMES.get(
                        app_name,
                        app_name
                    )
                ),

                "enabled": bool(
                    config.get(
                        "enabled",
                        False
                    )
                ),

                "win32_found": (
                    executable
                    is not None
                ),

                "packaged_fallback": (
                    packaged
                ),

                "windows_family": (
                    windows_info[
                        "family"
                    ]
                ),
            }
        )

    return results


# ============================================================
# TEST DIRECT
# ============================================================


# ============================================================
# FERMETURE CONTROLEE DES FENETRES
# ============================================================

WM_CLOSE = 0x0010


def is_application_close_source_allowed(
    app_name,
    source="unspecified",
    explicit_user_command=False
):
    """
    Politique dédiée à la fermeture.

    La fermeture n'est jamais héritée automatiquement
    des permissions d'ouverture : une commande manuelle
    explicite est exigée par défaut.
    """

    application = get_application_config(
        app_name
    )

    if not application:
        return False

    policy = get_application_policy()

    source = (
        str(source)
        .strip()
        .lower()
    )

    if source == "manual":

        if (
            policy.get(
                "close_requires_explicit_user_command",
                True
            )
            and
            not explicit_user_command
        ):
            return False

        return True

    if source == "routine":

        if not policy.get(
            "allow_close_from_routine",
            False
        ):
            return False

        return bool(
            application.get(
                "allow_close_from_routine",
                False
            )
        )

    if source == "habit":

        if not policy.get(
            "allow_close_from_habit",
            False
        ):
            return False

        return bool(
            application.get(
                "allow_close_from_habit",
                False
            )
        )

    return False


def get_window_title(
    hwnd
):
    try:
        user32 = ctypes.windll.user32

        length = user32.GetWindowTextLengthW(
            hwnd
        )

        if length <= 0:
            return ""

        buffer = ctypes.create_unicode_buffer(
            length + 1
        )

        user32.GetWindowTextW(
            hwnd,
            buffer,
            length + 1
        )

        return buffer.value.strip()

    except Exception:
        return ""


def get_window_class_name(
    hwnd
):
    try:
        buffer = ctypes.create_unicode_buffer(
            256
        )

        ctypes.windll.user32.GetClassNameW(
            hwnd,
            buffer,
            256
        )

        return buffer.value.strip()

    except Exception:
        return ""


def is_window_cloaked(
    hwnd
):
    try:
        dwmapi = ctypes.windll.dwmapi

        cloaked = wintypes.DWORD(
            0
        )

        result = dwmapi.DwmGetWindowAttribute(
            hwnd,
            14,
            ctypes.byref(
                cloaked
            ),
            ctypes.sizeof(
                cloaked
            )
        )

        if result != 0:
            return False

        return cloaked.value != 0

    except Exception:
        return False


def get_window_pid(
    hwnd
):
    try:
        pid = wintypes.DWORD(
            0
        )

        ctypes.windll.user32.GetWindowThreadProcessId(
            hwnd,
            ctypes.byref(
                pid
            )
        )

        return int(
            pid.value
        )

    except Exception:
        return 0


def get_process_create_time(
    pid
):
    try:
        return float(
            psutil.Process(
                int(pid)
            ).create_time()
        )

    except (
        psutil.NoSuchProcess,
        psutil.AccessDenied,
        ValueError,
        TypeError,
    ):
        return None


def get_child_process_id_matching(
    hwnd,
    process_ids
):
    """
    Sous Windows 10, certaines applications UWP/MSIX
    peuvent être hébergées dans ApplicationFrameHost.

    On recherche alors un enfant de la fenêtre dont le PID
    appartient réellement à l'application autorisée.
    """

    if not process_ids:
        return None

    expected = set(
        int(pid)
        for pid in process_ids
    )

    found = ctypes.c_ulong(
        0
    )

    try:
        user32 = ctypes.windll.user32

        EnumChildProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HWND,
            wintypes.LPARAM
        )

        @EnumChildProc
        def callback(
            child_hwnd,
            lparam
        ):
            child_pid = wintypes.DWORD(
                0
            )

            user32.GetWindowThreadProcessId(
                child_hwnd,
                ctypes.byref(
                    child_pid
                )
            )

            if child_pid.value in expected:
                found.value = child_pid.value
                return False

            return True

        user32.EnumChildWindows(
            hwnd,
            callback,
            0
        )

    except Exception:
        return None

    if found.value:
        return int(
            found.value
        )

    return None


def get_application_window_records(
    app_name
):
    """
    Retourne uniquement les fenêtres visibles appartenant
    à une application du catalogue fermé.

    Aucune recherche par chemin ou nom fourni par l'utilisateur
    n'est effectuée.
    """

    if not isinstance(
        app_name,
        str
    ):
        return []

    app_name = (
        app_name
        .strip()
        .lower()
    )

    if (
        app_name not in PROCESS_MAP
        or
        is_hard_blocked_application(
            app_name
        )
    ):
        return []

    process_ids = get_process_ids(
        PROCESS_MAP[
            app_name
        ]
    )

    if not process_ids:
        return []

    expected_pids = set(
        int(pid)
        for pid in process_ids
    )

    records = []

    try:
        user32 = ctypes.windll.user32

        EnumWindowsProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HWND,
            wintypes.LPARAM
        )

        @EnumWindowsProc
        def callback(
            hwnd,
            lparam
        ):
            if not user32.IsWindowVisible(
                hwnd
            ):
                return True

            if is_window_cloaked(
                hwnd
            ):
                return True

            window_pid = get_window_pid(
                hwnd
            )

            if not window_pid:
                return True

            window_class = get_window_class_name(
                hwnd
            )

            title = get_window_title(
                hwnd
            )

            direct_match = (
                window_pid
                in
                expected_pids
            )

            app_process_id = (
                window_pid
                if direct_match
                else None
            )

            # ------------------------------------------------
            # Hôte UWP/MSIX Windows 10
            # ------------------------------------------------

            if (
                not direct_match
                and
                window_class
                ==
                "ApplicationFrameWindow"
            ):
                app_process_id = (
                    get_child_process_id_matching(
                        hwnd,
                        expected_pids
                    )
                )

            # ------------------------------------------------
            # Explorateur : jamais le shell du Bureau
            # ------------------------------------------------

            if app_name == "explorer":
                if window_class not in {
                    "CabinetWClass",
                    "ExploreWClass",
                }:
                    return True

                if not direct_match:
                    return True

            elif app_process_id is None:
                return True

            # ------------------------------------------------
            # Filtres supplémentaires Edge / VS Code
            # ------------------------------------------------

            title_lower = title.lower()

            if app_name == "edge":
                if not (
                    "microsoft edge" in title_lower
                    or
                    title_lower.endswith(
                        " - edge"
                    )
                ):
                    return True

            if app_name == "vscode":
                if not (
                    "visual studio code" in title_lower
                    or
                    title_lower.endswith(
                        " - code"
                    )
                ):
                    return True

            records.append(
                {
                    "hwnd": int(hwnd),
                    "window_pid": int(window_pid),
                    "window_process_create_time": (
                        get_process_create_time(
                            window_pid
                        )
                    ),
                    "app_pid": int(
                        app_process_id
                        or
                        window_pid
                    ),
                    "title": title,
                    "class_name": window_class,
                }
            )

            return True

        user32.EnumWindows(
            callback,
            0
        )

    except Exception:
        return []

    return records


def get_application_window_handles(
    app_name
):
    return [
        item[
            "hwnd"
        ]
        for item in get_application_window_records(
            app_name
        )
    ]


def is_expected_application_window(
    hwnd,
    app_name,
    expected_pid=None,
    expected_process_create_time=None
):
    """
    Révalidation juste avant une fermeture.

    Cette vérification évite d'utiliser aveuglément un ancien
    handle de fenêtre stocké localement.
    """

    try:
        hwnd = int(
            hwnd
        )
    except (
        TypeError,
        ValueError,
    ):
        return False

    for record in get_application_window_records(
        app_name
    ):
        if record[
            "hwnd"
        ] != hwnd:
            continue

        if (
            expected_pid is not None
            and
            record[
                "window_pid"
            ]
            !=
            int(
                expected_pid
            )
        ):
            return False

        if expected_process_create_time is not None:
            current_create_time = record.get(
                "window_process_create_time"
            )

            if current_create_time is None:
                return False

            try:
                if abs(
                    float(current_create_time)
                    -
                    float(expected_process_create_time)
                ) > 0.5:
                    return False
            except (
                TypeError,
                ValueError,
            ):
                return False

        return True

    return False


def close_application_window(
    hwnd,
    app_name,
    source="manual",
    explicit_user_command=False,
    expected_pid=None,
    expected_process_create_time=None
):
    """
    Envoie WM_CLOSE à UNE fenêtre validée.

    Aucun TerminateProcess, taskkill, shell, PowerShell ou CMD.
    Les applications peuvent donc afficher leur propre boîte de
    confirmation si un document n'est pas enregistré.
    """

    if not get_application_permission(
        app_name,
        "can_close"
    ):
        return (
            False,
            "Fermeture interdite par permissions.json."
        )

    if not is_application_close_source_allowed(
        app_name,
        source=source,
        explicit_user_command=explicit_user_command
    ):
        return (
            False,
            "Fermeture non autorisée dans ce contexte."
        )

    if not is_expected_application_window(
        hwnd,
        app_name,
        expected_pid=expected_pid,
        expected_process_create_time=(
            expected_process_create_time
        )
    ):
        return (
            False,
            "La fenêtre n'est plus une fenêtre autorisée de l'application."
        )

    try:
        result = ctypes.windll.user32.PostMessageW(
            int(hwnd),
            WM_CLOSE,
            0,
            0
        )

        if not result:
            return (
                False,
                "Windows a refusé la demande de fermeture."
            )

        return (
            True,
            "Demande de fermeture envoyée."
        )

    except Exception as error:
        return (
            False,
            (
                "Impossible d'envoyer la demande de fermeture : "
                f"{error}"
            )
        )


def close_application(
    app_name,
    source="unspecified",
    explicit_user_command=False
):
    """
    Ferme proprement les fenêtres visibles d'une application
    autorisée.

    La fermeture est volontairement GRACIEUSE :
    aucun processus n'est tué de force. Si Word, Excel, VS Code,
    Android Studio, etc. ont du travail non enregistré, leur boîte
    de confirmation habituelle reste donc active.
    """

    windows_info = get_windows_info()

    if not windows_info[
        "supported"
    ]:
        return (
            False,
            "AgentLocal prend en charge Windows 10 et Windows 11."
        )

    if not isinstance(
        app_name,
        str
    ):
        return (
            False,
            "Nom d'application invalide."
        )

    app_name = (
        app_name
        .strip()
        .lower()
    )

    if is_hard_blocked_application(
        app_name
    ):
        return (
            False,
            "Cette application système est protégée."
        )

    if app_name not in PROCESS_MAP:
        return (
            False,
            (
                "Application inconnue ou non autorisée : "
                f"{app_name}"
            )
        )

    if not get_application_permission(
        app_name,
        "can_close"
    ):
        return (
            False,
            (
                "Fermeture interdite pour : "
                f"{app_name}"
            )
        )

    if not is_application_close_source_allowed(
        app_name,
        source=source,
        explicit_user_command=explicit_user_command
    ):
        return (
            False,
            (
                "La fermeture exige une commande "
                "utilisateur explicite."
            )
        )

    display_name = DISPLAY_NAMES.get(
        app_name,
        app_name
    )

    records = get_application_window_records(
        app_name
    )

    if not records:
        return (
            True,
            f"{display_name} est déjà fermé."
        )

    requested = 0

    for record in records:
        success, _ = close_application_window(
            record[
                "hwnd"
            ],
            app_name,
            source=source,
            explicit_user_command=explicit_user_command,
            expected_pid=record[
                "window_pid"
            ],
            expected_process_create_time=record.get(
                "window_process_create_time"
            )
        )

        if success:
            requested += 1

    if requested == 0:
        return (
            False,
            f"Aucune fenêtre de {display_name} n'a pu être fermée."
        )

    # Laisse l'application traiter WM_CLOSE sans bloquer longtemps.
    deadline = time.time() + 3.0

    remaining = records

    while time.time() < deadline:
        remaining = get_application_window_records(
            app_name
        )

        if not remaining:
            break

        time.sleep(
            0.15
        )

    if remaining:
        return (
            True,
            (
                f"Demande de fermeture envoyée à {display_name}. "
                f"{len(remaining)} fenêtre(s) restent ouvertes, "
                "probablement en attente d'une confirmation "
                "ou d'un enregistrement."
            )
        )

    return (
        True,
        f"{display_name} a été fermé proprement."
    )


if __name__ == "__main__":

    print()

    print(
        "=" * 70
    )

    print(
        (
            "AUDIT WINDOWS_TOOLS - "
            "AUCUNE APPLICATION N'EST LANCEE"
        )
    )

    print(
        "=" * 70
    )

    print()

    # ========================================================
    # WINDOWS
    # ========================================================

    windows_info = (
        get_windows_info()
    )

    print(
        "Système détecté :",
        windows_info[
            "label"
        ]
    )

    print(
        "Build Windows :",
        windows_info[
            "build"
        ]
    )

    print(
        "Compatible :",
        (
            "OUI"
            if windows_info[
                "supported"
            ]
            else
            "NON"
        )
    )

    print()

    # ========================================================
    # POLITIQUE
    # ========================================================

    policy = (
        get_application_policy()
    )

    print(
        "Politique applications :",
        (
            "active"
            if policy.get(
                "enabled",
                False
            )
            else
            "inactive"
        )
    )

    print()

    # ========================================================
    # APPLICATIONS
    # ========================================================

    for item in (
        audit_application_catalog()
    ):

        print(
            (
                f"- {item['display_name']} : "
                f"permission="
                f"{'OUI' if item['enabled'] else 'NON'} | "
                f"Win32="
                f"{'trouvé' if item['win32_found'] else 'non trouvé'} | "
                f"package="
                f"{'prévu' if item['packaged_fallback'] else 'non'}"
            )
        )

    print()

    # ========================================================
    # COMPATIBILITE WEB_TOOLS
    # ========================================================

    edge_path = find_edge()

    print(
        "Compatibilité web_tools.py :"
    )

    print(
        (
            "- find_edge() : "
            f"{edge_path if edge_path else 'Edge non trouvé'}"
        )
    )

    print(
        (
            "- get_application_permission("
            "'edge', 'can_open') : "
            f"{get_application_permission('edge', 'can_open')}"
        )
    )

    print()

    # ========================================================
    # OUTILS PROTEGES
    # ========================================================

    print(
        "Outils système toujours bloqués :"
    )

    for target in (
        "cmd",
        "powershell",
        "windows_terminal",
        "regedit",
        "msconfig",
    ):

        print(
            (
                f"- {target} : "
                f"{'BLOQUÉ' if is_hard_blocked_application(target) else 'ERREUR'}"
            )
        )

    print()

    print(
        (
            "Aucune application n'a été ouverte "
            "pendant cet audit."
        )
    )

    print()