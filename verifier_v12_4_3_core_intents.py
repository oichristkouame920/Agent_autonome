from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
for path in (ROOT, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from backends.backend_manager import interpret
from app.agent import verify_explicit_list_directory
from app.response_style import decorate_response
from app.windows_startup import _vbs_text

cases = {
    "liste mes telechargment": ("list_directory", "downloads"),
    "montre mes téléchargements": ("list_directory", "downloads"),
    "Processus": ("read_process_info", "summary"),
    "montre moi les processus": ("read_process_info", "summary"),
    "quel est ton etat": ("read_system_info", "agent"),
}

for text, expected in cases.items():
    result = interpret(text)
    assert result.get("routing") == "deterministic_preflight", (text, result)
    action = result.get("actions", [])[0]
    assert (action.get("action"), action.get("target")) == expected, (text, action)
    print(f"OK - {text} -> {expected[0]}/{expected[1]}")

assert verify_explicit_list_directory("liste mes telechargment", "downloads")
assert verify_explicit_list_directory("montre moi mes téléchargements", "downloads")
print("OK - preuve explicite Téléchargements tolère faute et forme naturelle")

identity = interpret("qui est tu")
assert decorate_response(identity.get("reply", "")).startswith("🤖 ")
print("OK - identité AgentLocal -> emoji agent")

assert not _vbs_text().encode("ascii").startswith(b"\xef\xbb\xbf")
print("OK - script VBS compatible ASCII / sans BOM")

print("V12.4.3 INTENTIONS COEUR / ROUTAGE DETERMINISTE : OK")
