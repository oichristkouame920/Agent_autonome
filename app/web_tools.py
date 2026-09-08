import ctypes
import ipaddress
import json
import re
import subprocess
import time

from ctypes import wintypes

from pathlib import Path
from urllib.parse import urlparse

from windows_tools import (
    close_application_window,
    find_edge,
    get_application_permission,
    get_application_window_records,
    is_application_close_source_allowed,
)

from browser_bridge import close_site_via_bridge


# ============================================================
# CHEMINS
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]

SITES_FILE = (
    ROOT_DIR
    / "config"
    / "sites.json"
)

PERMISSIONS_FILE = (
    ROOT_DIR
    / "config"
    / "permissions.json"
)

WEB_WINDOW_STATE_FILE = (
    ROOT_DIR
    / "memory"
    / "web_windows.json"
)


# ============================================================
# ALIAS DE SAISIE
# ============================================================

INPUT_ALIASES = {
    # Microsoft
    "microsoft teams": "teams",
    "ms teams": "teams",
    "one drive": "onedrive",
    "microsoft one drive": "onedrive",
    "microsoft onedrive": "onedrive",
    "microsoft 365": "microsoft365",
    "office 365": "microsoft365",
    "microsoft office": "office",
    "microsoft outlook": "outlook",
    "microsoft word": "word",
    "microsoft excel": "excel",
    "microsoft powerpoint": "powerpoint",
    "power point": "powerpoint",
    "microsoft forms": "microsoftforms",
    "microsoft planner": "planner",
    "microsoft todo": "todo",
    "microsoft to do": "todo",

    # Google
    "google drive": "googledrive",
    "google docs": "docs",
    "google sheets": "sheets",
    "google slides": "slides",
    "google meet": "meet",
    "google calendar": "calendar",
    "google chat": "googlechat",
    "google forms": "googleforms",
    "google contacts": "contacts",
    "google keep": "keep",
    "google classroom": "classroom",
    "google photos": "photos",
    "google maps": "maps",
    "google translate": "translate",
}


# ============================================================
# CHARGEMENT DES SITES
# ============================================================

def load_sites():
    """
    Charge les alias personnalisés depuis sites.json.
    """

    if not SITES_FILE.exists():
        return {}

    try:

        with open(
            SITES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if not isinstance(data, dict):
                return {}

            return data

    except (
        OSError,
        json.JSONDecodeError
    ):
        return {}


# ============================================================
# POLITIQUE DE FERMETURE WEB
# ============================================================

def load_permissions():
    """
    Charge permissions.json sans jamais autoriser une fonction
    si le fichier est absent ou invalide.
    """

    if not PERMISSIONS_FILE.exists():
        return {}

    try:
        with open(
            PERMISSIONS_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

    except (
        OSError,
        json.JSONDecodeError,
    ):
        pass

    return {}


def get_web_close_policy():
    policy = load_permissions().get(
        "web_close_policy",
        {}
    )

    if not isinstance(policy, dict):
        return {}

    return policy


# ============================================================
# UI AUTOMATION EDGE - CONSTANTES
# ============================================================

UIA_CONTROL_TYPE_PROPERTY_ID = 30003
UIA_EDIT_CONTROL_TYPE_ID = 50004
UIA_TAB_ITEM_CONTROL_TYPE_ID = 50019
UIA_VALUE_PATTERN_ID = 10002
UIA_SELECTION_ITEM_PATTERN_ID = 10010
UIA_TEXT_PATTERN_ID = 10014
UIA_LEGACY_ACCESSIBLE_PATTERN_ID = 10018
UIA_TREE_SCOPE_DESCENDANTS = 0x4

VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_L = 0x4C
VK_W = 0x57
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
SW_RESTORE = 9


ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


def send_ctrl_w():
    """
    Ferme uniquement l'onglet Edge actif.

    Aucun taskkill, TerminateProcess, PowerShell ou CMD.
    """

    inputs = (INPUT * 4)(
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_CONTROL,
                wScan=0,
                dwFlags=0,
                time=0,
                dwExtraInfo=0,
            )
        ),
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_W,
                wScan=0,
                dwFlags=0,
                time=0,
                dwExtraInfo=0,
            )
        ),
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_W,
                wScan=0,
                dwFlags=KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=0,
            )
        ),
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_CONTROL,
                wScan=0,
                dwFlags=KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=0,
            )
        ),
    )

    try:
        user32 = ctypes.windll.user32

        user32.SendInput.argtypes = [
            wintypes.UINT,
            ctypes.POINTER(INPUT),
            ctypes.c_int,
        ]

        user32.SendInput.restype = wintypes.UINT

        sent = user32.SendInput(
            len(inputs),
            inputs,
            ctypes.sizeof(INPUT)
        )

        return sent == len(inputs)

    except Exception:
        return False


def normalize_host(host):
    if not isinstance(host, str):
        return ""

    host = (
        host
        .strip()
        .lower()
        .rstrip(".")
    )

    if host.startswith("www."):
        host = host[4:]

    return host


def extract_host_from_possible_url(value):
    """
    Convertit uniquement une valeur ressemblant réellement à une URL
    en nom d'hôte. Aucun texte de titre de fenêtre n'est accepté.
    """

    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    candidate = value

    if candidate.startswith("https://"):
        pass

    elif candidate.startswith("http://"):
        # AgentLocal n'ouvre pas HTTP et ne s'en sert pas pour la
        # fermeture ciblée par domaine.
        return None

    else:
        # Edge peut afficher l'adresse sans le schéma dans l'UIA.
        if " " in candidate:
            return None

        first_part = candidate.split("/", 1)[0]

        if not is_valid_domain(
            first_part.rstrip(".")
        ):
            return None

        candidate = (
            "https://"
            + candidate
        )

    try:
        parsed = urlparse(
            candidate
        )

    except ValueError:
        return None

    host = normalize_host(
        parsed.hostname or ""
    )

    if not host:
        return None

    if is_forbidden_host(
        host
    ):
        return None

    return host


