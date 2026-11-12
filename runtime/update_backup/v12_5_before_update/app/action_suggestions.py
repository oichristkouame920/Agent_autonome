"""Suggestions d'actions contextuelles pour AgentLocal.

V11.8 : plusieurs suggestions concrètes, actionnables et sûres.
- 1 à 3 suggestions maximum.
- Les suggestions restent en mémoire de session uniquement.
- Aucune action destructive n'est proposée automatiquement.
- Chaque suggestion possède un identifiant, un libellé et une commande canonique.
- Compatibilité conservée avec l'API V11.6/V11.7 (get_pending_suggestion,
  build_suggestion, etc.).
"""
from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Iterable


SUGGESTION_TTL_SECONDS = 300
MAX_SUGGESTIONS = 3


@dataclass(frozen=True)
class Suggestion:
    suggestion_id: str
    label: str
    command: str
    text: str
    created_at: float


_pending: list[Suggestion] = []


def _norm(value: object) -> str:
    text = str(value or "").strip().lower().replace("’", "'")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .!?")


def clear_pending_suggestion() -> None:
    global _pending
    _pending = []


def _purge_expired() -> None:
    global _pending
    now = time.monotonic()
    _pending = [s for s in _pending if now - s.created_at <= SUGGESTION_TTL_SECONDS]


def get_pending_suggestions() -> list[Suggestion]:
    _purge_expired()
    return list(_pending)


def get_pending_suggestion() -> Suggestion | None:
    """Compat V11.6 : renvoie la première suggestion en attente."""
    suggestions = get_pending_suggestions()
    return suggestions[0] if suggestions else None


def set_pending_suggestions(items: Iterable[tuple[str, str, str]]) -> list[Suggestion]:
    """Enregistre jusqu'à trois suggestions (id, label, commande)."""
    global _pending
    now = time.monotonic()
    suggestions: list[Suggestion] = []
    seen_commands: set[str] = set()
    for raw_id, raw_label, raw_command in items:
        label = str(raw_label or "").strip()
        command = str(raw_command or "").strip()
        suggestion_id = str(raw_id or "").strip() or f"suggestion_{len(suggestions) + 1}"
        if not label or not command or command.casefold() in seen_commands:
            continue
        seen_commands.add(command.casefold())
        suggestions.append(
            Suggestion(
                suggestion_id=suggestion_id,
                label=label,
                command=command,
                text=label,
                created_at=now,
            )
        )
        if len(suggestions) >= MAX_SUGGESTIONS:
            break
    _pending = suggestions
    return list(_pending)


def set_pending_suggestion(command: str, text: str) -> Suggestion:
    """Compat V11.6 : enregistre une seule suggestion."""
    items = set_pending_suggestions([("suggestion_1", text, command)])
    return items[0]


def is_accept_suggestion_message(message: object) -> bool:
    text = _norm(message)
    if text in {
        "fais la suggestion", "execute la suggestion", "exécute la suggestion",
        "lance la suggestion", "oui fais la suggestion", "oui, fais la suggestion",
        "vas-y fais la suggestion", "vas y fais la suggestion",
    }:
        return True
    return bool(re.fullmatch(r"(?:choisis|prends|fais|lance|execute|exécute)?\s*(?:la\s+)?(?:suggestion\s*)?[123]", text))


def is_reject_suggestion_message(message: object) -> bool:
    text = _norm(message)
    return text in {
        "non", "non laisse", "non laisse tomber", "laisse", "laisse tomber",
        "laisse tomber la suggestion", "annule", "annule la suggestion",
        "ignore", "ignore la suggestion", "pas maintenant", "plus tard",
    }


def _choice_index(text: str) -> int | None:
    value = _norm(text)
    direct = {
        "1": 0, "un": 0, "le premier": 0, "la premiere": 0, "premier": 0, "premiere": 0,
        "suggestion 1": 0, "la suggestion 1": 0, "choix 1": 0,
        "2": 1, "deux": 1, "le deuxieme": 1, "la deuxieme": 1, "deuxieme": 1,
        "suggestion 2": 1, "la suggestion 2": 1, "choix 2": 1,
        "3": 2, "trois": 2, "le troisieme": 2, "la troisieme": 2, "troisieme": 2,
        "suggestion 3": 2, "la suggestion 3": 2, "choix 3": 2,
    }
    if value in direct:
        return direct[value]
    match = re.fullmatch(
        r"(?:choisis|prends|fais|lance|execute|exécute)?\s*(?:la\s+)?(?:suggestion\s*)?([123])",
        value,
    )
    if match:
        return int(match.group(1)) - 1
    return None


