"""V12.5.2: parseur prudent de demandes en plusieurs etapes.

Aucune execution ici. Une sequence n'est reconnue que si chaque etape porte
son propre verbe explicite. Les fragments entre guillemets sont preserves.
"""
from __future__ import annotations

import re
import threading
from copy import deepcopy

MAX_STEPS = 4
MAX_MESSAGE_LENGTH = 900

# Seuls les delimitateurs explicites sont retenus. "et" seul reste confie
# a l'ancien moteur pour ne pas modifier ses comportements.
# Un connecteur incomplet en fin de phrase doit etre reconnu et refuse
# AVANT le passage au parseur historique (qui pourrait executer un prefixe).
# Ex.: "ouvre Word puis" ou "ouvre Word et après".
_DELIMITER = re.compile(
    r"\s+(?:(?:et\s+)?puis|ensuite|et\s+apr[eè]s)(?=[\s,.!?;:]|$)\s*|\s*;\s*",
    re.I,
)
_VERB = re.compile(
    r"(?:ouvre|ouvrir|lance|lancer|affiche|afficher|montre|montrer|"
    r"liste|lister|cherche|chercher|trouve|trouver|v[eé]rifie|v[eé]rifier|"
    r"regarde|regarder|donne|donner|consulte|consulter|"
    r"passe|passer|active|activer|mets|mettre|"
    r"ferme|fermer|lis|lire|quel|quelle|quels|quelles|"
    r"combien|est[- ]ce|peux[- ]tu|pourrais[- ]tu)\b",
    re.I,
)
# Ne jamais decomposer une saisie dont le sens est du texte libre.
_FREE_TEXT = re.compile(r"\b(?:avec\s+le\s+contenu|ajoute\s+le\s+texte|ecris\s+le\s+texte|texte\s*:)\b", re.I)
_lock = threading.RLock()
_last_sequence = None


def _outside_quotes_mask(text: str) -> str:
    """Masque les citations typographiques ou doubles sans modifier les offsets."""
    masked = []
    quote = None
    for char in text:
        if quote:
            masked.append(" " if char != "\n" else "\n")
            if char == quote:
                quote = None
        elif char in {'"', '«', '“'}:
            quote = {'"': '"', '«': '»', '“': '”'}[char]
            masked.append(" ")
        else:
            masked.append(char)
    return "".join(masked)


def split_explicit_sequence(message: object):
    """Renvoie (etapes, erreur). None signifie commande simple inchangee.

    Une sequence suspecte est refusee sans jamais executer la premiere etape.
    """
    if not isinstance(message, str) or not message.strip():
        return None, None
    if len(message) > MAX_MESSAGE_LENGTH:
        if _DELIMITER.search(_outside_quotes_mask(message)):
            return None, "Demande trop longue pour une sequence : decoupe-la en plusieurs messages."
        return None, None

    masked = _outside_quotes_mask(message)
    matches = list(_DELIMITER.finditer(masked))
    if not matches:
        return None, None

    # On interdit les transformations de texte libre, meme si un verbe suit
    # "puis" : le sens pourrait etre une citation, pas une seconde action.
    if _FREE_TEXT.search(masked):
        return None, None

    # Tous les delimiteurs non cites doivent correspondre a une commande.
    # Sinon, l'instruction complete est refusee, au lieu de laisser l'ancien
    # parseur executer accidentellement la premiere sous-commande.
    starts = [0]
    ends = []
    for match in matches:
        tail = masked[match.end():].lstrip(" \t\r\n,.!?:")
        if not _VERB.match(tail):
            return None, (
                "Une etape apres un connecteur est incomplete. "
                "Repete le verbe, par exemple : ouvre Word puis ouvre Excel."
            )
        ends.append(match.start())
        starts.append(match.end())

    ends.append(len(message))
    segments = [message[start:end].strip(" \t\r\n,.!?;:") for start, end in zip(starts, ends)]

    if len(segments) > MAX_STEPS:
        return None, f"Maximum {MAX_STEPS} etapes par demande. Reformule en plusieurs demandes."
    if any(not segment for segment in segments):
        return None, "Une etape de ta demande est vide. Aucune action lancee."
    if any(not _VERB.match(segment) for segment in segments):
        return None, "Chaque etape doit commencer par une action explicite. Aucune action lancee."
    return segments, None


def remember_sequence(steps, outcomes, completed):
    """Historique ephemere, sans stockage sur disque ni contenu de fichiers."""
    global _last_sequence
    record = {
        "steps": [str(x)[:180] for x in steps][:MAX_STEPS],
        "outcomes": [bool(x) for x in outcomes][:MAX_STEPS],
        "completed": bool(completed),
    }
    with _lock:
        _last_sequence = record


def get_last_sequence():
    with _lock:
        return deepcopy(_last_sequence)


def describe_last_sequence():
    record = get_last_sequence()
    if not record:
        return "Aucune demande en plusieurs etapes n'a encore ete executee pendant cette session."
    lines = ["Derniere demande en plusieurs etapes :"]
    for index, step in enumerate(record["steps"]):
        if index >= len(record["outcomes"]):
            state = "non executee"
        else:
            state = "reussie" if record["outcomes"][index] else "en echec"
        lines.append(f"{index + 1}. {step} : {state}")
    return "\n".join(lines)