def target_host_matches(
    candidate_host,
    target_host,
    allow_subdomains=False
):
    candidate_host = normalize_host(
        candidate_host
    )

    target_host = normalize_host(
        target_host
    )

    if not candidate_host or not target_host:
        return False

    if candidate_host == target_host:
        return True

    if allow_subdomains:
        return candidate_host.endswith(
            "." + target_host
        )

    return False


def create_uia_client():
    """
    Crée le client Microsoft UI Automation de façon paresseuse.

    comtypes n'est chargé que lorsqu'une fermeture d'onglet Edge
    manuel est réellement demandée.
    """

    try:
        import comtypes
        import comtypes.client

        comtypes.CoInitialize()

        uia_module = comtypes.client.GetModule(
            "UIAutomationCore.dll"
        )

        uia = comtypes.client.CreateObject(
            "{ff48dba4-60ef-4201-aa87-54103eef594e}",
            interface=uia_module.IUIAutomation
        )

        return (
            True,
            comtypes,
            uia_module,
            uia,
            None,
        )

    except Exception as error:
        return (
            False,
            None,
            None,
            None,
            (
                "Microsoft UI Automation n'a pas pu être initialisé. "
                "Vérifie que la dépendance 'comtypes' est installée. "
                f"Détail : {error}"
            ),
        )


def uia_find_descendants_by_control_type(
    uia,
    root_element,
    control_type
):
    try:
        condition = uia.CreatePropertyCondition(
            UIA_CONTROL_TYPE_PROPERTY_ID,
            int(control_type)
        )

        collection = root_element.FindAll(
            UIA_TREE_SCOPE_DESCENDANTS,
            condition
        )

        if collection is None:
            return []

        return [
            collection.GetElement(index)
            for index in range(
                int(collection.Length)
            )
        ]

    except Exception:
        return []


def get_uia_value_pattern_value(
    element,
    uia_module
):
    try:
        pattern = element.GetCurrentPattern(
            UIA_VALUE_PATTERN_ID
        )

        if not pattern:
            return None

        value_pattern = pattern.QueryInterface(
            uia_module.IUIAutomationValuePattern
        )

        value = value_pattern.CurrentValue

        if isinstance(value, str):
            return value.strip()

    except Exception:
        pass

    return None


def get_uia_text_pattern_value(
    element,
    uia_module
):
    """
    Fallback pour les builds Chromium/Edge qui n'exposent pas
    l'Omnibox via ValuePattern mais fournissent TextPattern.
    """

    try:
        interface = getattr(
            uia_module,
            "IUIAutomationTextPattern",
            None
        )

        if interface is None:
            return None

        pattern = element.GetCurrentPattern(
            UIA_TEXT_PATTERN_ID
        )

        if not pattern:
            return None

        text_pattern = pattern.QueryInterface(
            interface
        )

        document_range = text_pattern.DocumentRange

        if document_range is None:
            return None

        value = document_range.GetText(
            -1
        )

        if isinstance(value, str):
            return value.strip()

    except Exception:
        pass

    return None


def get_uia_legacy_accessible_value(
    element,
    uia_module
):
    """
    Dernier fallback UIA : certains contrôles Edge exposent la
    valeur de l'Omnibox via LegacyIAccessiblePattern.
    """

    try:
        interface = getattr(
            uia_module,
            "IUIAutomationLegacyIAccessiblePattern",
            None
        )

        if interface is None:
            return None

        pattern = element.GetCurrentPattern(
            UIA_LEGACY_ACCESSIBLE_PATTERN_ID
        )

        if not pattern:
            return None

        legacy_pattern = pattern.QueryInterface(
            interface
        )

        value = legacy_pattern.CurrentValue

        if isinstance(value, str):
            return value.strip()

    except Exception:
        pass

    return None


def get_uia_best_text_value(
    element,
    uia_module
):
    """
    Lit une valeur textuelle sans presse-papiers.

    Ordre :
    1. ValuePattern ;
    2. TextPattern ;
    3. LegacyIAccessiblePattern.
    """

    for reader in (
        get_uia_value_pattern_value,
        get_uia_text_pattern_value,
        get_uia_legacy_accessible_value,
    ):
        value = reader(
            element,
            uia_module
        )

        if value:
            return value

    return None


def get_uia_selection_item_pattern(
    element,
    uia_module
):
    try:
        pattern = element.GetCurrentPattern(
            UIA_SELECTION_ITEM_PATTERN_ID
        )

        if not pattern:
            return None

        return pattern.QueryInterface(
            uia_module.IUIAutomationSelectionItemPattern
        )

    except Exception:
        return None


def normalize_uia_label(value):
    if not isinstance(value, str):
        return ""

    return (
        value
        .strip()
        .lower()
        .replace("’", "'")
    )


