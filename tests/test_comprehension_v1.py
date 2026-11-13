"""Tests de comprehension: ZERO action Windows / aucune sortie utilisateur modifiee."""
import json
import os
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from comprehension.data_quality import load_split, validate_corpus
from comprehension.guide import closest_examples, few_shot_hint
from comprehension.sft import export
from comprehension import feedback
from backends.llm_fidelity import semantic_fidelity


class CorpusTests(unittest.TestCase):
    def test_corpus_integrity(self):
        report=validate_corpus()
        self.assertTrue(report['ok'], report['errors'])
        self.assertGreaterEqual(report['train'],350)
        self.assertGreaterEqual(report['eval'],180)

    def test_training_holdout_disjoint(self):
        train={r['input'].casefold() for r in load_split('train')}
        evaluation={r['input'].casefold() for r in load_split('eval')}
        self.assertFalse(train & evaluation)

    def test_all_four_types_present(self):
        result={r['output']['type'] for r in load_split('train')}
        self.assertEqual(result, {'command','clarification','conversation','refusal'})

    def test_covers_languages(self):
        names={r['language'] for r in load_split('train')}
        self.assertGreaterEqual(names, {'fr','fr-ci','en','es'})

    def test_negatives_never_converted(self):
        for row in load_split('train')+load_split('eval'):
            if row['domain']=='negation':
                self.assertNotEqual(row['output']['type'],'command',row['id'])

    def test_no_sensitive_examples_in_command(self):
        for row in load_split('train')+load_split('eval'):
            if row['domain']=='policy':
                self.assertNotEqual(row['output']['type'],'command')

    def test_export_no_training_side_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=export(Path(tmp))
            self.assertEqual(report['train']+report['validation'],len(load_split('train')))
            self.assertEqual(report['test_holdout'],len(load_split('eval')))
            path=Path(tmp)/'train_sft.jsonl'
            with path.open(encoding='utf-8') as f:
                one=json.loads(f.readline())
            self.assertEqual([x['role'] for x in one['messages']],['system','user','assistant'])
            self.assertIn('type', one['messages'][-1]['content'])


class PromptGuideTests(unittest.TestCase):
    def test_prompt_contains_references(self):
        text=few_shot_hint('ouvre Word')
        self.assertIn('ouvre Word',text)
        self.assertIn('"reponse"',text)

    def test_negative_no_action_in_examples(self):
        for message in ('n\'ouvre pas Word','dont open Excel','no abras Edge','faut pas ouvrir Word hein'):
            lines=closest_examples(message)
            self.assertTrue(lines,message)
            self.assertTrue(all(e['output']['type']!='command' for e in lines),message)

    def test_no_context_does_not_invent_examples(self):
        self.assertEqual(few_shot_hint(''), '')

    def test_bounded(self):
        for phrase in ('ouvre Word','tchai mon pc rame', 'what can you do?'):
            text=few_shot_hint(phrase,max_chars=350)
            self.assertLessEqual(len(text),390)

    def test_deterministic_selection(self):
        self.assertEqual(few_shot_hint('ouvre Excel'),few_shot_hint('ouvre Excel'))

    def test_randomized_input_does_not_execute(self):
        rng=random.Random(812)
        words=['word','excel','ouvre','ferme','pas','ne','tchai','merci','hello','50','gbê','..','?']
        for _ in range(220):
            phrase=' '.join(rng.choices(words,k=rng.randint(1,10)))
            result=few_shot_hint(phrase)
            self.assertLess(len(result),1600)

    def test_llama_prompt_includes_local_examples(self):
        from backends.llama_backend import _build_prompt
        prompt=_build_prompt('ouvre Word')
        self.assertIn('Exemples de reference',prompt)
        self.assertIn('Demande utilisateur',prompt)
        self.assertIn('"ouvre Word"',prompt)

    def test_llama_prompt_keeps_non_action_negation(self):
        from backends.llama_backend import _build_prompt
        prompt=_build_prompt("n’ouvre pas Word")
        start=prompt.index('Exemples de reference')
        end=prompt.index('Demande utilisateur :',start)
        section=prompt[start:end]
        self.assertNotIn('"type":"command"',section)

    def test_multilingual_negations_not_actionable(self):
        phrases=(
            "don't open Word",'do not start Excel','never close Edge',
            'please do not delete report.pdf', 'no abras Word',
            'por favor no quiero abrir Excel','nunca borres el archivo',
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertFalse(semantic_fidelity(phrase, 'ouvre Word')[0])

    def test_shell_and_negations_cannot_be_laundered(self):
        self.assertFalse(semantic_fidelity('n\'ouvre pas Word','ouvre Word')[0])
        self.assertFalse(semantic_fidelity('ouvre Excel','ouvre Word')[0])
        self.assertFalse(semantic_fidelity('mets le volume à 15%','mets le volume à 90%')[0])


class ManualLearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pending=patch.object(feedback, '_PENDING',Path(self.tmp.name)/'pending.json')
        self.approved=patch.object(feedback, '_APPROVED',Path(self.tmp.name)/'approved.json')
        self.pending.start();self.approved.start()
        self.addCleanup(self.pending.stop);self.addCleanup(self.approved.stop)

    def test_requires_explicit_approval(self):
        cid=feedback.propose('ouvre Excel s’il te plaît','ouvre Excel')
        self.assertEqual(feedback.approved_examples(),[])
        self.assertTrue(feedback.approve(cid))
        self.assertEqual(len(feedback.approved_examples()),1)

    def test_forbidden_target(self):
        with self.assertRaises(ValueError):
            feedback.propose('ouvre excel','lance PowerShell')

    def test_negation_blocked(self):
        with self.assertRaises(ValueError):
            feedback.propose('n’ouvre pas Word','ouvre Word')

    def test_entity_mismatch(self):
        with self.assertRaises(ValueError):
            feedback.propose('ouvre Excel','ouvre Word')

    def test_no_sensitive_paths_or_email(self):
        for phrase in ('ouvre Word C:\\Users\\someone\\secret','ouvre Word test@example.com','ouvre Word avec password'):
            with self.subTest(phrase=phrase),self.assertRaises(ValueError):
                feedback.propose(phrase,'ouvre Word')

    def test_bad_id_not_approved(self):
        self.assertFalse(feedback.approve('bad identifier'))

if __name__=='__main__':unittest.main()
