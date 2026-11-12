"""Tests non destructifs des ameliorations V12.5.2."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for candidate in (ROOT, APP):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import agent
from command_sequences import (
    split_explicit_sequence,
    describe_last_sequence,
    remember_sequence,
)
from session_context import clear_session_context, set_last_entity
from backends.deterministic_backend import interpret as deterministic_interpret


class SequenceParserTests(unittest.TestCase):
    def test_two_explicit_steps(self):
        self.assertEqual(
            split_explicit_sequence("ouvre Word puis ouvre Excel"),
            (["ouvre Word", "ouvre Excel"], None),
        )

    def test_connectors_with_punctuation(self):
        self.assertEqual(
            split_explicit_sequence("liste mes Documents, ensuite montre l'etat de mon PC"),
            (["liste mes Documents", "montre l'etat de mon PC"], None),
        )

    def test_semicolon_and_et_apres(self):
        steps, error = split_explicit_sequence("ouvre word; ouvre excel et après ouvre github")
        self.assertIsNone(error)
        self.assertEqual(len(steps), 3)

    def test_no_implicit_et_split(self):
        self.assertEqual(split_explicit_sequence("ouvre word et excel"), (None, None))

    def test_quotes_not_split(self):
        self.assertEqual(
            split_explicit_sequence('affiche le texte « ouvre Word puis ouvre Excel »'),
            (None, None),
        )

    def test_literal_content_not_split(self):
        self.assertEqual(
            split_explicit_sequence('crée notes.txt avec le contenu bonjour puis ouvre Word'),
            (None, None),
        )

    def test_no_incomplete_second_command(self):
        steps, error = split_explicit_sequence('ouvre word puis Excel')
        self.assertIsNone(steps)
        self.assertIn('incomplete', error)

    def test_block_mixed_unrecognized_sensitive_tail(self):
        steps, error = split_explicit_sequence('ouvre word puis ouvre excel ; supprime mes documents')
        self.assertIsNone(steps)
        self.assertIn('incomplete', error)

    def test_incomplete_trailing_connectors_block_before_any_action(self):
        commands = (
            "ouvre Word puis", "ouvre Word puis.",
            "ouvre Word ensuite", "ouvre Word et après",
            "ouvre Word puis ouvre Excel ensuite",
            "ouvre Word puis ouvre Excel puis",
        )
        for command in commands:
            with self.subTest(command=command):
                steps, error = split_explicit_sequence(command)
                self.assertIsNone(steps)
                self.assertIsNotNone(error)
                with patch.object(agent, "execute_action") as execute:
                    response = agent.process_instruction(command)
                execute.assert_not_called()
                self.assertIn("Aucune action lancee", response)

    def test_connector_inside_quotes_does_not_trigger_block(self):
        self.assertEqual(
            split_explicit_sequence('affiche le texte « ouvre Word puis »'),
            (None, None),
        )

    def test_bounded_max_steps(self):
        steps, error = split_explicit_sequence(' puis '.join(['ouvre word'] * 5))
        self.assertIsNone(steps)
        self.assertIn('Maximum 4', error)


class BehaviorIntegrationTests(unittest.TestCase):
    def setUp(self):
        agent.DEBUG = False
        clear_session_context()
        # Pas d'ecriture de memoire / pas de lancement d'application.
        self.learning = patch.object(agent, "learn_from_actions", return_value=[])
        self.learning.start()
        self.addCleanup(self.learning.stop)

    def test_sequential_actions_success_and_history(self):
        with patch.object(agent, "execute_action", side_effect=[
            (True, "Word est ouvert"), (True, "Excel est ouvert")
        ]) as execute:
            reply = agent.process_instruction("ouvre Word puis ouvre Excel")
        self.assertEqual(execute.call_count, 2)
        self.assertIn("Etape 1/2 reussie", reply)
        self.assertIn("Etape 2/2 reussie", reply)
        self.assertIn("2. ouvre Excel : reussie", agent.process_instruction("resume les dernieres etapes"))

    def test_block_any_sensitive_action_before_execution(self):
        with patch.object(agent, "execute_action") as execute:
            reply = agent.process_instruction("ouvre Word puis ferme Excel")
        execute.assert_not_called()
        self.assertIn("Aucune action lancee", reply)

    def test_stop_after_first_execution_failure(self):
        with patch.object(agent, "execute_action", return_value=(False, "Echec simulé")) as execute:
            reply = agent.process_instruction("ouvre Word puis ouvre Excel")
        self.assertEqual(execute.call_count, 1)
        self.assertIn("1 etape(s) non executee(s)", reply)
        self.assertIn("2. ouvre Excel : non executee", describe_last_sequence())

    def test_negation_does_not_execute_any_step(self):
        with patch.object(agent, "execute_action") as execute:
            reply = agent.process_instruction("n'ouvre pas Word puis ouvre Excel")
        execute.assert_not_called()
        self.assertIn("Aucune action lancee", reply)

    def test_llm_invented_target_rejected(self):
        altered = deterministic_interpret("ouvre Word")
        altered["actions"][0]["target"] = "excel"
        with patch.object(agent, "interpret_instruction", return_value=altered), \
                patch.object(agent, "execute_action") as execute:
            reply = agent.process_instruction("ouvre Word puis ouvre Excel")
        execute.assert_not_called()
        self.assertIn("moteur de securite local", reply)

    def test_relaunch_context_only_after_an_entity(self):
        self.assertIsNone(agent._resolve_session_reference_command("rouvre-le"))
        set_last_entity("application", "vscode", "open_application")
        self.assertEqual(agent._resolve_session_reference_command("rouvre-le"), "ouvre vscode")
        set_last_entity("website", "github", "open_website")
        self.assertEqual(agent._resolve_session_reference_command("relance-la"), "ouvre github")

    def test_learned_expression_cycle_is_bounded(self):
        def cycle(value):
            return "b" if value == "a" else "a"
        with patch.object(agent, "resolve_learned_expression", side_effect=cycle), \
                patch.object(agent, "interpret_instruction") as interprets:
            reply = agent.process_instruction("a")
        interprets.assert_not_called()
        self.assertIn("trop de reformulations", reply)

    def test_history_remains_in_ram_only(self):
        remember_sequence(["ouvre Word", "ouvre Excel"], [True], False)
        self.assertIn("non executee", describe_last_sequence())


if __name__ == "__main__":
    unittest.main()
