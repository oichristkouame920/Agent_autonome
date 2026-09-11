from backends.deterministic_backend import NATURAL_LANGUAGE_PATCH_VERSION, interpret

CASES = [
    ("faut ouvrir edge", "open_application", "edge"),
    ("ouvre moi github l\u00e0", "open_website", "github"),
    ("teams est lanc\u00e9 m\u00eame ?", "check_application", "teams"),
    ("word est ouvert ou bien ?", "check_application", "word"),
    ("mets vscode \u00e0 gauche l\u00e0", "manage_window", "vscode"),
    ("faut lancer ma routine", "run_routine", "work_start"),
    ("y a quoi dans documents l\u00e0 ?", "list_directory", "documents"),
]

SAFE_NO_ACTION = [
    "ouvre pas edge",
    "faut ouvrir powershell",
    "ouvre \u00e7a l\u00e0",
    "supprime rapport l\u00e0",
    "faut g\u00e9rer \u00e7a",
]

errors = []
print("Version :", NATURAL_LANGUAGE_PATCH_VERSION)
print()
for text, action, target in CASES:
    result = interpret(text)
    actions = result.get("actions", [])
    ok = bool(actions) and actions[0].get("action") == action and actions[0].get("target") == target
    print(("OK   " if ok else "ECHEC"), "-", text)
    if not ok:
        errors.append((text, result))

for text in SAFE_NO_ACTION:
    result = interpret(text)
    ok = not result.get("actions", [])
    print(("OK   " if ok else "ECHEC"), "-", text, "(aucune action)")
    if not ok:
        errors.append((text, result))

print()
if errors:
    print("ECHEC - certaines protections ou formulations ne correspondent pas a la V6 CI.")
    raise SystemExit(1)
print("LANGAGE V6 CI ACTIF")
