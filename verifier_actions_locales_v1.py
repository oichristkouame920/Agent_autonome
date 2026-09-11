"""Vérification non destructive des Actions locales V1."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

from backends.deterministic_backend import interpret

TESTS = [
    ("j'utilise combien de RAM ?", "read_system_info", "memory"),
    ("regarde un peu combien d'espace il reste sur mon disque", "read_system_info", "disk"),
    ("mon processeur travaille à combien ?", "read_system_info", "cpu"),
    ("depuis combien de temps le PC est allumé ?", "read_system_info", "uptime"),
    ("qu'est-ce que j'ai copié ?", "read_clipboard", "clipboard"),
    ("copie ce texte : Bonjour merci", "write_clipboard", "clipboard"),
    ("liste mes onglets", "list_browser_tabs", "edge"),
    ("passe sur l'onglet GitHub", "activate_browser_tab", "github"),
    ("ouvre-le", "open_last_reference", "session"),
]

failed = []
for text, expected_action, expected_target in TESTS:
    result = interpret(text)
    actions = result.get("actions", []) if isinstance(result, dict) else []
    ok = (
        len(actions) == 1
        and actions[0].get("action") == expected_action
        and actions[0].get("target") == expected_target
    )
    print(("OK   " if ok else "ECHEC") + " - " + text)
    if not ok:
        failed.append((text, result))

permissions = json.loads((ROOT / "config" / "permissions.json").read_text(encoding="utf-8"))
for name in (
    "system_information_policy",
    "clipboard_policy",
    "browser_tab_policy",
    "session_context_policy",
):
    policy = permissions.get(name, {})
    ok = bool(
        policy.get("enabled")
        and policy.get("require_explicit_user_command")
        and not policy.get("allow_from_routine")
        and not policy.get("allow_from_habit")
    )
    print(("OK   " if ok else "ECHEC") + " - politique " + name)
    if not ok:
        failed.append((name, policy))

clipboard = permissions.get("clipboard_policy", {})
if clipboard.get("allow_execute_clipboard_content") or clipboard.get("allow_open_clipboard_url"):
    failed.append(("clipboard_policy", "execution/ouverture du contenu interdite attendue"))

session = permissions.get("session_context_policy", {})
if not session.get("memory_only") or session.get("persist_to_disk"):
    failed.append(("session_context_policy", "memoire RAM uniquement attendue"))

if failed:
    print("\nACTIONS LOCALES V1 : ECHEC")
    for item in failed:
        print(item)
    raise SystemExit(1)

print("\nACTIONS LOCALES V1 ACTIVES - verification non destructive OK")