def is_edge_address_bar_element(element):
    """
    Identifie l'Omnibox Edge sans dépendre uniquement de la langue.

    Chromium expose généralement la classe UIA OmniboxViewViews.
    Les noms anglais/français restent des fallbacks contrôlés.
    """

    try:
        class_name = normalize_uia_label(
            element.CurrentClassName
        )
    except Exception:
        class_name = ""

    if class_name == "omniboxviewviews":
        return True

    try:
        name = normalize_uia_label(
            element.CurrentName
        )
    except Exception:
        name = ""

    known_names = {
        "address and search bar",
        "search or enter web address",
        "barre d'adresse et de recherche",
        "barre d’adresse et de recherche",
        "rechercher ou entrer une adresse web",
    }

    return name in known_names


def get_edge_address_bar_hosts(
    uia,
    uia_module,
    edge_element
):
    """
    Retourne uniquement l'hôte exposé par l'Omnibox Edge.

    Les champs de recherche présents dans les pages web sont ignorés,
    même s'ils contiennent une chaîne ressemblant à un domaine.
    """

    hosts = []

    for edit in uia_find_descendants_by_control_type(
        uia,
        edge_element,
        UIA_EDIT_CONTROL_TYPE_ID
    ):
        if not is_edge_address_bar_element(
            edit
        ):
            continue

        value = get_uia_best_text_value(
            edit,
            uia_module
        )

        host = extract_host_from_possible_url(
            value
        )

        if (
            host
            and
            host not in hosts
        ):
            hosts.append(
                host
            )

    return hosts


def bring_edge_window_to_front(
    hwnd,
    edge_element=None
):
    """
    Met réellement une fenêtre Edge au premier plan.

    SetForegroundWindow peut être refusé par Windows lorsque
    AgentLocal n'est pas la fenêtre active. Le fallback
    AttachThreadInput reste une API Win32 standard disponible
    sous Windows 10 et Windows 11.
    """

    try:
        hwnd = int(
            hwnd
        )

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        user32.ShowWindow(
            hwnd,
            SW_RESTORE
        )

        user32.BringWindowToTop(
            hwnd
        )

        user32.SetForegroundWindow(
            hwnd
        )

        time.sleep(
            0.08
        )

        if int(
            user32.GetForegroundWindow() or 0
        ) != hwnd:
            current_thread = int(
                kernel32.GetCurrentThreadId()
            )

            foreground_hwnd = int(
                user32.GetForegroundWindow() or 0
            )

            foreground_thread = 0

            if foreground_hwnd:
                foreground_thread = int(
                    user32.GetWindowThreadProcessId(
                        foreground_hwnd,
                        None
                    )
                )

            target_thread = int(
                user32.GetWindowThreadProcessId(
                    hwnd,
                    None
                )
            )

            attached_foreground = False
            attached_target = False

            try:
                if (
                    foreground_thread
                    and
                    foreground_thread != current_thread
                ):
                    attached_foreground = bool(
                        user32.AttachThreadInput(
                            current_thread,
                            foreground_thread,
                            True
                        )
                    )

                if (
                    target_thread
                    and
                    target_thread != current_thread
                ):
                    attached_target = bool(
                        user32.AttachThreadInput(
                            current_thread,
                            target_thread,
                            True
                        )
                    )

                user32.ShowWindow(
                    hwnd,
                    SW_RESTORE
                )

                user32.BringWindowToTop(
                    hwnd
                )

                user32.SetForegroundWindow(
                    hwnd
                )

                try:
                    user32.SetFocus(
                        hwnd
                    )
                except Exception:
                    pass

            finally:
                if attached_target:
                    try:
                        user32.AttachThreadInput(
                            current_thread,
                            target_thread,
                            False
                        )
                    except Exception:
                        pass

                if attached_foreground:
                    try:
                        user32.AttachThreadInput(
                            current_thread,
                            foreground_thread,
                            False
                        )
                    except Exception:
                        pass

        if edge_element is not None:
            try:
                edge_element.SetFocus()
            except Exception:
                pass

        time.sleep(
            0.12
        )

        return int(
            user32.GetForegroundWindow() or 0
        ) == hwnd

    except Exception:
        return False


def send_ctrl_l():
    """
    Place le focus dans l'Omnibox Edge.

    Utilisé uniquement pour lire l'URL de l'onglet actif via UIA.
    Aucun contenu n'est copié dans le presse-papiers.
    """

    inputs = (INPUT * 4)(
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_CONTROL,
                wScan=0,
                dwFlags=0,
                time=0,
                dwExtraInfo=0,
            )
        ),
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_L,
                wScan=0,
                dwFlags=0,
                time=0,
                dwExtraInfo=0,
            )
        ),
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_L,
                wScan=0,
                dwFlags=KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=0,
            )
        ),
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_CONTROL,
                wScan=0,
                dwFlags=KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=0,
            )
        ),
    )

    try:
        user32 = ctypes.windll.user32

        user32.SendInput.argtypes = [
            wintypes.UINT,
            ctypes.POINTER(INPUT),
            ctypes.c_int,
        ]
        user32.SendInput.restype = wintypes.UINT

        sent = user32.SendInput(
            len(inputs),
            inputs,
            ctypes.sizeof(INPUT)
        )

        return sent == len(inputs)

    except Exception:
        return False


def send_escape():
    """Retire le focus de l'Omnibox sans modifier l'adresse."""

    inputs = (INPUT * 2)(
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_ESCAPE,
                wScan=0,
                dwFlags=0,
                time=0,
                dwExtraInfo=0,
            )
        ),
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_ESCAPE,
                wScan=0,
                dwFlags=KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=0,
            )
        ),
    )

    try:
        user32 = ctypes.windll.user32
        sent = user32.SendInput(
            len(inputs),
            inputs,
            ctypes.sizeof(INPUT)
        )
        return sent == len(inputs)
    except Exception:
        return False


