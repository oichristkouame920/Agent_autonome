import ctypes
import json
import os
import subprocess
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
# APPLICATIONS CONNUES
# ============================================================

PROCESS_MAP = {
    "edge": "msedge.exe",
    "vscode": "Code.exe",
}


DISPLAY_NAMES = {
    "edge": "Edge",
    "vscode": "VS Code",
}


# ============================================================
# PERMISSIONS
# ============================================================

def load_permissions():
    """
    Charge les permissions depuis permissions.json.

    En cas d'erreur, aucune permission n'est accordée.
    """

    try:
        with open(
            PERMISSIONS_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except (
        FileNotFoundError,
        json.JSONDecodeError
    ):
        return {}


def get_application_permission(
    app_name,
    permission
):
    """
    Vérifie une permission pour une application.
    """

    permissions = load_permissions()

    application = (
        permissions
        .get("applications", {})
        .get(app_name, {})
    )

    return (
        application.get("enabled", False)
        and
        application.get(permission, False)
    )


# ============================================================
# PROCESSUS WINDOWS
# ============================================================

def get_process_ids(process_name):
    """
    Retourne les PID correspondant au processus demandé.
    """

    process_ids = []

    for process in psutil.process_iter(
        ["pid", "name"]
    ):
        try:

            name = process.info["name"]

            if (
                name
                and name.lower() == process_name.lower()
            ):
                process_ids.append(
                    process.info["pid"]
                )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied
        ):
            continue

    return process_ids


# ============================================================
# DETECTION DES FENETRES VISIBLES
# ============================================================

def has_visible_window(
    process_ids,
    app_name
):
    """
    Vérifie si l'application possède réellement
    une fenêtre visible.

    Les processus qui restent en arrière-plan
    ne sont pas considérés comme une application ouverte.
    """

    if not process_ids:
        return False

    user32 = ctypes.windll.user32
    dwmapi = ctypes.windll.dwmapi

    found = ctypes.c_bool(False)

    EnumWindowsProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM
    )

    @EnumWindowsProc
    def callback(hwnd, lparam):

        # ----------------------------------------------------
        # Fenêtre visible ?
        # ----------------------------------------------------

        if not user32.IsWindowVisible(hwnd):
            return True

        # ----------------------------------------------------
        # PID de la fenêtre
        # ----------------------------------------------------

        pid = wintypes.DWORD()

        user32.GetWindowThreadProcessId(
            hwnd,
            ctypes.byref(pid)
        )

        if pid.value not in process_ids:
            return True

        # ----------------------------------------------------
        # Ignore les fenêtres Windows masquées / cloaked
        # ----------------------------------------------------

        cloaked = wintypes.DWORD(0)

        try:

            dwmapi.DwmGetWindowAttribute(
                hwnd,
                14,  # DWMWA_CLOAKED
                ctypes.byref(cloaked),
                ctypes.sizeof(cloaked)
            )

            if cloaked.value != 0:
                return True

        except Exception:
            pass

        # ----------------------------------------------------
        # Titre de la fenêtre
        # ----------------------------------------------------

        title_length = (
            user32.GetWindowTextLengthW(hwnd)
        )

        if title_length <= 0:
            return True

        buffer = ctypes.create_unicode_buffer(
            title_length + 1
        )

        user32.GetWindowTextW(
            hwnd,
            buffer,
            title_length + 1
        )

        title = (
            buffer.value
            .strip()
            .lower()
        )

        if not title:
            return True

        # ----------------------------------------------------
        # MICROSOFT EDGE
        # ----------------------------------------------------

        if app_name == "edge":

            if (
                "microsoft edge" in title
                or title.endswith(" - edge")
            ):
                found.value = True
                return False

        # ----------------------------------------------------
        # VISUAL STUDIO CODE
        # ----------------------------------------------------

        elif app_name == "vscode":

            if (
                "visual studio code" in title
                or title.endswith(" - code")
            ):
                found.value = True
                return False

        return True

    user32.EnumWindows(
        callback,
        0
    )

    return found.value


