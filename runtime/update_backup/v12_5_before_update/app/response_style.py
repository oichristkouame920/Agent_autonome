"""Presentation legere des reponses AgentLocal.

Ce module ne change jamais les actions, les permissions ou l'interpretation.
Il ne fait qu'ajouter des reperes visuels aux textes deja produits.
"""
from __future__ import annotations

import re

try:
    from user_profile import load_preferences
except Exception:  # compatibilite / tests isoles
    load_preferences = None

_EMOJI_PREFIXES = ("✅", "⚠️", "❌", "ℹ️", "🖥️", "🌐", "📁", "📝", "📰", "🌤️", "🔁", "🔊", "🔒", "⚡", "🤖", "👋", "💡", "🚨", "📊", "🪟")


def _plain(text: object) -> str:
    return str(text or "").strip()


def choose_emoji(text: str, *, error: bool = False) -> str:
    low = text.casefold()
    if error or any(x in low for x in ("erreur", "échec", "echec", "impossible", "introuvable")):
        return "❌"
    if any(x in low for x in ("critique", "alerte", "problème", "probleme")):
        return "🚨"
    if any(x in low for x in ("attention", "avertissement", "élevé", "eleve", "faible", "indisponible")):
        return "⚠️"
    if any(x in low for x in ("météo", "meteo", "température", "temperature")):
        return "🌤️"
    if any(x in low for x in ("actualité", "actualite", "briefing")):
        return "📰"
    if any(x in low for x in ("routine", "planification", "tâche", "tache")):
        return "🔁"
    if any(x in low for x in ("internet", "réseau", "reseau", "edge", "site", "onglet", "web")):
        return "🌐"
    # Les réponses d'identité doivent rester identifiées comme AgentLocal, même
    # si elles mentionnent ensuite les fichiers ou les applications autorisées.
    if low.startswith("je suis agentlocal") or "ton assistant sur ce pc" in low:
        return "🤖"
    if any(x in low for x in ("fenêtre", "fenetre", "fenêtres", "fenetres")):
        return "🪟"
    if any(x in low for x in ("fichier", "dossier", "document", "télécharg", "telecharg")):
        return "📁"
    if any(x in low for x in ("cpu", "ram", "disque", "pc", "processus", "machine")):
        return "🖥️"
    # Le mot "son" doit etre un mot complet : sinon "sont" declenchait
    # a tort l'emoji audio dans des phrases comme "quelles sont les fenetres".
    if re.search(r"\b(?:volume|audio|son)\b", low):
        return "🔊"
    if any(x in low for x in ("llm", "modèle", "modele", "agentlocal", "backend", "moteur")):
        return "🤖"
    if any(x in low for x in ("ouvert", "lancé", "lance", "terminé", "termine", "réussi", "reussi", "c'est fait", "ok")):
        return "✅"
    if any(x in low for x in ("bonjour", "salut", "bonsoir", "hello")):
        return "👋"
    return "ℹ️"


def get_presentation_preferences() -> dict:
    default = {"response_style": "natural", "emoji_level": "light", "daily_quote": True, "smart_suggestions": True}
    if load_preferences is None:
        return default
    try:
        prefs = load_preferences()
        block = prefs.get("assistant", {}) if isinstance(prefs, dict) else {}
        if isinstance(block, dict):
            default.update({key: block.get(key, default[key]) for key in default})
    except Exception:
        pass
    return default


def decorate_response(text: object, *, error: bool = False) -> str:
    """Ajoute un repere visuel selon la preference locale, sans changer le sens."""
    value = _plain(text)
    if not value:
        return value
    prefs = get_presentation_preferences()
    if str(prefs.get("emoji_level", "light")).lower() == "none":
        return value
    if value.startswith(_EMOJI_PREFIXES):
        return value
    # Ne jamais toucher a un bloc de code ou a un contenu structure brut.
    if value.startswith("{") or value.startswith("[") and "Thinking" not in value:
        return value
    first = value.splitlines()[0].strip()
    emoji = choose_emoji(first or value, error=error)
    return f"{emoji} {value}"


def decorate_suggestion_label(label: object) -> str:
    value = _plain(label)
    if not value:
        return value
    prefs = get_presentation_preferences()
    if str(prefs.get("emoji_level", "light")).lower() == "none":
        return value
    if value.startswith(_EMOJI_PREFIXES):
        return value
    return f"{choose_emoji(value)} {value}"