def send_ctrl_tab():
    """
    Passe à l'onglet Edge suivant dans la fenêtre active.
    """

    inputs = (INPUT * 4)(
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_CONTROL,
                wScan=0,
                dwFlags=0,
                time=0,
                dwExtraInfo=0,
            )
        ),
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_TAB,
                wScan=0,
                dwFlags=0,
                time=0,
                dwExtraInfo=0,
            )
        ),
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_TAB,
                wScan=0,
                dwFlags=KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=0,
            )
        ),
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_CONTROL,
                wScan=0,
                dwFlags=KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=0,
            )
        ),
    )

    try:
        user32 = ctypes.windll.user32
        sent = user32.SendInput(
            len(inputs),
            inputs,
            ctypes.sizeof(INPUT)
        )
        return sent == len(inputs)
    except Exception:
        return False


def get_active_edge_host_via_focused_omnibox(
    uia,
    uia_module,
    hwnd,
    edge_element=None
):
    """
    Lit l'adresse réelle de l'onglet Edge actif.

    Cette méthode est le fallback robuste pour les versions d'Edge qui
    n'exposent pas correctement l'Omnibox lors d'une simple recherche
    dans l'arbre UI Automation.

    Étapes :
    - met la fenêtre Edge au premier plan ;
    - Ctrl+L donne explicitement le focus à l'Omnibox ;
    - UI Automation lit la valeur du contrôle qui a réellement le focus ;
    - Échap rend le focus à la page ;
    - aucun presse-papiers n'est utilisé.
    """

    if not bring_edge_window_to_front(
        hwnd,
        edge_element=edge_element
    ):
        return None

    if not send_ctrl_l():
        return None

    time.sleep(0.15)

    value = None

    try:
        focused = uia.GetFocusedElement()

        if focused is not None:
            value = get_uia_best_text_value(
                focused,
                uia_module
            )

            # Certains builds Chromium exposent la valeur dans le nom
            # du contrôle lorsque les patterns de texte ne sont pas disponibles.
            if not value:
                try:
                    candidate_name = focused.CurrentName
                except Exception:
                    candidate_name = None

                if extract_host_from_possible_url(
                    candidate_name
                ):
                    value = candidate_name

    except Exception:
        value = None

    finally:
        send_escape()
        time.sleep(0.05)

    return extract_host_from_possible_url(
        value
    )


def get_edge_tab_count(
    uia,
    edge_element,
    maximum_tabs
):
    """
    Détermine un nombre borné d'onglets à inspecter.

    Edge expose normalement ses onglets comme TabItem. Si ce n'est pas
    le cas, AgentLocal effectue un balayage strictement borné à
    maximum_tabs. Chaque fermeture reste conditionnée à une URL vérifiée.
    """

    tab_items = uia_find_descendants_by_control_type(
        uia,
        edge_element,
        UIA_TAB_ITEM_CONTROL_TYPE_ID
    )

    if not tab_items:
        return max(
            1,
            int(maximum_tabs)
        )

    return max(
        1,
        min(
            len(tab_items),
            int(maximum_tabs)
        )
    )


