from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Current tester must ignore every obsolete conformance checker and keep V12.
tester = (ROOT / "tester_agentlocal.ps1").read_text(encoding="utf-8-sig")
assert '^verifier_conformite_pack_' in tester
assert 'verifier_conformite_pack_v12.py' in tester

# The user launcher must not carry a UTF-8 BOM because cmd.exe may echo commands.
raw = (ROOT / "AgentLocal.bat").read_bytes()
assert not raw.startswith(b"\xef\xbb\xbf"), "AgentLocal.bat contient encore un BOM UTF-8"
assert raw.lstrip().startswith(b"@echo off"), "AgentLocal.bat ne commence pas par @echo off"

print("V12.1 R4 mise a jour atomique / nettoyage legacy : OK")