# ============================================================
# VERIFICATION D'UNE APPLICATION
# ============================================================

def is_application_running(app_name):
    """
    Vérifie si une vraie fenêtre de l'application
    est actuellement ouverte.
    """

    app_name = (
        app_name
        .lower()
        .strip()
    )

    # --------------------------------------------------------
    # Application connue ?
    # --------------------------------------------------------

    if app_name not in PROCESS_MAP:

        return (
            False,
            (
                "Application inconnue ou "
                f"non autorisée : {app_name}"
            )
        )

    # --------------------------------------------------------
    # Permission de vérification ?
    # --------------------------------------------------------

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

    process_name = (
        PROCESS_MAP[app_name]
    )

    process_ids = get_process_ids(
        process_name
    )

    display_name = DISPLAY_NAMES.get(
        app_name,
        app_name
    )

    # --------------------------------------------------------
    # Aucun processus
    # --------------------------------------------------------

    if not process_ids:

        return (
            False,
            f"{display_name} est fermé."
        )

    # --------------------------------------------------------
    # Une vraie fenêtre est visible
    # --------------------------------------------------------

    if has_visible_window(
        process_ids,
        app_name
    ):

        return (
            True,
            f"{display_name} est ouvert."
        )

    # --------------------------------------------------------
    # Processus en arrière-plan uniquement
    # --------------------------------------------------------

    return (
        False,
        (
            f"{display_name} n'a aucune fenêtre "
            "ouverte (processus en arrière-plan uniquement)."
        )
    )


# ============================================================
# RECHERCHE DE MICROSOFT EDGE
# ============================================================

def find_edge():
    """
    Recherche Microsoft Edge uniquement
    dans ses emplacements standards.
    """

    candidates = []

    program_files = os.environ.get(
        "ProgramFiles"
    )

    program_files_x86 = os.environ.get(
        "ProgramFiles(x86)"
    )

    local_app_data = os.environ.get(
        "LOCALAPPDATA"
    )

    # --------------------------------------------------------
    # Program Files
    # --------------------------------------------------------

    if program_files:

        candidates.append(
            Path(program_files)
            / "Microsoft"
            / "Edge"
            / "Application"
            / "msedge.exe"
        )

    # --------------------------------------------------------
    # Program Files (x86)
    # --------------------------------------------------------

    if program_files_x86:

        candidates.append(
            Path(program_files_x86)
            / "Microsoft"
            / "Edge"
            / "Application"
            / "msedge.exe"
        )

    # --------------------------------------------------------
    # Installation utilisateur
    # --------------------------------------------------------

    if local_app_data:

        candidates.append(
            Path(local_app_data)
            / "Microsoft"
            / "Edge"
            / "Application"
            / "msedge.exe"
        )

    # --------------------------------------------------------
    # Premier chemin existant
    # --------------------------------------------------------

    for path in candidates:

        if path.exists():
            return path

    return None


# ============================================================
# RECHERCHE DE VISUAL STUDIO CODE
# ============================================================

def find_vscode():
    """
    Recherche Visual Studio Code uniquement
    dans ses emplacements standards.
    """

    candidates = []

    local_app_data = os.environ.get(
        "LOCALAPPDATA"
    )

    program_files = os.environ.get(
        "ProgramFiles"
    )

    program_files_x86 = os.environ.get(
        "ProgramFiles(x86)"
    )

    # --------------------------------------------------------
    # Installation utilisateur
    # --------------------------------------------------------

    if local_app_data:

        candidates.append(
            Path(local_app_data)
            / "Programs"
            / "Microsoft VS Code"
            / "Code.exe"
        )

    # --------------------------------------------------------
    # Installation système 64 bits
    # --------------------------------------------------------

    if program_files:

        candidates.append(
            Path(program_files)
            / "Microsoft VS Code"
            / "Code.exe"
        )

    # --------------------------------------------------------
    # Installation système 32 bits
    # --------------------------------------------------------

    if program_files_x86:

        candidates.append(
            Path(program_files_x86)
            / "Microsoft VS Code"
            / "Code.exe"
        )

    # --------------------------------------------------------
    # Premier chemin existant
    # --------------------------------------------------------

    for path in candidates:

        if path.exists():
            return path

    return None