def close_manual_edge_tabs_for_url(
    target_url,
    maximum_tabs=10,
    allow_subdomains=False
):
    """
    Recherche et ferme des onglets Edge, y compris ceux ouverts
    manuellement.

    Deux méthodes sûres sont utilisées :

    1. UI Automation directe : sélection d'un TabItem puis lecture de
       l'Omnibox si Edge expose correctement ses contrôles.

    2. Fallback Omnibox focalisée : AgentLocal parcourt un nombre borné
       d'onglets avec Ctrl+Tab, donne explicitement le focus à la barre
       d'adresse avec Ctrl+L, puis lit la valeur réelle de l'Omnibox via
       UI Automation. Aucun titre de fenêtre n'est utilisé pour décider
       d'une fermeture et le presse-papiers n'est jamais modifié.

    La fermeture est effectuée uniquement après vérification du domaine
    réel de l'onglet actif.
    """

    try:
        maximum_tabs = int(
            maximum_tabs
        )
    except (
        TypeError,
        ValueError,
    ):
        maximum_tabs = 10

    maximum_tabs = max(
        1,
        min(
            maximum_tabs,
            20
        )
    )

    try:
        target_host = normalize_host(
            urlparse(
                target_url
            ).hostname or ""
        )
    except ValueError:
        return (
            0,
            "URL cible invalide."
        )

    if not target_host:
        return (
            0,
            "Hôte cible invalide."
        )

    success, comtypes_module, uia_module, uia, error = (
        create_uia_client()
    )

    if not success:
        return (
            0,
            error
        )

    closed_count = 0
    inspected_any_verified_url = False

    try:
        while closed_count < maximum_tabs:
            found_and_closed = False

            # Relecture après chaque fermeture : la structure Edge et
            # les handles peuvent avoir changé.
            edge_windows = get_application_window_records(
                "edge"
            )

            if not edge_windows:
                break

            for record in edge_windows:
                hwnd = record.get(
                    "hwnd"
                )

                if not hwnd:
                    continue

                try:
                    edge_element = uia.ElementFromHandle(
                        int(hwnd)
                    )
                except Exception:
                    continue

                if edge_element is None:
                    continue

                bring_edge_window_to_front(
                    hwnd,
                    edge_element=edge_element
                )

                # ====================================================
                # METHODE 1 : UIA DIRECTE
                # ====================================================

                tab_items = uia_find_descendants_by_control_type(
                    uia,
                    edge_element,
                    UIA_TAB_ITEM_CONTROL_TYPE_ID
                )

                for tab_item in tab_items:
                    selection = get_uia_selection_item_pattern(
                        tab_item,
                        uia_module
                    )

                    if selection is None:
                        continue

                    try:
                        selection.Select()
                    except Exception:
                        continue

                    time.sleep(0.12)

                    hosts = get_edge_address_bar_hosts(
                        uia,
                        uia_module,
                        edge_element
                    )

                    if hosts:
                        inspected_any_verified_url = True

                    if not any(
                        target_host_matches(
                            host,
                            target_host,
                            allow_subdomains=allow_subdomains
                        )
                        for host in hosts
                    ):
                        continue

                    # Double vérification juste avant la fermeture.
                    verified_hosts = get_edge_address_bar_hosts(
                        uia,
                        uia_module,
                        edge_element
                    )

                    if not any(
                        target_host_matches(
                            host,
                            target_host,
                            allow_subdomains=allow_subdomains
                        )
                        for host in verified_hosts
                    ):
                        continue

                    bring_edge_window_to_front(
                        hwnd,
                        edge_element=edge_element
                    )

                    if send_ctrl_w():
                        closed_count += 1
                        found_and_closed = True
                        time.sleep(0.30)
                        break

                if found_and_closed:
                    break

                # ====================================================
                # METHODE 2 : FALLBACK CTRL+L + UIA
                # ====================================================

                tab_count = get_edge_tab_count(
                    uia,
                    edge_element,
                    maximum_tabs
                )

                # Si Edge expose le nombre d'onglets, un cycle complet
                # revient naturellement à l'onglet de départ lorsqu'aucun
                # match n'est trouvé.
                for tab_index in range(tab_count):
                    host = get_active_edge_host_via_focused_omnibox(
                        uia,
                        uia_module,
                        hwnd,
                        edge_element=edge_element
                    )

                    if host:
                        inspected_any_verified_url = True

                    if (
                        host
                        and
                        target_host_matches(
                            host,
                            target_host,
                            allow_subdomains=allow_subdomains
                        )
                    ):
                        # Double vérification immédiatement avant Ctrl+W.
                        verified_host = (
                            get_active_edge_host_via_focused_omnibox(
                                uia,
                                uia_module,
                                hwnd,
                                edge_element=edge_element
                            )
                        )

                        if (
                            verified_host
                            and
                            target_host_matches(
                                verified_host,
                                target_host,
                                allow_subdomains=allow_subdomains
                            )
                        ):
                            bring_edge_window_to_front(
                                hwnd,
                                edge_element=edge_element
                            )

                            if send_ctrl_w():
                                closed_count += 1
                                found_and_closed = True
                                time.sleep(0.30)
                                break

                    # Dernier onglet du cycle : inutile d'envoyer Ctrl+Tab.
                    if tab_index + 1 < tab_count:
                        bring_edge_window_to_front(
                            hwnd,
                            edge_element=edge_element
                        )

                        if not send_ctrl_tab():
                            break

                        time.sleep(0.14)

                if found_and_closed:
                    break

            if not found_and_closed:
                break

    finally:
        try:
            comtypes_module.CoUninitialize()
        except Exception:
            pass

    if closed_count:
        return (
            closed_count,
            None
        )

    if not inspected_any_verified_url:
        return (
            0,
            (
                "Edge a été trouvé, mais aucune URL d'onglet n'a pu "
                "être lue de façon vérifiable, même après focalisation "
                "forcée de la barre d'adresse. Vérifie qu'Edge et "
                "AgentLocal utilisent le même niveau de privilège Windows."
            )
        )

    return (
        0,
        None
    )


# ============================================================
# NORMALISATION DE LA SAISIE
# ============================================================

def normalize_site_input(value):
    """
    Exemples acceptés :

    github
    ouvre github
    ouvrir github
    va sur github
    ouvre le site github
    ouvre microsoft teams
    ouvre google drive
    wikipedia.org
    """

    if not isinstance(value, str):
        return ""

    value = (
        value
        .lower()
        .strip()
    )

    prefixes = [
        "ouvre le site ",
        "ouvrir le site ",
        "va sur le site ",
        "aller sur le site ",
        "ouvre ",
        "ouvrir ",
        "va sur ",
        "aller sur ",
        "lance ",
        "lancer ",
    ]

    for prefix in prefixes:

        if value.startswith(prefix):

            value = value[
                len(prefix):
            ].strip()

            break

    value = value.strip(
        " .,!?:;"
    )

    return INPUT_ALIASES.get(
        value,
        value
    )


# ============================================================
# ALIAS PERSONNALISE
# ============================================================

def get_custom_alias(site_name):
    """
    Cherche le site dans sites.json.
    """

    config = load_sites()

    websites = config.get(
        "websites",
        {}
    )

    site = websites.get(
        site_name
    )

    if not isinstance(
        site,
        dict
    ):
        return None

    if not site.get(
        "enabled",
        False
    ):
        return None

    url = site.get(
        "url"
    )

    if not isinstance(
        url,
        str
    ):
        return None

    return url.strip()


# ============================================================
# VALIDATION DES DOMAINES
# ============================================================

DOMAIN_PATTERN = re.compile(
    r"^(?:[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9-]{0,61}"
    r"[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,63}$"
)

SIMPLE_NAME_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9-]{0,62}$"
)