def resolve_suggestion_message(message: object) -> str | None:
    """Résout une réponse courte vers une commande canonique sûre."""
    suggestions = get_pending_suggestions()
    if not suggestions:
        return None

    text = _norm(message)
    index = _choice_index(text)
    if index is not None:
        if 0 <= index < len(suggestions):
            return suggestions[index].command
        return None

    # V11.8 : une validation courte choisit la première suggestion, mais
    # seulement lorsqu'une suggestion est réellement en attente.
    if text in {
        "oui", "ok", "d'accord", "daccord", "vas-y", "vas y", "go",
        "fais-le", "fais le", "lance", "execute", "exécute", "allez",
    } or is_accept_suggestion_message(text):
        return suggestions[0].command

    # Permet aussi « les plus récents », « passe sur whatsapp », etc. en
    # comparant le libellé sans exiger la commande exacte.
    for suggestion in suggestions:
        label = _norm(suggestion.label)
        command = _norm(suggestion.command)
        if text == label or text == command:
            return suggestion.command
        # Correspondance prudente : au moins 4 caractères et un libellé contenu.
        if len(text) >= 4 and (text in label or label in text):
            return suggestion.command
    return None


def _has_failure(display_results: Iterable[object]) -> bool:
    for value in display_results:
        text = _norm(value)
        if (
            text.startswith("je n'ai pas exécuté")
            or text.startswith("je n'ai pas execute")
            or text.startswith("erreur")
        ):
            return True
    return False


def _pretty_root(value: str) -> str:
    return {
        "documents": "Documents",
        "downloads": "Téléchargements",
        "desktop": "Bureau",
        "pictures": "Images",
        "videos": "Vidéos",
        "music": "Musique",
        "auto": "mes dossiers autorisés",
    }.get(value, value.capitalize() if value else "ce dossier")


