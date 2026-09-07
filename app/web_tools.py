import ipaddress
import json
import re
import subprocess

from pathlib import Path
from urllib.parse import urlparse

from windows_tools import (
    find_edge,
    get_application_permission,
)


# ============================================================
# CHEMINS
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]

SITES_FILE = (
    ROOT_DIR
    / "config"
    / "sites.json"
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
# LANCEMENT EDGE
# ============================================================

def launch_edge_with_urls(
    executable,
    urls
):
    """
    Lance toutes les URL avec une seule
    commande Edge.

    Si Edge est déjà ouvert, les URL sont
    normalement ajoutées comme onglets.
    """

    command = [
        str(executable)
    ]

    command.extend(
        urls
    )

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


# ============================================================
# OUVERTURE D'UN SITE
# ============================================================

def open_website(site_name):

    # Le navigateur reste soumis à la même frontière
    # de permissions que les autres applications.
    if not get_application_permission(
        "edge",
        "can_open"
    ):

        return (
            False,
            "Ouverture d'Edge interdite par permissions.json."
        )

    success, url, error = (
        resolve_site(
            site_name
        )
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
            (
                "Microsoft Edge n'a pas "
                "été trouvé."
            )
        )

    try:

        launch_edge_with_urls(
            edge,
            [url]
        )

        return (
            True,
            f"Site ouvert : {url}"
        )

    except OSError as error:

        return (
            False,
            (
                "Impossible d'ouvrir "
                f"le site : {error}"
            )
        )


# ============================================================
# OUVERTURE RAPIDE DE PLUSIEURS SITES
# ============================================================

def open_websites(site_names):
    """
    Version optimisée pour les routines.

    Les sites sont résolus localement
    sans requête DNS puis transmis à Edge
    en une seule commande.
    """

    if not get_application_permission(
        "edge",
        "can_open"
    ):

        return (
            False,
            [
                "REFUSE : ouverture d'Edge interdite "
                "par permissions.json."
            ]
        )

    if not site_names:

        return (
            False,
            ["Aucun site à ouvrir."]
        )

    # --------------------------------------------------------
    # SUPPRESSION DES DOUBLONS
    # --------------------------------------------------------

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
            normalized
        )

    urls = []

    seen_urls = set()

    results = []

    # --------------------------------------------------------
    # RESOLUTION LOCALE RAPIDE
    # --------------------------------------------------------

    for site_name in unique_sites:

        success, url, error = (
            resolve_site(
                site_name
            )
        )

        if not success:

            results.append(
                (
                    f"REFUSE : {site_name} "
                    f"-> {error}"
                )
            )

            continue

        if url in seen_urls:
            continue

        seen_urls.add(
            url
        )

        urls.append(
            url
        )

        results.append(
            (
                f"PRET : {site_name} "
                f"-> {url}"
            )
        )

    if not urls:

        return (
            False,
            results
        )

    # --------------------------------------------------------
    # EDGE
    # --------------------------------------------------------

    edge = find_edge()

    if edge is None:

        results.append(
            (
                "REFUSE : Microsoft Edge "
                "n'a pas été trouvé."
            )
        )

        return (
            False,
            results
        )

    # --------------------------------------------------------
    # UNE SEULE COMMANDE
    # --------------------------------------------------------

    try:

        launch_edge_with_urls(
            edge,
            urls
        )

        results.append(
            (
                f"OK : {len(urls)} site(s) "
                "envoyé(s) à Edge."
            )
        )

        return (
            True,
            results
        )

    except OSError as error:

        results.append(
            (
                "REFUSE : impossible "
                f"d'ouvrir Edge : {error}"
            )
        )

        return (
            False,
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