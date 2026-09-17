from contextlib import ExitStack
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
for item in (ROOT, ROOT / 'app'):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

import web_tools
from browser_bridge import bridge_request, is_bridge_configured

print('Verification V10.9.1 - Web dans Edge existant (pont + secours natif)')

# Test non destructif du routage : aucune page n'est réellement ouverte.
with ExitStack() as stack:
    stack.enter_context(patch.object(web_tools, 'get_application_permission', return_value=True))
    stack.enter_context(patch.object(web_tools, 'resolve_site', return_value=(True, 'https://github.com/', None)))
    stack.enter_context(patch.object(web_tools, 'find_edge', return_value=Path('msedge.exe')))
    stack.enter_context(patch.object(web_tools, 'get_application_window_records', return_value=[{'hwnd': 1}]))
    stack.enter_context(patch.object(web_tools, 'load_permissions', return_value={'browser_tab_policy': {'enabled': True, 'allow_open_site_in_existing_window': True}}))
    stack.enter_context(patch.object(web_tools, 'open_site_via_bridge', return_value=(False, 'pont simulé indisponible')))
    native = stack.enter_context(patch.object(web_tools, 'launch_edge_reuse_existing_window'))
    new_window = stack.enter_context(patch.object(web_tools, 'launch_edge_new_window'))

    ok, message = web_tools.open_website('github', source='manual', explicit_user_command=True)
    if not ok:
        raise SystemExit('ECHEC - le secours natif Edge ne prend pas le relais')
    if native.call_count != 1:
        raise SystemExit('ECHEC - le secours natif sans --new-window n a pas été utilisé')
    if new_window.call_count != 0:
        raise SystemExit('ECHEC - le chemin --new-window a été utilisé alors qu Edge existait')

print('OK - ouverture manuelle dans Edge existant prioritaire')
print('OK - secours natif Edge disponible sans --new-window')
print('OK - aucune navigation réelle pendant le contrôle de routage')

# Diagnostic live facultatif du pont, sans navigation ni modification d'onglet.
if not is_bridge_configured():
    print('INFO - pont Edge non configuré; le secours natif reste disponible')
else:
    ok, _, message = bridge_request('ping', {}, timeout_seconds=3.0)
    if ok:
        print('OK - pont Edge répond au ping local')
    else:
        print('INFO - pont Edge ne répond pas actuellement; le secours natif sera utilisé')
        print('DETAIL - ' + str(message))

print('V10.9.1 WEB / EDGE EXISTANT ACTIF - verification non destructive OK')
