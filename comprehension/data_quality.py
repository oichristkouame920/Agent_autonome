"""Qualite du corpus, separation train/eval et verifications de surete."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_ALLOWED = {'command','conversation','clarification','refusal'}
_NEGATED = re.compile(r"(?:\b(?:pas|jamais|sans|not|don't|dont|do not|never|no)\b|n[’']ouvre|n[’']ex[ée]cute)", re.I)
_SHELL = re.compile(r'\b(?:powershell|cmd\.exe|cmd|bash|wsl|sudo|terminal)\b', re.I)


def load_split(split: str) -> list[dict]:
    if split not in ('train','eval'):
        raise ValueError('split inconnu')
    # Les nouveaux jeux de roles restent separables et compatibles avec V1/V1.1.
    paths = (_ROOT/'data'/f'{split}.jsonl', _ROOT/'data'/f'{split}_audiences.jsonl')
    rows = []
    for path in paths:
        if not path.exists():
            if path == paths[0]:
                raise FileNotFoundError(f'Corpus principal absent : {path}')
            continue
        if path.stat().st_size > 2_000_000:
            raise ValueError(f'Corpus trop volumineux : {path.name}')
        with path.open(encoding='utf-8') as stream:
            rows.extend(json.loads(line) for line in stream if line.strip())
    return rows


def validate_corpus() -> dict:
    errors=[]; seen={}; labels=Counter(); langs=Counter(); domains=Counter()
    for split in ('train','eval'):
        rows=load_split(split)
        if not rows: errors.append(f'{split}: corpus vide')
        for index, row in enumerate(rows, 1):
            ident=f'{split}:{index}'
            if not isinstance(row,dict): errors.append(f'{ident}: ligne non objet');continue
            required=('id','input','output','language','domain','risk')
            if any(x not in row for x in required): errors.append(f'{ident}: champs manquants');continue
            if 'audience' in row and row['audience'] not in ('professional','beginner'):
                errors.append(f'{ident}: audience invalide')
            phrase=row['input']; output=row['output']
            if not isinstance(phrase,str) or not 1<=len(phrase)<=400: errors.append(f'{ident}: texte invalide');continue
            key=' '.join(phrase.casefold().split())
            if key in seen: errors.append(f'{ident}: doublon de {seen[key]}')
            seen[key]=ident
            if not isinstance(output,dict) or output.get('type') not in _ALLOWED: errors.append(f'{ident}: sortie invalide');continue
            typ=output['type']
            if typ=='command':
                cmd=output.get('canonical_command')
                if not isinstance(cmd,str) or not 1<=len(cmd)<=250: errors.append(f'{ident}: commande invalide')
                else:
                    if _SHELL.search(cmd): errors.append(f'{ident}: commande shell interdite')
                    if _NEGATED.search(phrase): errors.append(f'{ident}: phrase negative convertie en action')
            else:
                r=output.get('reply')
                if not isinstance(r,str) or not 1<=len(r)<=400: errors.append(f'{ident}: reponse manquante')
                if output.get('canonical_command'): errors.append(f'{ident}: action rattachee a une reponse sans action')
            labels[(split,typ)]+=1;langs[(split,row['language'])]+=1; domains[(split,row['domain'])]+=1
    return {'ok':not errors,'train':sum(n for (s,_),n in labels.items() if s=='train'),
        'eval':sum(n for (s,_),n in labels.items() if s=='eval'),
        'labels':{f'{s}/{k}':v for (s,k),v in sorted(labels.items())},
        'languages':{f'{s}/{k}':v for (s,k),v in sorted(langs.items())},
        'domains':{f'{s}/{k}':v for (s,k),v in sorted(domains.items())},
        'errors':errors[:30]}
