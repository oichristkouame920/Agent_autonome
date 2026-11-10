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

print('Verification V10.9.1 compatibilite - comportement supersede par V11.4.1')

# Depuis V11.4.1, si Edge est deja ouvert et que le pont local echoue,
# AgentLocal refuse plutot que de lancer msedge.exe avec une URL, car Windows
# pourrait alors creer une seconde fenetre. Ce verifier historique controle
# desormais explicitement cette regle de non-regression.
with ExitStack() as stack:
    stack.enter_context(patch.object(web_tools, 'get_application_permission', return_value=True))
    stack.enter_context(patch.object(web_tools, 'resolve_site', return_value=(True, 'https://github.com/', None)))
    stack.enter_context(patch.object(web_tools, 'find_edge', return_value=Path('msedge.exe')))
    stack.enter_context(patch.object(web_tools, 'get_application_window_records', return_value=[{'hwnd': 1}]))
    stack.enter_context(patch.object(web_tools, 'load_permissions', return_value={'browser_tab_policy': {'enabled': True, 'allow_open_site_in_existing_window': True}}))
    stack.enter_context(patch.object(web_tools, 'open_site_via_bridge', return_value=(False, 'pont simule indisponible')))
    native = stack.enter_context(patch.object(web_tools, 'launch_edge_reuse_existing_window'))
    new_window = stack.enter_context(patch.object(web_tools, 'launch_edge_new_window'))

    ok, message = web_tools.open_website('github', source='manual', explicit_user_command=True)
    if ok:
        raise SystemExit('ECHEC - un echec du pont ne doit plus etre masque par un fallback natif')
    if native.call_count != 0:
        raise SystemExit('ECHEC - le fallback natif historique a ete utilise')
    if new_window.call_count != 0:
        raise SystemExit('ECHEC - une nouvelle fenetre Edge a ete creee alors qu Edge existait')
    if 'extension AgentLocal' not in str(message):
        raise SystemExit('ECHEC - le message de refus ne signale pas le pont/extension AgentLocal')

print('OK - pont Edge prioritaire lorsque la fenetre existe')
print('OK - aucun fallback natif si le pont echoue')
print('OK - aucune nouvelle fenetre Edge n est creee dans ce cas')

# Diagnostic live facultatif du pont, sans navigation ni modification d'onglet.
if not is_bridge_configured():
    print('INFO - pont Edge non configure; les commandes d onglet resteront indisponibles')
else:
    ok, _, message = bridge_request('ping', {}, timeout_seconds=3.0)
    if ok:
        print('OK - pont Edge repond au ping local')
    else:
        print('INFO - pont Edge ne repond pas actuellement; AgentLocal refusera sans creer une seconde fenetre')
        print('DETAIL - ' + str(message))

print('V10.9.1 COMPATIBILITE V11.4.1 - verification non destructive OK')
