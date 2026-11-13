"""V12.5.4: tests sans exécution de commandes et sans modele charge."""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for root in (ROOT, ROOT / 'app'):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from backends import llama_backend
from backends.llm_fidelity import semantic_fidelity, normalized_confidence


class GuardTests(unittest.TestCase):
    def test_normalization_leaves_valid_commands_usable(self):
        cases = (
            ('faut ouvrir Word là', 'ouvre word'),
            ('je voudrais utiliser mon éditeur de code', 'ouvre VS Code'),
            ('ouvre « Word »', 'ouvre word'),
            ('ouvre le fichier rapport.pdf', 'ouvre rapport.pdf'),
            ('mets le volume à 10 %', 'mets le volume à 10 %'),
            ('faut ouvrir bloc-notes', 'ouvre notepad'),
            ('ouvre le site Github', 'ouvre github'),
        )
        for original, normalized in cases:
            with self.subTest(original=original):
                self.assertTrue(semantic_fidelity(original, normalized)[0])

    def test_negation_blocks_hallucinated_positive_command(self):
        for phrase in (
            "n'ouvre pas Word", 'ne ferme jamais Excel', 'faut pas lancer Edge',
            'surtout pas ouvrir Word', 'ouvre pas Teams', 'sans supprimer mon fichier',
            'je veux pas lancer Word', "pas besoin d'ouvrir Excel",
        ):
            with self.subTest(phrase=phrase):
                self.assertFalse(semantic_fidelity(phrase, 'ouvre Word')[0])

    def test_ambiguous_pronoun_blocked(self):
        for phrase in ('ouvre ça', 'lance ce truc', 'ferme celui-là'):
            self.assertFalse(semantic_fidelity(phrase, 'ouvre Word')[0])

    def test_wrong_target_blocked(self):
        for original, canonical in (
            ('ouvre excel','ouvre word'), ('ouvre Word','ouvre google'),
            ('ouvre Firefox','ouvre Chrome'), ('ouvre Chrome ou Edge','ouvre Edge'),
            ('ferme Outlook','ouvre Outlook'), ('renomme fichier.txt','copie fichier.txt'),
            ('supprime rapport.pdf','ouvre rapport.pdf'), ('deplace rapport.pdf','copie rapport.pdf'),
            ('copie rapport.pdf','supprime rapport.pdf'),
        ):
            with self.subTest(original=original):
                self.assertFalse(semantic_fidelity(original, canonical)[0])

    def test_paths_numbers_quoted_strings_and_filenames(self):
        for original, canonical in (
            ('ouvre Rapport2025.pdf', 'ouvre Rapport2026.pdf'),
            ('ouvre rapport.pdf', 'ouvre rapport.docx'),
            ('ouvre C:\\Users\\moi\\a.txt', 'ouvre C:\\Users\\moi\\b.txt'),
            ('mets le volume à 10%', 'mets le volume à 100%'),
            ('ouvre "Budget annuel.xlsx"', 'ouvre "Budget été.xlsx"'),
            ('ouvre rapport.pdf', 'ouvre dossier.zip'),
        ):
            with self.subTest(original=original):
                self.assertFalse(semantic_fidelity(original, canonical)[0])

    def test_invalid_inputs_fail_closed(self):
        for original, canonical in ((None,'ouvre word'),('ouvre word',None),('','ouvre word'),('ouvre word','')):
            self.assertFalse(semantic_fidelity(original, canonical)[0])

    def test_confidence_nan_inf_and_bad_values(self):
        for value in ('NaN',float('nan'),'Infinity',float('inf'),-float('inf'),'bad',None):
            self.assertEqual(normalized_confidence(value), 0.0)
        self.assertEqual(normalized_confidence(0.94), 0.94)
        self.assertEqual(normalized_confidence(900), 1.0)


class LLMIntegrationTests(unittest.TestCase):
    def _interpret(self, phrase, generated_command, confidence=.99):
        raw = json.dumps({
            'type':'command',
            'canonical_command':generated_command,
            'confidence':confidence,
        })
        with patch.object(llama_backend,'availability',return_value=(True,None)), \
             patch.object(llama_backend,'get_active_model_config',return_value=('qwen_small',{'minimum_confidence':.72},{})), \
             patch.object(llama_backend,'_run_llama_adaptive',return_value=(raw,'mock')):
            return llama_backend.interpret(phrase)

    def test_negative_never_executes(self):
        result=self._interpret("n'ouvre pas Word",'ouvre word')
        self.assertEqual(result.get('actions'),[])
        self.assertEqual(result.get('llm_type'),'clarification')

    def test_changed_target_never_executes(self):
        result=self._interpret('ouvre excel','ouvre word')
        self.assertEqual(result.get('actions'),[])

    def test_allowed_intent_still_executable(self):
        result=self._interpret('faut ouvrir Word là','ouvre word')
        self.assertEqual(result.get('actions')[0]['target'],'word')
        self.assertEqual(result.get('routing'),'llm_normalized_then_deterministic')

    def test_nan_confidence_never_executes(self):
        result=self._interpret('ouvre word','ouvre word','NaN')
        self.assertEqual(result.get('actions'),[])
        self.assertEqual(result.get('llm_type'),'clarification')

    def test_user_volume_number_kept(self):
        good=self._interpret('mets le volume à 10%', 'mets le volume à 10%')
        bad=self._interpret('mets le volume à 10%', 'mets le volume à 100%')
        self.assertEqual(bad.get('actions'),[])
        self.assertTrue(good.get('actions'))


if __name__ == '__main__':
    unittest.main()
