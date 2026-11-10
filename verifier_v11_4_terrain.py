import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
for item in (ROOT, ROOT / "app", ROOT / "backends"):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

import controlled_local_tools
import web_tools
from deterministic_backend import interpret


def ok(label):
    print(f"OK - {label}")


def fail(label, detail=""):
    print(f"ERREUR - {label}{': ' + detail if detail else ''}")
    raise SystemExit(1)


# URL WhatsApp canonique
success, url, error = web_tools.resolve_site("whatsapp")
if not success or url != "https://web.whatsapp.com/":
    fail("URL WhatsApp Web", error or str(url))
ok("WhatsApp pointe vers web.whatsapp.com")

# Langage terrain
checks = {
    "quelle sont mes habitude": "list_habits",
    "donne l'etat du pc": "read_system_info",
    "le volume ?": "read_audio_state",
    "liste tout lew fichier en .txt": "advanced_file_search",
    "combien de memoire il me reste": "read_system_info",
    "quelle sont les caracteristique de ma machine": "read_system_info",
    "verifie que whatsapp est ouvert": "check_browser_site",
}
for phrase, expected in checks.items():
    result = interpret(phrase)
    actions = result.get("actions", []) if isinstance(result, dict) else []
    if not result.get("understood") or not actions or actions[0].get("action") != expected:
        fail(f"langage: {phrase}", repr(result))
    ok(f"langage: {phrase}")

# Conversation locale
for phrase in ("qui est tu", "quel est ton role", "cree document.txt dans document"):
    result = interpret(phrase)
    if not isinstance(result, dict) or not result.get("understood") or not result.get("conversation"):
        fail(f"conversation: {phrase}", repr(result))
    ok(f"conversation: {phrase}")

# Detection WhatsApp non destructive via mocks
policy = {
    "enabled": True,
    "require_explicit_user_command": True,
    "allow_check_site_open": True,
    "allow_subdomains": False,
}
with patch.object(controlled_local_tools, "_load_permissions", return_value={"browser_tab_policy": policy}), \
     patch.object(controlled_local_tools, "resolve_site", return_value=(True, "https://web.whatsapp.com/", None)), \
     patch.object(controlled_local_tools, "list_tabs_via_bridge", return_value=(True, [{"url": "https://web.whatsapp.com/", "title": "WhatsApp", "active": True}], "ok")):
    success, message = controlled_local_tools.check_browser_site_open(
        "whatsapp", explicit_user_command=True, source="manual"
    )
if not success or "est ouvert" not in message:
    fail("detection WhatsApp", message)
ok("detection WhatsApp Web")

# Regle une seule fenetre Edge, non destructive via mocks
edge_path = Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe")
with patch.object(web_tools, "get_application_permission", return_value=True), \
     patch.object(web_tools, "find_edge", return_value=edge_path), \
     patch.object(web_tools, "get_application_window_records", return_value=[{"hwnd": 101}]), \
     patch.object(web_tools, "open_site_via_bridge", return_value=(True, "ok")) as bridge, \
     patch.object(web_tools, "launch_edge_new_window") as new_window:
    success, message = web_tools.open_website("github", source="routine", explicit_user_command=False)
if not success:
    fail("routine Edge partagee", message)
if new_window.called:
    fail("routine Edge partagee", "une nouvelle fenetre aurait ete demandee")
if bridge.call_count != 1:
    fail("routine Edge partagee", "le pont Edge n'a pas ete utilise")
ok("routine: reutilisation de la fenetre Edge existante")

print()
print("V11.4 RETOURS TERRAIN / EDGE UNIQUE ACTIF - verification non destructive OK")
