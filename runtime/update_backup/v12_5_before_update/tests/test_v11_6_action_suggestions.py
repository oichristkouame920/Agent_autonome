import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from action_suggestions import (
    build_suggestion,
    clear_pending_suggestion,
    get_pending_suggestion,
    is_accept_suggestion_message,
    is_reject_suggestion_message,
)


def setup_function():
    clear_pending_suggestion()


def test_suggestion_after_directory_listing_is_safe():
    s = build_suggestion(
        "liste mes documents",
        [{"action": "list_directory", "target": "documents", "params": {}}],
        ["Contenu de Documents :"],
    )
    assert s is not None
    assert "récents" in s.command
    assert get_pending_suggestion() is not None


def test_no_suggestion_after_failure():
    s = build_suggestion(
        "ouvre inconnu",
        [{"action": "open_file_auto", "target": "documents", "params": {}}],
        ["Je n'ai pas exécuté cette action : introuvable"],
    )
    assert s is None
    assert get_pending_suggestion() is None


def test_no_suggestion_for_multiple_actions():
    s = build_suggestion(
        "ouvre github et chatgpt",
        [
            {"action": "open_website", "target": "github", "params": {}},
            {"action": "open_website", "target": "chatgpt", "params": {}},
        ],
        ["OK", "OK"],
    )
    assert s is None


def test_accept_and_reject_phrases_are_explicit():
    assert is_accept_suggestion_message("fais la suggestion")
    assert is_accept_suggestion_message("oui fais la suggestion")
    assert not is_accept_suggestion_message("oui")
    assert is_reject_suggestion_message("pas maintenant")


def test_suggestions_never_offer_destructive_action():
    samples = [
        ("read_system_info", "summary"),
        ("read_network_info", "status"),
        ("list_browser_tabs", "edge"),
        ("list_habits", "all"),
    ]
    forbidden = ("supprime", "efface", "déplace", "deplace", "renomme", "ferme")
    for action, target in samples:
        s = build_suggestion("x", [{"action": action, "target": target, "params": {}}], ["OK"])
        if s:
            assert not any(word in s.command.lower() for word in forbidden)
