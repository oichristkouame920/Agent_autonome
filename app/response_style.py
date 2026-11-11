"""Presentation legere des reponses AgentLocal.

Ce module ne change jamais les actions, les permissions ou l'interpretation.
Il ne fait qu'ajouter des reperes visuels aux textes deja produits.
"""
from __future__ import annotations

import re

_EMOJI_PREFIXES = ("✅", "⚠️", "❌", "ℹ️", "🖥️", "🌐", "📁", "📝", "📰", "🌤️", "🔁", "🔊", "🔒", "⚡", "🤖", "👋", "💡", "🚨", "📊")


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
    if any(x in low for x in ("fichier", "dossier", "document", "télécharg", "telecharg")):
        return "📁"
    if any(x in low for x in ("cpu", "ram", "disque", "pc", "processus", "machine")):
        return "🖥️"
    if any(x in low for x in ("volume", "audio", "son")):
        return "🔊"
    if any(x in low for x in ("llm", "modèle", "modele", "agentlocal", "backend", "moteur")):
        return "🤖"
    if any(x in low for x in ("ouvert", "lancé", "lance", "terminé", "termine", "réussi", "reussi", "c'est fait", "ok")):
        return "✅"
    if any(x in low for x in ("bonjour", "salut", "bonsoir", "hello")):
        return "👋"
    return "ℹ️"


def decorate_response(text: object, *, error: bool = False) -> str:
    """Ajoute un seul repere visuel sans reecrire le contenu fonctionnel."""
    value = _plain(text)
    if not value:
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
    if not value or value.startswith(_EMOJI_PREFIXES):
        return value
    return f"{choose_emoji(value)} {value}"
