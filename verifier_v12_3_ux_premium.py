from __future__ import annotations
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
APP=ROOT/"app"
for p in (ROOT,APP):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from project_version import AGENTLOCAL_VERSION, AGENTLOCAL_BUILD
from daily_quotes import quote_of_day
from response_style import decorate_response
assert AGENTLOCAL_VERSION == "12.5"
assert "v12.3-ux-premium" in AGENTLOCAL_BUILD
q=json.loads((ROOT/"config/quotes.json").read_text(encoding="utf-8"))
assert len(q.get("quotes",[])) >= 28
assert quote_of_day()["text"]
assert decorate_response("CPU : 12 %").startswith("🖥️")
src=(ROOT/"app/gui.py").read_text(encoding="utf-8")
for token in ("CARD_META","NAV_ICONS","Citation du jour","decorate_response","quote_bg"):
    assert token in src
bat=(ROOT/"AgentLocal.bat").read_text(encoding="utf-8-sig")
labels=[line.strip().casefold() for line in bat.splitlines() if line.strip().startswith(":")]
assert len(labels)==len(set(labels))
assert "call :CLEAN_OBSOLETE" in bat[bat.index(":VERIFY"):bat.index(":SETUP")]
print("V12.3 UX Premium : cartes, couleurs, emoji, citation et lanceur corrige - OK")
