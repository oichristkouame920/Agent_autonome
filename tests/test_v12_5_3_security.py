"""Test sans modification systeme de la securite AgentLocal V12.5.3."""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))

import admin_tasks
import security_center


class SecurityTests(unittest.TestCase):
    def test_default_policy_is_deny(self):
        with tempfile.TemporaryDirectory() as td, patch.object(security_center, 'SETTINGS_FILE', Path(td) / 'cfg.json'):
            self.assertFalse(security_center.load_settings()['allow_elevation_requests'])

    def test_save_is_opt_in_only(self):
        with tempfile.TemporaryDirectory() as td, patch.object(security_center, 'SETTINGS_FILE', Path(td) / 'cfg.json'):
            with self.assertRaises(ValueError):
                security_center.save_settings('true')
            self.assertTrue(security_center.save_settings(True)['allow_elevation_requests'])
            self.assertTrue(security_center.load_settings()['allow_elevation_requests'])
            self.assertFalse(security_center.save_settings(False)['allow_elevation_requests'])
            self.assertFalse(security_center.load_settings()['allow_elevation_requests'])

    def test_malformed_config_defaults_deny(self):
        with tempfile.TemporaryDirectory() as td, patch.object(security_center, 'SETTINGS_FILE', Path(td) / 'cfg.json'):
            security_center.SETTINGS_FILE.write_text('{',encoding='utf-8')
            self.assertFalse(security_center.load_settings()['allow_elevation_requests'])
            security_center.SETTINGS_FILE.write_text('{"allow_elevation_requests": "true"}',encoding='utf-8')
            self.assertFalse(security_center.load_settings()['allow_elevation_requests'])

    def test_unknown_request_rejected_without_touching_windows(self):
        for action in ('powershell.exe', 'cmd /c del C:\\', '', '../admin_tasks.py', 'flush_dns_cache --action all'):
            with patch.object(security_center.ctypes, 'windll', create=True) as mock:
                ok, reason = security_center.request_one_shot_elevation(action, explicit_confirmation=True)
                self.assertFalse(ok)
                mock.shell32.ShellExecuteW.assert_not_called()

    def test_confirmation_is_mandatory(self):
        with patch.object(security_center.ctypes, 'windll', create=True) as mock:
            ok, reason = security_center.request_one_shot_elevation('flush_dns_cache')
            self.assertFalse(ok)
            mock.shell32.ShellExecuteW.assert_not_called()

    def test_opt_in_required(self):
        with patch.object(security_center, 'load_settings', return_value={'allow_elevation_requests': False}):
            with patch.object(security_center.ctypes, 'windll', create=True) as mock:
                ok, _ = security_center.request_one_shot_elevation('flush_dns_cache', explicit_confirmation=True)
                self.assertFalse(ok)
                mock.shell32.ShellExecuteW.assert_not_called()

    def test_no_elevation_on_other_platform(self):
        with patch.object(security_center, 'load_settings', return_value={'allow_elevation_requests': True}):
            with patch.object(security_center.sys, 'platform', 'linux'):
                ok, _ = security_center.request_one_shot_elevation('flush_dns_cache', explicit_confirmation=True)
                self.assertFalse(ok)

    def test_explicit_elevation_attempt_is_allowlisted_and_quoted(self):
        with patch.object(security_center, 'load_settings', return_value={'allow_elevation_requests': True}), \
             patch.object(security_center.sys, 'platform', 'win32'), \
             patch.object(security_center.ctypes, 'windll', create=True) as mock:
            mock.shell32.ShellExecuteW.return_value = 42
            ok, msg = security_center.request_one_shot_elevation('flush_dns_cache', explicit_confirmation=True)
            self.assertTrue(ok)
            args = mock.shell32.ShellExecuteW.call_args.args
            self.assertEqual(args[1], 'runas')
            self.assertIn('admin_tasks.py', args[3])
            self.assertIn('flush_dns_cache', args[3])
            self.assertNotIn('powershell', args[3].lower())

    def test_cancelled_uac_never_reports_success(self):
        with patch.object(security_center, 'load_settings', return_value={'allow_elevation_requests': True}), \
             patch.object(security_center.sys, 'platform', 'win32'), \
             patch.object(security_center.ctypes, 'windll', create=True) as mock:
            mock.shell32.ShellExecuteW.return_value = 5
            ok, _ = security_center.request_one_shot_elevation('flush_dns_cache', explicit_confirmation=True)
            self.assertFalse(ok)

    def test_unknown_admin_operation_never_runs(self):
        with patch.object(admin_tasks, 'is_windows_admin', return_value=True), patch.object(admin_tasks.subprocess, 'run') as mock:
            ok, _ = admin_tasks.execute_admin_action('disable_defender')
            self.assertFalse(ok)
            mock.assert_not_called()

    def test_no_admin_rights_never_runs_task(self):
        with patch.object(admin_tasks, 'is_windows_admin', return_value=False), patch.object(admin_tasks.subprocess, 'run') as mock:
            ok, _ = admin_tasks.execute_admin_action('flush_dns_cache')
            self.assertFalse(ok)
            mock.assert_not_called()

    def test_admin_exec_uses_fixed_system_bin_no_shell(self):
        with patch.object(admin_tasks, 'is_windows_admin', return_value=True), \
             patch.object(admin_tasks, 'system_executable', return_value=Path('C:/Windows/System32/ipconfig.exe')), \
             patch.object(admin_tasks.subprocess, 'run') as mock:
            mock.return_value.returncode = 0
            ok, _ = admin_tasks.execute_admin_action('flush_dns_cache')
            self.assertTrue(ok)
            args, kwargs = mock.call_args
            self.assertEqual(args[0][1], '/flushdns')
            self.assertFalse(kwargs['shell'])
            self.assertEqual(len(args[0]), 2)

    def test_failed_admin_task_not_success(self):
        with patch.object(admin_tasks, 'is_windows_admin', return_value=True), \
             patch.object(admin_tasks, 'system_executable', return_value=Path('C:/Windows/System32/ipconfig.exe')), \
             patch.object(admin_tasks.subprocess, 'run', side_effect=subprocess.TimeoutExpired('x', 30)):
            ok, msg = admin_tasks.execute_admin_action('flush_dns_cache')
            self.assertFalse(ok)

    def test_agent_policy_unchanged(self):
        info = security_center.status()
        self.assertTrue(info['arbitrary_shell_disabled'])
        self.assertTrue(info['agent_elevation_disabled'])

    def test_launcher_exposes_security_option_and_direct_command(self):
        data = (ROOT / 'AgentLocal.bat').read_text(encoding='ascii')
        self.assertIn('[10] Securite et autorisations',data)
        self.assertIn('if /I "%CMD%"=="security" goto SECURITY',data)
        self.assertIn('call :RUN_PY "app\\security_center.py"',data)

    def test_gui_button_accessible(self):
        data = (ROOT / 'app' / 'gui.py').read_text(encoding='utf-8')
        self.assertIn('open_security_center(self.root)', data)

    def test_import_has_no_side_effects(self):
        # Imports do not create config files or trigger UAC.
        with tempfile.TemporaryDirectory() as td, patch.object(security_center, 'SETTINGS_FILE', Path(td) / 'cfg.json'):
            with patch.object(security_center.ctypes, 'windll', create=True) as mock:
                importlib.reload(admin_tasks)
                self.assertFalse(security_center.SETTINGS_FILE.exists())
                mock.shell32.ShellExecuteW.assert_not_called()


if __name__ == '__main__':
    unittest.main()
