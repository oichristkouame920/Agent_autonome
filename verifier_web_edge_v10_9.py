from contextlib import ExitStack
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
for item in (ROOT, ROOT / 'app'):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

import web_tools
from browser_bridge import open_site_via_bridge

print('Verification V10.9 - ouverture Web dans Edge existant')

if not callable(open_site_via_bridge):
    raise SystemExit('ECHEC - open_site_via_bridge absent du pont Edge')

with ExitStack() as stack:
    stack.enter_context(patch.object(web_tools, 'get_application_permission', return_value=True))
    stack.enter_context(patch.object(web_tools, 'resolve_site', return_value=(True, 'https://github.com/', None)))
    stack.enter_context(patch.object(web_tools, 'find_edge', return_value=Path('msedge.exe')))
    stack.enter_context(patch.object(web_tools, 'get_application_window_records', return_value=[{'hwnd': 1}]))
    bridge = stack.enter_context(patch.object(web_tools, 'open_site_via_bridge', return_value=(True, 'ok')))
    launch = stack.enter_context(patch.object(web_tools, 'launch_edge_new_window'))

    ok, message = web_tools.open_website(
        'github',
        source='manual',
        explicit_user_command=True,
    )

    if not ok or 'fenêtre Edge existante' not in message:
        raise SystemExit('ECHEC - la règle Edge existant n est pas active')
    if bridge.call_count != 1:
        raise SystemExit('ECHEC - le pont Edge n a pas été utilisé')
    if launch.call_count != 0:
        raise SystemExit('ECHEC - une nouvelle fenêtre Edge aurait été lancée')

print('OK - pont Edge compatible')
print('OK - une ouverture Web manuelle réutilise une fenêtre Edge existante')
print('OK - aucune nouvelle fenêtre Edge n est créée si une fenêtre existe déjà')
print('OK - aucune navigation réelle n a été effectuée pendant ce contrôle')
print('V10.9 WEB / EDGE EXISTANT ACTIVE - verification non destructive OK')
