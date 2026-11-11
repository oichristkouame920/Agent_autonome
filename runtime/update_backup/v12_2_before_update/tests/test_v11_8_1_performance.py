import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.action_suggestions import build_suggestions
from backends import backend_manager
from backends.deterministic_backend import interpret
from project_version import AGENTLOCAL_VERSION


def _first_action(text):
    result = interpret(text)
    assert result.get("understood"), (text, result)
    actions = result.get("actions", [])
    assert actions, (text, result)
    return actions[0]


def test_version_hotfix():
    assert tuple(int(x) for x in AGENTLOCAL_VERSION.split(".")[:2]) >= (11, 8)


def test_pc_state_variants_use_deterministic_fast_path():
    for text in ("quelle l'etat de mon PC", "quel est l'etat de mon PC"):
        action = _first_action(text)
        assert action["action"] == "read_system_info"
        assert action["target"] == "summary"


def test_known_unsupported_sleep_does_not_need_llm():
    result = interpret("met mon PC en veille")
    assert result.get("understood")
    assert result.get("actions") == []
    assert "veille" in result.get("reply", "").lower()


def test_backend_selection_is_skipped_for_closed_deterministic_intent(monkeypatch):
    def forbidden_select_backend():
        raise AssertionError("select_backend ne doit pas être appelé pour une commande déterministe fermée")

    monkeypatch.setattr(backend_manager, "select_backend", forbidden_select_backend)
    result = backend_manager.interpret("quel est l'etat de mon PC")
    assert result.get("routing") == "deterministic_preflight"
    assert result.get("actions", [])[0]["action"] == "read_system_info"


def test_file_suggestions_keep_original_filter_and_do_not_loop_recent():
    suggestions = build_suggestions(
        "liste les fichiers word",
        [{
            "action": "advanced_file_search",
            "target": "auto",
            "params": {
                "file_kind": "word",
                "date_filter": "any",
                "date_field": "modified",
                "size_operator": "any",
                "size_bytes": 0,
                "sort": "modified_desc",
                "limit": 10,
                "count_only": False,
            },
        }],
        ["83 fichiers Word"],
    )
    commands = [item.command.lower() for item in suggestions]
    assert len(suggestions) <= 3
    assert any("word" in command and "plus gros" in command for command in commands)
    assert any("word" in command and "cette semaine" in command for command in commands)
    assert not any(command == "montre-moi les 5 fichiers les plus récents" for command in commands)
    for item in suggestions:
        assert interpret(item.command).get("understood"), item.command