def is_valid_domain(domain):

    domain = (
        domain
        .lower()
        .strip()
        .rstrip(".")
    )

    return bool(
        DOMAIN_PATTERN.fullmatch(
            domain
        )
    )


# ============================================================
# IP INTERDITES
# ============================================================

def is_forbidden_ip(ip):
    """
    Empêche explicitement l'accès direct
    aux IP locales et privées.
    """

    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


# ============================================================
# VALIDATION RAPIDE DE L'HOTE
# ============================================================

def is_forbidden_host(host):
    """
    Validation locale très rapide.

    Important :
    aucune résolution DNS n'est effectuée ici.

    Cela évite le délai présent dans
    l'ancienne version.
    """

    if not host:
        return True

    host = (
        host
        .lower()
        .strip()
        .rstrip(".")
    )

    # --------------------------------------------------------
    # NOMS LOCAUX INTERDITS
    # --------------------------------------------------------

    if host in {
        "localhost",
        "localhost.localdomain",
    }:
        return True

    if host.endswith(
        ".localhost"
    ):
        return True

    if host.endswith(
        ".local"
    ):
        return True

    if host.endswith(
        ".lan"
    ):
        return True

    # --------------------------------------------------------
    # IP FOURNIE DIRECTEMENT
    # --------------------------------------------------------

    try:

        ip = ipaddress.ip_address(
            host
        )

        return is_forbidden_ip(
            ip
        )

    except ValueError:
        pass

    # Domaine public classique.
    return False


# ============================================================
# VALIDATION URL
# ============================================================

def validate_url(url):
    """
    Règles de sécurité :

    HTTPS uniquement
    pas de credentials
    pas de port arbitraire
    pas de localhost
    pas d'IP locale explicite
    """

    if not isinstance(
        url,
        str
    ):
        return False

    try:

        parsed = urlparse(
            url
        )

    except ValueError:
        return False

    if parsed.scheme.lower() != "https":
        return False

    host = parsed.hostname

    if not host:
        return False

    if (
        parsed.username is not None
        or parsed.password is not None
    ):
        return False

    try:

        port = parsed.port

    except ValueError:
        return False

    if port not in {
        None,
        443
    }:
        return False

    if is_forbidden_host(
        host
    ):
        return False

    return True


# ============================================================
# RESOLUTION D'UN SITE
# ============================================================

def resolve_site(user_input):
    """
    Exemples :

    udmci
        -> sites.json

    teams
        -> sites.json

    github
        -> https://github.com/

    whatsapp
        -> https://whatsapp.com/

    wikipedia.org
        -> https://wikipedia.org/
    """

    value = normalize_site_input(
        user_input
    )

    if not value:

        return (
            False,
            None,
            "Nom du site vide."
        )

    # --------------------------------------------------------
    # ALIAS PERSONNALISE
    # --------------------------------------------------------

    alias = get_custom_alias(
        value
    )

    if alias:

        if validate_url(
            alias
        ):

            return (
                True,
                alias,
                None
            )

        return (
            False,
            None,
            (
                "L'URL configurée pour "
                f"{value} est invalide."
            )
        )

    # --------------------------------------------------------
    # URL HTTPS COMPLETE
    # --------------------------------------------------------

    if value.startswith(
        "https://"
    ):

        if validate_url(
            value
        ):

            return (
                True,
                value,
                None
            )

        return (
            False,
            None,
            "URL HTTPS interdite ou invalide."
        )

    # --------------------------------------------------------
    # ON N'ACCEPTE PAS HTTP
    # --------------------------------------------------------

    if value.startswith(
        "http://"
    ):

        return (
            False,
            None,
            "HTTP non sécurisé est interdit."
        )

    # --------------------------------------------------------
    # WWW
    # --------------------------------------------------------

    if value.startswith(
        "www."
    ):

        value = value[4:]

    # --------------------------------------------------------
    # DOMAINE COMPLET
    # --------------------------------------------------------

    if is_valid_domain(
        value
    ):

        url = (
            f"https://{value}/"
        )

        if validate_url(
            url
        ):

            return (
                True,
                url,
                None
            )

    # --------------------------------------------------------
    # NOM SIMPLE
    #
    # github -> github.com
    # whatsapp -> whatsapp.com
    # youtube -> youtube.com
    # --------------------------------------------------------

    if SIMPLE_NAME_PATTERN.fullmatch(
        value
    ):

        url = (
            f"https://{value}.com/"
        )

        if validate_url(
            url
        ):

            return (
                True,
                url,
                None
            )

    return (
        False,
        None,
        (
            "Impossible de déterminer "
            f"le site : {user_input}"
        )
    )


# ============================================================
# OPTIONS WINDOWS
# ============================================================

def get_detached_creation_flags():

    flags = 0

    if hasattr(
        subprocess,
        "CREATE_NEW_PROCESS_GROUP"
    ):

        flags |= (
            subprocess.CREATE_NEW_PROCESS_GROUP
        )

    if hasattr(
        subprocess,
        "DETACHED_PROCESS"
    ):

        flags |= (
            subprocess.DETACHED_PROCESS
        )

    return flags


# ============================================================
# ETAT LOCAL DES FENETRES WEB
# ============================================================

