"""Tests de resistance V12.5.2. Pas d'ouverture d'appli ni d'ecriture utilisateur."""
from __future__ import annotations

import random
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "app"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import agent
from command_sequences import get_last_sequence, remember_sequence, split_explicit_sequence
from session_context import clear_session_context


class StressSequenceTests(unittest.TestCase):
    def setUp(self):
        agent.DEBUG = False
        clear_session_context()
        learning = patch.object(agent, "learn_from_actions", return_value=[])
        learning.start()
        self.addCleanup(learning.stop)

    def test_dangling_connectors_are_denied_without_partial_execution(self):
        endings = ("puis", "ensuite", "et après", "puis.", "puis!", "ensuite ?", "et après:")
        for ending in endings:
            for prefix in ("ouvre Word", "ouvre Word puis ouvre Excel"):
                text = f"{prefix} {ending}"
                with self.subTest(text=text), patch.object(agent, "execute_action") as executor:
                    result = agent.process_instruction(text)
                    executor.assert_not_called()
                    self.assertIn("Aucune action lancee", result)

    def test_mutation_fuzz_never_breaks_parser_contract(self):
        rng = random.Random(20261112)
        vocabulary = ("ouvre", "Word", "Excel", "puis", "ensuite", ";", "«", "»", '"',
                      " ", "  ", "\n", "ferme", "supprime", "et après", "🏁", ",", ".", "\x00")
        for _ in range(3500):
            sentence = " ".join(rng.choices(vocabulary, k=rng.randrange(1, 22)))
            steps, error = split_explicit_sequence(sentence)
            self.assertFalse(steps is not None and error is not None)
            if steps is not None:
                self.assertLessEqual(len(steps), 4)
                self.assertGreaterEqual(len(steps), 2)
                self.assertTrue(all(step.strip() for step in steps))

    def test_long_requests_never_trigger_execution(self):
        data = "ouvre Word puis ouvre Excel " + "m" * 1200
        with patch.object(agent, "execute_action") as executor:
            reply = agent.process_instruction(data)
            executor.assert_not_called()
            self.assertIn("Aucune action lancee", reply)

    def test_refuse_disallowed_action_after_safe_first_step(self):
        for command in (
            "ouvre Word puis ferme Excel",
            "ouvre Word puis supprime fichier.txt dans Documents",
            "ouvre Word puis lance ma routine",
            "ouvre Word puis éteins le PC",
        ):
            with self.subTest(command=command), patch.object(agent, "execute_action") as executor:
                response = agent.process_instruction(command)
                executor.assert_not_called()
                self.assertIn("Aucune action lancee", response)

    def test_backend_attempt_to_invent_action_is_refused(self):
        action = {"action": "open_application", "target": "excel", "params": {}}
        with patch.object(agent, "interpret_instruction", return_value={"actions": [action]}), \
                patch.object(agent, "execute_action") as executor:
            response = agent.process_instruction("ouvre Word puis ouvre Excel")
            executor.assert_not_called()
            self.assertIn("Aucune action lancee", response)

    def test_exception_during_first_step_stops_remaining_steps(self):
        with patch.object(agent, "execute_action", side_effect=RuntimeError("secret result")) as executor:
            response = agent.process_instruction("ouvre Word puis ouvre Excel")
            self.assertEqual(executor.call_count, 1)
            self.assertIn("1 etape(s) non executee(s)", response)
            self.assertNotIn("secret result", response)

    def test_history_results_are_isolated_and_thread_safe(self):
        errors = []
        def worker(i):
            try:
                for _ in range(100):
                    remember_sequence(["ouvre Word", "ouvre Excel"], [True, bool(i % 2)], False)
                    result = get_last_sequence()
                    if len(result["steps"]) != 2:
                        errors.append("history corrupted")
                    result["steps"].append("mutation")
            except Exception as exc:
                errors.append(str(exc))
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(get_last_sequence()["steps"]), 2)


if __name__ == "__main__":
    unittest.main()
