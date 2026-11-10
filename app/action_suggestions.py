"""Suggestions d'actions sûres pour AgentLocal.

V11.6 : une seule suggestion contextuelle à la fois, en mémoire de session.
Aucune suggestion n'est exécutée automatiquement. Seules des commandes à faible risque
(lecture, ouverture, navigation non destructive) sont proposées.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable


SUGGESTION_TTL_SECONDS = 300


@dataclass(frozen=True)
class Suggestion:
    command: str
    text: str
    created_at: float


_pending: Suggestion | None = None


def _norm(value: object) -> str:
    text = str(value or "").strip().lower().replace("’", "'")
    return " ".join(text.split())


def clear_pending_suggestion() -> None:
    global _pending
    _pending = None


def get_pending_suggestion() -> Suggestion | None:
    global _pending
    if _pending is None:
        return None
    if time.monotonic() - _pending.created_at > SUGGESTION_TTL_SECONDS:
        _pending = None
        return None
    return _pending


def set_pending_suggestion(command: str, text: str) -> Suggestion:
    global _pending
    _pending = Suggestion(command=command.strip(), text=text.strip(), created_at=time.monotonic())
    return _pending


def is_accept_suggestion_message(message: object) -> bool:
    text = _norm(message)
    return text in {
        "fais la suggestion",
        "execute la suggestion",
        "exécute la suggestion",
        "lance la suggestion",
        "oui fais la suggestion",
        "oui, fais la suggestion",
        "vas-y fais la suggestion",
        "vas y fais la suggestion",
    }


def is_reject_suggestion_message(message: object) -> bool:
    text = _norm(message)
    return text in {
        "non laisse",
        "non laisse tomber",
        "laisse tomber la suggestion",
        "annule la suggestion",
        "ignore la suggestion",
        "pas maintenant",
    }


def _has_failure(display_results: Iterable[object]) -> bool:
    for value in display_results:
        text = _norm(value)
        if text.startswith("je n'ai pas exécuté") or text.startswith("je n'ai pas execute"):
            return True
    return False


def build_suggestion(user_message: object, actions: list[dict], display_results: list[object]) -> Suggestion | None:
    """Construit au plus une suggestion sûre à partir des actions réellement demandées."""
    clear_pending_suggestion()
    if not actions or _has_failure(display_results):
        return None

    # Les commandes multiples/routines ne reçoivent pas de suggestion : on évite le bruit.
    if len(actions) != 1:
        return None

    action_data = actions[0] if isinstance(actions[0], dict) else {}
    action = _norm(action_data.get("action"))
    target = _norm(action_data.get("target"))
    params = action_data.get("params") if isinstance(action_data.get("params"), dict) else {}

    command = None
    text = None

    if action in {"list_directory", "list_directory_auto"}:
        root = target or _norm(params.get("root"))
        pretty = {
            "documents": "Documents", "downloads": "Téléchargements", "desktop": "Bureau",
            "pictures": "Images", "videos": "Vidéos", "music": "Musique",
        }.get(root, root.capitalize() if root else "ce dossier")
        command = f"montre-moi les 5 fichiers les plus récents dans {pretty}"
        text = f"Si tu veux, je peux aussi te montrer les fichiers les plus récents dans {pretty}."

    elif action in {"find_filesystem_item", "advanced_file_search"}:
        command = "ouvre-le"
        text = "Si c’est bien l’élément que tu cherchais, je peux aussi l’ouvrir."

    elif action == "read_system_info":
        command = "quelle est la vitesse de ma connexion ?"
        text = "Si tu veux, je peux aussi vérifier l’état de ta connexion réseau."

    elif action == "read_network_info":
        command = "donne-moi l'état du PC"
        text = "Je peux aussi te donner un aperçu rapide de l’état du PC."

    elif action == "read_audio_state":
        command = "mets le volume à 30%"
        text = "Si tu veux régler le son, tu peux me donner directement un pourcentage."

    elif action in {"open_website", "open_browser_site_existing_edge"}:
        command = "liste mes onglets"
        text = "Si tu veux, je peux aussi te montrer les onglets Edge ouverts."

    elif action == "list_browser_tabs":
        command = "vérifie que whatsapp est ouvert"
        text = "Je peux aussi vérifier si un site précis est déjà ouvert."

    elif action in {"open_file", "open_file_auto", "open_directory", "open_directory_auto"}:
        # Pas de suggestion automatique après une ouverture : trop facile de devenir bavard.
        return None

    elif action == "list_habits":
        command = "lance ma routine"
        text = "Si tu veux démarrer ton environnement de travail, je peux aussi lancer ta routine."

    if not command or not text:
        return None

    return set_pending_suggestion(command, text)


def format_suggestion(suggestion: Suggestion) -> str:
    return (
        f"Suggestion : {suggestion.text}\n"
        f"Commande proposée : « {suggestion.command} »\n"
        "Si tu veux que je la lance, dis simplement : « fais la suggestion »."
    )
