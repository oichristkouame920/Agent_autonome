"""Offline, non-destructive tests for the AgentLocal environment bootstrap."""
import importlib.util
import io
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'runtime' / 'agentlocal_test_manager.py'
SPEC = importlib.util.spec_from_file_location('agentlocal_test_manager', SOURCE)
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)


class StubResult:
    def __init__(self, out='', code=0):
        self.stdout = out
        self.stderr = ''
        self.returncode = code


def probe_response(missing=(), bits=64):
    import json
    return StubResult('AGENTLOCAL_ENV_JSON=' + json.dumps({
        'python': '3.14.7', 'bits': bits, 'missing': list(missing),
        'installed': {x: 'installed' for x in ('psutil','pypdf') if x not in missing}}))


def silent_call(fn, *args, **kwargs):
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        return fn(*args, **kwargs)


class ManagerTests(unittest.TestCase):
    def test_dependencies_fixed(self):
        self.assertEqual(manager.DEPENDENCIES, ('psutil', 'pypdf'))

    def test_default_full_command(self):
        self.assertIn('discover', manager.mode_commands(Path('.'), 'full')[0])

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            manager.mode_commands(Path('.'), 'live')

    def test_quick_test_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp) / 'tests'
            t.mkdir()
            (t/'test_agentlocal_test_manager.py').write_text('')
            self.assertEqual(manager.mode_commands(Path(tmp), 'quick')[0][-2],
                             'tests.test_agentlocal_test_manager')

    def test_probe_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(manager.probe(Path(tmp)/'missing.exe')['ok'])

    def test_probe_psutil_missing(self):
        info = manager.probe(Path(sys.executable), runner=lambda *a, **kw: probe_response(['psutil']))
        self.assertFalse(info['ok'])
        self.assertIn('psutil', info['reason'])

    def test_probe_pypdf_missing(self):
        info = manager.probe(Path(sys.executable), runner=lambda *a, **kw: probe_response(['pypdf']))
        self.assertFalse(info['ok'])

    def test_probe_python32_refused(self):
        info = manager.probe(Path(sys.executable), runner=lambda *a, **kw: probe_response(bits=32))
        self.assertFalse(info['ok'])

    def test_probe_both_installed(self):
        info = manager.probe(Path(sys.executable), runner=lambda *a, **kw: probe_response())
        self.assertTrue(info['ok'])

    def test_probe_broken_interpreter(self):
        info = manager.probe(Path(sys.executable), runner=lambda *a, **kw: StubResult(code=1))
        self.assertFalse(info['ok'])

    def test_probe_timeout(self):
        import subprocess
        def timeout(*a, **kw):
            raise subprocess.TimeoutExpired('python', 12)
        self.assertEqual(manager.probe(Path(sys.executable), runner=timeout)['reason'], 'TimeoutExpired')

    def test_select_prefers_portable_over_venv(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for p in (base/'runtime/python/python.exe', base/'.venv/Scripts/python.exe'):
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b'exe')
            self.assertEqual(manager.select(base, sys.executable,
                     runner=lambda *a, **kw: probe_response())[0], 'portable')

    def test_select_skips_missing_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for p in (base/'runtime/python/python.exe', base/'.venv/Scripts/python.exe'):
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b'exe')
            def fake_runner(command, **kw):
                if 'runtime/python' in command[0].replace('\\', '/'):
                    return probe_response(['psutil'])
                return probe_response()
            self.assertEqual(manager.select(base, sys.executable, runner=fake_runner)[0], 'venv')

    def test_repair_requires_online_or_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'requirements.txt').write_text('psutil>=5.9.0\n')
            self.assertEqual(silent_call(manager.repair, Path(tmp)), 2)

    def test_offline_no_wheels_refuses_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'requirements.txt').write_text('psutil>=5.9.0\n')
            exe = root/'.venv/Scripts/python.exe'
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b'exe')
            def no_execution(*a, **kw):
                self.fail('Aucun lancement de pip attendu sans cache')
            self.assertEqual(silent_call(manager.repair, root, offline=True, runner=no_execution), 3)

    def test_tests_refuse_no_python(self):
        with patch.object(manager, 'select', return_value=None):
            self.assertEqual(silent_call(manager.run_tests), 3)

    def test_tests_call_python_without_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'tests').mkdir()
            (root/'tests/test_agentlocal_test_manager.py').write_text('')
            calls = []
            def fake(command, **kw):
                calls.append((command, kw))
                return StubResult()
            with patch.object(manager, 'select', return_value=('venv', Path(sys.executable), {'python':'3.14.7'})):
                rc = silent_call(manager.run_tests, 'full', root=root, runner=fake)
            self.assertEqual(rc, 0)
            self.assertEqual(calls[0][0][0], sys.executable)
            self.assertFalse(calls[0][1].get('shell', False))

    def test_safety_gate_blocks_under_512_mb(self):
        with patch.object(manager, 'available_memory', return_value=(4*2**30, 300*2**20)):
            self.assertEqual(silent_call(manager.safety_gate), 6)

    def test_safety_gate_allows_above_512_mb(self):
        with patch.object(manager, 'available_memory', return_value=(4*2**30, 900*2**20)):
            self.assertEqual(silent_call(manager.safety_gate), 0)

    def test_low_ram_blocks_full_tests(self):
        with patch.object(manager, 'select', return_value=('venv',Path(sys.executable),{'python':'3.14.7'})):
            with patch.object(manager, 'available_memory', return_value=(4*2**30, 400*2**20)):
                self.assertEqual(silent_call(manager.run_tests, mode='full', runner=lambda *a, **kw: self.fail('No subprocess')), 6)

    def test_low_ram_allows_quick_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'tests').mkdir()
            (root/'tests/test_agentlocal_test_manager.py').write_text('')
            with patch.object(manager, 'select', return_value=('venv',Path(sys.executable),{'python':'3.14.7'})):
                with patch.object(manager, 'available_memory', return_value=(4*2**30, 400*2**20)):
                    self.assertEqual(silent_call(manager.run_tests, mode='quick', root=root, runner=lambda *a,**kw: StubResult()), 0)

    def test_tests_propagate_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(manager, 'select', return_value=('venv',Path(sys.executable),{'python':'3.14.7'})):
                self.assertEqual(silent_call(manager.run_tests, root=Path(tmp), runner=lambda *a,**kw: StubResult(code=7)), 7)


if __name__ == '__main__':
    unittest.main()
