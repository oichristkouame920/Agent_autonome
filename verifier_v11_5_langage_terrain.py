from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
for path in (ROOT, ROOT / "app", ROOT / "backends"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from backends.deterministic_backend import interpret


def action(text):
    result = interpret(text)
    if not result.get("understood"):
        raise AssertionError(f"Non compris : {text}")
    actions = result.get("actions") or []
    if not actions:
        raise AssertionError(f"Aucune action : {text} -> {result}")
    return actions[0]


checks = []

a = action("liste tout mes documents")
checks.append((a["action"] == "list_directory" and a["target"] == "documents", "liste tout mes documents"))

a = action("ouvre Formation JS")
checks.append((a["action"] == "open_file_auto" and a.get("params", {}).get("allow_directory_fallback") is True, "ouverture fichier/dossier unifiee"))

a = action("ferme le dossier Formation JS")
checks.append((a["action"] == "close_directory_auto", "fermeture ciblee dossier"))

r = interpret("ouvre l'invite de commande")
checks.append((r.get("understood") and not r.get("actions") and "interdite" in r.get("reply", "").lower(), "invite de commande bloquee"))

a = action("quelles sont mes habitudes ?")
checks.append((a["action"] == "list_habits" and a["target"] == "summary", "resume habitudes"))

r = interpret("supprime le dossier AnyDesk")
checks.append((r.get("understood") and not r.get("actions") and "AnyDesk" in r.get("reply", ""), "suppression dossier comprise sans execution"))

a = action("check moi si teams est ouvert")
checks.append((a["action"] == "check_application" and a["target"] == "teams", "langage moins formel"))

failed = [label for ok, label in checks if not ok]
for ok, label in checks:
    print(("OK" if ok else "ECHEC") + " - " + label)

if failed:
    raise SystemExit("V11.5 ECHEC : " + ", ".join(failed))

print("\nV11.5 LANGAGE TERRAIN ACTIF - verification non destructive OK")
