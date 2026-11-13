"""Tests non destructifs des usages professionnels / debutants.

N'instancie pas le modele et n'appelle aucun outil Windows.
"""
import json
import tempfile
import unittest
from pathlib import Path

from comprehension.audience import audience_for, audience_hint
from comprehension.data_quality import load_split, validate_corpus
from comprehension.guide import closest_examples, few_shot_hint
from comprehension.sft import export


class AudienceCorpusTests(unittest.TestCase):
    def test_validate_every_split(self):
        report = validate_corpus()
        self.assertTrue(report['ok'], report['errors'])
        self.assertGreaterEqual(report['train'], 500)
        self.assertGreaterEqual(report['eval'], 230)

    def test_source_examples_have_audience_labels(self):
        for split, minimum in [('train', 150), ('eval', 50)]:
            rows = [r for r in load_split(split) if r.get('audience')]
            self.assertGreaterEqual(len(rows), minimum)
            self.assertEqual({r['audience'] for r in rows}, {'professional', 'beginner'})
            self.assertTrue(all(r['domain'].startswith(('pro_', 'beginner_')) for r in rows))

    def test_held_out_inputs_unique(self):
        train = {' '.join(r['input'].casefold().split()) for r in load_split('train')}
        eval_rows = {' '.join(r['input'].casefold().split()) for r in load_split('eval')}
        self.assertFalse(train & eval_rows)

    def test_professions_diversified(self):
        domains = {r['domain'] for r in load_split('train') if r.get('audience') == 'professional'}
        self.assertGreaterEqual(domains, {'pro_it_support','pro_development','pro_data_finance',
                                          'pro_hr_education','pro_marketing_project','pro_action','pro_safety'})

    def test_beginner_chatgpt_and_computer_help_covered(self):
        domains = {r['domain'] for r in load_split('train') if r.get('audience') == 'beginner'}
        self.assertGreaterEqual(domains, {'beginner_chatgpt','beginner_pc','beginner_office',
                                          'beginner_action','beginner_fr_ci','beginner_safety'})

    def test_expected_actions_from_approved_set(self):
        approved = {'ouvre Excel','ouvre Word','ouvre PowerPoint','ouvre Teams','ouvre Edge',
                    'ouvre VS Code','ouvre GitHub','ouvre Outlook','donne-moi l’état du PC',
                    'mets le volume à 15%','mets le volume à 20%'}
        for split in ('train','eval'):
            for row in load_split(split):
                if not row.get('audience') or row['output']['type'] != 'command':
                    continue
                self.assertIn(row['output']['canonical_command'], approved, row['id'])

    def test_question_or_advice_not_executable(self):
        for split in ('train','eval'):
            for row in load_split(split):
                if not row.get('audience'):
                    continue
                if row['output']['type'] != 'command':
                    self.assertNotIn('canonical_command',row['output'],row['id'])

    def test_export_includes_audience_and_separate_holdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            counts=export(Path(tmp))
            self.assertEqual(counts['train']+counts['validation'],len(load_split('train')))
            self.assertEqual(counts['test_holdout'],len(load_split('eval')))
            all_train=(Path(tmp)/'train_sft.jsonl').read_text(encoding='utf-8')
            validation=(Path(tmp)/'validation_sft.jsonl').read_text(encoding='utf-8')
            self.assertTrue('Pour mon reporting, lance Excel.' in all_train+validation)
            self.assertNotIn('Pour la revue de sécurité du trimestre,',all_train+validation)


class AudienceRoutingTests(unittest.TestCase):
    def test_professional_direct(self):
        for prompt in ('En tant que développeur, optimise notre API',
                       'Je suis responsable RH, propose une grille',
                       'As a developer, advise on our SQL migration'):
            with self.subTest(prompt=prompt):
                self.assertEqual(audience_for(prompt),'professional')

    def test_beginner_explicit(self):
        for prompt in ('Je suis débutant, explique les fichiers',
                       'Je ne comprends pas les paramètres',
                       'Je connais ChatGPT mais je suis novice',
                       'Explain simply, I am a beginner'):
            with self.subTest(prompt=prompt):
                self.assertEqual(audience_for(prompt),'beginner')

    def test_person_can_be_expert_and_beginner(self):
        self.assertEqual(audience_for('Je suis développeur, mais je débute dans Excel'),'beginner')

    def test_no_permanent_role_inference(self):
        self.assertEqual(audience_for('ouvre Word'),'neutral')
        self.assertEqual(audience_hint(''),'')
        self.assertEqual(audience_for('merci pour ton aide'),'neutral')

    def test_guide_teaches_style_without_permissions(self):
        hint=few_shot_hint('En tant que développeur, explique les risques des logs')
        self.assertIn('professionnel',hint)
        self.assertIn('ne pretends pas',hint)
        novice=few_shot_hint('Je suis débutant, explique ce que je dois faire')
        self.assertIn('debutant',novice)
        self.assertIn('pas a pas',novice)
        self.assertNotIn('autorisation administrateur permanente',novice)

    def test_small_prompt_budget(self):
        for text in ('Je suis débutant, aide-moi avec Excel',
                     'En tant que professionnel, analyse les écarts budgetaires',
                     'faut pas ouvrir Word, je suis novice'):
            for budget in (150,300,450,1050):
                with self.subTest(text=text,budget=budget):
                    self.assertLessEqual(len(few_shot_hint(text,max_chars=budget)),budget)

    def test_negative_samples_never_add_command(self):
        for prompt in ('je suis débutant n’ouvre pas Word',
                       'pour notre équipe, ne lance jamais Excel',
                       'As a developer, do not open Edge'):
            chosen=closest_examples(prompt)
            self.assertTrue(all(r['output']['type']!='command' for r in chosen), prompt)

    def test_examples_prioritize_pro_audience(self):
        selected=closest_examples('En tant que développeur, donne une revue de code Python',3)
        self.assertTrue(any(r.get('audience')=='professional' for r in selected))

    def test_examples_prioritize_beginner_audience(self):
        selected=closest_examples('Je suis débutant, explique la RAM simplement',3)
        self.assertTrue(any(r.get('audience')=='beginner' for r in selected))

    def test_response_schema_still_fixed(self):
        from backends.llama_backend import _build_prompt
        prompt=_build_prompt('Je suis débutant, explique le fonctionnement de la RAM')
        self.assertIn('"type":"conversation"',prompt)
        self.assertIn('Demande utilisateur :',prompt)
        self.assertIn('debutant',prompt)
        self.assertIn('Tu ne commandes jamais Windows',prompt)


if __name__ == '__main__':
    unittest.main()