def load_web_window_state():
    try:
        if not WEB_WINDOW_STATE_FILE.exists():
            return {
                "schema_version": 1,
                "windows": [],
            }

        with open(
            WEB_WINDOW_STATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(
                file
            )

        if not isinstance(
            data,
            dict
        ):
            return {
                "schema_version": 1,
                "windows": [],
            }

        windows = data.get(
            "windows",
            []
        )

        if not isinstance(
            windows,
            list
        ):
            windows = []

        return {
            "schema_version": 1,
            "windows": windows,
        }

    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {
            "schema_version": 1,
            "windows": [],
        }


def save_web_window_state(
    state
):
    try:
        WEB_WINDOW_STATE_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        temporary = WEB_WINDOW_STATE_FILE.with_suffix(
            ".tmp"
        )

        with open(
            temporary,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                state,
                file,
                ensure_ascii=False,
                indent=2
            )

        temporary.replace(
            WEB_WINDOW_STATE_FILE
        )

        return True

    except OSError:
        return False


def remember_web_windows(
    url,
    records
):
    if not records:
        return False

    state = load_web_window_state()

    windows = state.get(
        "windows",
        []
    )

    # Évite les doublons exacts.
    existing = {
        (
            item.get(
                "url"
            ),
            item.get(
                "hwnd"
            ),
            item.get(
                "window_pid"
            ),
            item.get(
                "window_process_create_time"
            ),
        )
        for item in windows
        if isinstance(
            item,
            dict
        )
    }

    for record in records:
        key = (
            url,
            record.get(
                "hwnd"
            ),
            record.get(
                "window_pid"
            ),
            record.get(
                "window_process_create_time"
            ),
        )

        if key in existing:
            continue

        windows.append(
            {
                "url": url,
                "hwnd": record.get(
                    "hwnd"
                ),
                "window_pid": record.get(
                    "window_pid"
                ),
                "window_process_create_time": record.get(
                    "window_process_create_time"
                ),
                "opened_at": time.time(),
            }
        )

        existing.add(
            key
        )

    state[
        "windows"
    ] = windows

    return save_web_window_state(
        state
    )


# ============================================================
# LANCEMENT EDGE
# ============================================================

def launch_edge_new_window(
    executable,
    url
):
    """
    Chaque site ouvert par AgentLocal reçoit sa propre
    fenêtre Edge. Cela permet une fermeture ciblée ultérieure
    sans toucher aux autres fenêtres Edge de l'utilisateur.
    """

    command = [
        str(
            executable
        ),
        "--new-window",
        url,
    ]

    subprocess.Popen(
        command,
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=(
            get_detached_creation_flags()
        )
    )


def wait_for_new_edge_windows(
    previous_handles,
    timeout_seconds=5.0
):
    previous_handles = set(
        int(value)
        for value in previous_handles
    )

    deadline = (
        time.time()
        +
        float(
            timeout_seconds
        )
    )

    detected = []

    while time.time() < deadline:
        current = get_application_window_records(
            "edge"
        )

        detected = [
            item
            for item in current
            if item[
                "hwnd"
            ] not in previous_handles
        ]

        if detected:
            # Petit délai pour laisser Edge stabiliser la fenêtre.
            time.sleep(
                0.20
            )

            latest = get_application_window_records(
                "edge"
            )

            detected = [
                item
                for item in latest
                if item[
                    "hwnd"
                ] not in previous_handles
            ]

            if detected:
                return detected

        time.sleep(
            0.10
        )

    return detected


# ============================================================
# OUVERTURE D'UN SITE
# ============================================================

def open_website(
    site_name,
    source="unspecified",
    explicit_user_command=False
):
    # Edge reste soumis à sa permission d'ouverture.
    if not get_application_permission(
        "edge",
        "can_open"
    ):
        return (
            False,
            "Ouverture d'Edge interdite par permissions.json."
        )

    success, url, error = resolve_site(
        site_name
    )

    if not success:
        return (
            False,
            error
        )

    edge = find_edge()

    if edge is None:
        return (
            False,
            "Microsoft Edge n'a pas été trouvé."
        )

    before_records = get_application_window_records(
        "edge"
    )

    before_handles = {
        item[
            "hwnd"
        ]
        for item in before_records
    }

    try:
        launch_edge_new_window(
            edge,
            url
        )

    except OSError as error:
        return (
            False,
            (
                "Impossible d'ouvrir le site : "
                f"{error}"
            )
        )

    new_records = wait_for_new_edge_windows(
        before_handles
    )

    if new_records:
        remember_web_windows(
            url,
            new_records
        )

        return (
            True,
            (
                f"Site ouvert dans une fenêtre Edge suivie : {url}"
            )
        )

    # Le site a été transmis à Edge, mais si Windows/Edge n'a pas
    # permis d'identifier une nouvelle fenêtre, AgentLocal refuse
    # plus tard de fermer une fenêtre au hasard.
    return (
        True,
        (
            f"Site ouvert : {url}. "
            "La fenêtre n'a pas pu être enregistrée pour une "
            "fermeture ciblée."
        )
    )


# ============================================================
# FERMETURE D'UN SITE
# ============================================================

def close_website(
    site_name,
    source="manual",
    explicit_user_command=False
):
    """
    Ferme le site demandé dans Edge de façon ciblée.

    Priorité :
    1. pont navigateur local AgentLocal (URL réelle fournie par Edge) ;
    2. repli sur une fenêtre explicitement suivie par AgentLocal.

    Aucun onglet manuel n'est fermé sur la base de son titre.
    La méthode UI Automation historique n'est plus utilisée pour
    les onglets manuels.
    """

    if not get_application_permission(
        "edge",
        "can_close"
    ):
        return (
            False,
            "Fermeture d'Edge interdite par permissions.json."
        )

    if not is_application_close_source_allowed(
        "edge",
        source=source,
        explicit_user_command=explicit_user_command
    ):
        return (
            False,
            (
                "La fermeture d'un site exige une commande "
                "utilisateur explicite."
            )
        )

    policy = get_web_close_policy()

    if not policy.get(
        "enabled",
        False
    ):
        return (
            False,
            "La politique de fermeture des sites est désactivée."
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
            "La fermeture d'un site exige une commande explicite."
        )

    if source == "routine" and not policy.get(
        "allow_from_routine",
        False
    ):
        return (
            False,
            "La fermeture de sites depuis une routine est interdite."
        )

    if source == "habit" and not policy.get(
        "allow_from_habit",
        False
    ):
        return (
            False,
            "La fermeture de sites depuis une habitude est interdite."
        )

    success, url, error = resolve_site(
        site_name
    )

    if not success:
        return (
            False,
            error
        )

    tracked_closed_count = 0
    manual_closed_count = 0
    manual_error = None

    # ========================================================
    # 1. PONT NAVIGATEUR LOCAL
    # ========================================================

    if (
        policy.get(
            "allow_manual_edge_tabs",
            False
        )
        and
        policy.get(
            "manual_edge_strategy",
            "native_extension_bridge"
        ) == "native_extension_bridge"
    ):
        bridge_success, bridge_count, bridge_message = (
            close_site_via_bridge(
                url,
                close_all=policy.get(
                    "close_all_matching_tabs",
                    True
                ),
                maximum_tabs=policy.get(
                    "maximum_manual_tabs_per_command",
                    10
                ),
                allow_subdomains=policy.get(
                    "allow_subdomains",
                    False
                )
            )
        )

        if bridge_success:
            manual_closed_count = bridge_count

            # Le pont a fermé les onglets à partir de leurs URL réelles.
            # Les anciens handles suivis pour cette URL deviennent alors
            # potentiellement obsolètes et sont retirés de l'état local.
            state = load_web_window_state()
            windows = state.get(
                "windows",
                []
            )

            state[
                "windows"
            ] = [
                item
                for item in windows
                if not (
                    isinstance(
                        item,
                        dict
                    )
                    and
                    item.get(
                        "url"
                    ) == url
                )
            ]

            save_web_window_state(
                state
            )

        else:
            manual_error = bridge_message

    # ========================================================
    # 2. REPLI : FENETRES SUIVIES PAR AGENTLOCAL
    # ========================================================

    if manual_closed_count == 0 and policy.get(
        "allow_tracked_agent_windows",
        True
    ):
        state = load_web_window_state()

        windows = state.get(
            "windows",
            []
        )

        matching = [
            item
            for item in windows
            if (
                isinstance(
                    item,
                    dict
                )
                and
                item.get(
                    "url"
                ) == url
            )
        ]

        for item in matching:
            close_success, _ = close_application_window(
                item.get(
                    "hwnd"
                ),
                "edge",
                source=source,
                explicit_user_command=explicit_user_command,
                expected_pid=item.get(
                    "window_pid"
                ),
                expected_process_create_time=item.get(
                    "window_process_create_time"
                )
            )

            if close_success:
                tracked_closed_count += 1

        matching_ids = {
            id(item)
            for item in matching
        }

        state[
            "windows"
        ] = [
            item
            for item in windows
            if id(item) not in matching_ids
        ]

        save_web_window_state(
            state
        )

    total_closed = (
        tracked_closed_count
        +
        manual_closed_count
    )

    if total_closed == 0:
        if manual_error:
            return (
                False,
                manual_error
            )

        return (
            False,
            (
                "Aucun onglet ou fenêtre Edge correspondant "
                f"à {url} n'a pu être fermé."
            )
        )

    details = []

    if tracked_closed_count:
        details.append(
            f"{tracked_closed_count} fenêtre(s) suivie(s)"
        )

    if manual_closed_count:
        details.append(
            f"{manual_closed_count} onglet(s) manuel(s)"
        )

    return (
        True,
        (
            "Fermeture demandée pour "
            f"{url} : "
            + ", ".join(details)
            + "."
        )
    )


# ============================================================
# OUVERTURE DE PLUSIEURS SITES
# ============================================================

def open_websites(
    site_names
):
    """
    Ouvre chaque site dans sa propre fenêtre Edge afin que chaque
    fenêtre puisse être fermée individuellement plus tard.
    """

    if not get_application_permission(
        "edge",
        "can_open"
    ):
        return (
            False,
            [
                "REFUSE : ouverture d'Edge interdite par "
                "permissions.json."
            ]
        )

    if not site_names:
        return (
            False,
            [
                "Aucun site à ouvrir."
            ]
        )

    unique_sites = []
    seen_sites = set()

    for site_name in site_names:
        normalized = normalize_site_input(
            site_name
        )

        if not normalized:
            continue

        if normalized in seen_sites:
            continue

        seen_sites.add(
            normalized
        )

        unique_sites.append(
            site_name
        )

    results = []
    success_count = 0

    for site_name in unique_sites:
        success, message = open_website(
            site_name,
            source="routine",
            explicit_user_command=False
        )

        if success:
            success_count += 1
            results.append(
                f"OK : {message}"
            )
        else:
            results.append(
                f"REFUSE : {message}"
            )

    return (
        success_count > 0,
        results
    )


# ============================================================
# TEST DIRECT
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 55)
    print("TEST WEB_TOOLS RAPIDE")
    print("=" * 55)
    print()

    site = input(
        "Site à ouvrir : "
    ).strip()

    success, message = (
        open_website(
            site
        )
    )

    print()
    print(
        message
    )

    print(
        "Résultat :",
        success
    )