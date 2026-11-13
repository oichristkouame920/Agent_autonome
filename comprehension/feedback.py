"""Apprentissage local uniquement sur corrections approuvees par l'utilisateur.

Aucune collecte en arriere-plan, aucune action Windows. Donnees sous memory/.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from uuid import uuid4

from .data_quality import load_split

_PROJECT = Path(__file__).resolve().parents[1]
_PENDING = _PROJECT / 'memory' / 'language_pending.json'
_APPROVED = _PROJECT / 'memory' / 'language_approved.json'
_EMAIL = re.compile(r'\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b', re.I)
_SECRET = re.compile(r'\b(?:api[_ -]?key|token|password|mot de passe|secret|bearer)\b', re.I)
_PATH = re.compile(r'\b[A-Za-z]:\\')
_NEG = re.compile(r'\b(?:pas|jamais|sans|not|never|do not|dont|don\'t|no)\b|n[’\']ouvre',re.I)


def _read(path: Path) -> list[dict]:
    try:
        if path.stat().st_size > 250_000:
            return []
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data,list) else []
    except (OSError, ValueError):
        return []


def _write(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='approved_language_',suffix='.tmp',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(rows,stream,ensure_ascii=False,indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        Path(name).unlink(missing_ok=True)


def _safe_text(text: str) -> bool:
    return isinstance(text,str) and 1 <= len(text.strip()) <= 180 and not any(rx.search(text) for rx in (_EMAIL,_SECRET,_PATH))


def allowed_commands() -> set[str]:
    return {item['output']['canonical_command'] for item in load_split('train') if item['output']['type']=='command'}


def propose(phrase: str, target: str) -> str:
    """Propose la correspondance vers une commande du corpus; jamais appliquee seule."""
    if not _safe_text(phrase) or not _safe_text(target):
        raise ValueError('Phrase invalide ou contenant des donnees potentiellement sensibles')
    if _NEG.search(phrase):
        raise ValueError('La phrase contient une negation: ne jamais creer une action affirmative')
    if target not in allowed_commands():
        raise ValueError('Commande inconnue: seuls les exemples deja pris en charge peuvent etre appris')
    # Controle cible et nombres par la garde V12.5.4.
    from backends.llm_fidelity import semantic_fidelity
    ok,detail=semantic_fidelity(phrase,target)
    if not ok:
        raise ValueError('Reformulation non fidele: '+detail)
    rows=_read(_PENDING)
    ident=uuid4().hex[:12]
    if len(rows)>=100:
        raise ValueError('Limite de corrections en attente atteinte')
    rows.append({'id':ident,'input':phrase.strip(),'output':{'type':'command','canonical_command':target,'confidence':0.9}})
    _write(_PENDING,rows)
    return ident


def approve(ident: str) -> bool:
    """Confirmation explicite obligatoire; pas d'auto-apprentissage."""
    if not re.fullmatch(r'[0-9a-f]{12}',str(ident)):
        return False
    rows=_read(_PENDING)
    matched=[x for x in rows if x.get('id')==ident]
    if len(matched)!=1:
        return False
    item=matched[0]
    if not _safe_text(item['input']) or item['output'].get('canonical_command') not in allowed_commands():
        return False
    approved=_read(_APPROVED)
    if len(approved)>=100:
        return False
    if any(x.get('input','').casefold()==item['input'].casefold() for x in approved):
        return False
    _write(_APPROVED,approved+[item])
    _write(_PENDING,[x for x in rows if x.get('id')!=ident])
    return True


def approved_examples() -> list[dict]:
    """Retourne seulement les exemples valides et approuves."""
    output=[]
    for item in _read(_APPROVED)[:100]:
        phrase=item.get('input','')
        cmd=item.get('output',{}).get('canonical_command')
        if _safe_text(phrase) and cmd in allowed_commands() and not _NEG.search(phrase):
            output.append({'id':item['id'],'input':phrase,'output':item['output'],'domain':'approved'})
    return output
