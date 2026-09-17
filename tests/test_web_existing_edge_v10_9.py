import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for item in (ROOT, ROOT / 'app'):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

import web_tools


class WebExistingEdgeV109Tests(unittest.TestCase):
    def _common(self):
        return (
            patch.object(web_tools, 'get_application_permission', return_value=True),
            patch.object(web_tools, 'resolve_site', return_value=(True, 'https://github.com/', None)),
            patch.object(web_tools, 'find_edge', return_value=Path('C:/Program Files/Microsoft/Edge/Application/msedge.exe')),
        )

    def test_manual_open_reuses_existing_edge_window(self):
        p1, p2, p3 = self._common()
        with p1, p2, p3, \
             patch.object(web_tools, 'get_application_window_records', return_value=[{'hwnd': 101}]), \
             patch.object(web_tools, 'open_site_via_bridge', return_value=(True, 'ok')) as bridge, \
             patch.object(web_tools, 'launch_edge_new_window') as launch:
            ok, message = web_tools.open_website(
                'github', source='manual', explicit_user_command=True
            )
        self.assertTrue(ok, msg=message)
        self.assertIn('fenêtre Edge existante', message)
        bridge.assert_called_once_with('https://github.com/')
        launch.assert_not_called()

    def test_bridge_failure_does_not_create_second_window(self):
        p1, p2, p3 = self._common()
        with p1, p2, p3, \
             patch.object(web_tools, 'get_application_window_records', return_value=[{'hwnd': 101}]), \
             patch.object(web_tools, 'open_site_via_bridge', return_value=(False, 'pont indisponible')), \
             patch.object(web_tools, 'launch_edge_new_window') as launch:
            ok, message = web_tools.open_website(
                'github', source='manual', explicit_user_command=True
            )
        self.assertFalse(ok)
        self.assertIn('extension AgentLocal', message)
        launch.assert_not_called()

    def test_manual_open_starts_edge_if_no_window_exists(self):
        p1, p2, p3 = self._common()
        with p1, p2, p3, \
             patch.object(web_tools, 'get_application_window_records', return_value=[]), \
             patch.object(web_tools, 'open_site_via_bridge') as bridge, \
             patch.object(web_tools, 'launch_edge_new_window') as launch, \
             patch.object(web_tools, 'wait_for_new_edge_windows', return_value=[{'hwnd': 202}]), \
             patch.object(web_tools, 'remember_web_windows') as remember:
            ok, message = web_tools.open_website(
                'github', source='manual', explicit_user_command=True
            )
        self.assertTrue(ok, msg=message)
        self.assertIn('nouvelle fenêtre Edge', message)
        bridge.assert_not_called()
        launch.assert_called_once()
        remember.assert_called_once()

    def test_routine_keeps_previous_new_window_behavior(self):
        p1, p2, p3 = self._common()
        with p1, p2, p3, \
             patch.object(web_tools, 'get_application_window_records', return_value=[{'hwnd': 101}]), \
             patch.object(web_tools, 'open_site_via_bridge') as bridge, \
             patch.object(web_tools, 'launch_edge_new_window') as launch, \
             patch.object(web_tools, 'wait_for_new_edge_windows', return_value=[{'hwnd': 202}]), \
             patch.object(web_tools, 'remember_web_windows'):
            ok, message = web_tools.open_website(
                'github', source='routine', explicit_user_command=False
            )
        self.assertTrue(ok, msg=message)
        bridge.assert_not_called()
        launch.assert_called_once()


if __name__ == '__main__':
    unittest.main()
