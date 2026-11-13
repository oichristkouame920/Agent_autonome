"""Tests de stress non destructifs pour la branche comprehension.

Aucune action OS, aucune installation, aucun LLM reel par defaut.
"""
import json
import random
import string
import unittest
from unittest.mock import patch

from comprehension.guide import closest_examples, few_shot_hint, _prepared_examples
from comprehension.resource_diagnostics import plan_for_memory, offline_benchmark, live_benchmark
from backends.llm_fidelity import semantic_fidelity


class LanguageFidelityStress(unittest.TestCase):
    def test_open_and_close_never_cross(self):
        for app in ('Word', 'Excel', 'PowerPoint', 'Teams', 'Edge', 'VS Code'):
            for instruction,expected in [('ouvre ', 'ouvre'), ('lance ', 'ouvre'), ('ferme ','ferme')]:
                with self.subTest(instruction=instruction, app=app):
                    rows=closest_examples(instruction+app)
                    for ex in rows:
                        if ex['output']['type']=='command':
                            canonical=ex['output']['canonical_command']
                            self.assertTrue(canonical.startswith(expected), canonical)
                            self.assertIn(app.casefold(), canonical.casefold())
                            self.assertEqual(canonical.casefold().count(app.casefold()),1)

    def test_typical_ivoirian_requests_do_not_turn_into_closures(self):
        for msg in ('tu me lances Word un peu', 'faut ouvrir Word la', 'lance Excel stp', 'could you open Word?'):
            with self.subTest(msg=msg):
                examples=closest_examples(msg)
                self.assertTrue(examples)
                self.assertTrue(all(ex['output']['type']=='command' for ex in examples))
                self.assertTrue(all(not ex['output']['canonical_command'].startswith('ferme') for ex in examples))

    def test_advice_is_not_action(self):
        for msg in ('comment ouvrir Word ?', 'how to open Excel?', 'explique comment ouvrir Teams',
                    'comment supprimer un fichier ?', 'how do I launch Word?'):
            with self.subTest(msg=msg):
                self.assertTrue(all(ex['output']['type']!='command' for ex in closest_examples(msg)))

    def test_negations_cross_languages(self):
        samples=('ne lance pas Word', 'surtout pas Excel', 'faut pas ouvrir Teams hein',
                 "don't open Word", 'do not open Edge', 'no abras Excel', 'nunca abrir Word')
        for msg in samples:
            with self.subTest(msg=msg):
                self.assertTrue(all(ex['output']['type']!='command' for ex in closest_examples(msg)))
                self.assertLessEqual(len(few_shot_hint(msg)),1050)

    def test_chatgpt_reference_not_a_second_target(self):
        allowed=[('I used ChatGPT before, now could you open Word for me?', 'ouvre Word'),
                 ('je connais ChatGPT, ouvre Excel', 'ouvre Excel')]
        for msg,canonical in allowed:
            self.assertTrue(semantic_fidelity(msg, canonical)[0], (msg, canonical))
        forbidden=[('ouvre ChatGPT et Excel', 'ouvre Excel'), ('ouvre Word et Excel', 'ouvre Word'),
                   ('ouvre Word','ouvre Excel'), ('comment ouvrir Word?','ouvre Word')]
        for msg,canonical in forbidden:
            self.assertFalse(semantic_fidelity(msg,canonical)[0], (msg,canonical))

    def test_llm_cannot_invent_app_from_vague_request(self):
        for message, canonical in (
            ('Mon ordinateur est lent, explique pourquoi', 'ouvre Word'),
            ('Quelle heure est-il ?', 'ouvre Excel'),
            ('Pourrais-tu m aider ?', 'ouvre PowerPoint'),
            ('Could you help with my PC?', 'ouvre Word'),
            ('Je veux juste un conseil.', 'ouvre Teams'),
        ):
            self.assertFalse(semantic_fidelity(message,canonical)[0],message)
        for message,canonical in (
            ('ouvre mon navigateur', 'ouvre Edge'),
            ('ouvre le traitement de texte', 'ouvre Word'),
            ('ouvre mon tableur', 'ouvre Excel'),
        ):
            self.assertTrue(semantic_fidelity(message,canonical)[0],message)

    def test_interpret_never_executes_system_tools_in_simulation(self):
        from backends import llama_backend
        from backends import deterministic_backend
        cases=(
            ('ne lance pas Word', 'ouvre Word'),
            ('do not open Excel', 'ouvre Excel'),
            ('no abras Teams', 'ouvre Teams'),
            ('Comment ouvrir Word ?', 'ouvre Word'),
            ('Mon PC est lent', 'ouvre Word'),
            ('ouvre Excel', 'ouvre Word'),
        )
        for user_message,canonical in cases:
            with self.subTest(user_message=user_message), \
                 patch.object(llama_backend,'availability',return_value=(True,None)), \
                 patch.object(llama_backend,'get_active_model_config',return_value=('qwen_small', {'minimum_confidence': 0.72}, {})), \
                 patch.object(llama_backend,'_run_llama_adaptive',return_value=(json.dumps({'type':'command','canonical_command':canonical,'confidence':0.99}),'fake')), \
                 patch.object(deterministic_backend,'interpret',side_effect=AssertionError('commande non autorisee')), \
                 patch('subprocess.run',side_effect=AssertionError('subprocess.run interdit')), \
                 patch('subprocess.Popen',side_effect=AssertionError('Popen interdit')):
                result=llama_backend.interpret(user_message)
                self.assertEqual(result.get('actions',[]),[])

    def test_timeout_simulated_no_action(self):
        import subprocess
        from backends import llama_backend
        with patch.object(llama_backend,'availability',return_value=(True,None)), \
             patch.object(llama_backend,'get_active_model_config',return_value=('qwen_small',{'minimum_confidence':0.72},{})), \
             patch.object(llama_backend,'_run_llama_adaptive',side_effect=subprocess.TimeoutExpired(['llama-cli'],45)), \
             patch('subprocess.Popen',side_effect=AssertionError('Popen interdit')):
            with self.assertRaises(subprocess.TimeoutExpired):
                llama_backend.interpret('ouvre Word')

    def test_numeric_targets_and_paths_must_match(self):
        for msg,canonical in [('mets le volume à 20%','mets le volume à 100%'),
                              ('ouvre rapport.pdf','ouvre budget.pdf'),
                              ('ouvre Word','ouvre Excel'),
                              ('copie C:\\Users\\Public\\a.txt','copie C:\\Users\\Public\\b.txt')]:
            self.assertFalse(semantic_fidelity(msg,canonical)[0])

    def test_references_cached_only_static(self):
        a=_prepared_examples()
        b=_prepared_examples()
        self.assertIs(a,b)
        self.assertLessEqual(len(a),800)

    def test_large_input_short_circuit(self):
        self.assertEqual(closest_examples('ouvre Word ' * 1000),[])
        self.assertEqual(few_shot_hint('ouvre Word ' * 1000), '')

    def test_randomized_adversarial_inputs_never_exceed_budget(self):
        rng=random.Random(9514)
        words=('ouvre','Word','ne','pas','ferme','Excel','PowerPoint','comment','why','no',
               'never','attention','0','500','%','nouchi','\"','\\','--',';')
        for _ in range(1500):
            msg=' '.join(rng.choice(words) for _ in range(rng.randint(1,22)))
            self.assertLessEqual(len(closest_examples(msg)),4)
            self.assertLessEqual(len(few_shot_hint(msg)),1050)


