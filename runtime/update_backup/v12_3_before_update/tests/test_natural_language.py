import unittest

from backends.deterministic_backend import interpret


class NaturalLanguageTests(unittest.TestCase):
    def assert_action(self, message, action, target=None):
        result = interpret(message)
        self.assertTrue(result.get("understood"), msg=(message, result))
        actions = result.get("actions", [])
        self.assertEqual(len(actions), 1, msg=(message, result))
        self.assertEqual(actions[0].get("action"), action, msg=(message, result))
        if target is not None:
            self.assertEqual(actions[0].get("target"), target, msg=(message, result))
        return result, actions[0]

    def test_existing_command_stays_compatible(self):
        result, action = self.assert_action("ouvre github", "open_website", "github")
        self.assertFalse(result.get("natural_language", False))

    def test_polite_open_website(self):
        result, _ = self.assert_action(
            "Peux-tu m'ouvrir GitHub s'il te plaît ?",
            "open_website",
            "github",
        )
        self.assertTrue(result.get("natural_language"))

    def test_polite_open_application(self):
        self.assert_action("Est-ce que tu peux ouvrir Word ?", "open_application", "word")

    def test_polite_close_application(self):
        self.assert_action("Tu peux me fermer Word, stp ?", "close_application", "word")

    def test_find_file(self):
        _, action = self.assert_action(
            "S'il te plaît, cherche-moi le fichier rapport dans Documents.",
            "find_filesystem_item",
            "documents",
        )
        self.assertEqual(action["params"]["item_type"], "file")
        self.assertEqual(action["params"]["name"], "rapport")

    def test_list_natural_question(self):
        self.assert_action(
            "Tu peux me montrer ce qu'il y a dans mes Téléchargements ?",
            "list_directory",
            "downloads",
        )

    def test_open_folder_conjugated(self):
        self.assert_action(
            "J'aimerais que tu ouvres le dossier Cours dans Documents.",
            "open_directory",
            "documents",
        )

    def test_read_file_conjugated(self):
        _, action = self.assert_action(
            "Je voudrais que tu lises le fichier budget dans Documents.",
            "read_file_content",
            "documents",
        )
        self.assertEqual(action["params"]["file_name"], "budget")

    def test_read_file_give_content(self):
        _, action = self.assert_action(
            "Donne-moi le contenu du fichier notes.txt dans Documents",
            "read_file_content",
            "documents",
        )
        self.assertEqual(action["params"]["file_name"], "notes.txt")

    def test_create_folder(self):
        self.assert_action(
            "Peux-tu créer un dossier Factures dans Documents ?",
            "create_folder",
            "documents",
        )

    def test_create_file_preserves_literal_content(self):
        _, action = self.assert_action(
            "Peux-tu créer notes.txt dans Documents avec le contenu Merci ?",
            "create_file_with_content",
            "documents",
        )
        self.assertEqual(action["params"]["content"], "Merci ?")

    def test_rename(self):
        self.assert_action(
            "Est-ce que tu peux renommer rapport en rapport-final ?",
            "rename_file_auto",
            "auto",
        )

    def test_delete_synonym_is_still_single_file_action(self):
        self.assert_action(
            "Tu peux effacer brouillon.txt ?",
            "delete_file_auto",
            "auto",
        )

    def test_copy_synonym(self):
        _, action = self.assert_action(
            "Pourrais-tu dupliquer rapport.pdf de Documents vers Bureau ?",
            "copy_file_between_roots",
            "documents",
        )
        self.assertEqual(action["params"]["destination_root"], "desktop")

    def test_move_synonym(self):
        self.assert_action(
            "Tu peux ranger rapport.pdf dans le dossier Archives ?",
            "move_file_within_root",
            "documents",
        )

    def test_where_is_file(self):
        self.assert_action("Où se trouve le fichier contrat ?", "find_filesystem_item", "auto")

    def test_what_is_in_documents(self):
        self.assert_action("Qu'est-ce qu'il y a dans mes Documents ?", "list_directory", "documents")

    def test_routine_natural_infinitive(self):
        self.assert_action(
            "Peux-tu préparer mon environnement de travail ?",
            "run_routine",
            "work_start",
        )

    def test_routine_launch_natural_infinitive(self):
        self.assert_action(
            "Peux-tu lancer ma routine de travail ?",
            "run_routine",
            "work_start",
        )

    def test_check_application_natural_infinitive(self):
        self.assert_action(
            "Est-ce que tu peux vérifier si Word est ouvert ?",
            "check_application",
            "word",
        )

    def test_direct_where_question_with_politeness(self):
        self.assert_action(
            "Peux-tu me dire où se trouve le fichier contrat, stp ?",
            "find_filesystem_item",
            "auto",
        )

    def test_permanent_delete_remains_unrecognized(self):
        result = interpret("Tu peux supprimer définitivement brouillon.txt ?")
        self.assertFalse(result.get("understood"), msg=result)
        self.assertEqual(result.get("actions"), [])

    def test_unknown_natural_request_does_not_invent_action(self):
        result = interpret("Peux-tu redémarrer complètement l'ordinateur ?")
        self.assertFalse(result.get("understood"), msg=result)
        self.assertEqual(result.get("actions"), [])


if __name__ == "__main__":
    unittest.main()
