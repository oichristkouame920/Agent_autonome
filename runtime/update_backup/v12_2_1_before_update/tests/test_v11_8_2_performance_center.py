import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.action_suggestions import build_suggestions
from app.controlled_local_tools import read_process_info, read_system_info
from backends import backend_manager
from backends.deterministic_backend import interpret
from project_version import AGENTLOCAL_BUILD, AGENTLOCAL_VERSION


def _first_action(text):
    result = interpret(text)
    assert result.get("understood"), (text, result)
    actions = result.get("actions", [])
    assert actions, (text, result)
    return actions[0]


def test_version_performance_center():
    assert tuple(map(int, AGENTLOCAL_VERSION.split("."))) >= (11, 8, 2)
    assert tuple(int(x) for x in AGENTLOCAL_VERSION.split(".")[:2]) >= (11, 8)


def test_performance_dashboard_commands_are_deterministic():
    for text in (
        "affiche le tableau de performances du PC",
        "montre les performances de mon PC",
        "panneau performance",
    ):
        action = _first_action(text)
        assert action["action"] == "read_system_info"
        assert action["target"] == "performance"


def test_process_commands_are_deterministic():
    samples = {
        "montre les processus les plus gourmands": "top",
        "montre les processus qui consomment le plus de CPU": "top_cpu",
        "montre les processus qui consomment le plus de RAM": "top_memory",
        "combien de processus sont en cours": "summary",
    }
    for text, target in samples.items():
        action = _first_action(text)
        assert action["action"] == "read_process_info"
        assert action["target"] == target


def test_pc_state_suggestions_are_actionable_and_concrete():
    suggestions = build_suggestions(
        "donne-moi l'état du PC",
        [{"schema_version": 1, "action": "read_system_info", "target": "summary", "params": None}],
        ["État du PC : RAM 50% ; CPU 10%"],
    )
    labels = [item.label for item in suggestions]
    commands = [item.command for item in suggestions]
    assert labels == [
        "Voir les processus les plus gourmands",
        "Chercher les fichiers les plus lourds",
        "Ouvrir le tableau de performances",
    ]
    assert len(suggestions) == 3
    for command in commands:
        assert interpret(command).get("understood"), command


def test_performance_suggestions_include_process_files_network():
    suggestions = build_suggestions(
        "affiche le tableau de performances du PC",
        [{"schema_version": 1, "action": "read_system_info", "target": "performance", "params": None}],
        ["Tableau de performances du PC"],
    )
    labels = [item.label.lower() for item in suggestions]
    assert any("processus" in label for label in labels)
    assert any("fichiers" in label for label in labels)
    assert any("réseau" in label or "reseau" in label for label in labels)


def test_process_policy_is_strictly_read_only():
    permissions = json.loads((ROOT / "config/permissions.json").read_text(encoding="utf-8-sig"))
    policy = permissions["process_information_policy"]
    assert policy["enabled"] is True
    assert policy["read_only"] is True
    assert policy["allow_process_termination"] is False
    assert policy["allow_from_routine"] is False
    assert policy["allow_from_habit"] is False


def test_runtime_readers_return_human_readable_text():
    ok, text = read_system_info("performance", explicit_user_command=True, source="manual")
    assert ok, text
    assert "CPU" in text or "RAM" in text

    ok, text = read_process_info("summary", explicit_user_command=True, source="manual")
    assert ok, text
    assert "Processus" in text


def test_process_diagnostics_use_deterministic_fast_path(monkeypatch):
    def forbidden_select_backend():
        raise AssertionError("Le diagnostic processus ne doit pas sonder llama.cpp")

    monkeypatch.setattr(backend_manager, "select_backend", forbidden_select_backend)
    result = backend_manager.interpret("montre les processus les plus gourmands")
    assert result.get("routing") == "deterministic_preflight"
    assert result.get("actions", [])[0].get("action") == "read_process_info"
