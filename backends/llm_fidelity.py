"""Garde-fou V12.5.4: fidelite minimale des reformulations du LLM.

Ce module n'execute aucune commande. Le moteur deterministe continue de
valider les actions; cette couche refuse seulement certaines transformations
manifestement incompatibles avec la demande originale.
"""
from __future__ import annotations

import math
import re
import unicodedata

# Liste volontairement courte: cibles dont le nom est explicite. Une cible
# generique comme «mon navigateur» peut toujours etre reformulee en «Edge».
_NAMES = {
    "visual studio code": "vscode", "vs code": "vscode", "vscode": "vscode",
    "bloc-notes": "notepad", "bloc notes": "notepad", "notepad": "notepad",
    "powerpoint": "powerpoint", "word": "word", "excel": "excel",
    "firefox": "firefox", "chrome": "chrome", "edge": "edge",
    "teams": "teams", "outlook": "outlook", "github": "github",
    "whatsapp": "whatsapp", "youtube": "youtube", "chatgpt": "chatgpt",
    "onedrive": "onedrive", "descript": "descript",
}
_NAMES_RX = re.compile(r"(?<!\w)(" + "|".join(re.escape(k) for k in sorted(_NAMES, key=len, reverse=True)) + r")(?!\w)", re.I)
_NEGATION_RX = re.compile(
    r"\b(?:ne|n['’])\s*\w+(?:\s+\w+){0,5}\s+(?:pas|jamais|plus)\b"
    r"|\b(?:faut\s+pas|il\s+ne\s+faut\s+pas|surtout\s+pas|ne\s+pas|n['’]ouvre\s+pas|sans\s+(?:ouvrir|lancer|fermer|supprimer|effacer|deplacer))\b"
    r"|\b(?:ouvre|lance|ferme|supprime|efface|deplace|copie|renomme|veux|veut|souhaite|dois|doit)\s+pas\b"
    r"|\bpas\s+(?:besoin|la\s+peine)\b",
    re.I,
)
# Negations explicites en anglais et espagnol. Les refuser avant qu'un LLM
# ne puisse les convertir accidentellement en commandes positives.
_NEGATION_MULTILINGUAL_RX = re.compile(
    r"\b(?:do\s+not|don['’]?t|never|dont)\b.{0,90}\b(?:open|launch|start|run|close|delete|remove|copy|move|rename)\b"
    r"|\bwithout\s+(?:opening|launching|starting|running|closing|deleting|removing|copying|moving|renaming)\b"
    r"|\b(?:no|nunca)\b.{0,90}\b(?:abras|abrir|abres|cierres|cerrar|borres|borrar|ejecutes|ejecutar|lances|lanzar|iniciar|copiar|copies|muevas|mover|renombrar)\b",
    re.I,
)

# Ressources explicites que l'IA ne doit ni inventer ni remplacer.
_FILENAME_RX = re.compile(r"(?<![\w.])([\w+.-]+\.(?:pdf|docx?|xlsx?|pptx?|txt|csv|json|zip|py|md))(?!\w)", re.I)
_WINDOWS_PATH_RX = re.compile(r"(?<!\w)[a-z]:\\[^\s\"'»]+", re.I)
_QUOTED_RX = re.compile(r'[«“"]([^«»“”"]{2,140})[»”"]')
_NUMBERS_RX = re.compile(r"(?<!\w)\d+(?:[.,]\d+)?(?:\s*%)?(?!\w)")
_VAGUE_RX = re.compile(r"\b(?:ouvre|lance|ferme|supprime|deplace|copie|renomme)\s+(?:ca|cela|le\s+truc|ce\s+truc|celui[- ]la|celle[- ]la)\b", re.I)
# Cas courants d'utilisateurs habitués a ChatGPT qui parlent de leur passé
# et demandent explicitement l'ouverture d'une AUTRE application.
# Ne pas retirer ChatGPT lorsqu'il est lui-meme la cible de l'action.
_CHATGPT_CONTEXT_RX = re.compile(
    r"\b(?:used|using|know|familiar\s+with|connais|connaitre|utilise|utilisee|utiliser|" 
    r"utilisais|deja\s+utilise|comme\s+sur)\s+chatgpt\b", re.I,
)
_ADVICE_RX = re.compile(
    r"\b(?:comment|how\s+to|how\s+do|como|explique|explain|apprends|teach\s+me)\b", re.I,
)

_ACTION_GROUPS = (
    (re.compile(r"\b(?:ferme|fermer|quitte|quitter)\b", re.I), re.compile(r"\b(?:ferme|fermer|quitte|quitter)\b", re.I)),
    (re.compile(r"\b(?:supprime|supprimer|efface|effacer)\b", re.I), re.compile(r"\b(?:supprime|supprimer|efface|effacer)\b", re.I)),
    (re.compile(r"\b(?:renomme|renommer)\b", re.I), re.compile(r"\b(?:renomme|renommer)\b", re.I)),
    (re.compile(r"\b(?:deplace|deplacer|déplace|déplacer)\b", re.I), re.compile(r"\b(?:deplace|deplacer|déplace|déplacer)\b", re.I)),
    (re.compile(r"\b(?:copie|copier)\b", re.I), re.compile(r"\b(?:copie|copier)\b", re.I)),
)


