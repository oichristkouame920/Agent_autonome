"""Selection frugale d'exemples de dialogue pour le Qwen actuel.

Lecture seule. N'execute jamais d'action, n'ajoute aucune permission.
Le guide ne lit que des exemples de reference approuves et locaux.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from .audience import audience_for, audience_hint
from .data_quality import load_split

_ROOT = Path(__file__).resolve().parent
_DATA = _ROOT / 'data' / 'train.jsonl'
_TOKEN = re.compile(r"[a-z0-9]+", re.I)
_NEGATION = re.compile(r"\b(?:ne|n|pas|jamais|surtout|sans|dont|don't|not|no|never|nunca|do not|faut pas|no abras)\b", re.I)
_STOP = {'je','tu','de','le','la','les','un','une','des','en','et','dans','pour','mon','ma','mes','the','a','an','me','to','my','of','on','un','una'}


def _fold(value: str) -> str:
    s = unicodedata.normalize('NFKD', value.casefold())
    return ''.join(c for c in s if not unicodedata.combining(c)).replace('’', "'")


def _tokens(value: str) -> set[str]:
    return {t for t in _TOKEN.findall(_fold(value)) if t not in _STOP and len(t) > 1}


@lru_cache(maxsize=1)
def _examples() -> tuple[dict, ...]:
    rows = []
    for e in load_split('train'):
        if not isinstance(e, dict) or not isinstance(e.get('input'), str) or not isinstance(e.get('output'), dict):
            continue
        # Les exemples de roles sont valides et lies au code du projet.
        rows.append(e)
    return tuple(rows)


# Cette classification sert uniquement a choisir les EXEMPLES du prompt.
# Elle ne valide ni n'execute aucune action; les permissions restent dans
# le moteur deterministe et le filtre de fidelite.
_ACTION_OPEN = re.compile(r"\b(?:ouvr(?:e|es|ez|ons|ent|ir|irez)?|lanc(?:e|es|ez|ons|ent|er)?|demarr(?:e|es|ez|ons|ent|er)?|start|open|launch|abre|abrir|inicia)\b", re.I)
_ACTION_CLOSE = re.compile(r"\b(?:ferm(?:e|es|ez|ons|ent|er)?|quitt(?:e|es|ez|ons|ent|er)?|close|quit|exit|cierra|cerrar)\b", re.I)
_ACTION_SET = re.compile(r"\b(?:regl(?:e|es|ez|ons|ent|er)?|mets|mettre|set|ajust(?:e|es|ez|er)?|fixe|baisse|monte)\b", re.I)
_ADVICE = re.compile(r"\b(?:comment|how to|how do|como|explique|explain|apprends|learn|tutorial|savoir comment)\b", re.I)
_TARGETS = (
    'powerpoint', 'vs code', 'outlook', 'github', 'excel', 'word', 'teams', 'edge',
)


def _targets(value: str) -> set[str]:
    folded = _fold(value)
    return {target for target in _TARGETS
            if re.search(r'(?<![a-z])'+re.escape(target)+r'(?![a-z])',folded)}


def _target(value: str) -> str:
    matches = _targets(value)
    return next((t for t in _TARGETS if t in matches), '')


def _intent_hint(value: str) -> str:
    """Indice lexical de l'intention pour la SELECTION des exemples uniquement."""
    folded = _fold(value)
    if _ADVICE.search(folded):
        return 'advice'
    if _ACTION_CLOSE.search(folded) and _target(folded):
        return 'close'
    if _ACTION_OPEN.search(folded) and _target(folded):
        return 'open'
    if _ACTION_SET.search(folded) and ('son' in folded or 'volume' in folded or '%' in folded):
        return 'audio_set'
    return ''


def _example_intent(ex: dict) -> str:
    output=ex['output']
    if output['type']!='command':
        return ''
    canonical=_fold(output.get('canonical_command', ''))
    if 'volume' in canonical or '%' in canonical:
        return 'audio_set'
    if _ACTION_CLOSE.search(canonical) and _target(canonical):
        return 'close'
    if _ACTION_OPEN.search(canonical) and _target(canonical):
        return 'open'
    return ''


