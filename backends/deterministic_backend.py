import json
import re
import unicodedata
from pathlib import Path


# ============================================================
# VERSION
# ============================================================

SCHEMA_VERSION = 1
NATURAL_LANGUAGE_PATCH_VERSION = "2026-09-11-actions-v1"


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
    "microsodt edge": "edge",
    "microsft edge": "edge",
    "microsoft edg": "edge",

    # VS Code
    "vscode": "vscode",
    "vs code": "vscode",
    "visual studio code": "vscode",
    "vscod": "vscode",
    "vs cod": "vscode",
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
    "teems": "teams",
    "team": "teams",

    # Microsoft Office
    "word": "word",
    "microsoft word": "word",

    "excel": "excel",
    "microsoft excel": "excel",
    "exel": "excel",

    "powerpoint": "powerpoint",
    "power point": "powerpoint",
    "microsoft powerpoint": "powerpoint",

    "outlook": "outlook",
    "microsoft outlook": "outlook",
    "outlok": "outlook",

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
    "mes document": "documents",
    "mon document": "documents",
    "docuement": "documents",
    "docuements": "documents",

    # Téléchargements
    "telechargement": "downloads",
    "telechargements": "downloads",
    "mes telechargements": "downloads",
    "mes telechargement": "downloads",
    "mon telechargement": "downloads",
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
MASS_MODIFY_TERMS = set(MASS_DELETE_TERMS)


VAGUE_FILESYSTEM_REFERENCES = {
    "fichier",
    "le fichier",
    "la fichier",
    "un fichier",
    "ce fichier",
    "mon fichier",
    "les fichiers",
    "document",
    "le document",
    "un document",
    "ce document",
    "mon document",
    "dossier",
    "le dossier",
    "un dossier",
    "ce dossier",
    "mon dossier",
    "quelque chose",
    "un truc",
    "le truc",
    "ce truc",
    "ca",
    "cela",
    "ceci",
    "tout",
    "tous",
    "toutes",
    "tout ca",
    "tout cela",
    "tous les fichiers",
    "tous mes fichiers",
    "tous les documents",
    "tous mes documents",
    "toutes les photos",
    "toutes les images",
    "toutes les videos",
    "toutes les musiques",
    "celui ci",
    "celui la",
    "le dernier fichier",
    "le dernier document",
    "le dernier dossier",
    "lui",
}


def is_vague_filesystem_reference(value):
    normalized = normalize_text(value)
    normalized = normalized.replace("-", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(
        r"\s+(?:la|hein|meme|ou\s+bien)\s*$",
        "",
        normalized,
        count=1,
    ).strip()
    return normalized in VAGUE_FILESYSTEM_REFERENCES


WRITABLE_TEXT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".tsv", ".json",
    ".xml", ".yaml", ".yml", ".log", ".ini",
    ".cfg", ".conf", ".toml", ".ics", ".vcf",
    ".html", ".htm", ".rtf", ".eml",
}

APPEND_SAFE_TEXT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".tsv", ".log",
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
# CIBLES D'EXECUTION EXPLICITEMENT INTERDITES
# ============================================================

BLOCKED_EXECUTION_TARGET_NAMES = {
    "powershell",
    "power shell",
    "cmd",
    "invite de commandes",
    "invite de commande",
    "terminal",
    "windows terminal",
    "bash",
    "wsl",
}


# ============================================================
# SITES
# ============================================================

