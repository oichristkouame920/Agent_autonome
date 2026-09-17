"""Vérification non destructive V10.3 corrigée (capture + cohérence du pont Edge)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for value in (ROOT, ROOT / "app"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import browser_bridge
import agent
from backends.deterministic_backend import interpret


def require(cond, message):
    if not cond:
        raise RuntimeError(message)


def main():
    require(callable(getattr(browser_bridge, "open_site_via_bridge", None)),
            "browser_bridge.py n'est pas la version attendue: open_site_via_bridge manque.")
    print("OK - pont Edge compatible: open_site_via_bridge présent")

    for text, target in [
        ("capture tout l'écran", "full_screen"),
        ("fais une capture d'écran", "full_screen"),
        ("capture la fenêtre active", "active_window"),
    ]:
        result = interpret(text)
        actions = result.get("actions", []) if isinstance(result, dict) else []
        require(len(actions) == 1, f"Phrase non reconnue: {text!r} -> {result}")
        action = actions[0]
        require(action.get("action") == "take_screenshot", f"Mauvaise action: {action}")
        require(action.get("target") == target, f"Mauvaise cible: {action}")
        valid, error = agent.validate_action(action)
        require(valid, f"Contrat capture refusé: {error}")
        print(f"OK - {text} -> {target}")

    negative = interpret("fais pas de capture d'écran")
    require(not negative.get("actions"), "La négation de capture ne doit produire aucune action.")
    print("OK - négation de capture bloquée")

    permissions = json.loads((ROOT / "config" / "permissions.json").read_text(encoding="utf-8"))
    policy = permissions.get("screenshot_policy", {})
    require(policy.get("enabled") is True, "screenshot_policy.enabled doit être true")
    require(policy.get("require_explicit_user_command") is True,
            "La capture doit exiger une commande explicite")
    require(policy.get("allow_from_routine") is False, "Capture interdite depuis routine")
    require(policy.get("allow_from_habit") is False, "Capture interdite depuis habitude")
    require(policy.get("allow_automatic_capture") is False, "Capture automatique interdite")
    print("OK - politique capture contrôlée")

    print()
    print("V10.3 CORRIGEE ACTIVE - verification non destructive OK")
    print("Aucune capture et aucune navigation Edge n'ont été effectuées.")


if __name__ == "__main__":
    main()
