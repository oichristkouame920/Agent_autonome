from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.action_suggestions import build_suggestions
from app.windows_tools import PROCESS_MAP
from backends.deterministic_backend import APPLICATION_ALIASES, FIELD_LANGUAGE_PATCH_VERSION, interpret
from project_version import AGENTLOCAL_BUILD, AGENTLOCAL_VERSION, SCHEMA_COMPAT_VERSION


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


# 1) Fichiers critiques présents.
critical_files = [
    "app/agent.py",
    "app/gui.py",
    "app/action_suggestions.py",
    "app/session_context.py",
    "app/windows_tools.py",
    "backends/deterministic_backend.py",
    "backends/backend_manager.py",
    "config/permissions.json",
    "config/sites.json",
    "config/routines.json",
    "config/browser_bridge.json",
    "browser_extension/manifest.json",
    "browser_extension/background.js",
    "browser_extension/bridge_config.js",
    "browser_native_host/com.agentlocal.bridge.json",
    "tester_agentlocal.bat",
    "tester_agentlocal.ps1",
    "project_version.py",
]
for relative in critical_files:
    check((ROOT / relative).is_file(), f"Fichier critique manquant : {relative}")

# 2) Source de vérité de version.
check(AGENTLOCAL_VERSION == "11.8", "Version centrale inattendue")
check(SCHEMA_COMPAT_VERSION == 1, "Schéma de compatibilité inattendu")
check(FIELD_LANGUAGE_PATCH_VERSION == AGENTLOCAL_BUILD, "Backend déterministe non aligné sur le build V11.8")

# 3) Tous les JSON de configuration doivent être valides.
for path in sorted((ROOT / "config").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8-sig"))
json.loads((ROOT / "browser_extension/manifest.json").read_text(encoding="utf-8-sig"))
json.loads((ROOT / "browser_native_host/com.agentlocal.bridge.json").read_text(encoding="utf-8-sig"))

permissions = json.loads((ROOT / "config/permissions.json").read_text(encoding="utf-8-sig"))
apps = set(permissions.get("applications", {}))
alias_targets = set(APPLICATION_ALIASES.values())
process_apps = set(PROCESS_MAP)
window_apps = set(permissions.get("window_management", {}).get("allowed_applications", []))

check(alias_targets <= apps, f"Alias application sans permission : {sorted(alias_targets - apps)}")
check(alias_targets <= process_apps, f"Alias application sans PROCESS_MAP : {sorted(alias_targets - process_apps)}")
check(apps == process_apps, f"Permissions/PROCESS_MAP désalignés : permissions-only={sorted(apps-process_apps)}, process-only={sorted(process_apps-apps)}")
check(window_apps <= apps, f"Gestion fenêtres contient des applications inconnues : {sorted(window_apps-apps)}")

# 4) Firefox ajouté de bout en bout.
check("firefox" in apps and "firefox" in process_apps, "Firefox n'est pas aligné dans le catalogue")
check(interpret("lance fire fox").get("actions", [{}])[0].get("target") == "firefox", "Alias 'fire fox' non fonctionnel")

# 5) Pont Edge : config Python, extension et native host doivent partager host/port/id/token.
bridge = json.loads((ROOT / "config/browser_bridge.json").read_text(encoding="utf-8-sig"))
ext_js = (ROOT / "browser_extension/bridge_config.js").read_text(encoding="utf-8-sig")
native = json.loads((ROOT / "browser_native_host/com.agentlocal.bridge.json").read_text(encoding="utf-8-sig"))

def js_value(name: str) -> str | None:
    match = re.search(rf'"?{re.escape(name)}"?\s*:\s*(?:"([^"]*)"|(\d+)|true|false)', ext_js)
    if not match:
        return None
    return match.group(1) if match.group(1) is not None else match.group(2)

check(js_value("host") == str(bridge.get("host")), "Host du pont Edge désaligné")
check(int(js_value("port") or -1) == int(bridge.get("port", -2)), "Port du pont Edge désaligné")
check(js_value("extensionId") == str(bridge.get("extension_id")), "Extension ID désaligné")
check(js_value("token") == str(bridge.get("token")), "Token du pont Edge désaligné")
allowed_origins = set(native.get("allowed_origins", []))
expected_origin = f"chrome-extension://{bridge.get('extension_id')}/"
check(expected_origin in allowed_origins, "Native host non aligné avec l'extension Edge")

# 6) Suggestions : 1 à 3, concrètes, interprétables, non destructives.
destructive_actions = {
    "delete_file", "delete_file_auto", "move_file_within_root", "move_file_between_roots",
    "rename_file", "rename_file_auto", "close_application", "close_website",
}
suggestion_samples = [
    ("list_directory", "documents", ["Contenu de Documents :"]),
    ("read_system_info", "summary", ["PC OK"]),
    ("read_network_info", "status", ["Réseau OK"]),
    ("read_audio_state", "audio", ["Volume 30%"]),
    ("take_screenshot", "full_screen", ["Capture enregistrée"]),
    ("list_browser_tabs", "edge", ["WhatsApp — web.whatsapp.com\nChatGPT — chatgpt.com"]),
]
for action_name, target, display in suggestion_samples:
    suggestions = build_suggestions(
        "verification",
        [{"action": action_name, "target": target, "params": {}}],
        display,
    )
    check(len(suggestions) <= 3, f"Trop de suggestions pour {action_name}")
    for suggestion in suggestions:
        check(bool(suggestion.label.strip()), "Suggestion sans libellé")
        check(bool(suggestion.command.strip()), "Suggestion sans commande")
        result = interpret(suggestion.command)
        check(bool(result.get("understood")), f"Suggestion non interprétable : {suggestion.command}")
        for generated in result.get("actions", []):
            check(generated.get("action") not in destructive_actions, f"Suggestion destructive interdite : {suggestion.command}")

# 7) Le GUI et le coeur doivent exposer la même API de suggestions.
agent_source = (ROOT / "app/agent.py").read_text(encoding="utf-8")
gui_source = (ROOT / "app/gui.py").read_text(encoding="utf-8")
check("def get_pending_action_suggestions" in agent_source, "API suggestions absente d'agent.py")
check("def execute_suggestion" in gui_source, "Boutons de suggestions absents du GUI")
check("get_pending_action_suggestions" in gui_source, "GUI non connecté aux suggestions du coeur")

# 8) Le lanceur global doit compiler, valider, lancer les verifiers puis pytest/tests.
runner = (ROOT / "tester_agentlocal.ps1").read_text(encoding="utf-8-sig")
for token in ("compileall", "json.tool", "verifier_*.py", "pytest -q tests"):
    check(token in runner, f"Lanceur global incomplet : {token}")
check("verifier_runtime_v11_2.py" in runner and "--startup" in runner, "Le test global ne tolère pas correctement le mode dégradé")
check("verifier_resilience_v11_3.py" in runner, "Le test global n'intègre pas le vérificateur de résilience")

# 9) Pas de fichiers temporaires sources connus dans le pack.
for pattern in ("*.tmp", "*.temp"):
    bad = [p for p in ROOT.rglob(pattern) if ".venv" not in p.parts and "runtime" not in p.parts]
    check(not bad, f"Fichiers temporaires détectés : {[str(p.relative_to(ROOT)) for p in bad[:10]]}")

print("Conformité pack AgentLocal V11.8 : OK")
