from backends.backend_manager import interpret
from backends.deterministic_backend import parse_habit_command
from project_version import AGENTLOCAL_BUILD

CASES = (
    "Quelles sont mes habitudes ?",
    "quelle sont mes habitudes ?",
    "liste mes habitudes",
    "quelles sont mes habittudes ?",
)

for phrase in CASES:
    result = interpret(phrase)
    assert result.get("routing") == "deterministic_preflight", phrase
    actions = result.get("actions", [])
    assert actions and actions[0].get("action") == "list_habits", phrase

assert parse_habit_command("Quelles sont mes habitudes ?")

BRIEFING_CASES = (
    "Briefing du jour",
    "mon briefing du jour",
    "affiche le briefing",
    "donne-moi le briefing du jour",
)
for phrase in BRIEFING_CASES:
    result = interpret(phrase)
    assert result.get("routing") == "deterministic_preflight", phrase
    actions = result.get("actions", [])
    assert actions and actions[0].get("action") == "read_daily_briefing", phrase

assert "v12.4.2-language-routing" in AGENTLOCAL_BUILD
print("V12.4.2 routage langage / habitudes : OK")
