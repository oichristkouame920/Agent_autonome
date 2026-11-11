import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for item in (ROOT, ROOT / 'app'):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

import agent
import recursive_file_tools as rft
import session_undo
from backends import backend_manager
from backends.deterministic_backend import interpret


class UndoLanguageV107Tests(unittest.TestCase):
    def test_variants(self):
        phrases = (
            'annule la dernière opération fichier',
            'annule le dernier déplacement',
            'annule la dernière copie',
            'annule le dernier renommage',
            'remets le dernier fichier comme avant',
            'reviens sur le dernier déplacement',
        )
        for text in phrases:
            with self.subTest(text=text):
                result = interpret(text)
                self.assertTrue(result.get('understood'), result)
                self.assertEqual(result['actions'][0]['action'], 'undo_last_file_action')
                self.assertEqual(result['actions'][0]['target'], 'session')

    def test_negative_does_nothing(self):
        result = interpret("annule pas la dernière opération fichier")
        self.assertTrue(result.get('understood'), result)
        self.assertEqual(result.get('actions'), [])


class UndoContractV107Tests(unittest.TestCase):
    def test_contract(self):
        action = {
            'schema_version': 1,
            'action': 'undo_last_file_action',
            'target': 'session',
            'params': {},
        }
        self.assertEqual(agent.validate_action(action), (True, None))

    def test_wrong_target_rejected(self):
        action = {
            'schema_version': 1,
            'action': 'undo_last_file_action',
            'target': 'documents',
            'params': {},
        }
        self.assertFalse(agent.validate_action(action)[0])

    def test_bypasses_llama(self):
        class DummyLlama:
            calls = 0
            @classmethod
            def interpret(cls, _message):
                cls.calls += 1
                return {'schema_version': 1, 'backend': 'llama', 'understood': False, 'actions': []}
        original = backend_manager.select_backend
        try:
            backend_manager.select_backend = lambda: (True, 'llama', DummyLlama, None)
            result = backend_manager.interpret('annule la dernière opération fichier')
            self.assertEqual(result.get('backend'), 'deterministic')
            self.assertEqual(DummyLlama.calls, 0)
        finally:
            backend_manager.select_backend = original


class UndoToolV107Tests(unittest.TestCase):
    def setUp(self):
        session_undo.clear_last_file_undo()

    def tearDown(self):
        session_undo.clear_last_file_undo()

    def _policy(self):
        return {
            'file_undo_policy': {
                'enabled': True,
                'require_explicit_user_command': True,
                'allowed_operations': ['rename', 'move', 'copy'],
                'single_level': True,
                'maximum_age_seconds': 900,
                'copy_undo_mode': 'recycle_bin',
                'allow_from_routine': False,
                'allow_from_habit': False,
            }
        }

    def _patch_fs(self, base):
        roots = {'documents': base / 'Documents', 'downloads': base / 'Downloads'}
        for path in roots.values():
            path.mkdir(exist_ok=True)

        def root_path(name):
            return roots[name], None

        def resolve_existing(name, relative, expected='any', allow_root=False):
            path = roots[name] / Path(str(relative).replace('\\', '/')) if relative else roots[name]
            if not path.exists():
                return False, 'absent'
            if expected == 'file' and not path.is_file():
                return False, 'not file'
            if expected == 'dir' and not path.is_dir():
                return False, 'not dir'
            return True, path

        def resolve_new(name, relative, leaf_kind='file'):
            path = roots[name] / Path(str(relative).replace('\\', '/'))
            if path.exists():
                return False, 'exists'
            if not path.parent.exists():
                return False, 'parent absent'
            return True, path

        def display(name, path):
            return f'{name}\\{Path(path).relative_to(roots[name])}'

        return patch.multiple(
            rft,
            _root_path=root_path,
            resolve_existing_inside_root=resolve_existing,
            resolve_new_leaf_inside_root=resolve_new,
            relative_display=display,
        ), roots

    def test_undo_move(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            patches, roots = self._patch_fs(base)
            source = roots['documents'] / 'rapport.txt'
            source.write_text('abc', encoding='utf-8')
            dest_dir = roots['documents'] / 'Archives'
            dest_dir.mkdir()
            destination = dest_dir / 'rapport.txt'
            source.rename(destination)
            fp = rft.base.get_file_fingerprint(destination)
            session_undo.set_last_file_undo({
                'kind': 'move', 'source_root': 'documents', 'source_relative': 'rapport.txt',
                'destination_root': 'documents', 'destination_relative': 'Archives\\rapport.txt',
                'destination_fingerprint': list(fp),
            })
            with patches, patch.object(rft.base, 'get_filesystem_config', return_value=self._policy()):
                ok, msg = rft.undo_last_file_action(True, 'manual')
            self.assertTrue(ok, msg)
            self.assertTrue(source.exists())
            self.assertFalse(destination.exists())

    def test_changed_file_refuses_undo(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            patches, roots = self._patch_fs(base)
            dest_dir = roots['documents'] / 'Archives'; dest_dir.mkdir()
            destination = dest_dir / 'rapport.txt'
            destination.write_text('abc', encoding='utf-8')
            fp = rft.base.get_file_fingerprint(destination)
            session_undo.set_last_file_undo({
                'kind': 'move', 'source_root': 'documents', 'source_relative': 'rapport.txt',
                'destination_root': 'documents', 'destination_relative': 'Archives\\rapport.txt',
                'destination_fingerprint': list(fp),
            })
            destination.write_text('modifié', encoding='utf-8')
            with patches, patch.object(rft.base, 'get_filesystem_config', return_value=self._policy()):
                ok, _ = rft.undo_last_file_action(True, 'manual')
            self.assertFalse(ok)
            self.assertTrue(destination.exists())

    def test_copy_undo_uses_recycle_bin(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            patches, roots = self._patch_fs(base)
            destination = roots['downloads'] / 'copie.txt'
            destination.write_text('abc', encoding='utf-8')
            fp = rft.base.get_file_fingerprint(destination)
            session_undo.set_last_file_undo({
                'kind': 'copy', 'source_root': 'documents', 'source_relative': 'copie.txt',
                'destination_root': 'downloads', 'destination_relative': 'copie.txt',
                'destination_fingerprint': list(fp),
            })
            def recycle(path):
                Path(path).unlink()
                return True, None
            with patches, patch.object(rft.base, 'get_filesystem_config', return_value=self._policy()), \
                 patch.object(rft.base, 'send_file_to_recycle_bin', side_effect=recycle):
                ok, msg = rft.undo_last_file_action(True, 'manual')
            self.assertTrue(ok, msg)
            self.assertFalse(destination.exists())

    def test_routine_rejected(self):
        with patch.object(rft.base, 'get_filesystem_config', return_value=self._policy()):
            ok, _ = rft.undo_last_file_action(True, 'routine')
        self.assertFalse(ok)


if __name__ == '__main__':
    unittest.main()
