import unittest

from backends.deterministic_backend import interpret


class NaturalLanguageV2Tests(unittest.TestCase):
    def assert_action(self, message, action, target=None, count=1):
        result = interpret(message)
        self.assertTrue(result.get("understood"), msg=(message, result))
        actions = result.get("actions", [])
        self.assertEqual(len(actions), count, msg=(message, result))
        self.assertEqual(actions[0].get("action"), action, msg=(message, result))
        if target is not None:
            self.assertEqual(actions[0].get("target"), target, msg=(message, result))
        return result, actions

    def assert_unrecognized(self, message):
        result = interpret(message)
        self.assertFalse(result.get("understood"), msg=(message, result))
        self.assertEqual(result.get("actions", []), [], msg=(message, result))

    def test_indirect_need_finds_file(self):
        _, actions = self.assert_action(
            "J'ai besoin du rapport que j'ai mis dans Documents",
            "find_filesystem_item",
            "documents",
        )
        self.assertEqual(actions[0]["params"]["name"], "rapport")
        self.assertEqual(actions[0]["params"]["item_type"], "file")

    def test_possessive_search_is_cleaned(self):
        _, actions = self.assert_action(
            "Tu peux retrouver mon rapport dans mes documents ?",
            "find_filesystem_item",
            "documents",
        )
        self.assertEqual(actions[0]["params"]["name"], "rapport")

    def test_open_relative_clause(self):
        _, actions = self.assert_action(
            "Ouvre-moi le rapport qui est dans Documents",
            "open_file",
            "documents",
        )
        self.assertEqual(actions[0]["params"]["file_name"], "rapport")

    def test_polite_open_relative_clause(self):
        _, actions = self.assert_action(
            "Peux-tu m'ouvrir le fichier rapport qui est dans Documents ?",
            "open_file",
            "documents",
        )
        self.assertEqual(actions[0]["params"]["file_name"], "rapport")

    def test_go_fetch_file(self):
        self.assert_action(
            "Va me chercher rapport.pdf dans Téléchargements",
            "find_filesystem_item",
            "downloads",
        )

    def test_show_my_files(self):
        self.assert_action(
            "Montre moi mes fichiers dans Documents",
            "list_directory",
            "documents",
        )

    def test_fais_voir(self):
        self.assert_action(
            "Fais voir ce qu'il y a dans Documents",
            "list_directory",
            "documents",
        )

    def test_can_i_see_documents(self):
        self.assert_action(
            "Je peux voir les documents ?",
            "list_directory",
            "documents",
        )

    def test_singular_downloads_wording(self):
        self.assert_action(
            "liste mes telechargement",
            "list_directory",
            "downloads",
        )

    def test_word_is_open(self):
        self.assert_action("Word est ouvert ?", "check_application", "word")

    def test_word_is_running_question(self):
        self.assert_action("Est ce que Word tourne ?", "check_application", "word")

    def test_word_functional_request(self):
        self.assert_action(
            "Ouvre le truc pour écrire un document",
            "open_application",
            "word",
        )

    def test_word_functional_request_polite(self):
        self.assert_action(
            "Peux-tu m'ouvrir le truc pour écrire un document ?",
            "open_application",
            "word",
        )

    def test_word_need_request(self):
        self.assert_action(
            "J'ai besoin d'écrire un document",
            "open_application",
            "word",
        )

    def test_excel_functional_request(self):
        self.assert_action(
            "Ouvre l'application pour faire un tableau Excel",
            "open_application",
            "excel",
        )

    def test_powerpoint_functional_request(self):
        self.assert_action(
            "Ouvre ce qu'il faut pour préparer une présentation",
            "open_application",
            "powerpoint",
        )

    def test_calculator_functional_request(self):
        self.assert_action(
            "Ouvre l'outil pour faire des calculs",
            "open_application",
            "calculator",
        )

    def test_capture_functional_request(self):
        self.assert_action(
            "Ouvre l'outil pour faire une capture d'écran",
            "open_application",
            "snipping_tool",
        )

    def test_paint_functional_request(self):
        self.assert_action(
            "Ouvre le logiciel pour dessiner",
            "open_application",
            "paint",
        )

    def test_known_github_typo_one(self):
        self.assert_action("ouvre gitub", "open_website", "github")

    def test_known_github_typo_two(self):
        self.assert_action("ouvre githb", "open_website", "github")

    def test_known_excel_typo(self):
        self.assert_action("ouvre exel", "open_application", "excel")

    def test_filename_is_not_typo_corrected(self):
        _, actions = self.assert_action("ouvre rapprot", "open_file_auto", "auto")
        self.assertEqual(actions[0]["params"]["file_name"], "rapprot")

    def test_multi_target_then(self):
        result = interpret("ouvre Word puis GitHub")
        actions = result.get("actions", [])
        self.assertEqual(len(actions), 2, msg=result)
        self.assertEqual(actions[0]["action"], "open_application")
        self.assertEqual(actions[0]["target"], "word")
        self.assertEqual(actions[1]["action"], "open_website")
        self.assertEqual(actions[1]["target"], "github")

    def test_multi_target_and_then(self):
        result = interpret("ouvre Word et ensuite GitHub")
        actions = result.get("actions", [])
        self.assertEqual(len(actions), 2, msg=result)
        self.assertEqual(actions[0]["target"], "word")
        self.assertEqual(actions[1]["target"], "github")

    def test_move_put_wording(self):
        self.assert_action(
            "Mets rapport.pdf dans Archives",
            "move_file_within_root",
            "documents",
        )

    def test_move_bouge_wording(self):
        self.assert_action(
            "Bouge rapport.pdf dans Archives",
            "move_file_within_root",
            "documents",
        )

    def test_throw_file_means_recycle_bin_delete(self):
        self.assert_action("Jette brouillon.txt", "delete_file_auto", "auto")

    def test_remove_file_means_recycle_bin_delete(self):
        self.assert_action("Enlève brouillon.txt", "delete_file_auto", "auto")

    def test_casual_delete_without_file_context_is_not_inferred(self):
        self.assert_unrecognized("Enlève rapport")

    def test_permanent_delete_is_still_blocked(self):
        self.assert_unrecognized("Tu peux supprimer définitivement brouillon.txt ?")

    def test_unknown_functional_request_is_not_file(self):
        self.assert_unrecognized("Ouvre le truc pour pirater un compte")

    def assert_blocked_execution_target(self, message):
        result = interpret(message)
        self.assertTrue(result.get("understood"), msg=(message, result))
        self.assertEqual(result.get("actions"), [], msg=(message, result))
        self.assertTrue(result.get("conversation"), msg=(message, result))
        self.assertIn("interdite", result.get("reply", "").lower(), msg=(message, result))

    def test_powershell_target_is_blocked(self):
        self.assert_blocked_execution_target("ouvre powershell")

    def test_cmd_target_is_blocked(self):
        self.assert_blocked_execution_target("ouvre cmd")

    def test_terminal_target_is_blocked(self):
        self.assert_blocked_execution_target("ouvre le terminal")

    def test_windows_terminal_target_is_blocked(self):
        self.assert_blocked_execution_target("ouvre windows terminal")

    def test_file_named_terminal_txt_remains_openable(self):
        _, actions = self.assert_action(
            "ouvre le fichier terminal.txt dans Documents",
            "open_file",
            "documents",
        )
        self.assertEqual(actions[0]["params"]["file_name"], "terminal.txt")

    def test_hello_is_local_conversation(self):
        result = interpret("bonjour")
        self.assertTrue(result.get("understood"))
        self.assertEqual(result.get("actions"), [])
        self.assertTrue(result.get("conversation"))
        self.assertIn("Bonjour", result.get("reply", ""))

    def test_thanks_is_local_conversation(self):
        result = interpret("merci beaucoup")
        self.assertTrue(result.get("conversation"))
        self.assertEqual(result.get("actions"), [])

    def test_help_is_local_conversation(self):
        result = interpret("tu sais faire quoi ?")
        self.assertTrue(result.get("conversation"))
        self.assertIn("Je peux", result.get("reply", ""))

    def test_identity_is_local_conversation(self):
        result = interpret("tu es qui ?")
        self.assertTrue(result.get("conversation"))
        self.assertIn("AgentLocal", result.get("reply", ""))

    def test_vague_open_file_is_not_inferred(self):
        self.assert_unrecognized("ouvre ce fichier")

    def test_vague_delete_file_is_not_inferred(self):
        self.assert_unrecognized("supprime le fichier")

    def test_vague_move_file_is_not_inferred(self):
        self.assert_unrecognized("deplace le fichier dans Archives")

    def test_vague_rename_file_is_not_inferred(self):
        self.assert_unrecognized("renomme le fichier en test.txt")

    def test_vague_read_file_is_not_inferred(self):
        self.assert_unrecognized("lis le fichier")

    def test_named_extensionless_file_still_works(self):
        _, actions = self.assert_action("ouvre rapport", "open_file_auto", "auto")
        self.assertEqual(actions[0]["params"]["file_name"], "rapport")

    def test_unknown_machine_action_is_not_invented(self):
        self.assert_unrecognized("Peux-tu formater complètement le disque ?")

    def test_unknown_restart_action_is_not_invented(self):
        self.assert_unrecognized("Redémarre complètement l'ordinateur")

    def test_literal_file_content_remains_exact(self):
        _, actions = self.assert_action(
            "S'il te plaît, crée notes.txt dans Documents avec le contenu Bonjour, merci !",
            "create_file_with_content",
            "documents",
        )
        self.assertEqual(actions[0]["params"]["content"], "Bonjour, merci !")


if __name__ == "__main__":
    unittest.main()
