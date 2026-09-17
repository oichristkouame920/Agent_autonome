from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
for item in (ROOT, ROOT / 'app'):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

import agent
from backends.deterministic_backend import interpret

checks = [
    ('donne moi les infos de rapport.pdf dans Documents', 'inspect_file_metadata'),
    ('calcule le sha256 de rapport.pdf dans Documents', 'calculate_file_sha256'),
    ('compare a.txt et b.txt dans Documents', 'compare_files_sha256'),
    ('cherche les doublons dans Documents', 'find_duplicate_files'),
]

for phrase, expected in checks:
    result = interpret(phrase)
    actions = result.get('actions', []) if isinstance(result, dict) else []
    if not actions or actions[0].get('action') != expected:
        raise SystemExit(f'ERREUR - {phrase!r} -> {actions!r}')
    valid, error = agent.validate_action(actions[0])
    if not valid:
        raise SystemExit(f'ERREUR CONTRAT - {expected}: {error}')
    print(f'OK - {phrase} -> {expected}')

negative = interpret('cherche pas les doublons dans Documents')
if negative.get('actions'):
    raise SystemExit('ERREUR - une négation a produit une action')
print('OK - négation explicite -> aucune action')

permissions = json.loads((ROOT / 'config' / 'permissions.json').read_text(encoding='utf-8'))
policy = permissions.get('file_analysis_policy', {})
if not policy.get('enabled') or not policy.get('read_only'):
    raise SystemExit('ERREUR - file_analysis_policy doit être active et en lecture seule')
if policy.get('allow_from_routine') or policy.get('allow_from_habit'):
    raise SystemExit('ERREUR - routines/habitudes ne doivent pas accéder à l’analyse de fichiers')
print('OK - politique lecture seule / accès manuel uniquement')

print('\nV10.8 ANALYSE LOCALE DES FICHIERS ACTIVE - verification non destructive OK')