def _suggestion_items(user_message: object, actions: list[dict], display_results: list[object]):
    if not actions or _has_failure(display_results) or len(actions) != 1:
        return []

    action_data = actions[0] if isinstance(actions[0], dict) else {}
    action = _norm(action_data.get("action"))
    target = _norm(action_data.get("target"))
    params = action_data.get("params") if isinstance(action_data.get("params"), dict) else {}
    items: list[tuple[str, str, str]] = []

    if action in {"list_directory", "list_directory_auto"}:
        root = target or _norm(params.get("root"))
        pretty = _pretty_root(root)
        if root in {"documents", "downloads", "desktop", "pictures", "videos", "music"}:
            items.extend([
                ("recent", f"Voir les 5 fichiers les plus récents dans {pretty}", f"montre-moi les 5 fichiers les plus récents dans {pretty}"),
                ("large", f"Voir les plus gros fichiers dans {pretty}", f"montre-moi les 10 fichiers les plus gros dans {pretty}"),
                ("duplicates", f"Chercher les doublons dans {pretty}", f"cherche les doublons dans {pretty}"),
            ])
        else:
            items.append(("recent", "Voir les fichiers les plus récents", "montre-moi les 5 fichiers les plus récents"))

    elif action == "find_filesystem_item":
        items.append(("open_first", "Ouvrir le premier résultat", "ouvre le premier"))

    elif action == "advanced_file_search":
        # Les suggestions prolongent la recherche courante au lieu de repartir
        # sur tous les fichiers. Cela évite les rescans inutiles et les boucles
        # « résultats récents -> mêmes résultats récents ».
        kind = _norm(params.get("file_kind")) or "any"
        sort = _norm(params.get("sort")) or "modified_desc"
        date_filter = _norm(params.get("date_filter")) or "any"
        kind_word = {
            "any": "fichiers",
            "pdf": "PDF",
            "word": "fichiers Word",
            "excel": "fichiers Excel",
            "powerpoint": "présentations PowerPoint",
            "image": "images",
            "video": "vidéos",
            "audio": "fichiers audio",
            "text": "fichiers texte",
        }.get(kind, "fichiers")
        command_kind = {
            "any": "fichiers",
            "pdf": "PDF",
            "word": "fichiers word",
            "excel": "fichiers excel",
            "powerpoint": "fichiers powerpoint",
            "image": "images",
            "video": "vidéos",
            "audio": "fichiers audio",
            "text": "fichiers txt",
        }.get(kind, "fichiers")
        root_suffix = ""
        if target and target != "auto":
            root_suffix = f" dans {_pretty_root(target)}"

        items.append(("open_first", "Ouvrir le premier résultat", "ouvre le premier"))
        if sort != "size_desc":
            items.append((
                "largest_same_filter",
                f"Voir les 5 {kind_word} les plus gros",
                f"montre-moi les 5 {command_kind} les plus gros{root_suffix}",
            ))
        if date_filter != "this_week" and len(items) < MAX_SUGGESTIONS:
            items.append((
                "week_same_filter",
                f"Voir les {kind_word} modifiés cette semaine",
                f"cherche les {command_kind} modifiés cette semaine{root_suffix}",
            ))
        elif sort != "modified_desc" and len(items) < MAX_SUGGESTIONS:
            items.append((
                "recent_same_filter",
                f"Voir les 5 {kind_word} les plus récents",
                f"montre-moi les 5 {command_kind} les plus récents{root_suffix}",
            ))

    elif action == "create_schedule_draft":
        text = "\n".join(str(value or "") for value in display_results)
        match = re.search(r"\b(p-[0-9a-f]{8})\b", text, flags=re.IGNORECASE)
        if match:
            schedule_id = match.group(1).lower()
            items.extend([
                ("confirm_schedule", "Confirmer cette planification", f"confirme la planification {schedule_id}"),
                ("list_schedules", "Voir mes planifications", "liste mes planifications"),
            ])

    elif action in {"confirm_schedule", "enable_schedule", "disable_schedule", "delete_schedule"}:
        items.append(("list_schedules", "Voir mes planifications", "liste mes planifications"))

    elif action == "list_schedules":
        items.extend([
            ("briefing_7", "Planifier le briefing à 7 h", "programme mon briefing chaque matin à 7h"),
            ("routine_7", "Planifier ma routine à 7 h", "programme ma routine chaque matin à 7h"),
        ])

    elif action == "read_system_info":
        if target == "agent":
            items.extend([
                ("pc", "Voir l'état général du PC", "donne-moi l'état du PC"),
                ("processes", "Voir les processus les plus gourmands", "montre les processus les plus gourmands"),
                ("network", "Voir l'état de la connexion", "quel est l'état de ma connexion ?"),
            ])
        elif target == "windows":
            items.extend([
                ("processes", "Voir les processus les plus gourmands", "montre les processus les plus gourmands"),
                ("pc", "Voir l'état général du PC", "donne-moi l'état du PC"),
            ])
        elif target == "summary":
            items.extend([
                ("processes", "Voir les processus les plus gourmands", "montre les processus les plus gourmands"),
                ("large_files", "Chercher les fichiers les plus lourds", "montre-moi les 10 fichiers les plus gros"),
                ("performance", "Ouvrir le tableau de performances", "affiche le tableau de performances du PC"),
            ])
        elif target == "performance":
            items.extend([
                ("processes", "Voir les processus les plus gourmands", "montre les processus les plus gourmands"),
                ("large_files", "Chercher les fichiers les plus lourds", "montre-moi les 10 fichiers les plus gros"),
                ("network", "Voir l'activité réseau", "quel est le trafic réseau actuel"),
            ])
        else:
            items.extend([
                ("performance", "Ouvrir le tableau de performances", "affiche le tableau de performances du PC"),
                ("processes", "Voir les processus les plus gourmands", "montre les processus les plus gourmands"),
                ("pc", "Revenir à l'état général du PC", "donne-moi l'état du PC"),
            ])

    elif action == "read_process_info":
        if target == "top_cpu":
            items.extend([
                ("memory", "Trier les processus par RAM", "montre les processus qui consomment le plus de RAM"),
                ("performance", "Ouvrir le tableau de performances", "affiche le tableau de performances du PC"),
                ("pc", "Voir l'état général du PC", "donne-moi l'état du PC"),
            ])
        elif target == "top_memory":
            items.extend([
                ("cpu", "Trier les processus par CPU", "montre les processus qui consomment le plus de CPU"),
                ("performance", "Ouvrir le tableau de performances", "affiche le tableau de performances du PC"),
                ("pc", "Voir l'état général du PC", "donne-moi l'état du PC"),
            ])
        else:
            items.extend([
                ("cpu", "Trier par consommation CPU", "montre les processus qui consomment le plus de CPU"),
                ("memory", "Trier par consommation RAM", "montre les processus qui consomment le plus de RAM"),
                ("performance", "Ouvrir le tableau de performances", "affiche le tableau de performances du PC"),
            ])

    elif action == "read_network_info":
        items.extend([
            ("link_speed", "Voir la vitesse de liaison", "quelle est la vitesse de ma connexion ?"),
            ("pc", "Voir l'état général du PC", "donne-moi l'état du PC"),
        ])

    elif action == "read_weather":
        items.extend([
            ("news", "Voir les actualités du jour", "donne-moi les actualités du jour"),
            ("briefing", "Ouvrir le briefing du jour", "briefing du jour"),
            ("pc", "Voir l'état général du PC", "donne-moi l'état du PC"),
        ])

    elif action == "read_news":
        items.extend([
            ("weather", "Voir la météo du jour", "quelle est la météo d'aujourd'hui ?"),
            ("briefing", "Ouvrir le briefing du jour", "briefing du jour"),
            ("pc", "Voir l'état général du PC", "donne-moi l'état du PC"),
        ])

    elif action == "read_daily_briefing":
        items.extend([
            ("weather", "Actualiser la météo", "quelle est la météo d'aujourd'hui ?"),
            ("news", "Voir les actualités du jour", "donne-moi les actualités du jour"),
            ("updates", "Vérifier AgentLocal en ligne", "vérifie mes mises à jour"),
        ])

    elif action == "check_online_updates":
        items.extend([
            ("briefing", "Ouvrir le briefing du jour", "briefing du jour"),
            ("pc", "Voir l'état général du PC", "donne-moi l'état du PC"),
        ])

    elif action == "read_audio_state":
        items.extend([
            ("volume30", "Régler le volume à 30 %", "mets le volume à 30%"),
            ("mute", "Couper le son", "coupe le son"),
        ])

    elif action == "close_application":
        # Une cible comme Teams peut exister a la fois en application Windows
        # et en onglet Edge. Si le desktop est deja ferme, on ne pretend pas
        # que tout est ferme : on propose explicitement la fermeture Web.
        joined = "\n".join(str(x) for x in display_results).lower()
        dual_targets = {
            "teams": "Teams",
            "outlook": "Outlook",
            "whatsapp": "WhatsApp",
        }
        key = str(target or "").strip().lower()
        if key in dual_targets and ("deja ferme" in joined or "déjà fermé" in joined or "déjà fermée" in joined):
            label = dual_targets[key]
            items.extend([
                (f"close_web_{key}", f"Fermer {label} dans Edge", f"ferme le site {key}"),
                ("tabs", "Voir les onglets Edge ouverts", "liste mes onglets"),
            ])

    elif action in {"open_website", "open_browser_site_existing_edge"}:
        items.extend([
            ("tabs", "Voir les onglets Edge ouverts", "liste mes onglets"),
            ("switch", "Passer sur cet onglet", f"passe sur {target}" if target else "liste mes onglets"),
        ])

    elif action == "list_browser_tabs":
        joined = "\n".join(str(x) for x in display_results).lower()
        known = [
            ("whatsapp", "WhatsApp"), ("chatgpt", "ChatGPT"), ("teams", "Teams"),
            ("github", "GitHub"), ("outlook", "Outlook"), ("descript", "Descript"),
        ]
        for site, label in known:
            if site in joined:
                items.append((f"tab_{site}", f"Passer sur {label}", f"passe sur {site}"))
            if len(items) >= 3:
                break

    elif action == "take_screenshot":
        items.extend([
            ("captures", "Lister mes captures d'écran", "liste mes captures d'écran"),
            ("pictures", "Ouvrir le dossier Images", "ouvre le dossier Images"),
        ])

    elif action == "find_duplicate_files":
        items.extend([
            ("large", "Voir les plus gros fichiers de ce dossier", f"montre-moi les 10 fichiers les plus gros dans {_pretty_root(target)}"),
            ("recent", "Voir les fichiers les plus récents", f"montre-moi les 5 fichiers les plus récents dans {_pretty_root(target)}"),
        ])

    elif action == "list_habits":
        items.append(("routine", "Lancer ma routine de travail", "lance ma routine"))

    return items[:MAX_SUGGESTIONS]


def build_suggestions(user_message: object, actions: list[dict], display_results: list[object]) -> list[Suggestion]:
    clear_pending_suggestion()
    return set_pending_suggestions(_suggestion_items(user_message, actions, display_results))


def build_suggestion(user_message: object, actions: list[dict], display_results: list[object]) -> Suggestion | None:
    """Compat V11.6 : construit les suggestions et renvoie la première."""
    suggestions = build_suggestions(user_message, actions, display_results)
    return suggestions[0] if suggestions else None


def format_suggestions(suggestions: Iterable[Suggestion]) -> str:
    values = list(suggestions)[:MAX_SUGGESTIONS]
    if not values:
        return ""
    lines = ["Suggestions utiles :"]
    for index, suggestion in enumerate(values, start=1):
        lines.append(f"[{index}] {suggestion.label}")
    lines.append("Tu peux cliquer sur une suggestion ou répondre 1, 2, 3, « oui » ou « pas maintenant ».")
    return "\n".join(lines)


def format_suggestion(suggestion: Suggestion) -> str:
    """Compat V11.6 : affiche toutes les suggestions actuellement en attente."""
    pending = get_pending_suggestions()
    if not pending:
        pending = [suggestion]
    return format_suggestions(pending)
