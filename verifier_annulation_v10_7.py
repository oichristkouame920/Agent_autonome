import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for item in (ROOT, ROOT / 'app'):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

import agent
from backends.deterministic_backend import interpret
from session_undo import get_last_file_undo

checks = [
    ('annule la dernière opération fichier', 'undo_last_file_action'),
    ('annule le dernier déplacement', 'undo_last_file_action'),
    ('annule la dernière copie', 'undo_last_file_action'),
    ('annule le dernier renommage', 'undo_last_file_action'),
    ('remets le dernier fichier comme avant', 'undo_last_file_action'),
]

for text, wanted in checks:
    result = interpret(text)
    actions = result.get('actions', []) if isinstance(result, dict) else []
    assert actions and actions[0].get('action') == wanted, (text, result)
    print('OK -', text)

negative = interpret("annule pas la dernière opération fichier")
assert negative.get('understood') and negative.get('actions') == [], negative
print('OK - négation sans action')

contract = {
    'schema_version': 1,
    'action': 'undo_last_file_action',
    'target': 'session',
    'params': {},
}
assert agent.validate_action(contract) == (True, None)
print('OK - contrat d’annulation contrôlé')

assert get_last_file_undo(900) is None
print('OK - aucune opération utilisateur n’a été créée par ce vérificateur')
print('\nV10.7 ANNULATION FICHIER ACTIVE - verification non destructive OK')
