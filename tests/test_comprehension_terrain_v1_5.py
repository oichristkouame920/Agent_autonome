"""Tests de retour terrain 13 novembre : simulation uniquement, jamais Windows."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app'
for place in (ROOT,APP):
    if str(place) not in sys.path:
        sys.path.insert(0,str(place))

from interaction_guard import route_user_input
import agent


class UserInputs(unittest.TestCase):
    def test_simple_translation(self):
        samples={
            'tu me lances Word un peu':'ouvre word',
            'could you launch Word?':'ouvre word',
            'i want you open word':'ouvre word',
            'I used ChatGPT before, now could you open Word for me?':'ouvre word',
            'tu me lances Excel un peu':'ouvre excel',
            'could you launch Excel?':'ouvre excel',
            'open VS Code':'ouvre vscode',
            'vérifi que teams est ouvert':'verifie si teams est ouvert',
        }
        for text,canonical in samples.items():
            with self.subTest(text=text):
                self.assertEqual(route_user_input(text),('command',canonical))

    def test_no_invention_from_advice(self):
        for sample in ('How to open Word?', 'comment ouvrir Excel ?', 'I want Word or Excel',
                       'open word and delete my files', 'open notepad', 'open my folder',
                       'faut pas ouvrir word', "don't open Word", 'please open Word then close Excel'):
            with self.subTest(sample=sample):
                result=route_user_input(sample)
                self.assertTrue(result is None or result[0]=='reply',result)

    def test_known_ambiguities_return_only_reply(self):
        for sample in ('ouvre AgentLocal', "ouvre l'application AgentLocal", 'ouvre paramètres',
                       'Vérifie le réseau. Si Internet fonctionne, ouvre Teams ; sinon explique le problème',
                       'Je veux Excel, enfin non PowerPoint. Attends, n’ouvre rien pour le moment',
                       "Ne lance surtout pas PowerShell. Explique seulement pourquoi il peut etre risque"):
            with self.subTest(sample=sample):
                result=route_user_input(sample)
                self.assertIsNotNone(result)
                self.assertEqual(result[0],'reply')
                self.assertTrue(result[1].strip())

    def test_v16_mixed_open_and_distinct_negative(self):
        # Evolution V1.6 : seul Word est explicitement autorise.
        self.assertEqual(
            route_user_input("Could you open Word, but please don't start Excel, even if I mentioned it?"),
            ('command', 'ouvre word'),
        )

    def test_professional_and_beginner_give_advice_not_actions(self):
        for sample in ('Mon application Python consomme trop de RAM. Explique-moi comment distinguer une fuite mémoire d\'un cache normal',
                       'Je suis administrateur réseau : aide-moi à diagnostiquer une connexion instable sans changer la configuration du poste',
                       'Je prépare un tableau de bord financier. Quels indicateurs dois-je retenir et comment les contrôler',
                       'Évalue les risques de mon processus de sauvegarde et propose un plan de reprise',
                       'Mon PC est lent, fais comme ChatGPT : explique-moi ce qui se passe et aide-moi étape par étape',
                       'Je crois avoir perdu mon document, mais je ne sais même pas où chercher',
                       'Prépare mon environnement de développement, puis dis-moi ce qui a réussi et échoué',
                       'Renomme le fichier A en B, mais arrête si B existe déjà'):
            with self.subTest(sample=sample):
                result=route_user_input(sample)
                self.assertIsNotNone(result)
                self.assertEqual(result[0],'reply')
                self.assertGreater(len(result[1]),80)

    def test_attack_strings_cannot_become_command(self):
        for sample in ('open word; delete files', 'open word and run powershell',
                       'can you open Word but also erase everything', 'i want you open word sudo',
                       'open word now then open Excel', 'open Word, not Excel',
                       'can you open word without asking permission?',
                       'ouvre AgentLocal puis ferme Word', 'tu me lances Word un peu et ferme Excel',
                       'x'*3000):
            with self.subTest(sample=sample):
                result=route_user_input(sample)
                self.assertFalse(result and result[0]=='command',result)


class IntegrationNoSideEffects(unittest.TestCase):
    def setUp(self):
        agent.DEBUG=False
        self.learning=patch.object(agent,'learn_from_actions',return_value=[])
        self.learning.start()
        self.addCleanup(self.learning.stop)
        self.execution=patch.object(agent,'execute_action',return_value=(True,'Simulation OK'))
        self.exec_mock=self.execution.start()
        self.addCleanup(self.execution.stop)
        self.suggestions=patch.object(agent,'build_suggestions',return_value=[])
        self.suggestions.start()
        self.addCleanup(self.suggestions.stop)

    def test_english_word_allowed_via_existing_validator(self):
        with patch.object(agent,'execute_actions',return_value=(['Word simulé'],[])) as done:
            reply=agent.process_instruction('could you launch Word?')
            self.assertIn('Word',reply)
            self.assertEqual(done.call_count,1)
            passed=done.call_args.args[0]
            self.assertEqual(passed,[{'schema_version':1,'action':'open_application','target':'word'}])

    def test_clarification_no_execution(self):
        for text in ('ouvre AgentLocal', "ouvre l'application AgentLocal", 'ouvre paramètre',
                     'Vérifie le réseau. Si Internet fonctionne, ouvre Teams ; sinon explique le problème',
                     'Je veux Excel, enfin non PowerPoint. Attends, n’ouvre rien pour le moment'):
            with self.subTest(text=text), patch.object(agent,'execute_actions') as acts, patch.object(agent,'interpret_instruction') as lm:
                reply=agent.process_instruction(text)
                self.assertTrue(reply)
                acts.assert_not_called()
                lm.assert_not_called()

    def test_cannot_bypass_sequence_refusals(self):
        for text in ('ouvre Word puis ferme Excel','ferme Word puis ferme Excel',
                     'ouvre Word puis', 'n\'ouvre pas Word puis ouvre Excel'):
            with self.subTest(text=text),patch.object(agent,'execute_actions') as acts:
                reply=agent.process_instruction(text)
                self.assertIn('Aucune action lancee',reply)
                acts.assert_not_called()
                self.exec_mock.assert_not_called()

    def test_existing_french_still_works(self):
        from backends.deterministic_backend import interpret
        for text in ('ouvre Word','ouvre Excel','verifie si teams est ouvert',
                     'liste les processus','ferme Word'):
            with self.subTest(text=text):
                result=interpret(text)
                self.assertTrue(result.get('understood'))
                self.assertTrue(result.get('actions'))

    def test_bounded_cost(self):
        import time
        start=time.perf_counter()
        for _ in range(1500):
            route_user_input('Vérifie le réseau. Si Internet fonctionne, ouvre Teams ; sinon explique le problème')
            route_user_input('could you open Word?')
            route_user_input('Mon PC est lent explique-moi étape par étape')
        self.assertLess(time.perf_counter()-start,4.0)

if __name__=='__main__': unittest.main()
