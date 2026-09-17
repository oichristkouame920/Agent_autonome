from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

from backends.deterministic_backend import interpret, ADVANCED_SEARCH_PATCH_VERSION
import recursive_file_tools


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


require(
    ADVANCED_SEARCH_PATCH_VERSION == "2026-09-17-v10.1-advanced-file-search",
    "Version V10.1 non détectée dans le backend déterministe.",
)

cases = [
    ("montre-moi les PDF téléchargés aujourd'hui", "downloads", "pdf", "today"),
    ("retrouve les fichiers Word modifiés cette semaine", "auto", "word", "this_week"),
    ("montre-moi les 5 fichiers les plus récents", "auto", "any", "any"),
    ("combien j'ai de PDF dans Documents ?", "documents", "pdf", "any"),
    ("retrouve les images créées hier", "auto", "image", "yesterday"),
]

for text, target, kind, date_filter in cases:
    result = interpret(text)
    actions = result.get("actions", []) if isinstance(result, dict) else []
    require(len(actions) == 1, f"Phrase non reconnue : {text}")
    action = actions[0]
    require(action.get("action") == "advanced_file_search", f"Mauvaise action : {text}")
    require(action.get("target") == target, f"Mauvaise racine : {text}")
    params = action.get("params", {})
    require(params.get("file_kind") == kind, f"Mauvais type : {text}")
    require(params.get("date_filter") == date_filter, f"Mauvaise date : {text}")

# La recherche classique par nom ne doit pas être détournée.
normal = interpret("cherche rapport.pdf")
normal_actions = normal.get("actions", [])
require(normal_actions and normal_actions[0].get("action") == "find_filesystem_item", "Régression de la recherche par nom.")

# Une négation ne doit rien exécuter.
negative = interpret("montre pas les PDF téléchargés aujourd'hui")
require(negative.get("actions") == [], "Une négation déclenche encore une recherche.")

permissions = json.loads((ROOT / "config" / "permissions.json").read_text(encoding="utf-8"))
policy = permissions.get("filesystem", {}).get("advanced_search_policy", {})
require(policy.get("enabled") is True, "Politique de recherche avancée désactivée.")
require(policy.get("read_only") is True, "La recherche avancée doit rester en lecture seule.")
require(policy.get("metadata_only") is True, "La recherche doit rester limitée aux métadonnées.")
require(policy.get("require_explicit_user_command") is True, "Commande explicite obligatoire.")
require(policy.get("allow_from_routine") is False, "Les routines doivent être interdites.")
require(policy.get("allow_from_habit") is False, "Les habitudes doivent être interdites.")
require(policy.get("allow_automatic_search") is False, "La recherche automatique doit être interdite.")
require(int(policy.get("maximum_results", 999)) <= 20, "Trop de résultats autorisés.")
require(int(policy.get("maximum_search_entries", 999999)) <= 6000, "Trop d'entrées autorisées.")
require(callable(recursive_file_tools.advanced_search_files), "Outil de recherche avancée absent.")

print("RECHERCHE LOCALE V10.1 ACTIVE - verification non destructive OK")
