"""Citation quotidienne locale pour AgentLocal.

Aucune requete Internet. La rotation est deterministe par date afin qu'une meme
journee conserve la meme citation, meme apres redemarrage.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT_DIR / "config" / "quotes.json"

_FALLBACK = (
    "La régularité transforme les petits efforts en grands résultats.",
    "La simplicité est une forme de précision.",
    "Fais d'abord ce qui débloque le reste.",
)


def _load() -> dict:
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def quote_of_day(day: _dt.date | None = None) -> dict[str, str]:
    """Retourne une citation locale stable pour une date donnee."""
    cfg = _load()
    label = str(cfg.get("label") or "Citation du jour").strip() or "Citation du jour"
    author = str(cfg.get("author") or "AgentLocal").strip() or "AgentLocal"
    raw = cfg.get("quotes")
    quotes = [str(x).strip() for x in raw] if isinstance(raw, list) else []
    quotes = [x for x in quotes if x][:128]
    if not quotes:
        quotes = list(_FALLBACK)
    chosen_day = day or _dt.date.today()
    digest = hashlib.sha256(chosen_day.isoformat().encode("ascii")).digest()
    index = int.from_bytes(digest[:4], "big") % len(quotes)
    return {"label": label, "text": quotes[index], "author": author, "date": chosen_day.isoformat()}
