import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from action_suggestions import (
    build_suggestions,
    clear_pending_suggestion,
    get_pending_suggestions,
    resolve_suggestion_message,
)
from backends.deterministic_backend import interpret
from session_context import clear_session_context, set_last_entity
import agent


def setup_function():
    clear_pending_suggestion()
    clear_session_context()
    agent.DEBUG = False


def _first_action(text):
    result = interpret(text)
    assert result.get("understood"), (text, result)
    actions = result.get("actions", [])
    assert actions, (text, result)
    return actions[0]


def test_spoken_greeting_and_vague_delegation_are_conversational():
    greeting = interpret("salut chef tu es là ?")
    assert greeting.get("understood")
    assert greeting.get("actions") == []
    assert "là" in greeting.get("reply", "") or "la" in greeting.get("reply", "").lower()

    vague = interpret("tu peux gérer un truc pour moi ?")
    assert vague.get("understood")
    assert vague.get("actions") == []
    assert "dis-moi" in vague.get("reply", "")


def test_v118_safe_typos_and_file_kinds():
    assert _first_action("ouvrre bloc note")["target"] == "notepad"
    assert _first_action("donne moi letat du pc")["target"] == "summary"
    assert _first_action("liste tout lew fichier txt")["params"]["file_kind"] == "text"
    assert _first_action("liste les fichiers excem")["params"]["file_kind"] == "excel"
    assert _first_action("lsite tout les fichier docx")["params"]["file_kind"] == "word"
    assert _first_action("liste tout les fichier pptx")["params"]["file_kind"] == "powerpoint"
    assert _first_action("liste tout les fichiers xls")["params"]["file_kind"] == "excel"


def test_firefox_alias_is_understood():
    opened = _first_action("lance fire fox")
    assert opened["action"] == "open_application"
    assert opened["target"] == "firefox"

    checked = _first_action("verifie que fire fox est lancé")
    assert checked["action"] == "check_application"
    assert checked["target"] == "firefox"


def test_natural_documents_and_pictures_roots():
    docs = _first_action("liste tout ce que j'ai dans Documents")
    assert docs["action"] == "list_directory"
    assert docs["target"] == "documents"

    pictures = _first_action("liste le dossier images")
    assert pictures["action"] == "list_directory"
    assert pictures["target"] == "pictures"

    captures = _first_action("liste mes captures d'écran")
    assert captures["action"] == "list_directory"
    assert captures["target"] == "pictures"
    assert captures["params"]["relative_path"] == "Captures AgentLocal"


def test_direct_switch_to_known_web_tab():
    action = _first_action("passe sur whatsapp")
    assert action["action"] == "activate_browser_tab"
    assert action["target"] == "whatsapp"

    # Régression : Teams reste une application de fenêtre, pas un onglet forcé.
    action = _first_action("passe sur teams")
    assert action["action"] == "manage_window"
    assert action["target"] == "teams"
    assert action["params"]["operation"] == "focus"


def test_three_concrete_suggestions_after_documents_listing():
    suggestions = build_suggestions(
        "liste mes documents",
        [{"action": "list_directory", "target": "documents", "params": {}}],
        ["Contenu de Documents :"],
    )
    assert len(suggestions) == 3
    labels = [s.label.lower() for s in suggestions]
    assert any("récents" in value for value in labels)
    assert any("gros" in value for value in labels)
    assert any("doublons" in value for value in labels)


def test_short_answers_select_real_pending_suggestions():
    build_suggestions(
        "liste mes documents",
        [{"action": "list_directory", "target": "documents", "params": {}}],
        ["Contenu de Documents :"],
    )
    first = get_pending_suggestions()[0].command
    second = get_pending_suggestions()[1].command
    assert resolve_suggestion_message("oui") == first
    assert resolve_suggestion_message("2") == second
    assert resolve_suggestion_message("le deuxième") == second


def test_table_choice_creates_actionable_choices():
    response = agent.process_instruction("je veux faire un tableau")
    assert "Excel" in response
    pending = agent.get_pending_action_suggestions()
    assert len(pending) == 2
    assert pending[0]["command"] == "ouvre excel"
    assert pending[1]["command"] == "ouvre word"
    assert resolve_suggestion_message("excel") == "ouvre excel"


def test_session_reference_resolves_close_that():
    set_last_entity("application", "vscode", "check_application")
    assert agent._resolve_session_reference_command("ferme ça") == "ferme vscode"



def test_whatsapp_typo_prefers_known_site_over_file_search():
    action = _first_action("ouvre whatsap")
    assert action["action"] == "open_website"
    assert action["target"] == "whatsapp"


def test_largest_files_query_and_metadata_without_root():
    largest = _first_action("montre-moi les plus gros fichiers dans Téléchargements")
    assert largest["action"] == "advanced_file_search"
    assert largest["target"] == "downloads"
    assert largest["params"]["sort"] == "size_desc"

    metadata = _first_action("donne les infos de rapport.pdf")
    assert metadata["action"] == "inspect_file_metadata_auto"
    assert metadata["target"] == "auto"
    assert metadata["params"]["file_name"] == "rapport.pdf"


def test_mass_actions_are_understood_but_never_executed():
    for text in (
        "ouvre tous les fichiers trouvés",
        "supprime tous les gros fichiers",
        "déplace tous les PDF",
    ):
        result = interpret(text)
        assert result.get("understood"), (text, result)
        assert result.get("actions") == [], (text, result)
        assert result.get("reply"), (text, result)

def test_generated_suggestion_commands_are_interpretable_and_non_destructive():
    samples = [
        ("list_directory", "documents", ["Contenu de Documents :"]),
        ("read_system_info", "summary", ["PC OK"]),
        ("read_network_info", "status", ["Réseau OK"]),
        ("read_audio_state", "audio", ["Volume 30%"]),
        ("take_screenshot", "full_screen", ["Capture enregistrée"]),
        ("list_browser_tabs", "edge", ["1. WhatsApp — web.whatsapp.com\n2. ChatGPT — chatgpt.com"]),
    ]
    destructive = {"delete_file", "delete_file_auto", "move_file_within_root", "move_file_between_roots", "rename_file", "rename_file_auto"}
    for action, target, display in samples:
        suggestions = build_suggestions(
            "test",
            [{"action": action, "target": target, "params": {}}],
            display,
        )
        for suggestion in suggestions:
            result = interpret(suggestion.command)
            assert result.get("understood"), (suggestion, result)
            for generated_action in result.get("actions", []):
                assert generated_action.get("action") not in destructive