class ResourceAndSafety(unittest.TestCase):
    def test_four_gigabytes_simulation(self):
        state=plan_for_memory(4096,2400)
        self.assertEqual(state['profile'],'4gb_cautious')
        self.assertTrue(state['live_allowed'])
        self.assertEqual(state['suggested_threads_max'],2)
        self.assertFalse(state['warm_server_recommended'])
        self.assertFalse(plan_for_memory(4096,900)['live_allowed'])
        self.assertFalse(plan_for_memory(4096,1300)['live_allowed'])
        self.assertTrue(plan_for_memory(4096,1550)['live_allowed'])

    def test_unknown_memory_denies_live(self):
        for pair in ((None,None),(-1,100),(4096,None),(4096,-1)):
            self.assertFalse(plan_for_memory(*pair)['live_allowed'])

    def test_no_live_model_import_when_not_requested(self):
        # Ne doit ni demarrer subprocess ni creer de reseau pour le benchmark.
        with patch('subprocess.Popen',side_effect=AssertionError('Popen interdit')),\
             patch('subprocess.run',side_effect=AssertionError('run interdit')),\
             patch('urllib.request.urlopen',side_effect=AssertionError('reseau interdit')):
            stats=offline_benchmark(40)
        self.assertTrue(stats['passed'])
        self.assertLessEqual(stats['max_example_prompt_chars'],1050)

    def test_live_guard_refuses_when_low_memory(self):
        with patch('comprehension.resource_diagnostics.memory_snapshot',return_value={'total_mb':4096,'available_mb':512,'source':'simulated'}),\
             patch('subprocess.Popen',side_effect=AssertionError('Popen interdit')):
            stats=live_benchmark(4)
        self.assertEqual(stats['status'],'skipped_insufficient_ram')
        self.assertFalse(stats['results'])

    def test_limit_iterations(self):
        stats=offline_benchmark(5)
        self.assertEqual(stats['iterations'],5)
        self.assertTrue(stats['passed'])

    def test_user_prompts_not_cached(self):
        from comprehension import guide
        self.assertEqual(guide._prepared_examples.cache_info().maxsize,1)
        for i in range(200): closest_examples('phrase aleatoire '+str(i))
        self.assertLessEqual(guide._prepared_examples.cache_info().currsize,1)


if __name__=='__main__':
    unittest.main()
