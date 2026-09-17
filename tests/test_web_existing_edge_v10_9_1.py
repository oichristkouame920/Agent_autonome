import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for item in (ROOT, ROOT / 'app'):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

import web_tools


class WebExistingEdgeV1091Tests(unittest.TestCase):
    def _common(self):
        return (
            patch.object(web_tools, 'get_application_permission', return_value=True),
            patch.object(web_tools, 'resolve_site', return_value=(True, 'https://github.com/', None)),
            patch.object(web_tools, 'find_edge', return_value=Path('C:/Program Files/Microsoft/Edge/Application/msedge.exe')),
        )

    def test_bridge_success_reuses_existing_window(self):
        p1, p2, p3 = self._common()
        with p1, p2, p3, \
             patch.object(web_tools, 'get_application_window_records', return_value=[{'hwnd': 101}]), \
             patch.object(web_tools, 'load_permissions', return_value={'browser_tab_policy': {'enabled': True, 'allow_open_site_in_existing_window': True}}), \
             patch.object(web_tools, 'open_site_via_bridge', return_value=(True, 'ok')) as bridge, \
             patch.object(web_tools, 'launch_edge_reuse_existing_window') as native, \
             patch.object(web_tools, 'launch_edge_new_window') as new_window:
            ok, message = web_tools.open_website('github', source='manual', explicit_user_command=True)
        self.assertTrue(ok, msg=message)
        self.assertIn('fenêtre Edge existante', message)
        bridge.assert_called_once_with('https://github.com/')
        native.assert_not_called()
        new_window.assert_not_called()

    def test_bridge_failure_uses_native_edge_without_new_window(self):
        p1, p2, p3 = self._common()
        with p1, p2, p3, \
             patch.object(web_tools, 'get_application_window_records', return_value=[{'hwnd': 101}]), \
             patch.object(web_tools, 'load_permissions', return_value={'browser_tab_policy': {'enabled': True, 'allow_open_site_in_existing_window': True}}), \
             patch.object(web_tools, 'open_site_via_bridge', return_value=(False, 'pont indisponible')), \
             patch.object(web_tools, 'launch_edge_reuse_existing_window') as native, \
             patch.object(web_tools, 'launch_edge_new_window') as new_window:
            ok, message = web_tools.open_website('github', source='manual', explicit_user_command=True)
        self.assertTrue(ok, msg=message)
        self.assertIn('sans --new-window', message)
        native.assert_called_once()
        new_window.assert_not_called()

    def test_missing_policy_key_does_not_block_manual_migration(self):
        p1, p2, p3 = self._common()
        with p1, p2, p3, \
             patch.object(web_tools, 'get_application_window_records', return_value=[{'hwnd': 101}]), \
             patch.object(web_tools, 'load_permissions', return_value={}), \
             patch.object(web_tools, 'open_site_via_bridge', return_value=(False, 'pont indisponible')), \
             patch.object(web_tools, 'launch_edge_reuse_existing_window') as native, \
             patch.object(web_tools, 'launch_edge_new_window') as new_window:
            ok, message = web_tools.open_website('github', source='manual', explicit_user_command=True)
        self.assertTrue(ok, msg=message)
        native.assert_called_once()
        new_window.assert_not_called()

    def test_explicit_policy_disable_still_blocks(self):
        p1, p2, p3 = self._common()
        with p1, p2, p3, \
             patch.object(web_tools, 'get_application_window_records', return_value=[{'hwnd': 101}]), \
             patch.object(web_tools, 'load_permissions', return_value={'browser_tab_policy': {'enabled': False}}), \
             patch.object(web_tools, 'open_site_via_bridge') as bridge, \
             patch.object(web_tools, 'launch_edge_reuse_existing_window') as native:
            ok, message = web_tools.open_website('github', source='manual', explicit_user_command=True)
        self.assertFalse(ok)
        bridge.assert_not_called()
        native.assert_not_called()

    def test_no_existing_window_keeps_new_window_launch(self):
        p1, p2, p3 = self._common()
        with p1, p2, p3, \
             patch.object(web_tools, 'get_application_window_records', return_value=[]), \
             patch.object(web_tools, 'open_site_via_bridge') as bridge, \
             patch.object(web_tools, 'launch_edge_reuse_existing_window') as native, \
             patch.object(web_tools, 'launch_edge_new_window') as new_window, \
             patch.object(web_tools, 'wait_for_new_edge_windows', return_value=[{'hwnd': 202}]), \
             patch.object(web_tools, 'remember_web_windows'):
            ok, message = web_tools.open_website('github', source='manual', explicit_user_command=True)
        self.assertTrue(ok, msg=message)
        bridge.assert_not_called()
        native.assert_not_called()
        new_window.assert_called_once()

    @patch.object(web_tools.subprocess, 'Popen')
    @patch.object(web_tools, 'get_detached_creation_flags', return_value=0)
    def test_native_reuse_never_uses_new_window_or_shell(self, _flags, popen):
        edge = Path('C:/Program Files/Microsoft/Edge/Application/msedge.exe')
        web_tools.launch_edge_reuse_existing_window(edge, 'https://github.com/')
        args, kwargs = popen.call_args
        command = args[0]
        self.assertEqual(command, [str(edge), 'https://github.com/'])
        self.assertNotIn('--new-window', command)
        self.assertIs(kwargs['shell'], False)


if __name__ == '__main__':
    unittest.main()