# ============================================================
# RECHERCHE GENERALE D'UNE APPLICATION
# ============================================================

def find_application(app_name):
    """
    Retourne uniquement l'exécutable
    d'une application connue.

    Le LLM ne peut pas fournir lui-même
    un chemin d'exécutable arbitraire.
    """

    if app_name == "edge":
        return find_edge()

    if app_name == "vscode":
        return find_vscode()

    return None


# ============================================================
# LANCEMENT DETACHE
# ============================================================

def launch_detached(executable):
    """
    Lance une application graphique comme processus
    indépendant d'AgentLocal.

    Ainsi, lorsque AgentLocal s'arrête,
    l'application lancée doit rester ouverte.
    """

    subprocess.Popen(
        [str(executable)],

        # Aucun passage par cmd.exe ou PowerShell.
        shell=False,

        # L'application n'utilise pas l'entrée
        # standard d'AgentLocal.
        stdin=subprocess.DEVNULL,

        # Les logs de l'application ne polluent
        # pas la console AgentLocal.
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,

        # Ne conserve pas les descripteurs
        # de fichiers du processus parent.
        close_fds=True,

        # Nouveau groupe de processus
        # + détachement de la console AgentLocal.
        creationflags=(
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
        )
    )


# ============================================================
# OUVERTURE D'UNE APPLICATION
# ============================================================

def open_application(app_name):
    """
    Ouvre uniquement une application connue
    et explicitement autorisée.

    L'application est lancée indépendamment
    d'AgentLocal.
    """

    app_name = (
        app_name
        .lower()
        .strip()
    )

    # --------------------------------------------------------
    # Application connue ?
    # --------------------------------------------------------

    if app_name not in PROCESS_MAP:

        return (
            False,
            (
                "Application inconnue ou "
                f"non autorisée : {app_name}"
            )
        )

    # --------------------------------------------------------
    # Permission can_open ?
    # --------------------------------------------------------

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

    display_name = DISPLAY_NAMES.get(
        app_name,
        app_name
    )

    # --------------------------------------------------------
    # Application déjà ouverte ?
    # --------------------------------------------------------

    if get_application_permission(
        app_name,
        "can_check"
    ):

        running, _ = (
            is_application_running(
                app_name
            )
        )

        if running:

            return (
                True,
                f"{display_name} est déjà ouvert."
            )

    # --------------------------------------------------------
    # Recherche de l'exécutable
    # --------------------------------------------------------

    executable = find_application(
        app_name
    )

    if executable is None:

        return (
            False,
            (
                f"{display_name} n'a pas été "
                "trouvé sur cette machine."
            )
        )

    # --------------------------------------------------------
    # LANCEMENT DETACHE
    # --------------------------------------------------------

    try:

        launch_detached(
            executable
        )

        return (
            True,
            f"{display_name} a été lancé."
        )

    except OSError as error:

        return (
            False,
            (
                f"Impossible de lancer "
                f"{display_name} : {error}"
            )
        )


# ============================================================
# TEST DIRECT
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 55)
    print("TEST WINDOWS_TOOLS")
    print("=" * 55)

    # --------------------------------------------------------
    # EDGE
    # --------------------------------------------------------

    print()
    print("Edge :")

    running, message = (
        is_application_running(
            "edge"
        )
    )

    print(message)
    print(
        "Fenêtre ouverte :",
        running
    )

    # --------------------------------------------------------
    # VS CODE
    # --------------------------------------------------------

    print()
    print("VS Code :")

    running, message = (
        is_application_running(
            "vscode"
        )
    )

    print(message)
    print(
        "Fenêtre ouverte :",
        running
    )

    print()