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
import controlled_local_tools
from backends import backend_manager
from backends.deterministic_backend import interpret


class FileAnalysisLanguageV108Tests(unittest.TestCase):
    def test_metadata(self):
        result = interpret('donne moi les infos de rapport.pdf dans Documents')
        self.assertTrue(result.get('understood'), result)
        action = result['actions'][0]
        self.assertEqual(action['action'], 'inspect_file_metadata')
        self.assertEqual(action['target'], 'documents')
        self.assertEqual(action['params']['file_name'], 'rapport.pdf')

    def test_sha256(self):
        result = interpret('calcule le sha256 de rapport.pdf dans Documents')
        action = result['actions'][0]
        self.assertEqual(action['action'], 'calculate_file_sha256')
        self.assertEqual(action['target'], 'documents')

    def test_compare(self):
        result = interpret('compare a.txt et b.txt dans Documents')
        action = result['actions'][0]
        self.assertEqual(action['action'], 'compare_files_sha256')
        self.assertEqual(action['params']['left_name'], 'a.txt')
        self.assertEqual(action['params']['right_name'], 'b.txt')

    def test_duplicates(self):
        for text in (
            'cherche les doublons dans Documents',
            'trouve les fichiers en double dans Téléchargements',
            'y a des doublons dans Documents',
        ):
            with self.subTest(text=text):
                result = interpret(text)
                self.assertTrue(result.get('understood'), result)
                self.assertEqual(result['actions'][0]['action'], 'find_duplicate_files')

    def test_negative_does_nothing(self):
        result = interpret('cherche pas les doublons dans Documents')
        self.assertTrue(result.get('understood'), result)
        self.assertEqual(result.get('actions'), [])


class FileAnalysisContractV108Tests(unittest.TestCase):
    def test_valid_contracts(self):
        cases = [
            {'schema_version': 1, 'action': 'inspect_file_metadata', 'target': 'documents', 'params': {'file_name': 'rapport.pdf'}},
            {'schema_version': 1, 'action': 'calculate_file_sha256', 'target': 'documents', 'params': {'file_name': 'rapport.pdf'}},
            {'schema_version': 1, 'action': 'compare_files_sha256', 'target': 'documents', 'params': {'left_name': 'a.txt', 'right_name': 'b.txt'}},
            {'schema_version': 1, 'action': 'find_duplicate_files', 'target': 'documents', 'params': {}},
        ]
        for action in cases:
            with self.subTest(action=action['action']):
                self.assertEqual(agent.validate_action(action), (True, None))

    def test_bad_root_rejected(self):
        action = {'schema_version': 1, 'action': 'find_duplicate_files', 'target': 'windows', 'params': {}}
        self.assertFalse(agent.validate_action(action)[0])

    def test_bad_path_rejected(self):
        action = {'schema_version': 1, 'action': 'calculate_file_sha256', 'target': 'documents', 'params': {'file_name': '..\\secret.txt'}}
        self.assertFalse(agent.validate_action(action)[0])


class FileAnalysisToolV108Tests(unittest.TestCase):
    def _patch_files(self, base):
        def allowed_root(name):
            self.assertEqual(name, 'documents')
            return base

        def unique(name, root_name=None, item_type='any'):
            path = base / name
            if not path.is_file():
                return False, 'absent'
            return True, {'root_name': 'documents', 'relative_path': name, 'item_type': 'file'}

        def resolve_existing(root_name, relative_path, expected='any', allow_root=False):
            path = base / Path(str(relative_path).replace('\\', '/'))
            if not path.exists():
                return False, 'absent'
            if expected == 'file' and not path.is_file():
                return False, 'not file'
            return True, path

        return patch.multiple(
            controlled_local_tools,
            resolve_allowed_root=allowed_root,
            get_unique_reference_for_context=unique,
            resolve_existing_inside_root=resolve_existing,
            relative_display=lambda _root, path: f'Documents\\{Path(path).relative_to(base)}',
        )

    def test_metadata_and_hash(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / 'rapport.txt').write_text('bonjour', encoding='utf-8')
            with self._patch_files(base), patch.object(controlled_local_tools, 'is_blocked_file_type', return_value=False):
                ok, msg = controlled_local_tools.inspect_file_metadata('documents', 'rapport.txt', True, 'manual')
                self.assertTrue(ok, msg)
                self.assertIn('rapport.txt', msg)
                ok, msg = controlled_local_tools.calculate_file_sha256('documents', 'rapport.txt', True, 'manual')
                self.assertTrue(ok, msg)
                self.assertIn('SHA-256', msg)

    def test_compare_equal_and_different(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / 'a.txt').write_text('meme', encoding='utf-8')
            (base / 'b.txt').write_text('meme', encoding='utf-8')
            (base / 'c.txt').write_text('autre contenu', encoding='utf-8')
            with self._patch_files(base), patch.object(controlled_local_tools, 'is_blocked_file_type', return_value=False):
                ok, msg = controlled_local_tools.compare_files_sha256('documents', 'a.txt', 'b.txt', True, 'manual')
                self.assertTrue(ok, msg)
                self.assertIn('identiques', msg)
                ok, msg = controlled_local_tools.compare_files_sha256('documents', 'a.txt', 'c.txt', True, 'manual')
                self.assertTrue(ok, msg)
                self.assertIn('différents', msg)

    def test_duplicate_search_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / 'a.txt').write_text('copie', encoding='utf-8')
            (base / 'b.txt').write_text('copie', encoding='utf-8')
            (base / 'unique.txt').write_text('different', encoding='utf-8')
            with patch.object(controlled_local_tools, 'resolve_allowed_root', return_value=base), \
                 patch.object(controlled_local_tools, 'is_blocked_file_type', return_value=False), \
                 patch.object(controlled_local_tools.base_file_tools, 'is_hard_protected_path', return_value=False), \
                 patch.object(controlled_local_tools.base_file_tools, 'is_reparse_point', return_value=False), \
                 patch.object(controlled_local_tools.base_file_tools, 'is_hidden_or_system', return_value=False), \
                 patch.object(controlled_local_tools, 'relative_display', side_effect=lambda _root, path: f'Documents\\{Path(path).relative_to(base)}'):
                ok, msg = controlled_local_tools.find_duplicate_files('documents', True, 'manual')
            self.assertTrue(ok, msg)
            self.assertIn('Doublons exacts', msg)
            self.assertIn('a.txt', msg)
            self.assertIn('b.txt', msg)
            self.assertTrue((base / 'a.txt').exists())
            self.assertTrue((base / 'b.txt').exists())

    def test_routine_rejected(self):
        ok, _ = controlled_local_tools.find_duplicate_files('documents', True, 'routine')
        self.assertFalse(ok)


class FileAnalysisRoutingV108Tests(unittest.TestCase):
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
            result = backend_manager.interpret('cherche les doublons dans Documents')
            self.assertEqual(result.get('backend'), 'deterministic')
            self.assertEqual(DummyLlama.calls, 0)
        finally:
            backend_manager.select_backend = original


if __name__ == '__main__':
    unittest.main()