def _fold(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(x for x in value if not unicodedata.combining(x))


def _entities(value: str) -> set[str]:
    folded = _fold(value)
    return {_NAMES[m.group(1)] for m in _NAMES_RX.finditer(folded)}


def _items(regex: re.Pattern, value: str) -> set[str]:
    return {_fold(x).strip().strip('"«»“” ') for x in regex.findall(value)}


def semantic_fidelity(user_message: object, canonical_command: object) -> tuple[bool, str]:
    """Refuse une normalisation risquee; ne valide jamais une action.

    Les refus prennent la forme d'une clarification. Les cibles generiques
    restent traitees par le moteur deterministe, sans dictionnaire «magique».
    """
    if not isinstance(user_message, str) or not isinstance(canonical_command, str):
        return False, "Demande non exploitable. Reformule la commande."
    original, canonical = user_message.strip(), canonical_command.strip()
    if not original or not canonical or len(original) > 4000 or len(canonical) > 1200:
        return False, "Demande trop longue ou incomplete. Reformule-la."
    # La negation est dangereuse en cas de transformation en action affirmative.
    if _NEGATION_RX.search(original) or _NEGATION_MULTILINGUAL_RX.search(original):
        return False, "J'ai repere une negation. Precise ce que tu souhaites faire sans risque."
    if _VAGUE_RX.search(_fold(original)):
        return False, "Je ne sais pas a quoi renvoie cette expression. Precise la cible."
    # Une question de conseil ne donne pas permission d'agir.
    if _ADVICE_RX.search(_fold(original)):
        return False, "Ta demande ressemble a une question ou a un conseil, pas a une autorisation d'action."

    original_names = _entities(original)
    # La mention autobiographique de ChatGPT n'est pas une demande de l'ouvrir.
    # Condition stricte: une autre cible explicite doit etre presente.
    if 'chatgpt' in original_names and len(original_names) > 1 and _CHATGPT_CONTEXT_RX.search(_fold(original)):
        original_names.remove('chatgpt')
    normalized_names = _entities(canonical)
    if original_names and normalized_names != original_names:
        return False, "La reformulation change le nom de l'application ou du site. Precise ta cible."
    if not original_names and normalized_names:
        # Interdire les applications INVENTEES par le LLM. Seules quelques
        # periphrases generiques explicites et non ambigues sont admises.
        generic = _fold(original)
        aliases = {
            "navigateur": {"edge", "chrome", "firefox"},
            "browser": {"edge", "chrome", "firefox"},
            "traitement de texte": {"word"},
            "tableur": {"excel"},
            "editeur de code": {"vscode"},
            "code editor": {"vscode"},
        }
        action_requested = re.search(r"\b(?:ouvre|ouvrir|lance|lancer|demarre|demarrer|utiliser|open|start|launch)\b", generic)
        if not action_requested or not any(label in generic and normalized_names.issubset(names)
                   for label, names in aliases.items()):
            return False, "La reformulation invente une application ou un site. Precise la cible."
    if original_names and re.search(r"\bou\b", _fold(original)) and len(original_names) > 1:
        return False, "Plusieurs cibles sont proposees. Choisis laquelle utiliser."

    original_files = _items(_FILENAME_RX, original)
    normalized_files = _items(_FILENAME_RX, canonical)
    if normalized_files and not normalized_files.issubset(original_files):
        return False, "La reformulation introduit ou modifie un nom de fichier. Precise la cible."
    if original_files and not original_files.issubset(normalized_files):
        return False, "La reformulation a perdu un nom de fichier. Precise la cible."

    original_paths = _items(_WINDOWS_PATH_RX, original)
    normalized_paths = _items(_WINDOWS_PATH_RX, canonical)
    if normalized_paths != original_paths:
        return False, "La reformulation modifie un chemin de fichier. Precise le chemin."

    # Ne pas risquer un changement de quantite (son 10% -> son 100%).
    input_numbers = _items(_NUMBERS_RX, original)
    output_numbers = _items(_NUMBERS_RX, canonical)
    if output_numbers and not output_numbers.issubset(input_numbers):
        return False, "La reformulation change une valeur numerique. Precise la valeur."
    if input_numbers and not input_numbers.issubset(output_numbers):
        return False, "La reformulation a perdu une valeur numerique. Precise la valeur."

    for original_verb, expected_verb in _ACTION_GROUPS:
        if original_verb.search(_fold(original)) and not expected_verb.search(_fold(canonical)):
            return False, "La reformulation change le type d'action. Reformule la demande."

    # Les fragments cites sont significatifs pour les noms de contenus.
    for fragment in _QUOTED_RX.findall(original):
        if _fold(fragment).strip() not in _fold(canonical):
            return False, "La reformulation a modifie du texte entre guillemets."
    return True, ""


def normalized_confidence(value: object) -> float:
    """Confiance finie 0..1; NaN et Inf doivent echouer en mode ferme."""
    try:
        confidence = float(value)
    except (ValueError, TypeError, OverflowError):
        return 0.0
    return max(0.0, min(confidence, 1.0)) if math.isfinite(confidence) else 0.0
