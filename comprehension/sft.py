"""Export supervisé compatible avec les jeux de messages ChatML / TRL.

Aucun entrainement n'est lance par cet export.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from .data_quality import load_split, validate_corpus

SYSTEM = (
    'Tu es la couche de comprehension d AgentLocal. Tu ne realises jamais d action. '
    'Renvoie uniquement un JSON valide de type command, conversation, clarification ou refusal. '
    'Ne transforme jamais une negation en action; ne fabrique jamais de cible ou de nombre. '
    'Les commandes sont verifiees et executees uniquement par un moteur separe et autorise. '
    'Adapte les reponses conversationnelles au niveau demande : precis pour un professionnel, '
    'simple et pedagogique pour un debutant. N invente ni acces, ni fichier, ni action realisee.'
)


def export(output_dir: Path) -> dict[str,int]:
    report=validate_corpus()
    if not report['ok']:
        raise ValueError('Corpus invalide: '+str(report['errors']))
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    # Split stable : sous-ensemble de validation issu du corpus d'entrainement.
    # Le jeu eval.jsonl reste 100 % reserve au benchmark final.
    training=load_split('train')
    training_rows=[]
    validation_rows=[]
    for item in training:
        key=int(hashlib.sha256(item['input'].encode('utf-8')).hexdigest()[:8],16)
        (validation_rows if key % 5 == 0 else training_rows).append(item)
    if not training_rows or not validation_rows:
        raise RuntimeError('Split train/validation deséquilibré')
    batches={'train':training_rows,'validation':validation_rows,'test_holdout':load_split('eval')}
    totals={}
    for split,items in batches.items():
        path=output_dir/f'{split}_sft.jsonl'
        with path.open('w',encoding='utf-8',newline='\n') as stream:
            for item in items:
                messages=[{'role':'system','content':SYSTEM},
                          {'role':'user','content':item['input']},
                          {'role':'assistant','content':json.dumps(item['output'],ensure_ascii=False,separators=(',',':'))}]
                stream.write(json.dumps({'messages':messages},ensure_ascii=False)+'\n')
        totals[split]=len(items)
    return totals
