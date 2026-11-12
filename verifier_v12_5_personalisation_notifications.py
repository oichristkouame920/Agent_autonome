from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
from app.user_profile import sanitize_preferences
from app.theme_manager import build_palette, theme_names

prefs = sanitize_preferences({})
assert "appearance" in prefs
assert "notifications" in prefs
assert "understanding" in prefs
assert prefs["notifications"]["mode"] in {"realtime", "balanced", "discreet", "periodic", "silent"}
assert prefs["appearance"]["theme"] in theme_names()
assert prefs["privacy"]["capture_keystrokes"] is False
assert prefs["privacy"]["observe_private_content"] is False
assert prefs["privacy"]["automatic_sensitive_actions"] is False
palette = build_palette({"theme":"violet", "accent_color":"#123456"})
assert palette["accent"] == "#123456"

gui = (ROOT / "app" / "gui.py").read_text(encoding="utf-8")
for needle in ("_open_appearance_editor", "_open_notifications_editor", "_open_understanding_editor", "Résumé périodique", "Heures calmes", "Ajouter une expression"):
    assert needle in gui, needle

agent_source = (ROOT / "app" / "agent.py").read_text(encoding="utf-8")
assert "resolve_learned_expression" in agent_source
assert "record_unrecognized" in agent_source

for name in ("user_profile.json", "user_preferences.json", "notification_state.json", "language_profile.json"):
    manifest = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "memory/" in manifest

print("V12.5 personnalisation complète / notifications / compréhension : OK")
