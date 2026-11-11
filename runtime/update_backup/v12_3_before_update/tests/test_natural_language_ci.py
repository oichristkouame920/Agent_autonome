import unittest

from backends import backend_manager
from backends.deterministic_backend import interpret


class IvorianSpokenFrenchTests(unittest.TestCase):
    def assert_action(self, text, action, target=None, operation=None):
        result = interpret(text)
        self.assertTrue(result.get('understood'), msg=(text, result))
        actions = result.get('actions', [])
        self.assertGreaterEqual(len(actions), 1, msg=(text, result))
        first = actions[0]
        self.assertEqual(first.get('action'), action, msg=(text, result))
        if target is not None:
            self.assertEqual(first.get('target'), target, msg=(text, result))
        if operation is not None:
            self.assertEqual(first.get('params', {}).get('operation'), operation, msg=(text, result))
        return result

    def assert_no_action(self, text, understood=None, conversation=None):
        result = interpret(text)
        self.assertFalse(result.get('actions', []), msg=(text, result))
        if understood is not None:
            self.assertEqual(bool(result.get('understood')), understood, msg=(text, result))
        if conversation is not None:
            self.assertEqual(bool(result.get('conversation')), conversation, msg=(text, result))
        return result

    def test_apps_and_sites_with_spoken_markers(self):
        cases = [
            ('faut ouvrir edge', 'open_application', 'edge'),
            ('faut lancer word', 'open_application', 'word'),
            ('faut me lancer vscode', 'open_application', 'vscode'),
            ('ouvre moi github là', 'open_website', 'github'),
            ('je veux aller sur google là', 'open_website', 'google.com'),
            ('mets moi sur chatgpt', 'open_website', 'chatgpt'),
            ('stp ouvre moi edge', 'open_application', 'edge'),
            ("s'il te plaît faut lancer teams", 'open_application', 'teams'),
            ('bon ouvre edge', 'open_application', 'edge'),
            ('donc ouvre word', 'open_application', 'word'),
            ('ouvre microsoft edge là', 'open_application', 'edge'),
            ('va sur github là', 'open_website', 'github'),
            ('ouvre mes fichiers là', 'open_application', 'explorer'),
            ('je veux voir mes fichiers', 'open_application', 'explorer'),
            ('ouvre explorateur là', 'open_application', 'explorer'),
        ]
        for text, action, target in cases:
            with self.subTest(text=text):
                self.assert_action(text, action, target)

    def test_spoken_status_checks(self):
        cases = [
            ('tu peux voir si teams tourne là', 'teams'),
            ('teams est lancé même ?', 'teams'),
            ('word est ouvert ou bien ?', 'word'),
            ('vscode tourne ou bien ?', 'vscode'),
            ('check si edge est ouvert', 'edge'),
            ('regarde un peu si excel est lancé', 'excel'),
            ('dis moi si word tourne là', 'word'),
            ('faut vérifier si teams est ouvert', 'teams'),
            ('edge est ouvert même ?', 'edge'),
            ('excel fonctionne ou bien ?', 'excel'),
        ]
        for text, target in cases:
            with self.subTest(text=text):
                self.assert_action(text, 'check_application', target)

    def test_spoken_window_commands(self):
        cases = [
            ('agrandis edge là', 'edge', 'maximize'),
            ('réduis word un peu', 'word', 'minimize'),
            ('mets vscode à gauche là', 'vscode', 'snap_left'),
            ('mets edge à droite là', 'edge', 'snap_right'),
            ('ramène word devant', 'word', 'focus'),
            ('mets word devant là', 'word', 'focus'),
            ('passe sur teams là', 'teams', 'focus'),
            ('mets edge en grand là', 'edge', 'maximize'),
        ]
        for text, target, operation in cases:
            with self.subTest(text=text):
                self.assert_action(text, 'manage_window', target, operation)

    def test_spoken_routine_commands(self):
        cases = [
            'faut lancer ma routine',
            'lance ma routine là',
            'prépare moi pour le boulot là',
            'prépare moi pour travailler hein',
            'commence ma routine là',
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assert_action(text, 'run_routine', 'work_start')

    def test_non_destructive_file_phrases(self):
        cases = [
            ('ouvre le dossier documents là', 'open_directory', 'documents'),
            ('montre moi documents là', 'list_directory', 'documents'),
            ('fais voir ce qu\'il y a dans téléchargements là', 'list_directory', 'downloads'),
            ('cherche rapport dans documents là', 'find_filesystem_item', 'documents'),
            ('retrouve moi rapport là', 'find_filesystem_item', 'auto'),
            ('ouvre rapport là', 'open_file_auto', 'auto'),
        ]
        for text, action, target in cases:
            with self.subTest(text=text):
                self.assert_action(text, action, target)

    def test_ivoirian_listing_question(self):
        self.assert_action("y a quoi dans documents là ?", "list_directory", "documents")
        self.assert_action("il y a quoi dans téléchargements là ?", "list_directory", "downloads")

    def test_local_ivoirian_small_talk_is_conversation_only(self):
        for text in ("on est ensemble", "y a pas drap", "c'est comment ?"):
            with self.subTest(text=text):
                result = self.assert_no_action(text, understood=True, conversation=True)
                self.assertTrue(result.get("reply"))

    def test_ambiguous_spoken_references_do_not_execute(self):
        cases = [
            'ouvre ça là',
            'ferme ça là',
            'mets ça là-bas',
            'ouvre tout ça',
            'ferme tout ça',
            'ouvre le truc là',
            'ferme le truc là',
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assert_no_action(text)

    def test_window_organization_stays_non_autonomous(self):
        cases = [
            'arrange un peu mes fenêtres',
            'range mes fenêtres un peu',
            'organise mes fenêtres là',
        ]
        for text in cases:
            with self.subTest(text=text):
                result = self.assert_no_action(text, understood=True, conversation=True)
                self.assertIn('ne choisis pas', result.get('reply', ''))

    def test_vague_work_phrase_does_not_launch_routine(self):
        for text in ('on commence le boulot', 'on bosse maintenant', 'faut travailler', 'faut gérer ça'):
            with self.subTest(text=text):
                self.assert_no_action(text)

    def test_oral_negations_are_atomic_no_ops(self):
        cases = [
            'faut pas ouvrir edge',
            'ouvre pas edge',
            'ne lance pas teams hein',
            'faut pas toucher à mes fichiers',
            'supprime pas rapport',
            'ferme pas explorateur',
            'réduis pas word',
            'agrandis pas edge là',
            'lance pas ma routine',
            'va pas sur google',
        ]
        for text in cases:
            with self.subTest(text=text):
                result = self.assert_no_action(text, understood=True, conversation=True)
                self.assertIn('je ne fais rien', result.get('reply', '').lower())

    def test_forbidden_shell_requests_are_understood_but_refused(self):
        cases = [
            'faut ouvrir powershell',
            'ouvre cmd là',
            'lance terminal là',
            'ouvre edge puis powershell',
            'ouvre github et cmd',
            'bon lance wsl là',
        ]
        for text in cases:
            with self.subTest(text=text):
                result = self.assert_no_action(text, understood=True, conversation=True)
                self.assertIn('interdite', result.get('reply', '').lower())

    def test_destructive_file_commands_with_spoken_tail_require_precision(self):
        cases = [
            'supprime rapport là',
            'efface rapport hein',
            'mets rapport dans archives là',
            'copie rapport dans archives là',
            'renomme rapport en final là',
        ]
        for text in cases:
            with self.subTest(text=text):
                result = self.assert_no_action(text, understood=True, conversation=True)
                self.assertIn('formulation', result.get('reply', '').lower())

    def test_precise_destructive_command_still_works(self):
        self.assert_action('supprime rapport.txt dans Documents', 'delete_file', 'documents')
        self.assert_action('efface rapport.txt dans Documents', 'delete_file', 'documents')


class IvorianSpokenRoutingTests(unittest.TestCase):
    def test_spoken_high_confidence_requests_bypass_llama(self):
        class DummyLlama:
            calls = 0

            @classmethod
            def interpret(cls, _message):
                cls.calls += 1
                return {'schema_version': 1, 'backend': 'llama', 'understood': False, 'actions': []}

        original = backend_manager.select_backend
        try:
            backend_manager.select_backend = lambda: (True, 'llama', DummyLlama, None)
            for text in (
                'faut ouvrir edge',
                'teams est lancé même ?',
                'mets vscode à gauche là',
                'faut lancer ma routine',
                'faut pas ouvrir edge',
                'faut ouvrir powershell',
                'supprime rapport là',
            ):
                with self.subTest(text=text):
                    result = backend_manager.interpret(text)
                    self.assertEqual(result.get('backend'), 'deterministic')
                    self.assertEqual(result.get('routing'), 'deterministic_preflight')
            self.assertEqual(DummyLlama.calls, 0)
        finally:
            backend_manager.select_backend = original


if __name__ == '__main__':
    unittest.main()
