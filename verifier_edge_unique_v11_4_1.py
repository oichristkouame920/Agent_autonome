from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
APP = ROOT / 'app'
EXT = ROOT / 'browser_extension'

errors = []

web_tools = APP / 'web_tools.py'
background = EXT / 'background.js'
manifest = EXT / 'manifest.json'

for path in (web_tools, background, manifest):
    if not path.exists():
        errors.append(f'Fichier manquant : {path.relative_to(ROOT)}')

if not errors:
    web_text = web_tools.read_text(encoding='utf-8')
    js_text = background.read_text(encoding='utf-8')
    data = json.loads(manifest.read_text(encoding='utf-8'))

    if 'TARGET_WINDOW_STORAGE_KEY' not in js_text:
        errors.append('Extension : fenêtre cible persistante absente.')
    if 'chooseAgentLocalWindowId' not in js_text:
        errors.append('Extension : sélection de fenêtre AgentLocal absente.')
    if 'chrome.storage.session' not in js_text:
        errors.append('Extension : stockage de session absent.')
    if 'storage' not in data.get('permissions', []):
        errors.append('Manifest : permission storage absente.')
    if data.get('version') != '2.2.0':
        errors.append(f"Manifest : version attendue 2.2.0, trouvée {data.get('version')!r}.")

    required_chunks = [
        'Une fenêtre Edge est déjà ouverte, mais le pont local',
        "n'a pas pu ouvrir le nouvel onglet dans la",
        'Recharge l\'extension AgentLocal dans',
    ]
    if not all(chunk in web_text for chunk in required_chunks):
        errors.append('web_tools : refus strict en cas de panne du pont absent.')

    old_success = "a utilisé le mécanisme natif d'Edge sans --new-window"
    if old_success in web_text:
        errors.append('web_tools : ancien fallback natif encore actif.')

if errors:
    for error in errors:
        print('ERREUR -', error)
    sys.exit(1)

print('OK - extension Edge 2.2.0 detectee')
print('OK - fenetre cible AgentLocal unique memorisee par session')
print('OK - aucun fallback natif autorise si Edge est deja ouvert')
print('OK - aucun secret du pont Edge verifie ou modifie par ce script')
print()
print('V11.4.1 EDGE FENETRE UNIQUE ACTIVE - verification non destructive OK')
