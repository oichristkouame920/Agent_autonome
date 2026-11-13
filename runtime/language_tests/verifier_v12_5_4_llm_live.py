"""Evaluation manuelle, en lecture seule, du LLM local sur Windows.

Ne lance jamais les actions retournees par l'agent. Ne change aucune
preference et n'enregistre aucune demande de l'utilisateur.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

from backends import llama_backend

CASES = [
    ("faut ouvrir Edge là", "open_application", "edge"),
    ("ouvre moi Word stp", "open_application", "word"),
    ("j'aimerais lancer Excel", "open_application", "excel"),
    ("ouvre github", "open_website", "github"),
    ("n'ouvre pas Word", None, None),
    ("faut pas ouvrir Excel", None, None),
    ("ouvre Word ou Excel", None, None),
    ("ouvre ça", None, None),
]


def run():
    ok, message = llama_backend.availability()
    if not ok:
        print("LLM indisponible :", message)
        return 2
    print("Evaluation LLM en lecture seule : aucune commande ne sera executee.")
    correct = 0
    for i, (prompt, expected_action, expected_target) in enumerate(CASES, start=1):
        began = time.monotonic()
        try:
            result = llama_backend.interpret(prompt)
            actions = result.get("actions", []) if isinstance(result, dict) else []
            if expected_action is None:
                passed = not actions
            else:
                passed = (
                    len(actions) == 1
                    and actions[0].get("action") == expected_action
                    and actions[0].get("target") == expected_target
                )
            correct += int(passed)
            label = "OK" if passed else "A PRECISER"
            print(f"{i}/{len(CASES)} {label} {prompt!r} [{time.monotonic()-began:.2f}s]")
            if not passed:
                print("    Analyse :",result.get("llm_type", "action"), result.get("reply", ""))
                print("    Actions (non executees) :", actions)
        except Exception as exc:
            print(f"{i}/{len(CASES)} INDISPONIBLE {prompt!r} ({type(exc).__name__})")
    print(f"BILAN LLM : {correct}/{len(CASES)} scenarios corrects (execution des actions desactivee).")
    return 0 if correct == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(run())
