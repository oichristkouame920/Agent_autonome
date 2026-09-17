"""Vérification non destructive d'AgentLocal V10.3 - capture d'écran contrôlée."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for value in (ROOT, ROOT / "app"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import agent
from backends.deterministic_backend import interpret


def check_phrase(text, expected_target):
    result = interpret(text)
    actions = result.get("actions", []) if isinstance(result, dict) else []
    if len(actions) != 1:
        raise RuntimeError(f"Phrase non reconnue: {text!r} -> {result}")
    action = actions[0]
    if action.get("action") != "take_screenshot" or action.get("target") != expected_target:
        raise RuntimeError(f"Mauvais contrat: {text!r} -> {action}")
    valid, error = agent.validate_action(action)
    if not valid:
        raise RuntimeError(f"Contrat refusé: {text!r} -> {error}")
    print(f"OK - {text} -> {expected_target}")


def main():
    check_phrase("capture tout l'écran", "full_screen")
    check_phrase("fais une capture d'écran", "full_screen")
    check_phrase("capture la fenêtre active", "active_window")

    negative = interpret("fais pas de capture d'écran")
    if negative.get("actions"):
        raise RuntimeError("La négation de capture ne doit produire aucune action.")
    print("OK - négation de capture bloquée")

    permissions = json.loads((ROOT / "config" / "permissions.json").read_text(encoding="utf-8"))
    policy = permissions.get("screenshot_policy", {})
    required = {
        "enabled": True,
        "require_explicit_user_command": True,
        "allow_from_routine": False,
        "allow_from_habit": False,
        "allow_automatic_capture": False,
        "format": "png",
    }
    for key, expected in required.items():
        if policy.get(key) != expected:
            raise RuntimeError(f"Politique capture invalide pour {key}: {policy.get(key)!r}")
    if set(policy.get("allowed_modes", [])) != {"full_screen", "active_window"}:
        raise RuntimeError("Modes de capture inattendus.")

    print("OK - politique de capture manuelle et contrôlée")
    print()
    print("CAPTURE V10.3 ACTIVE - verification non destructive OK")
    print("Aucune capture réelle n'a été effectuée par ce script.")


if __name__ == "__main__":
    main()