def _prepare(ex: dict) -> tuple:
    """Index compact des references, jamais des demandes utilisateur."""
    folded = _fold(ex['input'])
    canonical = ex['output'].get('canonical_command', '')
    return (
        ex, _tokens(ex['input']), folded,
        ex['output']['type'] == 'command',
        ex.get('domain') == 'negation' or bool(_NEGATION.search(folded)),
        _example_intent(ex), _targets(canonical),
        set(re.findall(r'\b\d+\b', _fold(canonical))),
    )


@lru_cache(maxsize=1)
def _prepared_examples() -> tuple:
    # <= 600 exemples dans le corpus V1.2, charges une fois en lecture seule.
    # Ne pas mettre de requetes utilisateur en cache : pas de fuite RAM.
    return tuple(_prepare(ex) for ex in _examples())


def closest_examples(text: str, count: int = 3) -> list[dict]:
    """Exemples adaptes sans actions ni entrainement automatique.

    Evite les exemples positifs pour des negations ou demandes de conseils,
    les operations inverses (fermer/ouvrir), les cibles et nombres differents.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    count = max(0, min(int(count), 4))
    if not count:
        return []
    # Une requete extremement longue ne doit pas declencher un classement couteux.
    if len(text) > 2000:
        return []
    inp = _tokens(text)
    inp_fold = _fold(text)
    audience = audience_for(text)
    neg = bool(_NEGATION.search(inp_fold)) or "n'" in inp_fold
    action_hint = _intent_hint(text) if not neg else ''
    request_targets = _targets(text)
    request_numbers = set(re.findall(r'\b\d+\b', inp_fold))
    candidates = []
    prepared = list(_prepared_examples())
    try:
        from .feedback import approved_examples
        prepared.extend(_prepare(ex) for ex in approved_examples())
    except (OSError, ValueError):
        pass
    for ex, e_tokens, e_fold, is_command, e_negative, e_intent, ex_targets, ex_numbers in prepared:
        if not e_tokens:
            continue
        if neg and is_command:
            continue
        if not neg and e_negative:
            continue
        if action_hint == 'advice' and is_command:
            continue
        if action_hint and action_hint != 'advice':
            if not is_command or e_intent != action_hint:
                continue
            # Un exemple sur une autre application ou une sequence plus longue
            # perturbe le petit modele, meme si quelques mots coincident.
            if request_targets and ex_targets != request_targets:
                continue
        common = len(inp & e_tokens)
        if not common:
            continue
        score = 2 * common / max(1, len(inp) + len(e_tokens))
        if neg and e_negative:
            score += 0.45
        if audience != 'neutral' and ex.get('audience') == audience:
            score += 0.18
        if inp_fold == e_fold:
            score += 0.2
        if action_hint == 'audio_set':
            if request_numbers and ex_numbers and request_numbers != ex_numbers:
                continue
            if request_numbers and request_numbers == ex_numbers:
                score += 0.3
        if score > 0:
            candidates.append((score, ex))
    candidates.sort(key=lambda z: (-z[0], z[1]['id']))
    result, domains = [], set()
    for score, ex in candidates:
        if ex['domain'] in domains and len(result) < count - 1 and score < 0.7:
            continue
        result.append(ex)
        domains.add(ex['domain'])
        if len(result) >= count:
            break
    if len(result) < count:
        for _, ex in candidates:
            if ex not in result:
                result.append(ex)
                if len(result) >= count:
                    break
    return result


def few_shot_hint(message: str, max_chars: int = 1050) -> str:
    """Exemples de format JSON utiles au LLM, sans texte utilisateur non fiable repris ici."""
    limit = max(0, min(int(max_chars), 1500))
    if limit < 100:
        return ''
    hint = audience_hint(message)
    if hint and len(hint) + 10 > limit:
        hint = ''
    lines = []
    for ex in closest_examples(message, 3):
        obj = {'demande': ex['input'], 'reponse': ex['output']}
        item = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
        static_header = len('Exemples de reference (ne copie pas la cible; adapte-la a la demande reelle):\n')
        if len(item) + sum(map(len, lines)) + len(lines) + len(hint) + static_header + 2 > limit:
            continue
        lines.append(item)
    if not lines:
        return (hint+'\n') if hint else ''
    prefix = (hint+'\n') if hint else ''
    return prefix+'Exemples de reference (ne copie pas la cible; adapte-la a la demande reelle):\n'+'\n'.join(lines)+'\n'