WEBSITE_ALIASES = {
    "teams": "teams",
    "microsoft teams": "teams",
    "ms teams": "teams",
    "teems": "teams",

    "outlook": "outlook",
    "microsoft outlook": "outlook",
    "outlok": "outlook",

    "outlook perso": "outlook-perso",
    "outlook personnel": "outlook-perso",

    "onedrive": "onedrive",
    "one drive": "onedrive",
    "ondrive": "onedrive",

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

    "google": "google.com",
    "google search": "google.com",
    "recherche google": "google.com",

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
    "gitub": "github",
    "githb": "github",
    "gihub": "github",

    "chatgpt": "chatgpt",
    "chatgtp": "chatgpt",
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
# LANGAGE NATUREL CONTROLE
# ============================================================

def _has_literal_content_payload(text):
    """
    Detecte les commandes dont une partie de la phrase est du contenu
    utilisateur a conserver exactement. Dans ce cas, les transformations
    de fin de phrase sont volontairement desactivees.
    """

    normalized = normalize_text(text)
    markers = (
        " avec le contenu ",
        " contenant ",
        " remplace le contenu ",
        " remplacer le contenu ",
        " ajoute une ligne ",
        " ajouter une ligne ",
        " ajoute au fichier ",
        " ajouter au fichier ",
        " ajoute a fichier ",
        " ajouter a fichier ",
        " copie ce texte",
        " copier ce texte",
        " copie dans le presse papiers",
        " copier dans le presse papiers",
        " mets dans le presse papiers",
        " met dans le presse papiers",
    )
    padded = f" {normalized} "
    return any(marker in padded for marker in markers)


def _strip_natural_leading_wrappers(text):
    """Retire uniquement des amorces conversationnelles sans toucher au sens."""

    value = str(text or "").strip().replace("’", "'")
    patterns = (
        r"^(?:bonjour|salut|coucou|hello)\s*[,;:!-]?\s+",
        r"^(?:s'il\s+te\s+pla[iî]t|s'il\s+vous\s+pla[iî]t|stp|svp)\s*[,;:!-]?\s+",
        r"^(?:est[- ]ce\s+que\s+tu\s+(?:peux|pourrais)|est[- ]ce\s+que\s+vous\s+(?:pouvez|pourriez)|est\s+ce\s+que\s+tu\s+(?:peux|pourrais)|est\s+ce\s+que\s+vous\s+(?:pouvez|pourriez))\s+",
        r"^(?:tu\s+(?:peux|pourrais)(?:\s+juste)?|vous\s+(?:pouvez|pourriez)(?:\s+juste)?|peux[- ]tu|pourrais[- ]tu|pouvez[- ]vous|pourriez[- ]vous|si\s+tu\s+peux|tu\s+veux\s+bien|vous\s+voulez\s+bien|est[- ]ce\s+possible\s+de|est\s+ce\s+possible\s+de|possible\s+de)\s+",
        r"^(?:j'aimerais|j'aimerai|je\s+voudrais|je\s+veux|j'aurais\s+besoin|j'ai\s+besoin)\s+(?:que\s+(?:tu|vous)\s+)?",
        r"^(?:merci\s+de|veuillez|je\s+te\s+demande\s+de|je\s+vous\s+demande\s+de)\s+",
        r"^(?:ok|d'accord|bon|alors|donc|eh)\s*[,;:!-]?\s+",
        r"^(?:il\s+)?faut(?:\s+que\s+(?:tu|vous))?\s+",
    )

    for _ in range(4):
        previous = value
        for pattern in patterns:
            candidate = re.sub(pattern, "", value, count=1, flags=re.IGNORECASE).strip()
            if candidate != value:
                value = candidate
                break
        if value == previous:
            break

    return value


def _rewrite_natural_command_start(text):
    """
    Convertit un petit vocabulaire conversationnel vers les verbes deja
    autorises. Aucune nouvelle capacite n'est creee ici.
    """

    value = str(text or "").strip().replace("’", "'")

    command_verbs = (
        r"ouvre|ouvrir|ouvres|lance|lancer|lances|demarre|demarrer|demarres|"
        r"d[ée]marre|d[ée]marrer|d[ée]marres|ferme|fermer|fermes|quitte|quitter|"
        r"cherche|chercher|cherches|trouve|trouver|trouves|retrouve|retrouver|retrouves|"
        r"localise|localiser|localises|liste|lister|listes|affiche|afficher|affiches|"
        r"montre|montrer|montres|lis|lire|lises|cr[ée]e|cr[ée]er|cr[ée]es|"
        r"copie|copier|copies|duplique|dupliquer|dupliques|d[ée]place|d[ée]placer|d[ée]places|"
        r"range|ranger|ranges|renomme|renommer|renommes|supprime|supprimer|supprimes|"
        r"efface|effacer|effaces|verifie|verifier|verifies|v[ée]rifie|v[ée]rifier|v[ée]rifies|"
        r"accede|acceder|accedes|acc[èe]de|acc[èe]der|acc[èe]des|va|aller|vas|"
        r"mets|met|mettre|bouge|bouger|jette|jeter|enl[eè]ve|enlever|agrandis|agrandir|agrandit|reduis|reduire|r[ée]duit|minimise|minimiser|restaure|restaurer|pr[ée]pare|pr[ée]parer|commence|commencer"
    )

    value = re.sub(
        rf"^(?:m'|me\s+)(?=(?:{command_verbs})\b)",
        "",
        value,
        count=1,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        rf"^((?:{command_verbs}))(?:-moi|\s+moi)\b",
        r"\1",
        value,
        count=1,
        flags=re.IGNORECASE,
    )

    conjugation_rules = (
        (r"^(?:ouvrir|ouvres)\b", "ouvre"),
        (r"^(?:lancer|lances)\b", "lance"),
        (r"^(?:demarrer|d[ée]marrer|demarres|d[ée]marres)\b", "demarre"),
        (r"^(?:fermer|fermes)\b", "ferme"),
        (r"^cherches\b", "cherche"),
        (r"^trouves\b", "trouve"),
        (r"^affiches\b", "affiche"),
        (r"^montres\b", "montre"),
        (r"^listes\b", "liste"),
        (r"^lises\b", "lis"),
        (r"^cr[ée]es\b", "cree"),
        (r"^copies\b", "copie"),
        (r"^d[ée]places\b", "deplace"),
        (r"^renommes\b", "renomme"),
        (r"^supprimes\b", "supprime"),
        (r"^(?:verifier|v[ée]rifier|verifies|v[ée]rifies)\b", "verifie"),
        (r"^(?:acceder|acc[èeé]der|accedes|acc[èeé]des)\b", "accede"),
        (r"^(?:vas|ailles)\s+sur\b", "va sur"),
        (r"^r[ée]duit\b", "reduis"),
        (r"^(?:préparer|preparer|prépares|prepares)\b", "prépare"),
        (r"^(?:agrandit|agrandi)\b", "agrandis"),
    )
    for pattern, replacement in conjugation_rules:
        candidate = re.sub(pattern, replacement, value, count=1, flags=re.IGNORECASE)
        if candidate != value:
            value = candidate
            break

    synonym_rules = (
        (r"^(?:retrouve|retrouver|retrouves)\b", "trouve"),
        (r"^(?:localise|localiser|localises)\b", "trouve"),
        (r"^(?:efface|effacer|effaces)\b", "supprime"),
        (r"^(?:duplique|dupliquer|dupliques)\b", "copie"),
        (r"^(?:range|ranger|ranges)\b", "deplace"),
        (r"^(?:consulte|consulter|consultes)\s+le\s+contenu\b", "affiche le contenu"),
        (r"^(?:donne|donner|donnes)(?:-moi|\s+moi)?\s+le\s+contenu\s+(?:de|du)\s+(?:(?:le|la)\s+)?fichier\b", "lis le fichier"),
        (r"^(?:donne|donner|donnes)(?:-moi|\s+moi)?\s+le\s+contenu\b", "affiche le contenu"),
        (r"^ou\s+se\s+trouve\b", "ou est"),
        (r"^o[uù]\s+se\s+trouve\b", "ou est"),
        (r"^qu['’]?est[- ]ce\s+qu['’]?il\s+y\s+a\s+dans\b", "liste"),
        (r"^(?:montre|montrer)(?:-moi|\s+moi)?\s+ce\s+qu['’]?il\s+y\s+a\s+dans\b", "liste"),
        (r"^(?:affiche|afficher)(?:-moi|\s+moi)?\s+ce\s+qu['’]?il\s+y\s+a\s+dans\b", "liste"),
        (r"^lancer\s+ma\s+routine\s+de\s+travail\b", "lance ma routine de travail"),
    )
    for pattern, replacement in synonym_rules:
        candidate = re.sub(pattern, replacement, value, count=1, flags=re.IGNORECASE)
        if candidate != value:
            value = candidate
            break

    return value.strip()


SAFE_NATURAL_TARGET_TYPOS = {
    # Cibles connues uniquement. Aucune correction libre de nom de fichier.
    "gitub": "github",
    "githb": "github",
    "gihub": "github",
    "chatgtp": "chatgpt",
    "chat gtp": "chatgpt",
    "vscod": "vscode",
    "vs cod": "vs code",
    "exel": "excel",
    "outlok": "outlook",
    "teems": "teams",
    "ondrive": "onedrive",
    "microsodt edge": "microsoft edge",
    "microsft edge": "microsoft edge",
    "microsoft edg": "microsoft edge",
}


def _strip_natural_possessive_target(value):
    """Retire un determinant possessif uniquement dans une cible conversationnelle."""
    text = str(value or "").strip()
    return re.sub(
        r"^(?:mon|ma|mes)\s+",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    ).strip()


def _rewrite_safe_target_typo(text):
    """
    Corrige seulement quelques fautes connues sur des applications/sites autorises.
    Les noms de fichiers et dossiers ne sont jamais corriges automatiquement ici.
    """
    value = str(text or "").strip().replace("’", "'")
    match = re.fullmatch(
        r"(ouvre|ouvrir|lance|lancer|ferme|fermer|verifie|v[ée]rifie)\s+(.+?)\s*[.!?]?",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return value

    verb = match.group(1)
    target = normalize_text(match.group(2))
    corrected = SAFE_NATURAL_TARGET_TYPOS.get(target)
    if not corrected:
        return value

    if normalize_application_target(corrected) or corrected in WEBSITE_ALIASES or corrected in load_site_names():
        return f"{verb} {corrected}"
    return value


def _rewrite_indirect_natural_request(text):
    """
    Reconnait quelques intentions indirectes mais non ambigues.
    Cette fonction ne cree aucune capacite : elle reformule vers les verbes
    deja autorises et chaque resultat repasse ensuite dans les parseurs stricts.
    """
    value = str(text or "").strip().replace("’", "'")
    if not value:
        return value

    # --------------------------------------------------------
    # Ouvrir une application a partir d'un besoin fonctionnel simple.
    # Le catalogue est ferme et volontairement petit.
    # --------------------------------------------------------
    normalized = normalize_text(value).rstrip(" .!?")

    # Verifications conversationnelles courantes.
    # Aucune application n'est lancee ici : on ne fait qu'une verification.
    match = re.fullmatch(
        r"(?:verifie|verifier|assure toi|assure-toi|regarde|regarder|voir|check|checker|dis moi|dis-moi)\s+(?:que|si)\s+(.+?)\s+"
        r"(?:est\s+)?(?:ouvert|ouverte|lance|lancee|lancer|demarre|demarree|en cours|tourne|fonctionne)",
        normalized,
        flags=re.IGNORECASE,
    )
    if match:
        candidate = match.group(1).strip()
        if normalize_application_target(candidate):
            return f"verifie si {candidate} est ouvert"

    # Raccourci naturel vers une routine seulement lorsqu'une seule routine
    # confirmee est disponible. Avec plusieurs routines, on ne choisit pas.
    if normalized in {
        "lance ma routine", "demarre ma routine", "execute ma routine",
        "lance la routine", "demarre la routine",
    }:
        routine_ids = sorted(set(load_routine_triggers().values()))
        if len(routine_ids) == 1:
            return "lance ma routine de travail"

    # Quelques formulations utilisateur tres courantes qui restent
    # non ambiguës et ne declenchent qu'une action deja autorisee.
    if normalized in {
        "ouvre les fichiers",
        "ouvre mes fichiers",
        "ouvre mes fichier",
        "ouvre le gestionnaire de fichiers",
        "ouvre le gestionnaire de fichier",
        "montre mes fichiers",
        "affiche mes fichiers",
        "je veux voir mes fichiers",
        "je veux voir les fichiers",
    }:
        return "ouvre explorateur de fichiers"

    # Routine de travail : formulation explicite mais plus naturelle.
    # On ne la resout automatiquement que lorsqu'une seule routine confirmee
    # est disponible, comme pour « lance ma routine ».
    if normalized in {
        "prepare-moi pour travailler", "prepare moi pour travailler",
        "prepare moi pour le travail", "prepare-moi pour le travail",
        "prepare moi pour le boulot", "prepare-moi pour le boulot",
        "commence ma routine", "commencer ma routine",
    }:
        routine_ids = sorted(set(load_routine_triggers().values()))
        if len(routine_ids) == 1:
            return "lance ma routine de travail"

    # Tournures orales non ambigues vers une cible connue.
    match = re.fullmatch(
        r"(?:mets|met)\s+(?:moi\s+)?sur\s+(.+)",
        normalized,
        flags=re.IGNORECASE,
    )
    if match:
        candidate = match.group(1).strip()
        if normalize_application_target(candidate) or candidate in WEBSITE_ALIASES or candidate in load_site_names():
            return f"ouvre {candidate}"

    match = re.fullmatch(
        r"(?:ramene|ramener|mets|met)\s+(.+?)\s+devant",
        normalized,
        flags=re.IGNORECASE,
    )
    if match:
        candidate = match.group(1).strip()
        if normalize_application_target(candidate):
            return f"mets {candidate} au premier plan"

    task_rules = (
        (
            r"^(?:(?:ouvre|ouvrir|lance|lancer)\s+)?(?:(?:le|la|l')\s*)?(?:truc|outil|appli|application|logiciel|ce qu'il faut)?\s*(?:pour\s+)?(?:ecrire|rediger|taper|creer|faire)\s+(?:un\s+)?(?:document|texte)(?:\s+word)?$",
            "ouvre word",
        ),
        (
            r"^(?:j'ai besoin|je voudrais|j'aimerais|je veux)\s+d['e ]*(?:ecrire|rediger|taper|creer|faire)\s+(?:un\s+)?(?:document|texte)(?:\s+word)?$",
            "ouvre word",
        ),
        (
            r"^(?:(?:ouvre|ouvrir|lance|lancer)\s+)?(?:(?:le|la|l')\s*)?(?:truc|outil|appli|application|logiciel|ce qu'il faut)?\s*(?:pour\s+)?(?:faire|creer|remplir|modifier)\s+(?:un\s+)?(?:tableur|feuille de calcul|tableau excel|fichier excel)$",
            "ouvre excel",
        ),
        (
            r"^(?:(?:ouvre|ouvrir|lance|lancer)\s+)?(?:(?:le|la|l')\s*)?(?:truc|outil|appli|application|logiciel|ce qu'il faut)?\s*(?:pour\s+)?(?:faire|creer|preparer|modifier)\s+(?:une\s+)?(?:presentation|diaporama|presentation powerpoint)$",
            "ouvre powerpoint",
        ),
        (
            r"^(?:(?:ouvre|ouvrir|lance|lancer)\s+)?(?:(?:le|la|l')\s*)?(?:truc|outil|appli|application|logiciel|ce qu'il faut)?\s*(?:pour\s+)?(?:calculer|faire un calcul|faire des calculs)$",
            "ouvre calculatrice",
        ),
        (
            r"^(?:(?:ouvre|ouvrir|lance|lancer)\s+)?(?:(?:le|la|l')\s*)?(?:truc|outil|appli|application|logiciel|ce qu'il faut)?\s*(?:pour\s+)?(?:faire|prendre)\s+(?:une\s+)?capture d'ecran$",
            "ouvre outil de capture",
        ),
        (
            r"^(?:(?:ouvre|ouvrir|lance|lancer)\s+)?(?:(?:le|la|l')\s*)?(?:truc|outil|appli|application|logiciel|ce qu'il faut)?\s*(?:pour\s+)?(?:dessiner|peindre|modifier une image|retoucher une image)$",
            "ouvre paint",
        ),
    )
    for pattern, replacement in task_rules:
        if re.fullmatch(pattern, normalized, flags=re.IGNORECASE):
            return replacement

    # --------------------------------------------------------
    # "J'ai besoin du rapport que j'ai mis dans Documents"
    # => recherche non destructive.
    # --------------------------------------------------------
    match = re.fullmatch(
        r"(?:j'ai besoin de|j'ai besoin du|je cherche|je recherche|retrouve(?:-moi)?|trouve(?:-moi)?)\s+"
        r"(?:(?:le|la|un|une)\s+)?(?:(?:fichier|document)\s+)?(.+?)\s+"
        r"(?:que j'ai (?:mis|range|enregistre)|qui (?:est|se trouve))\s+dans\s+(.+?)\s*[.!?]?",
        value,
        flags=re.IGNORECASE,
    )
    if match:
        name = _strip_natural_possessive_target(match.group(1))
        location = match.group(2).strip()
        if name and location:
            return f"trouve le fichier {name} dans {location}"

    # "Ouvre le rapport qui est dans Documents".
    match = re.fullmatch(
        r"(?:ouvre|ouvrir)(?:-moi|\s+moi)?\s+"
        r"(?:(?:le|la|un|une)\s+)?(?:(?:fichier|document)\s+)?(.+?)\s+"
        r"(?:qui (?:est|se trouve)|que j'ai (?:mis|range|enregistre))\s+dans\s+(.+?)\s*[.!?]?",
        value,
        flags=re.IGNORECASE,
    )
    if match:
        name = _strip_natural_possessive_target(match.group(1))
        location = match.group(2).strip()
        if name and location:
            return f"ouvre le fichier {name} dans {location}"

    # Recherche : "va me chercher rapport.pdf dans Telechargements".
    match = re.fullmatch(
        r"(?:va\s+)?(?:me\s+)?(?:chercher|retrouver|trouver|localiser)\s+"
        r"(?:(?:le|la|un|une)\s+)?(?:(?:fichier|document)\s+)?(.+?)"
        r"(?:\s+dans\s+(.+?))?\s*[.!?]?",
        value,
        flags=re.IGNORECASE,
    )
    if match:
        name = _strip_natural_possessive_target(match.group(1))
        location = (match.group(2) or "").strip()
        if name:
            if location:
                return f"trouve {name} dans {location}"
            return f"trouve {name}"

    # Consultation d'un emplacement.
    list_patterns = (
        r"(?:il\s+)?y\s+a\s+quoi\s+dans\s+(.+?)\s*[.!]?",
        r"(?:montre|affiche|liste)(?:-moi|\s+moi)?\s+((?:bureau|desktop|documents?|telechargements?|downloads?|images?|photos?|pictures?|videos?|musiques?|music))\s*[.!]?",
        r"(?:fais\s+voir|montre(?:-moi|\s+moi)?|affiche(?:-moi|\s+moi)?)\s+(?:tout\s+)?ce\s+qu['’]?il\s+y\s+a\s+dans\s+(.+?)\s*[.!?]?",
        r"(?:montre(?:-moi|\s+moi)?|affiche(?:-moi|\s+moi)?|liste(?:-moi|\s+moi)?)\s+(?:mes|les)\s+(?:fichiers|documents)\s+dans\s+(.+?)\s*[.!?]?",
        r"(?:je\s+peux|puis[- ]je|est[- ]ce\s+que\s+je\s+peux)\s+voir\s+(.+?)\s*[.!?]?",
    )
    for pattern in list_patterns:
        match = re.fullmatch(pattern, value, flags=re.IGNORECASE)
        if match:
            target = match.group(1).strip()
            clean_target = re.sub(
                r"^(?:mes|mon|ma|les|le|la)\s+",
                "",
                target,
                count=1,
                flags=re.IGNORECASE,
            ).strip()
            if normalize_file_root(target):
                return f"liste {target}"
            if normalize_file_root(clean_target):
                return f"liste {clean_target}"

    # Verification d'une application : "Word est ouvert ?", "Word tourne ?"
    # ou "Est-ce que Word tourne ?".
    # Formes interrogatives courantes : "VS Code est-il ouvert ?".
    interrogative = re.fullmatch(
        r"(.+?)\s+est[- ]il\s+(?:ouvert|ouverte|lance|lancee|demarre|demarree)\s*[?!.]?",
        normalize_text(value),
        flags=re.IGNORECASE,
    )
    if interrogative:
        candidate = interrogative.group(1).strip()
        if normalize_application_target(candidate):
            return f"verifie si {candidate} est ouvert"

    check_value = re.sub(
        r"^(?:est[- ]ce\s+que|est\s+ce\s+que)\s+",
        "",
        normalize_text(value),
        count=1,
        flags=re.IGNORECASE,
    )
    match = re.fullmatch(
        r"(.+?)\s+(?:est\s+(?:bien\s+)?(?:ouvert|ouverte|lance|lancee)|tourne|fonctionne)(?:\s+en\s+ce\s+moment)?\s*[?!.]?",
        check_value,
        flags=re.IGNORECASE,
    )
    if match:
        candidate = match.group(1).strip()
        if normalize_application_target(candidate):
            return f"verifie si {candidate} est ouvert"

    # Deplacement conversationnel. On garde exactement la meme restriction
    # que la commande "deplace ... dans ..." existante.
    match = re.fullmatch(
        r"(?:mets|mettre|bouge|bouger)\s+(.+?)\s+(?:dans|vers)\s+(.+?)\s*[.!?]?",
        value,
        flags=re.IGNORECASE,
    )
    if match:
        return f"deplace {match.group(1).strip()} dans {match.group(2).strip()}"

    # Suppression familiere uniquement avec contexte fichier explicite ou
    # extension visible. La suppression finale reste la Corbeille Windows.
    match = re.fullmatch(
        r"(?:jette|jeter|enl[eè]ve|enlever)\s+(?:(?:le|la)\s+fichier\s+)?(.+?)\s*[.!?]?",
        value,
        flags=re.IGNORECASE,
    )
    if match:
        candidate = match.group(1).strip()
        has_file_word = bool(re.search(r"\bfichier\b", value, flags=re.IGNORECASE))
        has_extension = bool(Path(candidate).suffix)
        if has_file_word or has_extension:
            return f"supprime {candidate}"

    return value


def _looks_like_known_multi_target_request(value):
    """Detecte "Word puis GitHub" pour laisser le parseur multi-cibles agir."""
    normalized = normalize_text(value)
    if not normalized:
        return False
    split_value = normalized
    for connector in (" et ensuite ", " ainsi que ", " puis ", " et ", " + ", ";"):
        split_value = split_value.replace(connector, ",")
    parts = [part.strip() for part in split_value.split(",") if part.strip()]
    if len(parts) < 2 or len(parts) > 8:
        return False
    return all(resolve_open_target(part)[0] for part in parts)


def _looks_like_forbidden_execution_target(value):
    normalized = normalize_text(value)
    if not normalized:
        return False
    normalized = re.sub(
        r"^(?:le|la|l'|un|une)\s+",
        "",
        normalized,
        count=1,
        flags=re.IGNORECASE,
    ).strip()
    return normalized in BLOCKED_EXECUTION_TARGET_NAMES


def _contains_forbidden_execution_target(value):
    """Refuse atomiquement une demande multi-cibles contenant un shell interdit."""
    parts = split_targets(value)
    return any(_looks_like_forbidden_execution_target(part) for part in parts)


def _looks_like_functional_app_request(value):
    """Evite de confondre une demande fonctionnelle avec un nom de fichier."""
    normalized = normalize_text(value)
    if not normalized:
        return False
    markers = (
        "le truc pour ",
        "la truc pour ",
        "l'appli pour ",
        "appli pour ",
        "l'application pour ",
        "application pour ",
        "le logiciel pour ",
        "logiciel pour ",
        "l'outil pour ",
        "outil pour ",
        "ce qu'il faut pour ",
    )
    return any(normalized.startswith(marker) for marker in markers)


def _strip_natural_trailing_politeness(text):
    """Retire une formule de politesse finale hors contenu litteral utilisateur."""
    value = str(text or "").strip().replace("’", "'")
    if not value or _has_literal_content_payload(value):
        return value
    value = re.sub(
        r"\s*[,;:-]?\s*(?:s'il\s+te\s+pla[iî]t|s'il\s+vous\s+pla[iî]t|stp|svp|merci)\s*[.!?]*\s*$",
        "",
        value,
        count=1,
        flags=re.IGNORECASE,
    ).strip()
    return value.rstrip(" .!?").strip()



def _strip_spoken_ivoirian_fillers(text):
    """Nettoie quelques marqueurs oraux ivoiriens sans toucher au contenu litteral."""
    value = str(text or "").strip().replace("\u2019", "'")
    if not value or _has_literal_content_payload(value):
        return value

    # "regarde un peu si..." / "arrange un peu mes fenetres".
    value = re.sub(
        r"^(regarde|regarder|check|checker|arrange|organise|range|reorganise)\s+un\s+peu\s+",
        r"\1 ",
        value,
        count=1,
        flags=re.IGNORECASE,
    )

    # Marqueurs de fin tres frequents a l'oral. On les retire seulement dans
    # la variante conversationnelle; la phrase stricte reste analysee d'abord.
    for _ in range(3):
        cleaned = re.sub(
            r"\s+(?:l\u00e0|la|hein|m\u00eame|ou\s+bien|un\s+peu)\s*[.!?]*\s*$",
            "",
            value,
            count=1,
            flags=re.IGNORECASE,
        ).strip()
        if cleaned == value:
            break
        value = cleaned

    return value.rstrip(" .!?").strip()


def _is_explicit_negative_request(text):
    """Detecte les negations orales avant tout parseur d'action."""
    value = normalize_text(text).strip(" .!?")
    if not value:
        return False

    patterns = (
        r"^(?:il\s+)?faut\s+pas\b",
        r"^pas\s+la\s+peine\b",
        r"^je\s+(?:ne\s+)?veux\s+pas\b",
        r"^n[' ]?(?:ouvre|lance|demarre|ferme|verifie|agrandis|reduis|supprime|efface|deplace|copie|renomme|va|aller|mets|met|lis|lire|montre|affiche|regarde|passe|active)\s+pas\b",
        r"^ne\s+(?:ouvre|lance|demarre|ferme|verifie|agrandis|reduis|supprime|efface|deplace|copie|renomme|va|aller|mets|met|lis|lire|montre|affiche|regarde|passe|active)\s+pas\b",
        r"^(?:ouvre|lance|demarre|ferme|verifie|agrandis|reduis|supprime|efface|deplace|copie|renomme|va|aller|mets|met|lis|lire|montre|affiche|regarde|passe|active)\s+pas\b",
    )
    return any(re.search(pattern, value) for pattern in patterns)


def _looks_like_spoken_safe_context(text):
    """Autorise le retrait de marqueurs oraux surtout pour des actions non destructives."""
    raw_value = str(text or "").strip()
    value = normalize_text(_strip_spoken_ivoirian_fillers(raw_value)).strip(" .!?")
    if not value:
        return False

    safe_starts = (
        "ouvre ", "ouvrir ", "lance ", "lancer ", "ferme ", "fermer ",
        "va sur ", "aller sur ", "verifie ", "regarde ", "dis moi ",
        "check ", "checker ", "agrandis ", "agrandir ", "reduis ",
        "reduire ", "minimise ", "passe sur ", "active ",
        "lance ma routine", "demarre ma routine", "prepare ",
        "commence ma routine", "montre ", "affiche ", "liste ", "fais voir ",
        "cherche ", "trouve ", "retrouve ", "je veux voir ",
        "je veux aller sur ", "y a quoi dans ", "il y a quoi dans ", "faut ", "il faut ", "tu peux voir ",
        "peux tu voir ", "pourrais tu voir ", "bon ", "donc ",
    )
    if value.startswith(safe_starts):
        return True

    # Question courte tres courante : "Teams est lance meme ?" / "Word tourne ou bien ?".
    match = re.fullmatch(
        r"(.+?)\s+(?:est\s+(?:ouvert|ouverte|lance|lancee|demarre|demarree)|tourne|fonctionne)",
        value,
    )
    if match and normalize_application_target(match.group(1).strip()):
        return True

    # "mets" n'est nettoye que pour une fenetre ou une navigation connue,
    # jamais pour un deplacement de fichier vers un dossier.
    if re.fullmatch(r"(?:mets|met)\s+(?:moi\s+)?sur\s+.+", value):
        return True
    if re.fullmatch(
        r"(?:mets|met|place|positionne)\s+.+?\s+(?:a|sur)\s+(?:la\s+)?(?:gauche|droite)",
        value,
    ):
        return True
    if re.fullmatch(r"(?:mets|met)\s+.+?\s+(?:devant|au\s+premier\s+plan|en\s+grand)", value):
        return True

    return False


def _is_explicit_forbidden_execution_request(text):
    """Reconnait une demande explicite visant un shell interdit, y compris en langage oral."""
    value = str(text or "").strip()
    if not value:
        return False

    value = _strip_natural_trailing_politeness(value)
    value = _strip_spoken_ivoirian_fillers(value)
    value = _strip_natural_leading_wrappers(value)
    value = _rewrite_natural_command_start(value)
    normalized = normalize_text(value).strip(" .!?")

    match = re.match(
        r"^(?:ouvre|ouvrir|lance|lancer|demarre|demarrer|ferme|fermer|quitte|quitter)\s+(.+)$",
        normalized,
    )
    if not match:
        return False

    return _contains_forbidden_execution_target(match.group(1).strip())


def _is_ambiguous_spoken_destructive_request(text):
    """Ne devine jamais une cible destructive lorsqu'un marqueur oral peut faire partie du nom."""
    value = normalize_text(text).strip(" .!?")
    if not value:
        return False
    if not re.search(r"\s+(?:la|hein|meme|ou\s+bien|un\s+peu)$", value):
        return False

    # L'organisation globale des fenetres reste une conversation sans action.
    if re.fullmatch(
        r"(?:arrange|organise|range|reorganise)\s+(?:un\s+peu\s+)?(?:mes|les)\s+fenetres(?:\s+un\s+peu)?",
        value,
    ):
        return False

    # Les placements de fenetre restent non destructifs et explicites.
    if re.match(r"^(?:mets|met|place|positionne)\s+", value):
        if re.search(r"\s+(?:a|sur)\s+(?:la\s+)?(?:gauche|droite)\s+(?:la|hein|meme|ou\s+bien|un\s+peu)$", value):
            return False
        if re.search(r"\s+(?:devant|au\s+premier\s+plan|en\s+grand)\s+(?:la|hein|meme|ou\s+bien|un\s+peu)$", value):
            return False
        if re.match(r"^(?:mets|met)\s+moi\s+sur\s+", value):
            return False

    destructive = (
        "supprime ", "efface ", "deplace ", "range ", "copie ",
        "duplique ", "renomme ", "jette ", "enleve ", "mets ", "met ",
    )
    return value.startswith(destructive)

def build_natural_command_variants(user_message):
    """
    Produit des variantes plus naturelles, mais uniquement comme secours
    apres l'interpretation stricte. L'original reste toujours prioritaire.
    """

    original = str(user_message or "").strip()
    if not original:
        return []

    candidates = []

    def add(value):
        value = str(value or "").strip()
        if value and value != original and value not in candidates:
            candidates.append(value)

    direct_question = re.sub(
        r"^(?:(?:est[- ]ce\s+que\s+)?tu\s+(?:peux|pourrais)|peux[- ]tu|pourrais[- ]tu)\s+me\s+dire\s+o[uù]\s+(?:se\s+trouve|est)\s+",
        "trouve ",
        original.replace("’", "'"),
        count=1,
        flags=re.IGNORECASE,
    )
    if not _has_literal_content_payload(direct_question):
        direct_question = re.sub(
            r"\s*[,;:-]?\s*(?:s'il\s+te\s+pla[iî]t|s'il\s+vous\s+pla[iî]t|stp|svp|merci)\s*[.!?]*\s*$",
            "",
            direct_question,
            count=1,
            flags=re.IGNORECASE,
        ).strip()
        direct_question = direct_question.rstrip(" .!?").strip()
    add(direct_question)

    value = _rewrite_indirect_natural_request(original)
    value = _strip_natural_leading_wrappers(value)
    if _looks_like_spoken_safe_context(value):
        value = _strip_spoken_ivoirian_fillers(value)
    value = _rewrite_indirect_natural_request(value)
    value = _rewrite_natural_command_start(value)
    value = _rewrite_indirect_natural_request(value)
    value = _rewrite_safe_target_typo(value)
    if _looks_like_spoken_safe_context(value):
        value = _strip_spoken_ivoirian_fillers(value)

    if not _has_literal_content_payload(value):
        value = re.sub(
            r"\s*[,;:-]?\s*(?:s'il\s+te\s+pla[iî]t|s'il\s+vous\s+pla[iî]t|stp|svp|merci)\s*[.!?]*\s*$",
            "",
            value,
            count=1,
            flags=re.IGNORECASE,
        ).strip()
        value = value.rstrip(" .!?").strip()

    add(value)
    return candidates


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

    if value in BLOCKED_EXECUTION_TARGET_NAMES:
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

    trigger_map = load_routine_triggers()
    routine_id = trigger_map.get(text)

    # « Ma routine » n'est resolue que s'il existe une seule routine
    # active et confirmee. Avec plusieurs routines, AgentLocal ne choisit pas.
    if not routine_id and text in {
        "lance ma routine",
        "demarre ma routine",
        "execute ma routine",
        "lance la routine",
        "demarre la routine",
    }:
        routine_ids = sorted(set(trigger_map.values()))
        if len(routine_ids) == 1:
            routine_id = routine_ids[0]

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
        r"^verifie que (.+?) est ouvert$",
        r"^verifie que (.+?) est ouverte$",
        r"^verifie que (.+?) est lance$",
        r"^verifie que (.+?) est lancee$",
        r"^verifie que (.+?) est lancer$",
        r"^verifie que (.+?) tourne$",
        r"^verifie que (.+?) fonctionne$",
        r"^regarde si (.+?) est ouvert$",
        r"^regarde si (.+?) est ouverte$",
        r"^confirme que (.+?) est ouvert$",
        r"^confirme que (.+?) est ouverte$",
        r"^verifie (.+)$",
        r"^est ce que (.+?) est ouvert$",
        r"^est ce que (.+?) est ouverte$",
        r"^est ce que (.+?) est lance$",
        r"^est ce que (.+?) tourne$",
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
        " et ensuite ",
        ","
    )

    value = value.replace(
        " ainsi que ",
        ","
    )

    value = value.replace(
        " puis ",
        ","
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
        r"documents?|docuements?|"
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

    # ========================================================
    # FORME AVEC RACINE EXPLICITE
    # ========================================================

    pattern_with_root = (
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
        pattern_with_root,
        user_message,
        flags=re.IGNORECASE
    )

    if match:

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

        if not is_safe_simple_file_name(
            old_name
        ):
            return []

        if not is_safe_simple_file_name(
            new_name
        ):
            return []

        if (
            old_name.casefold()
            ==
            new_name.casefold()
        ):
            return []

        old_extension = get_extension_chain(old_name)
        new_extension = get_extension_chain(new_name)
        if old_extension and new_extension and old_extension != new_extension:
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

    # ========================================================
    # FORME SANS RACINE
    #
    # Exemple :
    #   renomme test.txt en archive.txt
    #
    # La recherche de l'emplacement n'est PAS faite ici.
    # Le backend ne fait qu'identifier l'intention.
    # file_tools.py recherchera ensuite uniquement dans les
    # six racines utilisateur autorisées.
    # ========================================================

    pattern_without_root = (
        r"^\s*"
        r"(?:renomme|renommer)"
        r"\s+"
        r"(?:(?:le|la)\s+fichier\s+)?"
        r"(.+?)"
        r"\s+en\s+"
        r"(.+?)"
        r"\s*[.!?]?\s*$"
    )

    match = re.fullmatch(
        pattern_without_root,
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

    if not is_safe_simple_file_name(
        old_name
    ):
        return []

    if not is_safe_simple_file_name(
        new_name
    ):
        return []

    if (
        old_name.casefold()
        ==
        new_name.casefold()
    ):
        return []

    old_extension = get_extension_chain(old_name)
    new_extension = get_extension_chain(new_name)
    if old_extension and new_extension and old_extension != new_extension:
        return []

    return [
        make_action(
            "rename_file_auto",
            "auto",
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
# MODIFIER UN FICHIER TEXTE EXISTANT
# ============================================================

def parse_modify_file_content(
    user_message
):
    """
    Formes strictes acceptées :

        remplace le contenu de notes.txt dans Documents par Réunion à 15h
        ajoute au fichier notes.txt dans Documents le contenu Pense à envoyer le rapport
        ajoute une ligne à journal.txt dans Documents avec le contenu Test terminé

    Les opérations de masse, chemins et jokers ne sont jamais interprétés.
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
            "replace_content",
            (
                r"^\s*"
                r"(?:remplace|remplacer)"
                r"\s+le\s+contenu\s+(?:de|du)\s+"
                r"(?:(?:le|la)\s+fichier\s+)?"
                r"(.+?)"
                r"\s+dans\s+"
                r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
                r"(" + root_pattern + r")"
                r"\s+par"
                r"\s*:?[ \t]*"
                r"(.+?)"
                r"\s*$"
            )
        ),
        (
            "append_line",
            (
                r"^\s*"
                r"(?:ajoute|ajouter)"
                r"\s+une\s+ligne\s+[àa]\s+"
                r"(?:(?:le|la)\s+fichier\s+)?"
                r"(.+?)"
                r"\s+dans\s+"
                r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
                r"(" + root_pattern + r")"
                r"\s+avec\s+le\s+contenu"
                r"\s*:?[ \t]*"
                r"(.+?)"
                r"\s*$"
            )
        ),
        (
            "append_content",
            (
                r"^\s*"
                r"(?:ajoute|ajouter)"
                r"\s+(?:au|à|a)\s+fichier\s+"
                r"(.+?)"
                r"\s+dans\s+"
                r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
                r"(" + root_pattern + r")"
                r"\s+le\s+contenu"
                r"\s*:?[ \t]*"
                r"(.+?)"
                r"\s*$"
            )
        ),
    ]

    for mode, pattern in patterns:
        match = re.fullmatch(
            pattern,
            user_message,
            flags=re.IGNORECASE
        )

        if not match:
            continue

        file_name = match.group(1).strip()
        root_name = normalize_file_root(
            match.group(2)
        )
        content = match.group(3).strip()

        if not root_name:
            return []

        if not is_safe_simple_file_name(
            file_name
        ):
            return []

        if normalize_text(
            file_name
        ) in MASS_MODIFY_TERMS:
            return []

        extension = (
            Path(file_name)
            .suffix
            .lower()
        )

        if extension and extension not in WRITABLE_TEXT_EXTENSIONS:
            return []

        if (
            mode in {
                "append_content",
                "append_line",
            }
            and
            extension
            and
            extension not in APPEND_SAFE_TEXT_EXTENSIONS
        ):
            return []

        if not content:
            return []

        if (
            mode == "append_line"
            and
            ("\n" in content or "\r" in content)
        ):
            return []

        if len(content) > 65536:
            return []

        return [
            make_action(
                "modify_file_content",
                root_name,
                {
                    "file_name": file_name,
                    "content": content,
                    "mode": mode,
                }
            )
        ]

    return []


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

    # Pas d'action globale implicite et pas d'execution partielle lorsqu'une
    # des cibles demande un shell explicitement interdit.
    if normalize_text(content) in {
        "tout", "tous", "toutes", "toutes les applications",
        "toutes les applis", "toutes les fenetres",
    }:
        return []
    if is_vague_filesystem_reference(content):
        return []
    if _contains_forbidden_execution_target(content):
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

    if normalize_text(content) in {
        "tout", "tous", "toutes", "tous mes fichiers", "tous les fichiers",
        "tous mes documents", "tous les documents", "toutes les applications",
        "toutes les applis", "toutes les fenetres",
    }:
        return []
    if _contains_forbidden_execution_target(content):
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
# GESTION EXPLICITE DES FENETRES
# ============================================================

WINDOW_OPERATION_ALIASES = {
    "gauche": "snap_left",
    "droite": "snap_right",
}


def _normalize_window_application_target(value):
    """Accepte uniquement une application deja presente dans le catalogue ferme."""

    value = normalize_text(value).strip(" .!?")

    prefixes = (
        "la fenetre de l'application ",
        "fenetre de l'application ",
        "la fenetre de l'appli ",
        "fenetre de l'appli ",
        "la fenetre de ",
        "fenetre de ",
        "la fenetre ",
        "fenetre ",
        "l'application ",
        "application ",
        "l'appli ",
        "appli ",
        "le logiciel ",
        "logiciel ",
        "le ",
        "la ",
        "l'",
    )

    for prefix in prefixes:
        if value.startswith(prefix):
            value = value[len(prefix):].strip()
            break

    return normalize_application_target(value)


def parse_manage_window(text):
    """
    Gestion volontairement limitee des fenêtres.

    Exemples explicites acceptes :
        mets VS Code a gauche
        place Edge a droite
        agrandis Word
        reduis Excel
        restaure PowerPoint
        mets Outlook au premier plan
        passe sur VS Code
        mets VS Code a gauche et Edge a droite

    Aucune cible globale ("toutes les fenêtres") et aucune cible inconnue
    ne sont deduites automatiquement.
    """

    text = normalize_text(text).strip(" .!?")
    if not text:
        return []

    # --------------------------------------------------------
    # Deux placements explicites. Chaque cote et chaque cible
    # doivent être nommes par l'utilisateur.
    # --------------------------------------------------------
    match = re.fullmatch(
        r"(?:mets|met|mettre|place|placer|positionne|positionner)\s+"
        r"(.+?)\s+(?:a|sur)\s+(?:la\s+)?(gauche|droite)\s+"
        r"(?:et|puis|et\s+puis|et\s+ensuite)\s+"
        r"(.+?)\s+(?:a|sur)\s+(?:la\s+)?(gauche|droite)",
        text,
    )
    if match:
        first_app = _normalize_window_application_target(match.group(1))
        second_app = _normalize_window_application_target(match.group(3))
        if not first_app or not second_app:
            return []
        return [
            make_action(
                "manage_window",
                first_app,
                {"operation": WINDOW_OPERATION_ALIASES[match.group(2)]},
            ),
            make_action(
                "manage_window",
                second_app,
                {"operation": WINDOW_OPERATION_ALIASES[match.group(4)]},
            ),
        ]

    # --------------------------------------------------------
    # Placement sur une moitie de l'ecran
    # --------------------------------------------------------
    match = re.fullmatch(
        r"(?:mets|met|mettre|place|placer|positionne|positionner)\s+"
        r"(.+?)\s+(?:a|sur)\s+(?:la\s+)?(gauche|droite)",
        text,
    )
    if match:
        app_name = _normalize_window_application_target(match.group(1))
        if not app_name:
            return []
        return [
            make_action(
                "manage_window",
                app_name,
                {"operation": WINDOW_OPERATION_ALIASES[match.group(2)]},
            )
        ]

    # --------------------------------------------------------
    # Agrandir
    # --------------------------------------------------------
    match = re.fullmatch(
        r"(?:agrandis|agrandir|agrandit|agrandi|maximise|maximiser)\s+(.+)",
        text,
    )
    if match:
        app_name = _normalize_window_application_target(match.group(1))
        if app_name:
            return [make_action("manage_window", app_name, {"operation": "maximize"})]
        return []

    match = re.fullmatch(
        r"(?:mets|met|mettre)\s+(.+?)\s+en\s+grand",
        text,
    )
    if match:
        app_name = _normalize_window_application_target(match.group(1))
        if app_name:
            return [make_action("manage_window", app_name, {"operation": "maximize"})]
        return []

    # --------------------------------------------------------
    # Reduire
    # --------------------------------------------------------
    match = re.fullmatch(
        r"(?:reduis|reduire|minimise|minimiser)\s+(.+)",
        text,
    )
    if match:
        app_name = _normalize_window_application_target(match.group(1))
        if app_name:
            return [make_action("manage_window", app_name, {"operation": "minimize"})]
        return []

    # --------------------------------------------------------
    # Restaurer
    # --------------------------------------------------------
    match = re.fullmatch(
        r"(?:restaure|restaurer|retablis|retablir)\s+(.+)",
        text,
    )
    if match:
        app_name = _normalize_window_application_target(match.group(1))
        if app_name:
            return [make_action("manage_window", app_name, {"operation": "restore"})]
        return []

    match = re.fullmatch(
        r"(?:remets|remettre)\s+(.+?)\s+en\s+(?:mode\s+)?fenetre",
        text,
    )
    if match:
        app_name = _normalize_window_application_target(match.group(1))
        if app_name:
            return [make_action("manage_window", app_name, {"operation": "restore"})]
        return []

    # --------------------------------------------------------
    # Premier plan
    # --------------------------------------------------------
    match = re.fullmatch(
        r"(?:mets|met|mettre|place|placer)\s+(.+?)\s+au\s+premier\s+plan",
        text,
    )
    if match:
        app_name = _normalize_window_application_target(match.group(1))
        if app_name:
            return [make_action("manage_window", app_name, {"operation": "focus"})]
        return []

    match = re.fullmatch(
        r"(?:passe|passer|bascule|basculer)\s+(?:sur|a)\s+(.+)",
        text,
    )
    if match:
        app_name = _normalize_window_application_target(match.group(1))
        if app_name:
            return [make_action("manage_window", app_name, {"operation": "focus"})]
        return []

    match = re.fullmatch(
        r"(?:active|activer)\s+(.+)",
        text,
    )
    if match:
        app_name = _normalize_window_application_target(match.group(1))
        if app_name:
            return [make_action("manage_window", app_name, {"operation": "focus"})]
        return []

    return []


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
    # Modification contrôlée de fichier existant
    # --------------------------------------------------------

    if not actions:

        actions = parse_modify_file_content(
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
    # Gestion explicite d'une fenêtre d'application
    # --------------------------------------------------------

    if not actions:

        actions = parse_manage_window(
            text
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
# ACCES RECURSIF CONTROLE AUX SOUS-DOSSIERS
# ============================================================

_RECURSIVE_ROOT_PATTERN = (
    r"bureau|desktop|"
    r"documents?|docuements?|"
    r"téléchargements?|telechargements?|downloads?|"
    r"images?|photos?|pictures?|"
    r"vidéos?|videos?|"
    r"musiques?|music"
)


def _safe_relative_path_syntax(value, allow_empty=False):
    if value is None:
        return allow_empty
    if not isinstance(value, str):
        return False
    value = value.strip()
    if not value:
        return allow_empty
    if len(value) > 1024:
        return False
    if value.startswith(("\\\\", "//", "\\", "/")):
        return False
    if ":" in value or "*" in value or "?" in value:
        return False
    parts = value.replace("/", "\\").split("\\")
    if not parts or len(parts) > 10:
        return False
    for part in parts:
        if not part or part in {".", ".."} or ".." in part:
            return False
        if re.search(r'[<>:"/\\|?*\x00-\x1f]', part):
            return False
        if part.endswith((" ", ".")):
            return False
    return True


def _join_relative(parent, child):
    parent = str(parent or "").strip().replace("/", "\\").strip("\\")
    child = str(child or "").strip().replace("/", "\\").strip("\\")
    if parent and child:
        return parent + "\\" + child
    return parent or child


def _parse_root_location(value):
    """Retourne (racine_technique, chemin_relatif) ou (None, None)."""
    if not isinstance(value, str):
        return None, None

    raw = value.strip().strip(".!?")
    raw = re.sub(
        r"^(?:mes|mon|ma|le|la|les)\s+",
        "",
        raw,
        flags=re.IGNORECASE,
    )

    match = re.match(
        r"^(" + _RECURSIVE_ROOT_PATTERN + r")(?:[\\/](.*))?$",
        raw,
        flags=re.IGNORECASE,
    )
    if not match:
        return None, None

    root = normalize_file_root(match.group(1))
    relative = (match.group(2) or "").strip().replace("/", "\\").strip("\\")
    if not root:
        return None, None
    if relative and not _safe_relative_path_syntax(relative):
        return None, None
    return root, relative


def _make_nested_file_action(action, root, relative_path, **extra):
    params = {"file_name": relative_path}
    params.update(extra)
    return [make_action(action, root, params)]


def parse_find_filesystem_item_recursive(user_message):
    text = normalize_text(user_message)

    patterns = [
        (r"^(?:trouve|trouver|cherche|chercher) le fichier (.+?)(?: dans (.+))?$", "file"),
        (r"^(?:trouve|trouver|cherche|chercher) le dossier (.+?)(?: dans (.+))?$", "dir"),
        (r"^(?:trouve|trouver|cherche|chercher) (.+?)(?: dans (.+))?$", "any"),
        (r"^ou est le fichier (.+?)(?: dans (.+))?$", "file"),
        (r"^ou est le dossier (.+?)(?: dans (.+))?$", "dir"),
        (r"^ou est (.+?)(?: dans (.+))?$", "any"),
    ]

    for pattern, item_type in patterns:
        match = re.fullmatch(pattern, text)
        if not match:
            continue
        name = match.group(1).strip()
        location = match.group(2).strip() if match.lastindex and match.lastindex >= 2 and match.group(2) else None
        if not _safe_relative_path_syntax(name) or "\\" in name or "/" in name:
            return []
        target = "auto"
        root = None
        if location:
            root, relative = _parse_root_location(location)
            if not root or relative:
                return []
            target = root
        return [make_action(
            "find_filesystem_item",
            target,
            {"name": name, "item_type": item_type, "root_name": root},
        )]
    return []


def parse_list_directory_recursive(user_message):
    raw = user_message.strip()

    # liste le dossier Cours dans Documents\Master1
    match = re.fullmatch(
        r"\s*(?:liste|lister|affiche|afficher|montre|montrer)\s+(?:le\s+)?dossier\s+(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        folder = match.group(1).strip()
        root, parent = _parse_root_location(match.group(2))
        if root and _safe_relative_path_syntax(folder):
            relative = _join_relative(parent, folder)
            return [make_action("list_directory", root, {"relative_path": relative})]

    # liste Documents\Cours\Master1 / affiche le contenu de Documents\Cours
    normalized_raw = re.sub(
        r"^\s*(?:liste|lister|affiche|afficher|montre|montrer|voir)\s+(?:le\s+contenu\s+(?:de|du|des)\s+)?",
        "",
        raw,
        flags=re.IGNORECASE,
    ).strip().strip(".!?")
    root, relative = _parse_root_location(normalized_raw)
    if root and relative:
        return [make_action("list_directory", root, {"relative_path": relative})]

    # liste le dossier Cours (recherche unique puis listing)
    match = re.fullmatch(
        r"\s*(?:liste|lister|affiche|afficher|montre|montrer)\s+(?:le\s+)?dossier\s+([^\\/]+?)\s*[.!?]?\s*",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        name = match.group(1).strip()
        if _safe_relative_path_syntax(name):
            return [make_action("list_directory_auto", "auto", {"directory_name": name})]
    return []


def parse_access_directory_natural(user_message):
    """
    Navigation naturelle dans les dossiers autorisés.

    Exemples :
        accède au dossier Jean dans Documents
        accede au dossier Jean dans Documents\\Cours
        va dans le dossier Jean dans Documents
        entre dans le dossier Jean
        accède à Documents\\Cours\\Jean
        ouvre le dossier Jean dans Documents
        montre-moi le dossier Jean dans Documents

    "Accéder" signifie ici : afficher le contenu du dossier dans
    AgentLocal. Aucun Explorateur Windows n'est lancé par cette action.
    """
    raw = str(user_message or "").strip().replace("’", "'")

    # --------------------------------------------------------
    # Dossier nommé + emplacement explicite
    # --------------------------------------------------------
    patterns_with_location = [
        r"\s*(?:acc[eè]de|acc[eè]der)\s+(?:au|a|à)\s+(?:le\s+)?dossier\s+(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
        r"\s*(?:va|aller|entre|entrer)\s+dans\s+(?:le\s+)?dossier\s+(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
        r"\s*(?:ouvre|ouvrir)\s+(?:le\s+)?dossier\s+(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
        r"\s*(?:montre(?:-moi|\s+moi)?|affiche(?:-moi|\s+moi)?)\s+(?:le\s+)?dossier\s+(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
        r"\s*(?:montre(?:-moi|\s+moi)?|affiche(?:-moi|\s+moi)?)\s+le\s+contenu\s+(?:de|du)\s+dossier\s+(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
    ]

    for pattern in patterns_with_location:
        match = re.fullmatch(pattern, raw, flags=re.IGNORECASE)
        if not match:
            continue

        folder = match.group(1).strip()
        root, parent = _parse_root_location(match.group(2))

        if not root or not _safe_relative_path_syntax(folder):
            return []

        relative = _join_relative(parent, folder)
        return [
            make_action(
                "list_directory",
                root,
                {"relative_path": relative},
            )
        ]

    # --------------------------------------------------------
    # Chemin complet relatif à une racine autorisée
    # Ex. "accède à Documents\\Cours\\Jean"
    # --------------------------------------------------------
    direct_patterns = [
        r"\s*(?:acc[eè]de|acc[eè]der)\s+(?:a|à|dans)\s+(.+?)\s*[.!?]?\s*",
        r"\s*(?:va|aller)\s+dans\s+(.+?)\s*[.!?]?\s*",
        r"\s*(?:entre|entrer)\s+dans\s+(.+?)\s*[.!?]?\s*",
    ]

    for pattern in direct_patterns:
        match = re.fullmatch(pattern, raw, flags=re.IGNORECASE)
        if not match:
            continue

        root, relative = _parse_root_location(match.group(1))
        if root and relative:
            return [
                make_action(
                    "list_directory",
                    root,
                    {"relative_path": relative},
                )
            ]

    # --------------------------------------------------------
    # Dossier sans emplacement : recherche récursive unique
    # --------------------------------------------------------
    patterns_auto = [
        r"\s*(?:acc[eè]de|acc[eè]der)\s+(?:au|a|à)\s+(?:le\s+)?dossier\s+([^\\/]+?)\s*[.!?]?\s*",
        r"\s*(?:va|aller|entre|entrer)\s+dans\s+(?:le\s+)?dossier\s+([^\\/]+?)\s*[.!?]?\s*",
        r"\s*(?:ouvre|ouvrir)\s+(?:le\s+)?dossier\s+([^\\/]+?)\s*[.!?]?\s*",
        r"\s*(?:montre(?:-moi|\s+moi)?|affiche(?:-moi|\s+moi)?)\s+(?:le\s+)?dossier\s+([^\\/]+?)\s*[.!?]?\s*",
    ]

    for pattern in patterns_auto:
        match = re.fullmatch(pattern, raw, flags=re.IGNORECASE)
        if not match:
            continue

        name = match.group(1).strip()
        if _safe_relative_path_syntax(name):
            return [
                make_action(
                    "list_directory_auto",
                    "auto",
                    {"directory_name": name},
                )
            ]

    return []


def parse_read_file_recursive(user_message):
    raw = user_message.strip()

    patterns = [
        r"\s*(?:lis|lire)\s+(?:(?:le|la)\s+fichier\s+)?(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
        r"\s*(?:affiche|afficher|montre|montrer)\s+le\s+contenu\s+(?:de|du)\s+(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
    ]
    for pattern in patterns:
        match = re.fullmatch(pattern, raw, flags=re.IGNORECASE)
        if not match:
            continue
        file_part = match.group(1).strip()
        root, parent = _parse_root_location(match.group(2))
        if root and _safe_relative_path_syntax(file_part):
            relative = _join_relative(parent, file_part)
            return _make_nested_file_action("read_file_content", root, relative)

    # lis Documents\Cours\rapport.docx
    match = re.fullmatch(
        r"\s*(?:lis|lire)\s+(?:(?:le|la)\s+fichier\s+)?(.+?)\s*[.!?]?\s*",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        value = match.group(1).strip()
        root, relative = _parse_root_location(value)
        if root and relative:
            return _make_nested_file_action("read_file_content", root, relative)
        if _safe_relative_path_syntax(value) and "\\" not in value and "/" not in value:
            return [make_action("read_file_auto", "auto", {"file_name": value})]
    return []


def parse_create_folder_recursive(user_message):
    raw = user_message.strip()
    match = re.fullmatch(
        r"\s*(?:crée|cree|créer|creer)\s+(?:(?:un|le)\s+)?dossier\s+(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
        raw,
        flags=re.IGNORECASE,
    )
    if not match:
        return []
    folder = match.group(1).strip()
    root, parent = _parse_root_location(match.group(2))
    if not root or not _safe_relative_path_syntax(folder):
        return []
    relative = _join_relative(parent, folder)
    if "\\" not in relative:
        return []  # la forme racine simple est déjà gérée par l'ancien parseur
    return [make_action("create_folder", root, {"name": relative})]


def parse_create_file_recursive(user_message):
    raw = user_message.strip().replace("’", "'")
    patterns = [
        r"\s*(?:crée|cree|créer|creer)\s+(?:(?:le|un)\s+fichier\s+)?(.+?)\s+dans\s+(.+?)\s+avec\s+le\s+contenu\s*:?[ \t]*(.+?)\s*",
        r"\s*(?:crée|cree|créer|creer)\s+(?:(?:le|un)\s+fichier\s+)?(.+?)\s+dans\s+(.+?)\s+contenant\s*:?[ \t]*(.+?)\s*",
    ]
    for pattern in patterns:
        match = re.fullmatch(pattern, raw, flags=re.IGNORECASE)
        if not match:
            continue
        file_part = match.group(1).strip()
        root, parent = _parse_root_location(match.group(2))
        content = match.group(3).strip()
        if root and _safe_relative_path_syntax(file_part):
            relative = _join_relative(parent, file_part)
            if "\\" in relative:
                return [make_action("create_file_with_content", root, {"file_name": relative, "content": content})]
    return []


def parse_modify_file_recursive(user_message):
    raw = user_message.strip().replace("’", "'")
    specs = [
        (
            "replace_content",
            r"\s*(?:remplace|remplacer)\s+le\s+contenu\s+(?:de|du)\s+(?:(?:le|la)\s+fichier\s+)?(.+?)\s+dans\s+(.+?)\s+par\s*:?[ \t]*(.+?)\s*",
        ),
        (
            "append_line",
            r"\s*(?:ajoute|ajouter)\s+une\s+ligne\s+[àa]\s+(?:(?:le|la)\s+fichier\s+)?(.+?)\s+dans\s+(.+?)\s+avec\s+le\s+contenu\s*:?[ \t]*(.+?)\s*",
        ),
        (
            "append_content",
            r"\s*(?:ajoute|ajouter)\s+(?:au|à|a)\s+fichier\s+(.+?)\s+dans\s+(.+?)\s+le\s+contenu\s*:?[ \t]*(.+?)\s*",
        ),
    ]
    for mode, pattern in specs:
        match = re.fullmatch(pattern, raw, flags=re.IGNORECASE)
        if not match:
            continue
        file_part = match.group(1).strip()
        root, parent = _parse_root_location(match.group(2))
        content = match.group(3).strip()
        if root and _safe_relative_path_syntax(file_part):
            relative = _join_relative(parent, file_part)
            if "\\" in relative:
                return [make_action("modify_file_content", root, {"file_name": relative, "content": content, "mode": mode})]
    return []


def parse_rename_file_recursive(user_message):
    raw = user_message.strip()
    match = re.fullmatch(
        r"\s*(?:renomme|renommer)\s+(?:(?:le|la)\s+fichier\s+)?(.+?)\s+en\s+(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
        raw,
        flags=re.IGNORECASE,
    )
    if not match:
        return []
    old_part = match.group(1).strip()
    new_name = match.group(2).strip()
    root, parent = _parse_root_location(match.group(3))
    if not root or not _safe_relative_path_syntax(old_part) or not _safe_relative_path_syntax(new_name):
        return []
    if "\\" in new_name or "/" in new_name:
        return []
    old_relative = _join_relative(parent, old_part)
    if "\\" not in old_relative:
        return []
    return [make_action("rename_file", root, {"old_name": old_relative, "new_name": new_name})]


def parse_delete_file_recursive(user_message):
    raw = user_message.strip()
    normalized = normalize_text(raw)
    if any(fragment in normalized for fragment in (
        "definitivement", "sans corbeille", "sans passer par la corbeille", "vide la corbeille", "vider la corbeille"
    )):
        return []

    match = re.fullmatch(
        r"\s*(?:supprime|supprimer)\s+(?:(?:le|la)\s+fichier\s+)?(.+?)\s+(?:dans|de|du|des)\s+(.+?)\s*[.!?]?\s*",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        file_part = match.group(1).strip()
        root, parent = _parse_root_location(match.group(2))
        if root and _safe_relative_path_syntax(file_part):
            relative = _join_relative(parent, file_part)
            return _make_nested_file_action("delete_file", root, relative)

    # supprime Documents\Cours\rapport.txt
    match = re.fullmatch(
        r"\s*(?:supprime|supprimer)\s+(?:(?:le|la)\s+fichier\s+)?(.+?)\s*[.!?]?\s*",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        value = match.group(1).strip()
        root, relative = _parse_root_location(value)
        if root and relative:
            return _make_nested_file_action("delete_file", root, relative)
        if _safe_relative_path_syntax(value) and "\\" not in value and "/" not in value:
            return [make_action("delete_file_auto", "auto", {"file_name": value})]
    return []


def _parse_transfer_recursive(user_message, verb_pattern, action_between, action_within):
    raw = user_message.strip()

    # Forme : copie rapport.pdf de Documents\Cours vers Bureau\Archives
    match = re.fullmatch(
        r"\s*(?:" + verb_pattern + r")\s+(?:(?:le|la)\s+fichier\s+)?(.+?)\s+(?:de|du|des)\s+(.+?)\s+(?:vers|dans)\s+(.+?)\s*[.!?]?\s*",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        file_part = match.group(1).strip()
        source_root, source_parent = _parse_root_location(match.group(2))
        destination_root, destination_folder = _parse_root_location(match.group(3))
        if source_root and destination_root and _safe_relative_path_syntax(file_part):
            source_relative = _join_relative(source_parent, file_part)
            if source_root == destination_root:
                if action_within and destination_folder:
                    return [make_action(action_within, source_root, {
                        "file_name": source_relative,
                        "destination_folder": destination_folder,
                    })]
                return []
            return [make_action(action_between, source_root, {
                "source_root": source_root,
                "destination_root": destination_root,
                "file_name": source_relative,
                "destination_folder": destination_folder or None,
            })]

    # Forme : copie Documents\Cours\rapport.pdf vers Bureau\Archives
    match = re.fullmatch(
        r"\s*(?:" + verb_pattern + r")\s+(.+?)\s+(?:vers|dans)\s+(.+?)\s*[.!?]?\s*",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        source_root, source_relative = _parse_root_location(match.group(1))
        destination_root, destination_folder = _parse_root_location(match.group(2))
        if source_root and source_relative and destination_root:
            if source_root == destination_root:
                if action_within and destination_folder:
                    return [make_action(action_within, source_root, {
                        "file_name": source_relative,
                        "destination_folder": destination_folder,
                    })]
                return []
            return [make_action(action_between, source_root, {
                "source_root": source_root,
                "destination_root": destination_root,
                "file_name": source_relative,
                "destination_folder": destination_folder or None,
            })]
    return []


def parse_copy_file_recursive(user_message):
    return _parse_transfer_recursive(
        user_message,
        r"copie|copier",
        "copy_file_between_roots",
        None,
    )


def parse_move_file_recursive(user_message):
    return _parse_transfer_recursive(
        user_message,
        r"déplace|deplace|déplacer|deplacer",
        "move_file_between_roots",
        "move_file_within_root",
    )



# ============================================================
# OUVERTURE CONTROLEE DE DOSSIERS ET FICHIERS
# ============================================================

_OPENABLE_FILE_EXTENSIONS = {
    ".docx", ".odt", ".xlsx", ".ods", ".pptx", ".odp",
    ".pdf", ".html", ".htm",
    ".txt", ".md", ".csv", ".tsv", ".json", ".xml",
    ".yaml", ".yml", ".log", ".ini", ".cfg", ".conf",
    ".toml", ".ics", ".vcf", ".rtf", ".eml",
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp",
    ".tif", ".tiff",
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v",
    ".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma",
}


def _looks_like_openable_file(value):
    if not isinstance(value, str):
        return False
    value = value.strip()
    if not _safe_relative_path_syntax(value):
        return False
    suffix = Path(value.replace("\\", "/")).suffix.lower()
    return suffix in _OPENABLE_FILE_EXTENSIONS


def _reserved_non_file_open_target(value):
    """Evite que "ouvre Edge" ou "ouvre GitHub" devienne une recherche de fichier."""
    if not isinstance(value, str):
        return True

    value = value.strip()
    if not value or "\\" in value or "/" in value:
        return False

    normalized = normalize_text(value)
    # Une formule de politesse en fin de commande ne transforme pas une
    # application/site connu en faux nom de fichier (ex. « google stp »).
    clean_value = re.sub(r"\s+(?:stp|svp|merci)$", "", normalized).strip()
    if normalize_application_target(clean_value):
        return True
    if clean_value in WEBSITE_ALIASES:
        return True
    if clean_value in load_site_names():
        return True
    if clean_value in load_routine_triggers():
        return True
    if re.fullmatch(r"[a-z0-9][a-z0-9.-]*\.[a-z]{2,63}", clean_value):
        return True
    return False


def _looks_like_file_reference(value, explicit_file_context=False):
    """
    Accepte un fichier nomme sans extension ou avec seulement une partie du nom.
    La resolution reelle et l'unicite sont verifiees dans recursive_file_tools.py.
    """
    if not isinstance(value, str):
        return False

    value = value.strip()
    if not _safe_relative_path_syntax(value):
        return False

    leaf = value.replace("/", "\\").split("\\")[-1].strip()
    if not leaf:
        return False

    suffix = Path(leaf).suffix.lower()
    hard_blocked = {
        ".exe", ".com", ".bat", ".cmd", ".ps1", ".psm1", ".vbs", ".vbe",
        ".js", ".jse", ".wsf", ".wsh", ".scr", ".msi", ".msp", ".msc",
        ".cpl", ".dll", ".sys", ".reg", ".lnk", ".url", ".hta", ".jar",
    }
    if suffix in hard_blocked:
        return False

    if not explicit_file_context and _reserved_non_file_open_target(value):
        return False

    # Une extension autorisee reste le cas le plus precis. Sans extension,
    # le moteur de recherche fera une resolution unique par nom ou fragment.
    if suffix in _OPENABLE_FILE_EXTENSIONS:
        return True

    return bool(leaf)


def parse_open_directory_natural(user_message):
    """Parses manual requests that mean opening a folder in Explorer."""
    raw = str(user_message or "").strip().replace("\u2019", "'")

    # Named folder inside an explicitly allowed root/path.
    patterns_with_location = [
        r"\s*(?:ouvre|ouvrir)\s+(?:le\s+)?dossier\s+(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
        r"\s*(?:acc(?:e|\u00e8)de|acc(?:e|\u00e8)der)\s+(?:au|a|\u00e0)\s+(?:le\s+)?dossier\s+(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
        r"\s*(?:va|aller|entre|entrer)\s+dans\s+(?:le\s+)?dossier\s+(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
    ]

    for pattern in patterns_with_location:
        match = re.fullmatch(pattern, raw, flags=re.IGNORECASE)
        if not match:
            continue
        folder = match.group(1).strip()
        root, parent = _parse_root_location(match.group(2))
        if not root or not _safe_relative_path_syntax(folder):
            return []
        relative = _join_relative(parent, folder)
        return [make_action("open_directory", root, {"relative_path": relative})]

    # Explicit allowed-root path.
    direct_patterns = [
        r"\s*(?:ouvre|ouvrir)\s+(?:le\s+)?dossier\s+(.+?)\s*[.!?]?\s*",
        r"\s*(?:acc(?:e|\u00e8)de|acc(?:e|\u00e8)der)\s+(?:a|\u00e0|dans)\s+(.+?)\s*[.!?]?\s*",
        r"\s*(?:va|aller|entre|entrer)\s+dans\s+(.+?)\s*[.!?]?\s*",
    ]

    for pattern in direct_patterns:
        match = re.fullmatch(pattern, raw, flags=re.IGNORECASE)
        if not match:
            continue
        value = match.group(1).strip()
        root, relative = _parse_root_location(value)
        if root:
            return [make_action("open_directory", root, {"relative_path": relative or ""})]

    # Folder name without location: unique recursive discovery is required.
    auto_patterns = [
        r"\s*(?:ouvre|ouvrir)\s+(?:le\s+)?dossier\s+([^\\/]+?)\s*[.!?]?\s*",
        r"\s*(?:acc(?:e|\u00e8)de|acc(?:e|\u00e8)der)\s+(?:au|a|\u00e0)\s+(?:le\s+)?dossier\s+([^\\/]+?)\s*[.!?]?\s*",
        r"\s*(?:va|aller|entre|entrer)\s+dans\s+(?:le\s+)?dossier\s+([^\\/]+?)\s*[.!?]?\s*",
    ]

    for pattern in auto_patterns:
        match = re.fullmatch(pattern, raw, flags=re.IGNORECASE)
        if not match:
            continue
        name = match.group(1).strip()
        if _safe_relative_path_syntax(name) and "\\" not in name and "/" not in name:
            return [make_action("open_directory_auto", "auto", {"directory_name": name})]

    return []


def parse_open_file_natural(user_message):
    """Parses controlled file-opening requests without arbitrary associations."""
    raw = str(user_message or "").strip().replace("\u2019", "'")

    # File/document named inside an explicitly allowed root/path.
    patterns_with_location = [
        r"\s*(?:ouvre|ouvrir)\s+(?:(?:le|la)\s+)?(?:fichier|document)\s+(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
        r"\s*(?:acc(?:e|\u00e8)de|acc(?:e|\u00e8)der)\s+(?:au|a|\u00e0)\s+(?:(?:le|la)\s+)?(?:fichier|document)\s+(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
        r"\s*(?:ouvre|ouvrir)\s+(.+?)\s+dans\s+(.+?)\s*[.!?]?\s*",
    ]

    for pattern in patterns_with_location:
        match = re.fullmatch(pattern, raw, flags=re.IGNORECASE)
        if not match:
            continue
        file_part = match.group(1).strip()
        root, parent = _parse_root_location(match.group(2))
        if not root or not _looks_like_file_reference(file_part, explicit_file_context=True):
            continue
        relative = _join_relative(parent, file_part)
        return [make_action("open_file", root, {"file_name": relative})]

    # Explicit allowed-root file path.
    match = re.fullmatch(
        r"\s*(?:ouvre|ouvrir)\s+(.+?)\s*[.!?]?\s*",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        value = match.group(1).strip()
        root, relative = _parse_root_location(value)
        if root and relative and _looks_like_file_reference(relative, explicit_file_context=True):
            return [make_action("open_file", root, {"file_name": relative})]

    # Explicit file/document keyword without location.
    match = re.fullmatch(
        r"\s*(?:ouvre|ouvrir|acc(?:e|\u00e8)de|acc(?:e|\u00e8)der)\s+(?:(?:au|a|\u00e0)\s+)?(?:(?:le|la)\s+)?(?:fichier|document)\s+([^\\/]+?)\s*[.!?]?\s*",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        name = match.group(1).strip()
        if _looks_like_file_reference(name, explicit_file_context=True) and "\\" not in name and "/" not in name:
            return [make_action("open_file_auto", "auto", {"file_name": name})]

    # Natural short form: "ouvre rapport.pdf". Only known safe extensions
    # are accepted so commands such as "ouvre Edge" keep their old meaning.
    match = re.fullmatch(
        r"\s*(?:ouvre|ouvrir)\s+([^\\/]+?)\s*[.!?]?\s*",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        name = match.group(1).strip()
        if _looks_like_functional_app_request(name):
            return []
        if _looks_like_forbidden_execution_target(name):
            return []
        if _contains_forbidden_execution_target(name):
            return []
        if _looks_like_known_multi_target_request(name):
            return []
        if normalize_text(name) in SAFE_NATURAL_TARGET_TYPOS:
            return []
        if _looks_like_file_reference(name, explicit_file_context=False):
            return [make_action("open_file_auto", "auto", {"file_name": name})]

    return []

def parse_recursive_filesystem_command(user_message):
    parsers = (
        parse_open_directory_natural,
        parse_open_file_natural,
        parse_access_directory_natural,
        parse_find_filesystem_item_recursive,
        parse_list_directory_recursive,
        parse_read_file_recursive,
        parse_create_folder_recursive,
        parse_create_file_recursive,
        parse_modify_file_recursive,
        parse_rename_file_recursive,
        parse_delete_file_recursive,
        parse_copy_file_recursive,
        parse_move_file_recursive,
    )
    for parser in parsers:
        actions = parser(user_message)
        if actions:
            return actions
    return []


# Conserve toute l'interprétation historique, puis ajoute le nouveau
# langage de chemins uniquement si l'ancienne logique n'a rien compris.
_interpret_before_recursive_access = interpret


def _result_has_vague_filesystem_reference(result):
    if not isinstance(result, dict):
        return False
    actions = result.get("actions", [])
    if not isinstance(actions, list):
        return False

    file_actions = {
        "find_filesystem_item",
        "list_directory_auto",
        "create_folder",
        "create_file_with_content",
        "modify_file_content",
        "move_file_within_root",
        "move_file_between_roots",
        "copy_file_between_roots",
        "rename_file",
        "rename_file_auto",
        "delete_file",
        "delete_file_auto",
        "read_file_content",
        "read_file_auto",
        "open_directory_auto",
        "open_file",
        "open_file_auto",
    }
    candidate_fields = {
        "name",
        "file_name",
        "old_name",
        "directory_name",
        "destination_folder",
    }
    for action in actions:
        if not isinstance(action, dict):
            continue
        if str(action.get("action", "")).strip().lower() not in file_actions:
            continue
        params = action.get("params", {})
        if not isinstance(params, dict):
            continue
        for field in candidate_fields:
            value = params.get(field)
            if isinstance(value, str) and is_vague_filesystem_reference(value):
                return True
    return False


def _as_unrecognized_result(result):
    if isinstance(result, dict):
        safe = dict(result)
        safe["understood"] = False
        safe["actions"] = []
        safe.pop("natural_language", None)
        safe.pop("interpreted_as", None)
        return safe
    return {
        "schema_version": SCHEMA_VERSION,
        "backend": "deterministic",
        "understood": False,
        "actions": [],
    }




# ============================================================
# ACTIONS LOCALES V1 - ACCÈS CONTRÔLÉ
# ============================================================

def _normalize_root_for_controlled_action(value):
    normalized = normalize_text(value).strip(" .!?")
    normalized = re.sub(r"^(?:mes|mon|ma|le|la|les)\s+", "", normalized)
    return FILE_ROOT_ALIASES.get(normalized)


def parse_controlled_local_command(user_message):
    """Parse uniquement des intentions fermées et explicitement demandées."""
    raw = str(user_message or "").strip().replace("’", "'")
    text = normalize_text(raw).strip(" .!?")
    if not text:
        return []
    plain = re.sub(r"[-]+", " ", text)
    plain = re.sub(r"\s+", " ", plain).strip()

    # --------------------------------------------------------
    # Informations système en lecture seule
    # --------------------------------------------------------
    system_patterns = (
        ("memory", (
            r"(?:j'utilise|j utilise) combien de ram",
            r"combien de ram (?:j'utilise|j utilise)",
            r"(?:mon )?pc utilise combien de ram",
            r"(?:regarde|dis moi|montre) (?:un peu )?combien de ram (?:j'utilise|j utilise)",
            r"(?:la )?ram (?:la )?ca (?:prend|utilise) combien",
            r"(?:montre|donne moi|affiche) (?:l'utilisation|l utilisation|l'etat|l etat) (?:de )?(?:la )?(?:ram|memoire vive)",
            r"(?:utilisation|etat) (?:de )?(?:la )?(?:ram|memoire vive)",
            r"(?:ma )?ram (?:est )?(?:utilisee|utilise) a combien",
        )),
        ("disk", (
            r"(?:il reste|il me reste|j'ai|j ai) combien (?:d'espace|d espace) (?:sur )?(?:mon )?disque(?: c)?",
            r"(?:mon )?disque (?:la )?(?:il )?reste combien",
            r"(?:regarde|dis moi|montre) (?:un peu )?combien (?:d'espace|d espace) (?:il )?reste (?:sur )?(?:mon )?disque(?: c)?",
            r"combien (?:d'espace|d espace) (?:il )?reste (?:sur )?(?:mon )?disque(?: c)?",
            r"(?:montre|donne moi|affiche) (?:l'espace|l espace) (?:libre )?(?:sur )?(?:mon )?disque(?: c)?",
            r"(?:espace disque|espace libre(?: sur)?(?: le)? disque(?: c)?)",
        )),
        ("cpu", (
            r"(?:mon )?(?:cpu|processeur) (?:travaille|tourne|est utilise) a combien",
            r"(?:le )?(?:cpu|processeur) (?:la )?ca tourne a combien",
            r"(?:regarde|dis moi|montre) (?:un peu )?(?:l'utilisation|l utilisation) (?:du )?(?:cpu|processeur)",
            r"(?:montre|donne moi|affiche) (?:l'utilisation|l utilisation) (?:du )?(?:cpu|processeur)",
            r"(?:utilisation|etat) (?:du )?(?:cpu|processeur)",
        )),
        ("uptime", (
            r"depuis combien de temps (?:le |mon )?pc est allume",
            r"(?:le |mon )?pc est allume depuis quand",
            r"(?:le |mon )?pc est allume depuis combien de temps",
            r"(?:temps de fonctionnement|temps depuis le demarrage|uptime)(?: du pc)?",
        )),
        ("summary", (
            r"(?:montre|donne moi|affiche)?\s*(?:l'etat|l etat|les infos|les informations) (?:de )?(?:mon |du )?(?:pc|systeme)",
            r"(?:etat|infos|informations) systeme",
            r"comment va (?:mon )?pc",
        )),
    )
    for query, patterns in system_patterns:
        if any(re.fullmatch(pattern, plain) for pattern in patterns):
            return [make_action("read_system_info", query)]

    # --------------------------------------------------------
    # Presse-papiers texte
    # --------------------------------------------------------
    if text in {
        "qu'est ce que j'ai copie", "qu'est-ce que j'ai copie", "j'ai copie quoi",
        "montre moi ce que j'ai copie", "montre ce que j'ai copie",
        "affiche ce que j'ai copie", "dis moi ce que j'ai copie", "dis ce que j'ai copie",
        "j'ai copie quoi la",
        "lis le presse papiers", "lis le presse-papiers", "montre le presse papiers",
        "montre le presse-papiers", "affiche le presse papiers", "affiche le presse-papiers",
        "contenu du presse papiers", "contenu du presse-papiers",
    }:
        return [make_action("read_clipboard", "clipboard")]

    clipboard_patterns = (
        r"^(?:copie|copier)\s+(?:ce|le)\s+texte\s*:\s*(.+)$",
        r"^(?:copie|copier|mets|met)\s+dans\s+le\s+presse[- ]papiers\s*:\s*(.+)$",
    )
    for pattern in clipboard_patterns:
        match = re.fullmatch(pattern, raw, flags=re.IGNORECASE | re.DOTALL)
        if match:
            content = match.group(1)
            if content:
                return [make_action("write_clipboard", "clipboard", {"text": content})]

    # Copie contrôlée du chemin d'un fichier dans une racine nommée.
    match = re.fullmatch(
        r"(?:copie|copier)\s+le\s+chemin\s+(?:du\s+fichier\s+|de\s+)?(.+?)\s+dans\s+"
        r"(?:(?:mes|mon|ma|le|la|les)\s+)?"
        r"(bureau|documents?|t[eé]l[eé]chargements?|downloads?|images?|photos?|vid[eé]os?|musique)",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        root = _normalize_root_for_controlled_action(match.group(2))
        file_name = match.group(1).strip()
        if root and file_name and not is_vague_filesystem_reference(file_name):
            return [make_action("copy_file_path", root, {"file_name": file_name})]

    # --------------------------------------------------------
    # Onglets Edge via pont local existant
    # --------------------------------------------------------
    if text in {
        "liste mes onglets", "liste les onglets", "montre mes onglets", "montre les onglets",
        "affiche mes onglets", "affiche les onglets", "montre mes onglets edge",
        "montre les onglets edge", "quels onglets sont ouverts",
        "quels sont mes onglets", "y a quoi comme onglets", "il y a quoi comme onglets",
        "y a quoi d'ouvert dans edge", "il y a quoi d'ouvert dans edge",
    }:
        return [make_action("list_browser_tabs", "edge")]

    match = re.fullmatch(
        r"(?:passe|passer|va|aller|active|activer|mets|met)\s+(?:sur\s+)?(?:l'onglet|l onglet|onglet)\s+(.+)",
        text,
    )
    if match:
        site = match.group(1).strip()
        if site and site not in {"ca", "cela", "ceci", "le", "la", "lui"}:
            return [make_action("activate_browser_tab", site)]

    # --------------------------------------------------------
    # Référence conversationnelle temporaire
    # --------------------------------------------------------
    pronoun = text.replace("-", " ")
    pronoun = re.sub(r"\s+(?:la|hein|meme|ou bien|un peu)$", "", pronoun).strip()
    pronoun = re.sub(r"\s+", " ", pronoun).strip()
    if pronoun in {"ouvre le", "ouvre lui", "ouvre celui la", "ouvre celui ci"}:
        return [make_action("open_last_reference", "session")]
    if pronoun in {"lis le", "lis lui", "lis celui la", "lis celui ci"}:
        return [make_action("read_last_reference", "session")]
    if pronoun in {
        "copie son chemin", "copie le chemin de celui la", "copie le chemin de celui ci",
        "copie le chemin du dernier", "copie le chemin du fichier precedent",
    }:
        return [make_action("copy_last_reference_path", "session")]

    return []


def _interpret_strict_message(user_message):
    """Interprete une phrase sans reformulation conversationnelle."""

    habit_actions = parse_habit_command(user_message)
    if habit_actions:
        return {
            "schema_version": SCHEMA_VERSION,
            "backend": "deterministic",
            "understood": True,
            "actions": habit_actions,
        }

    actions = parse_controlled_local_command(user_message)
    if actions:
        return {
            "schema_version": SCHEMA_VERSION,
            "backend": "deterministic",
            "understood": True,
            "actions": actions,
        }

    actions = parse_recursive_filesystem_command(user_message)
    if actions:
        return {
            "schema_version": SCHEMA_VERSION,
            "backend": "deterministic",
            "understood": True,
            "actions": actions,
        }

    return _interpret_before_recursive_access(user_message)


def parse_local_conversation(user_message):
    """Petites reponses locales pour rendre l'interface moins robotique."""
    text = normalize_text(_strip_spoken_ivoirian_fillers(user_message)).strip(" .!?")
    text = re.sub(r"^(arrange|organise|range|reorganise)\s+un\s+peu\s+", r"\1 ", text)
    if not text:
        return None

    if text in {"bonjour", "salut", "coucou", "hello", "bonsoir"}:
        return "Bonjour ! Que puis-je faire pour toi ?"

    if text in {"merci", "merci beaucoup", "super merci", "parfait merci"}:
        return "Avec plaisir."

    if text in {"ok", "okay", "d'accord", "dac", "ca marche", "c'est bon"}:
        return "D'accord."

    if text in {"ca va", "comment ca va", "tu vas bien", "ca va agentlocal"}:
        return "Oui, tout va bien. Que veux-tu faire ?"

    if text in {"c'est comment", "c est comment", "ca dit quoi"}:
        return "Ca va. Que veux-tu faire ?"

    if text in {"on est ensemble", "ya pas drap", "y a pas drap"}:
        return "D'accord, on est ensemble."

    if text in {
        "arrange mes fenetres", "arrange les fenetres", "organise mes fenetres",
        "organise les fenetres", "range mes fenetres", "reorganise mes fenetres",
        "mets mes fenetres bien", "mets mes fenetres correctement",
        "organise mon ecran", "arrange mon ecran",
    }:
        return (
            "Je peux organiser les fenêtres, mais je ne choisis pas la disposition à ta place. "
            "Indique les applications et leur position, par exemple : « mets VS Code à gauche "
            "et Edge à droite »."
        )

    if text in {
        "aide", "help", "aide moi", "aide-moi", "que peux tu faire",
        "que peux-tu faire", "tu peux faire quoi", "qu'est ce que tu peux faire",
        "qu'est-ce que tu peux faire", "qu'est ce que tu sais faire", "tu sais faire quoi",
    }:
        return (
            "Je peux ouvrir ou fermer les applications et sites autorisés, lancer tes routines, "
            "vérifier une application, gérer explicitement une fenêtre autorisée, consulter en "
            "lecture seule la RAM, le CPU, le disque et le temps de fonctionnement du PC, lire "
            "ou écrire du texte dans le presse-papiers sur demande, lister ou activer un onglet "
            "Edge via le pont local, et travailler de façon contrôlée dans Bureau, Documents, "
            "Téléchargements, Images, Vidéos et Musique. Je peux aussi retenir temporairement "
            "un fichier trouvé pour comprendre ensuite « ouvre-le » ou « lis-le »."
        )

    if text in {"qui es tu", "qui es-tu", "c'est quoi agentlocal", "tu es qui"}:
        return (
            "Je suis AgentLocal, ton agent local sur ce PC. Je fonctionne avec des actions "
            "autorisées à l'avance et je n'exécute pas de commande système arbitraire."
        )

    return None


def _is_clipboard_execution_request(text):
    """Refuse l'exécution/ouverture automatique de ce qui est dans le presse-papiers."""
    value = normalize_text(text).replace("-", " ").strip(" .!?")
    value = re.sub(r"\s+", " ", value)
    if "presse papiers" not in value and "ce que j'ai copie" not in value and "ce que j ai copie" not in value:
        return False
    return bool(re.search(
        r"\b(?:ouvre|ouvrir|lance|lancer|execute|executer|demarre|demarrer|va sur|navigue vers)\b",
        value,
    ))


def interpret(user_message):
    # Une formule de politesse finale est retiree avant l'analyse stricte.
    # Cela evite qu'un « stp » ou « s'il te plait » soit pris pour une partie
    # d'un nom de fichier. Le contenu litteral des commandes d'ecriture reste
    # toujours intact.
    original_message = str(user_message or "").strip()

    if _is_clipboard_execution_request(original_message):
        return {
            "schema_version": SCHEMA_VERSION,
            "backend": "deterministic",
            "understood": True,
            "actions": [],
            "reply": (
                "Je peux lire ou écrire du texte dans le presse-papiers sur demande, "
                "mais je n'exécute et je n'ouvre jamais automatiquement son contenu."
            ),
            "conversation": True,
        }

    # Une negation explicite, y compris la forme orale "ouvre pas ..." ou
    # "faut pas ...", ne doit jamais devenir une action ni etre deleguee au LLM.
    if _is_explicit_negative_request(original_message):
        return {
            "schema_version": SCHEMA_VERSION,
            "backend": "deterministic",
            "understood": True,
            "actions": [],
            "reply": "D'accord, je ne fais rien.",
            "conversation": True,
        }

    if _is_explicit_forbidden_execution_request(original_message):
        return {
            "schema_version": SCHEMA_VERSION,
            "backend": "deterministic",
            "understood": True,
            "actions": [],
            "reply": (
                "Cette cible d'execution est interdite par les regles de securite d'AgentLocal."
            ),
            "conversation": True,
        }

    if _is_ambiguous_spoken_destructive_request(original_message):
        return {
            "schema_version": SCHEMA_VERSION,
            "backend": "deterministic",
            "understood": True,
            "actions": [],
            "reply": (
                "Je pr\u00e9f\u00e8re une formulation pr\u00e9cise pour cette action sur un fichier. "
                "Indique clairement le nom et la destination sans terme ambigu en fin de phrase."
            ),
            "conversation": True,
        }

    courtesy_cleaned = _strip_natural_trailing_politeness(original_message)
    strict_message = courtesy_cleaned if courtesy_cleaned else original_message
    courtesy_was_removed = bool(courtesy_cleaned and courtesy_cleaned != original_message)

    spoken_cleaned = _strip_spoken_ivoirian_fillers(strict_message)
    spoken_was_removed = bool(
        spoken_cleaned
        and spoken_cleaned != strict_message
        and _looks_like_spoken_safe_context(strict_message)
    )
    if spoken_was_removed:
        strict_message = spoken_cleaned

    if _looks_like_spoken_safe_context(strict_message) and re.match(
        r"^(?:ouvre|ouvrir|lance|lancer|ferme|fermer|cherche|chercher|trouve|trouver|retrouve|retrouver|montre|montrer|affiche|afficher)\s+moi\b",
        normalize_text(strict_message),
    ):
        direct_rewrite = _rewrite_natural_command_start(strict_message)
        if direct_rewrite != strict_message:
            strict_message = direct_rewrite
            spoken_was_removed = True

    # La phrase nettoyee (ou l'original si aucun suffixe de politesse) reste
    # prioritaire : compatibilite avec les commandes deja validees.
    result = _interpret_strict_message(strict_message)
    if isinstance(result, dict) and result.get("understood"):
        if not _result_has_vague_filesystem_reference(result):
            if courtesy_was_removed or spoken_was_removed:
                result = dict(result)
                result["natural_language"] = True
                result["interpreted_as"] = strict_message
            return result
        result = _as_unrecognized_result(result)

    # Le langage naturel est un secours local. Chaque variante repasse par
    # exactement les memes parseurs et permissions que la commande stricte.
    for candidate in build_natural_command_variants(strict_message):
        natural_result = _interpret_strict_message(candidate)
        if isinstance(natural_result, dict) and natural_result.get("understood"):
            if _result_has_vague_filesystem_reference(natural_result):
                continue
            natural_result = dict(natural_result)
            natural_result["natural_language"] = True
            natural_result["interpreted_as"] = candidate
            return natural_result

    reply = parse_local_conversation(strict_message)
    if reply:
        return {
            "schema_version": SCHEMA_VERSION,
            "backend": "deterministic",
            "understood": True,
            "actions": [],
            "reply": reply,
            "conversation": True,
        }

    return result

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
            "ferme",
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