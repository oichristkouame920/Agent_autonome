import unittest

from backends import backend_manager
from backends.deterministic_backend import interpret


class NaturalLanguageV5CoverageTests(unittest.TestCase):
    def assert_action(self, text, action, target=None, operation=None):
        result = interpret(text)
        self.assertTrue(result.get("understood"), msg=(text, result))
        actions = result.get("actions", [])
        self.assertGreaterEqual(len(actions), 1, msg=(text, result))
        first = actions[0]
        self.assertEqual(first.get("action"), action, msg=(text, result))
        if target is not None:
            self.assertEqual(first.get("target"), target, msg=(text, result))
        if operation is not None:
            self.assertEqual(first.get("params", {}).get("operation"), operation, msg=(text, result))
        return result

    def assert_no_action(self, text):
        result = interpret(text)
        self.assertFalse(result.get("actions", []), msg=(text, result))
        return result

    def test_natural_app_and_site_variants(self):
        cases = [
            ("vas sur google", "open_website", "google.com"),
            ("ouvre google stp", "open_website", "google.com"),
            ("ouvre gitub", "open_website", "github"),
            ("ouvre chat gtp", "open_website", "chatgpt"),
            ("j'ai besoin que tu ouvres excel", "open_application", "excel"),
            ("pourrais-tu lancer teams ?", "open_application", "teams"),
        ]
        for text, action, target in cases:
            with self.subTest(text=text):
                self.assert_action(text, action, target)

    def test_natural_check_variants(self):
        cases = [
            ("dis moi si vscode est ouvert", "vscode"),
            ("dis-moi si teams est lancé", "teams"),
            ("peux tu regarder si word tourne", "word"),
            ("vscode est-il ouvert", "vscode"),
            ("teams est il lancé", "teams"),
        ]
        for text, target in cases:
            with self.subTest(text=text):
                self.assert_action(text, "check_application", target)

    def test_window_conjugation_variant(self):
        self.assert_action("réduit edge", "manage_window", "edge", "minimize")

    def test_routine_variants(self):
        for text in ("prépare-moi pour travailler", "prépare moi pour travailler", "commence ma routine"):
            with self.subTest(text=text):
                self.assert_action(text, "run_routine", "work_start")

    def test_global_file_requests_are_not_executed(self):
        for text in (
            "ouvre ceci", "ouvre tout", "ouvre tous mes fichiers", "ouvre tous les fichiers",
            "supprime tout", "efface tout", "supprime tous mes fichiers",
        ):
            with self.subTest(text=text):
                self.assert_no_action(text)

    def test_global_close_is_not_executed(self):
        for text in ("ferme tout", "ferme toutes les applications"):
            with self.subTest(text=text):
                self.assert_no_action(text)

    def test_mixed_allowed_and_forbidden_targets_are_atomic_refusals(self):
        for text in ("ouvre edge et powershell", "ouvre edge et cmd", "ouvre github et powershell"):
            with self.subTest(text=text):
                self.assert_no_action(text)

    def test_negations_do_not_execute(self):
        for text in (
            "n'ouvre pas edge", "ne ferme pas edge", "ne vérifie pas teams",
            "n'agrandis pas edge", "je veux pas ouvrir word", "pas la peine d'ouvrir edge",
        ):
            with self.subTest(text=text):
                self.assert_no_action(text)

    def test_ambiguous_window_organization_asks_for_precision(self):
        for text in ("mets mes fenêtres bien", "mets mes fenêtres correctement", "organise mon écran"):
            with self.subTest(text=text):
                result = self.assert_no_action(text)
                self.assertTrue(result.get("conversation"), msg=(text, result))
                self.assertIn("ne choisis pas", result.get("reply", ""))

    def test_trailing_politeness_does_not_become_a_file_name(self):
        cases = [
            ("ouvre microsoft edge s'il te plaît", "open_application", "edge"),
            ("ouvre google s'il te plaît", "open_website", "google.com"),
            ("ouvre edge, s'il te plaît", "open_application", "edge"),
        ]
        for text, action, target in cases:
            with self.subTest(text=text):
                self.assert_action(text, action, target)

    def test_trailing_politeness_keeps_global_and_blocked_requests_safe(self):
        for text in (
            "ouvre tout stp", "supprime tout stp", "ferme tout stp",
            "ouvre ceci stp", "ouvre ce fichier stp", "ouvre edge puis cmd stp",
        ):
            with self.subTest(text=text):
                self.assert_no_action(text)

    def test_trailing_politeness_is_removed_from_natural_file_lookup(self):
        result = self.assert_action("ouvre rapport stp", "open_file_auto", "auto")
        self.assertEqual(result["actions"][0]["params"]["file_name"], "rapport")


class NaturalLanguageV5RoutingTests(unittest.TestCase):
    def test_new_high_confidence_phrases_use_deterministic_preflight(self):
        class DummyLlama:
            @staticmethod
            def interpret(_message):
                return {"schema_version": 1, "backend": "llama", "understood": False, "actions": []}

        original = backend_manager.select_backend
        try:
            backend_manager.select_backend = lambda: (True, "llama", DummyLlama, None)
            for text in ("vas sur google", "dis moi si vscode est ouvert", "réduit edge", "prépare-moi pour travailler"):
                with self.subTest(text=text):
                    result = backend_manager.interpret(text)
                    self.assertEqual(result.get("backend"), "deterministic")
                    self.assertEqual(result.get("routing"), "deterministic_preflight")
        finally:
            backend_manager.select_backend = original

    def test_unsafe_mixed_request_is_refused_by_preflight(self):
        result = backend_manager._deterministic_preflight("ouvre edge et powershell")
        self.assertIsNotNone(result)
        self.assertEqual(result.get("actions"), [])
        self.assertTrue(result.get("conversation"))
        self.assertIn("interdite", result.get("reply", "").lower())


if __name__ == "__main__":
    unittest.main()
