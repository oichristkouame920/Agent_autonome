from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "app", ROOT / "backends"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from backends.deterministic_backend import interpret
import controlled_open_tools
import windows_tools


def first_action(text):
    result = interpret(text)
    assert result.get("understood") is True
    actions = result.get("actions") or []
    assert actions
    return actions[0]


def test_list_all_my_documents_is_normalized():
    action = first_action("liste tout mes documents")
    assert action["action"] == "list_directory"
    assert action["target"] == "documents"


def test_bare_open_can_fallback_to_unique_directory():
    action = first_action("ouvre Formation JS")
    assert action["action"] == "open_file_auto"
    assert action["params"]["file_name"] == "Formation JS"
    assert action["params"]["allow_directory_fallback"] is True


def test_close_named_folder_is_understood():
    action = first_action("ferme le dossier Formation JS")
    assert action["action"] == "close_directory_auto"
    assert action["params"]["directory_name"] == "Formation JS"


def test_command_prompt_alias_is_blocked_not_treated_as_file():
    result = interpret("ouvre l'invite de commande")
    assert result.get("understood") is True
    assert result.get("actions") == []
    assert "interdite" in result.get("reply", "").lower()


def test_habit_request_uses_summary_not_pending_only():
    action = first_action("quelles sont mes habitudes ?")
    assert action["action"] == "list_habits"
    assert action["target"] == "summary"


def test_explicit_pending_habits_still_available():
    action = first_action("liste mes habitudes en attente")
    assert action["action"] == "list_habits"
    assert action["target"] == "pending"


def test_folder_delete_is_understood_but_not_executed():
    result = interpret("supprime le dossier AnyDesk")
    assert result.get("understood") is True
    assert result.get("actions") == []
    reply = result.get("reply", "")
    assert "AnyDesk" in reply
    assert "pas activée" in reply or "pas activee" in reply


def test_casual_conversation_tone():
    result = interpret("bonjour")
    assert "Je suis là" in result.get("reply", "")
    result = interpret("ok")
    assert result.get("reply") == "Ça marche."


def test_open_file_auto_directory_fallback(monkeypatch):
    monkeypatch.setattr(controlled_open_tools, "_manual_open_allowed", lambda *a, **k: (True, None))
    monkeypatch.setattr(
        controlled_open_tools.recursive,
        "get_unique_reference_for_context",
        lambda *a, **k: (True, {
            "root_name": "documents",
            "relative_path": "Formation JS",
            "item_type": "dir",
        }),
    )
    monkeypatch.setattr(
        controlled_open_tools,
        "open_directory",
        lambda root_name, relative_path, **kwargs: (True, f"Dossier ouvert : {root_name}/{relative_path}"),
    )

    ok, message = controlled_open_tools.open_file_auto(
        "Formation JS",
        explicit_user_command=True,
        source="manual",
        allow_directory_fallback=True,
    )
    assert ok is True
    assert "Formation JS" in message


def test_close_explorer_folder_refuses_multiple_matches(monkeypatch):
    records = [
        {"hwnd": 1, "window_pid": 10, "window_process_create_time": 1.0, "title": "Formation JS"},
        {"hwnd": 2, "window_pid": 10, "window_process_create_time": 1.0, "title": "Formation JS - Explorateur de fichiers"},
    ]
    monkeypatch.setattr(windows_tools, "get_application_window_records", lambda app: records)
    ok, message = windows_tools.close_explorer_window_by_folder_name(
        "Formation JS", explicit_user_command=True
    )
    assert ok is False
    assert "plusieurs" in message.lower()

def test_more_casual_phrasings_are_understood():
    action = first_action("fais voir mes documents")
    assert action["action"] == "list_directory"
    assert action["target"] == "documents"

    action = first_action("check moi si teams est ouvert")
    assert action["action"] == "check_application"
    assert action["target"] == "teams"

    action = first_action("ça dit quoi le pc")
    assert action["action"] == "read_system_info"
    assert action["target"] == "summary"

    action = first_action("le volume c est combien")
    assert action["action"] == "read_audio_state"
    assert action["target"] == "master"
