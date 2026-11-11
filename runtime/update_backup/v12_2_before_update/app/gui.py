"""Interface graphique AgentLocal V12.1.

Objectifs :
- Windows 10/11 64 bits.
- Interface professionnelle, chaleureuse et intuitive.
- Faible empreinte memoire : Tkinter/ttk uniquement.
- Aucun contournement de securite : toutes les actions passent par agent.py.
- Les informations de l'accueil restent en lecture seule.
"""

from __future__ import annotations

import datetime as _dt
import os
import queue
import shutil
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR / "app"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from project_version import AGENTLOCAL_VERSION  # noqa: E402
from connected_services import (  # noqa: E402
    build_daily_briefing,
    format_daily_briefing,
    format_news,
    format_weather,
    mark_morning_briefing_shown,
    should_show_morning_briefing,
)
from scheduler import (  # noqa: E402
    claim_schedule as claim_scheduled_execution,
    get_due_schedules,
    has_active_kind as has_active_schedule_kind,
    load_config as load_scheduler_config,
    mark_run as mark_schedule_run,
)
from routine_tools import execute_routine as execute_scheduled_routine  # noqa: E402
from runtime_resilience import (  # noqa: E402
    critical_health_messages,
    format_health_summary,
    log_exception,
    startup_health_report,
)

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None

AGENT_IMPORT_ERROR = None
try:
    import agent  # noqa: E402
except Exception as error:  # L'interface doit rester visible meme si le coeur echoue.
    agent = None
    AGENT_IMPORT_ERROR = error
    log_exception("gui.import_agent", error)

APP_TITLE = "AgentLocal"
MAX_COMMAND_LENGTH = 2000
POLL_INTERVAL_MS = 80
DASHBOARD_REFRESH_MS = 3000

# Palette sobre, contraste eleve, aucun framework externe.
COLORS = {
    "bg": "#F4F7FB",
    "sidebar": "#111827",
    "sidebar_hover": "#1F2937",
    "sidebar_active": "#253858",
    "card": "#FFFFFF",
    "border": "#E5EAF0",
    "text": "#172033",
    "muted": "#68758A",
    "accent": "#2F6FED",
    "accent_hover": "#255ED0",
    "success": "#15803D",
    "warning": "#B7791F",
    "danger": "#B42318",
    "soft_accent": "#EAF1FF",
    "soft_success": "#EAF8EF",
    "soft_warning": "#FFF7E6",
    "soft_neutral": "#F3F5F8",
    "conversation": "#FAFBFD",
}

if agent is not None:
    agent.DEBUG = False


def normalize_user_command(value: str) -> str:
    """Nettoie uniquement les bords sans reecrire la demande utilisateur."""
    if not isinstance(value, str):
        return ""
    return value.strip()


def get_runtime_summary() -> tuple[str, str]:
    """Lit la configuration sans charger volontairement un modele LLM."""
    if agent is None:
        return "Moteur : indisponible", "Apprentissage : indisponible"
    try:
        config = agent.get_agent_config()
    except Exception:
        config = {}

    backend = config.get("backend", {}) if isinstance(config, dict) else {}
    learning = config.get("learning", {}) if isinstance(config, dict) else {}

    if not isinstance(backend, dict):
        backend = {}
    if not isinstance(learning, dict):
        learning = {}

    mode = str(backend.get("mode", "auto")).strip().lower() or "auto"
    learning_enabled = bool(learning.get("enabled", False))

    backend_text = f"Moteur : {mode} - chargé à la demande"
    learning_text = "Apprentissage : activé" if learning_enabled else "Apprentissage : désactivé"
    return backend_text, learning_text


def is_local_gui_close_command(value: str) -> bool:
    text = str(value or "").strip().lower().replace("’", "'")
    text = " ".join(text.replace("-", " ").split())
    return text in {
        "sort", "quitte", "quitter", "ferme agentlocal",
        "ferme cette fenêtre", "ferme cette fenetre",
    }


def _format_bytes(value: float | int | None) -> str:
    if value is None:
        return "--"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "--"
    for unit in ("o", "Ko", "Mo", "Go", "To"):
        if number < 1024 or unit == "To":
            return f"{number:.0f} {unit}" if unit in {"o", "Ko"} else f"{number:.1f} {unit}"
        number /= 1024.0
    return "--"


def _format_uptime(seconds: float | int | None) -> str:
    if seconds is None:
        return "--"
    try:
        seconds = max(0, int(seconds))
    except (TypeError, ValueError):
        return "--"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days} j {hours} h"
    if hours:
        return f"{hours} h {minutes} min"
    return f"{minutes} min"


def _greeting() -> str:
    hour = _dt.datetime.now().hour
    if 5 <= hour < 12:
        return "Bonjour"
    if 12 <= hour < 18:
        return "Bon après-midi"
    return "Bonsoir"


class AgentLocalGUI:
    """Interface principale AgentLocal V12.1."""

    NAV_ITEMS = (
        ("Accueil", "home"),
        ("Briefing", "briefing"),
        ("Assistant", "assistant"),
        ("Mon PC", "pc"),
        ("Fichiers", "files"),
        ("Web", "web"),
        ("Routines", "routines"),
        ("Paramètres", "settings"),
    )

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.result_queue: queue.Queue[tuple[str, str, float]] = queue.Queue(maxsize=1)
        self.briefing_queue: queue.Queue[tuple[dict, bool]] = queue.Queue(maxsize=1)
        self.schedule_queue: queue.Queue[tuple[dict, bool, str, dict | None]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.briefing_worker: threading.Thread | None = None
        self.schedule_worker: threading.Thread | None = None
        self.briefing_fetching = False
        self.busy = False
        self.active_page = "home"
        self.nav_buttons: dict[str, tk.Button] = {}
        self.pages: dict[str, tk.Frame] = {}
        self.metric_vars: dict[str, tk.StringVar] = {}
        self.last_started_at = 0.0

        self.command_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Prêt")
        self.response_time_var = tk.StringVar(value="")
        self.backend_var = tk.StringVar()
        self.learning_var = tk.StringVar()
        self.health_var = tk.StringVar(value="État : vérification...")
        self.weather_var = tk.StringVar(value="Météo : chargement à la demande")
        self.news_var = tk.StringVar(value="Actualités : chargement à la demande")
        self.health_report = None
        self.safe_mode = False

        self._configure_window()
        self._configure_styles()
        self._build_interface()
        self._refresh_runtime_summary()
        self._run_startup_health_check()
        self._update_dashboard_metrics()
        self.show_page("home")

        self.root.after(POLL_INTERVAL_MS, self._poll_worker_result)
        self.root.after(DASHBOARD_REFRESH_MS, self._dashboard_loop)
        self.root.after(900, self._maybe_start_morning_briefing)
        self.root.after(2500, self._scheduler_loop)

    # ------------------------------------------------------------------
    # Fenetre et style
    # ------------------------------------------------------------------
    def _configure_window(self) -> None:
        self.root.title(f"{APP_TITLE} - Assistant local")
        self.root.geometry("1180x760")
        self.root.minsize(960, 640)
        self.root.configure(bg=COLORS["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        available = set(style.theme_names())
        for candidate in ("clam", "vista", "xpnative", "default"):
            if candidate in available:
                try:
                    style.theme_use(candidate)
                    break
                except tk.TclError:
                    continue

        style.configure("App.TFrame", background=COLORS["bg"])
        style.configure("Card.TFrame", background=COLORS["card"])
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 22, "bold"))
        style.configure("PageTitle.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 18, "bold"))
        style.configure("CardTitle.TLabel", background=COLORS["card"], foreground=COLORS["muted"], font=("Segoe UI", 9, "bold"))
        style.configure("CardValue.TLabel", background=COLORS["card"], foreground=COLORS["text"], font=("Segoe UI", 18, "bold"))
        style.configure("Body.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=("Segoe UI", 9))
        style.configure("CardBody.TLabel", background=COLORS["card"], foreground=COLORS["text"], font=("Segoe UI", 10))
        style.configure("CardMuted.TLabel", background=COLORS["card"], foreground=COLORS["muted"], font=("Segoe UI", 9))
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 9))
        style.configure("Secondary.TButton", font=("Segoe UI", 9), padding=(12, 8))
        style.configure("Suggestion.TButton", font=("Segoe UI", 9, "bold"), padding=(10, 8))

    def _build_interface(self) -> None:
        shell = tk.Frame(self.root, bg=COLORS["bg"])
        shell.pack(fill="both", expand=True)
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_columnconfigure(1, weight=1)

        self._build_sidebar(shell)

        content_shell = tk.Frame(shell, bg=COLORS["bg"])
        content_shell.grid(row=0, column=1, sticky="nsew")
        content_shell.grid_rowconfigure(1, weight=1)
        content_shell.grid_columnconfigure(0, weight=1)

        self._build_topbar(content_shell)

        self.page_host = tk.Frame(content_shell, bg=COLORS["bg"])
        self.page_host.grid(row=1, column=0, sticky="nsew", padx=24, pady=(12, 20))
        self.page_host.grid_rowconfigure(0, weight=1)
        self.page_host.grid_columnconfigure(0, weight=1)

        self._build_home_page()
        self._build_briefing_page()
        self._build_assistant_page()
        self._build_pc_page()
        self._build_files_page()
        self._build_web_page()
        self._build_routines_page()
        self._build_settings_page()

        self.root.bind("<Control-k>", self._focus_command)
        self.root.bind("<Control-K>", self._focus_command)
        self.root.bind("<Control-l>", self._on_clear_shortcut)
        self.root.bind("<Control-L>", self._on_clear_shortcut)

    def _build_sidebar(self, parent: tk.Widget) -> None:
        sidebar = tk.Frame(parent, bg=COLORS["sidebar"], width=205)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(9, weight=1)

        brand = tk.Frame(sidebar, bg=COLORS["sidebar"])
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(22, 24))
        tk.Label(brand, text="AgentLocal", bg=COLORS["sidebar"], fg="white", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(brand, text=f"Version {AGENTLOCAL_VERSION}", bg=COLORS["sidebar"], fg="#AAB4C4", font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 0))

        for row, (label, key) in enumerate(self.NAV_ITEMS, start=1):
            button = tk.Button(
                sidebar,
                text=label,
                command=lambda page=key: self.show_page(page),
                anchor="w",
                relief="flat",
                bd=0,
                padx=18,
                pady=11,
                bg=COLORS["sidebar"],
                fg="#D9E1EC",
                activebackground=COLORS["sidebar_hover"],
                activeforeground="white",
                font=("Segoe UI", 10),
                cursor="hand2",
                highlightthickness=0,
            )
            button.grid(row=row, column=0, sticky="ew", padx=10, pady=2)
            self.nav_buttons[key] = button

        footer = tk.Frame(sidebar, bg=COLORS["sidebar"])
        footer.grid(row=10, column=0, sticky="sew", padx=18, pady=18)
        tk.Label(footer, text="100 % local par défaut", bg=COLORS["sidebar"], fg="#8D9AAF", font=("Segoe UI", 8)).pack(anchor="w")
        tk.Label(footer, text="Actions contrôlées", bg=COLORS["sidebar"], fg="#8D9AAF", font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 0))

    def _build_topbar(self, parent: tk.Widget) -> None:
        bar = tk.Frame(parent, bg=COLORS["bg"], height=70)
        bar.grid(row=0, column=0, sticky="ew", padx=24, pady=(14, 0))
        bar.grid_columnconfigure(0, weight=1)

        left = tk.Frame(bar, bg=COLORS["bg"])
        left.grid(row=0, column=0, sticky="w")
        self.top_title = tk.Label(left, text="Accueil", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 16, "bold"))
        self.top_title.pack(anchor="w")
        self.top_subtitle = tk.Label(left, text="Ton espace local de travail", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 9))
        self.top_subtitle.pack(anchor="w", pady=(2, 0))

        right = tk.Frame(bar, bg=COLORS["bg"])
        right.grid(row=0, column=1, sticky="e")
        self.health_badge = tk.Label(right, text="Diagnostic...", bg=COLORS["soft_neutral"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        self.health_badge.pack(side="right")

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------
    def _new_page(self, key: str) -> tk.Frame:
        page = tk.Frame(self.page_host, bg=COLORS["bg"])
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_rowconfigure(99, weight=1)
        page.grid_columnconfigure(0, weight=1)
        self.pages[key] = page
        return page

    def _card(self, parent: tk.Widget, title: str, value_var: tk.StringVar | None = None, text: str | None = None, width: int = 220) -> tk.Frame:
        card = tk.Frame(parent, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1, bd=0, width=width, height=105)
        card.grid_propagate(False)
        tk.Label(card, text=title, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15, pady=(13, 5))
        if value_var is not None:
            tk.Label(card, textvariable=value_var, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=15)
        elif text is not None:
            tk.Label(card, text=text, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 11, "bold"), wraplength=max(140, width - 30), justify="left").pack(anchor="w", padx=15)
        return card

    def _section_title(self, parent: tk.Widget, title: str, subtitle: str = "") -> tk.Frame:
        frame = tk.Frame(parent, bg=COLORS["bg"])
        tk.Label(frame, text=title, bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 14, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(frame, text=subtitle, bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))
        return frame

    def _quick_button(self, parent: tk.Widget, text: str, command: str, description: str = "") -> tk.Frame:
        card = tk.Frame(parent, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        card.grid_columnconfigure(0, weight=1)
        tk.Label(card, text=text, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 10, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(11, 2))
        if description:
            tk.Label(card, text=description, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8), anchor="w", wraplength=220, justify="left").grid(row=1, column=0, sticky="ew", padx=14)
        tk.Button(
            card,
            text="Ouvrir",
            command=lambda c=command, label=text: self.run_shortcut(c, label),
            relief="flat",
            bd=0,
            bg=COLORS["soft_accent"],
            fg=COLORS["accent"],
            activebackground="#DDE8FF",
            activeforeground=COLORS["accent_hover"],
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
            highlightthickness=0,
            padx=10,
            pady=5,
        ).grid(row=0, column=1, rowspan=2, sticky="e", padx=12)
        return card

    def _build_home_page(self) -> None:
        page = self._new_page("home")

        hero = tk.Frame(page, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        hero.grid(row=0, column=0, sticky="ew")
        hero.grid_columnconfigure(0, weight=1)
        self.home_greeting = tk.Label(hero, text=f"{_greeting()} !", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 20, "bold"))
        self.home_greeting.grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        tk.Label(hero, text="AgentLocal est prêt. Parle naturellement, lance une action ou vérifie ton PC en un clic.", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 18))
        tk.Button(hero, text="Ouvrir l'Assistant", command=lambda: self.show_page("assistant"), relief="flat", bd=0, bg=COLORS["accent"], fg="white", activebackground=COLORS["accent_hover"], activeforeground="white", font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2", highlightthickness=0).grid(row=0, column=1, rowspan=2, padx=20)

        stats = tk.Frame(page, bg=COLORS["bg"])
        stats.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        for i in range(4):
            stats.grid_columnconfigure(i, weight=1, uniform="stats")

        for key, label in (("cpu", "CPU"), ("ram", "RAM"), ("disk", "Disque libre"), ("uptime", "Temps actif")):
            self.metric_vars[key] = tk.StringVar(value="--")

        cards = [
            self._card(stats, "CPU", self.metric_vars["cpu"]),
            self._card(stats, "RAM", self.metric_vars["ram"]),
            self._card(stats, "Disque libre", self.metric_vars["disk"]),
            self._card(stats, "Temps actif", self.metric_vars["uptime"]),
        ]
        for col, card in enumerate(cards):
            card.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0 if col == 3 else 6))

        section = self._section_title(page, "Actions rapides", "Les commandes les plus utiles restent locales et contrôlées.")
        section.grid(row=2, column=0, sticky="ew", pady=(20, 10))

        quick = tk.Frame(page, bg=COLORS["bg"])
        quick.grid(row=3, column=0, sticky="ew")
        quick.grid_columnconfigure(0, weight=1)
        quick.grid_columnconfigure(1, weight=1)
        self._quick_button(quick, "État du PC", "quel est l'état de mon PC", "CPU, RAM, disque, uptime").grid(row=0, column=0, sticky="ew", padx=(0, 7), pady=(0, 8))
        self._quick_button(quick, "Fichiers lourds", "montre-moi les plus gros fichiers", "Repérer ce qui occupe de l'espace").grid(row=0, column=1, sticky="ew", padx=(7, 0), pady=(0, 8))
        self._quick_button(quick, "Ma routine", "lance ma routine", "Préparer ton environnement de travail").grid(row=1, column=0, sticky="ew", padx=(0, 7), pady=(0, 8))
        self._quick_button(quick, "Onglets Edge", "liste mes onglets", "Voir les onglets accessibles par le pont local").grid(row=1, column=1, sticky="ew", padx=(7, 0), pady=(0, 8))
        self._quick_button(quick, "Briefing du jour", "briefing du jour", "Météo et actualités, uniquement si Internet est disponible").grid(row=2, column=0, sticky="ew", padx=(0, 7))
        self._quick_button(quick, "Météo", "quelle est la météo d'aujourd'hui ?", "Service Internet optionnel en lecture seule").grid(row=2, column=1, sticky="ew", padx=(7, 0))

    def _build_briefing_page(self) -> None:
        page = self._new_page("briefing")
        self._section_title(page, "Briefing du jour", "Internet est optionnel : si la connexion manque, AgentLocal reste entièrement utilisable en local.").grid(row=0, column=0, sticky="ew")

        weather_card = tk.Frame(page, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        weather_card.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        tk.Label(weather_card, text="Météo", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(13, 4))
        tk.Label(weather_card, textvariable=self.weather_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9), wraplength=760, justify="left").pack(anchor="w", padx=16, pady=(0, 13))

        news_card = tk.Frame(page, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        news_card.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        tk.Label(news_card, text="Actualités", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(13, 4))
        tk.Label(news_card, textvariable=self.news_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9), wraplength=780, justify="left").pack(anchor="w", padx=16, pady=(0, 13))

        actions = tk.Frame(page, bg=COLORS["bg"])
        actions.grid(row=3, column=0, sticky="w", pady=(14, 0))
        tk.Button(actions, text="Actualiser le briefing", command=lambda: self._start_briefing_refresh(show_popup=False, force=True), relief="flat", bd=0, bg=COLORS["accent"], fg="white", activebackground=COLORS["accent_hover"], activeforeground="white", font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2", highlightthickness=0).pack(side="left")
        tk.Button(actions, text="Demander dans l'Assistant", command=lambda: self.run_shortcut("briefing du jour", "Briefing du jour"), relief="flat", bd=0, bg=COLORS["soft_accent"], fg=COLORS["accent"], activebackground="#DDE8FF", font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2", highlightthickness=0).pack(side="left", padx=(8, 0))

        security = tk.Frame(page, bg=COLORS["soft_success"], highlightbackground="#CBE7D3", highlightthickness=1)
        security.grid(row=4, column=0, sticky="ew", pady=(18, 0))
        tk.Label(security, text="Sécurité Internet", bg=COLORS["soft_success"], fg=COLORS["success"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(12, 3))
        tk.Label(security, text="Les services connectés utilisent uniquement des requêtes HTTPS GET vers des domaines autorisés. Les titres et données reçus sont affichés comme du texte et ne peuvent jamais devenir des commandes système.", bg=COLORS["soft_success"], fg=COLORS["success"], font=("Segoe UI", 9), wraplength=800, justify="left").pack(anchor="w", padx=15, pady=(0, 12))

    def _build_assistant_page(self) -> None:
        page = self._new_page("assistant")
        page.grid_rowconfigure(0, weight=1)

        conversation_card = tk.Frame(page, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        conversation_card.grid(row=0, column=0, sticky="nsew")
        conversation_card.grid_rowconfigure(0, weight=1)
        conversation_card.grid_columnconfigure(0, weight=1)

        self.conversation = ScrolledText(
            conversation_card,
            wrap="word",
            state="disabled",
            font=("Segoe UI", 10),
            relief="flat",
            borderwidth=0,
            bg=COLORS["conversation"],
            fg=COLORS["text"],
            padx=16,
            pady=14,
            undo=False,
            maxundo=0,
        )
        self.conversation.grid(row=0, column=0, sticky="nsew")
        self.conversation.tag_configure("user", font=("Segoe UI", 10, "bold"), foreground=COLORS["accent"], spacing1=10)
        self.conversation.tag_configure("agent", font=("Segoe UI", 10), foreground=COLORS["text"], spacing1=5, spacing3=10)
        self.conversation.tag_configure("error", font=("Segoe UI", 10, "bold"), foreground=COLORS["danger"], spacing1=5, spacing3=10)

        self.suggestion_frame = tk.Frame(page, bg=COLORS["bg"])
        self.suggestion_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        for col in range(3):
            self.suggestion_frame.grid_columnconfigure(col, weight=1)
        self.suggestion_buttons: list[tk.Button] = []
        for index in range(3):
            button = tk.Button(
                self.suggestion_frame,
                text="",
                command=lambda i=index: self.execute_suggestion(i),
                relief="flat",
                bd=0,
                bg=COLORS["soft_accent"],
                fg=COLORS["accent"],
                activebackground="#DDE8FF",
                activeforeground=COLORS["accent_hover"],
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
                highlightthickness=0,
                padx=10,
                pady=9,
            )
            button.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 4, 0 if index == 2 else 4))
            button.grid_remove()
            self.suggestion_buttons.append(button)
        self.suggestion_frame.grid_remove()

        composer = tk.Frame(page, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        composer.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        composer.grid_columnconfigure(0, weight=1)

        self.command_entry = tk.Entry(composer, textvariable=self.command_var, font=("Segoe UI", 11), relief="flat", bd=0, bg="white", fg=COLORS["text"], insertbackground=COLORS["text"], highlightthickness=0)
        self.command_entry.grid(row=0, column=0, sticky="ew", padx=(14, 8), pady=12, ipady=5)
        self.command_entry.bind("<Return>", self._on_enter)

        self.execute_button = tk.Button(composer, text="Envoyer", command=self.execute_command, relief="flat", bd=0, bg=COLORS["accent"], fg="white", activebackground=COLORS["accent_hover"], activeforeground="white", font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2", highlightthickness=0)
        self.execute_button.grid(row=0, column=1, padx=(0, 7))

        self.clear_button = tk.Button(composer, text="Effacer", command=self.clear_conversation, relief="flat", bd=0, bg=COLORS["soft_neutral"], fg=COLORS["muted"], activebackground="#E7EAF0", font=("Segoe UI", 9), padx=12, pady=8, cursor="hand2", highlightthickness=0)
        self.clear_button.grid(row=0, column=2, padx=(0, 10))

        info = tk.Frame(page, bg=COLORS["bg"])
        info.grid(row=3, column=0, sticky="ew", pady=(7, 0))
        info.grid_columnconfigure(0, weight=1)
        tk.Label(info, text="Ctrl+K : écrire  •  Entrée : envoyer  •  Ctrl+L : effacer l'affichage", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        tk.Label(info, textvariable=self.status_var, bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 8, "bold")).grid(row=0, column=1, sticky="e")
        tk.Label(info, textvariable=self.response_time_var, bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 8)).grid(row=0, column=2, sticky="e", padx=(10, 0))

        self._append_agent("Salut ! Je suis prêt. Tu peux me parler normalement ou utiliser les raccourcis à gauche.")

    def _build_pc_page(self) -> None:
        page = self._new_page("pc")
        title = self._section_title(page, "Mon PC", "Vue rapide et actions de diagnostic en lecture seule.")
        title.grid(row=0, column=0, sticky="ew")

        metrics = tk.Frame(page, bg=COLORS["bg"])
        metrics.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        for i in range(4):
            metrics.grid_columnconfigure(i, weight=1, uniform="pcstats")
        for key, label in (("pc_cpu", "CPU"), ("pc_ram", "RAM"), ("pc_disk", "Disque libre"), ("pc_proc", "Processus")):
            self.metric_vars[key] = tk.StringVar(value="--")
        pc_cards = [
            self._card(metrics, "CPU", self.metric_vars["pc_cpu"]),
            self._card(metrics, "RAM", self.metric_vars["pc_ram"]),
            self._card(metrics, "Disque libre", self.metric_vars["pc_disk"]),
            self._card(metrics, "Processus", self.metric_vars["pc_proc"]),
        ]
        for col, card in enumerate(pc_cards):
            card.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0 if col == 3 else 6))

        actions = self._section_title(page, "Diagnostic", "Choisis ce que tu veux examiner.")
        actions.grid(row=2, column=0, sticky="ew", pady=(20, 10))
        grid = tk.Frame(page, bg=COLORS["bg"])
        grid.grid(row=3, column=0, sticky="ew")
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        items = [
            ("Tableau de performances", "ouvre le tableau de performances", "CPU, RAM, disque, uptime et processus"),
            ("Processus gourmands", "voir les processus les plus gourmands", "Classement instantané CPU / RAM"),
            ("État du réseau", "quel est l'état de ma connexion", "Interfaces et disponibilité réseau"),
            ("Performance AgentLocal", "quelle est ta performance", "Consommation et backend actuel"),
        ]
        for i, item in enumerate(items):
            self._quick_button(grid, *item).grid(row=i // 2, column=i % 2, sticky="ew", padx=(0 if i % 2 == 0 else 7, 0 if i % 2 == 1 else 7), pady=(0, 8))

    def _build_files_page(self) -> None:
        page = self._new_page("files")
        self._section_title(page, "Fichiers", "Accès contrôlé aux emplacements autorisés.").grid(row=0, column=0, sticky="ew")
        grid = tk.Frame(page, bg=COLORS["bg"])
        grid.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        items = [
            ("Documents", "liste mes documents", "Voir le contenu de Documents"),
            ("Téléchargements", "liste mes téléchargements", "Voir les téléchargements locaux"),
            ("Fichiers récents", "montre-moi les 10 fichiers les plus récents", "Derniers fichiers modifiés"),
            ("Fichiers lourds", "montre-moi les plus gros fichiers", "Trouver ce qui occupe le plus d'espace"),
            ("Doublons", "cherche les doublons dans Documents", "Analyse par empreinte SHA-256"),
            ("Captures", "liste mes captures d'écran", "Retrouver les captures AgentLocal"),
        ]
        for i, item in enumerate(items):
            self._quick_button(grid, *item).grid(row=i // 2, column=i % 2, sticky="ew", padx=(0 if i % 2 == 0 else 7, 0 if i % 2 == 1 else 7), pady=(0, 8))

    def _build_web_page(self) -> None:
        page = self._new_page("web")
        self._section_title(page, "Web", "Les sites s'ouvrent via Edge et restent soumis aux règles locales.").grid(row=0, column=0, sticky="ew")
        grid = tk.Frame(page, bg=COLORS["bg"])
        grid.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        items = [
            ("Onglets Edge", "liste mes onglets", "Voir les onglets accessibles par le pont local"),
            ("WhatsApp", "ouvre whatsapp", "Ouvrir ou réutiliser WhatsApp Web"),
            ("ChatGPT", "ouvre chatgpt", "Ouvrir ou réutiliser ChatGPT"),
            ("UDMCI", "ouvre udmci", "Ouvrir la plateforme UDMCI"),
            ("Outlook", "ouvre outlook", "Ouvrir la messagerie"),
            ("GitHub", "ouvre github", "Ouvrir GitHub dans Edge"),
        ]
        for i, item in enumerate(items):
            self._quick_button(grid, *item).grid(row=i // 2, column=i % 2, sticky="ew", padx=(0 if i % 2 == 0 else 7, 0 if i % 2 == 1 else 7), pady=(0, 8))

    def _build_routines_page(self) -> None:
        page = self._new_page("routines")
        self._section_title(page, "Routines", "Tes routines restent locales et ne gagnent aucune permission automatiquement.").grid(row=0, column=0, sticky="ew")
        grid = tk.Frame(page, bg=COLORS["bg"])
        grid.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        items = [
            ("Lancer ma routine", "lance ma routine", "Préparer l'environnement de travail"),
            ("Mes habitudes", "liste mes habitudes", "Habitudes validées et propositions"),
            ("Mes planifications", "liste mes planifications", "Automatisations horaires confirmées"),
            ("Briefing à 7 h", "programme mon briefing chaque matin à 7h", "Crée un brouillon à confirmer avant activation"),
        ]
        for i, item in enumerate(items):
            self._quick_button(grid, *item).grid(row=i // 2, column=i % 2, sticky="ew", padx=(0 if i % 2 == 0 else 7, 0 if i % 2 == 1 else 7), pady=(0, 8))

        note = tk.Frame(page, bg=COLORS["soft_warning"], highlightbackground="#F1D8A6", highlightthickness=1)
        note.grid(row=2, column=0, sticky="ew", pady=(18, 0))
        tk.Label(note, text="Sécurité des habitudes", bg=COLORS["soft_warning"], fg="#7A5611", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(12, 3))
        tk.Label(note, text="Une habitude ou une planification reste inactive tant qu’elle n’a pas été validée explicitement. Les automatisations ne peuvent utiliser que des actions autorisées.", bg=COLORS["soft_warning"], fg="#7A5611", font=("Segoe UI", 9), wraplength=720, justify="left").pack(anchor="w", padx=15, pady=(0, 12))

    def _build_settings_page(self) -> None:
        page = self._new_page("settings")
        self._section_title(page, "Paramètres", "Informations de fonctionnement. Les réglages sensibles restent dans les fichiers de configuration contrôlés.").grid(row=0, column=0, sticky="ew")

        card = tk.Frame(page, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        card.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        card.grid_columnconfigure(1, weight=1)
        rows = [
            ("Version", AGENTLOCAL_VERSION),
            ("Moteur", self.backend_var),
            ("État", self.health_var),
            ("Apprentissage", self.learning_var),
            ("Services Internet", "Optionnels - météo / actualités / mises à jour"),
            ("Planificateur", "Local - confirmation obligatoire - actif seulement quand AgentLocal tourne"),
        ]
        for i, (label, value) in enumerate(rows):
            tk.Label(card, text=label, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).grid(row=i, column=0, sticky="w", padx=16, pady=(12 if i == 0 else 7, 12 if i == len(rows)-1 else 7))
            if isinstance(value, tk.StringVar):
                tk.Label(card, textvariable=value, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9)).grid(row=i, column=1, sticky="w", padx=10)
            else:
                tk.Label(card, text=str(value), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9)).grid(row=i, column=1, sticky="w", padx=10)

        tk.Button(page, text="Lancer un diagnostic complet", command=lambda: self.run_shortcut("quel est l'état de mon PC", "Diagnostic du PC"), relief="flat", bd=0, bg=COLORS["accent"], fg="white", activebackground=COLORS["accent_hover"], activeforeground="white", font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2", highlightthickness=0).grid(row=2, column=0, sticky="w", pady=(16, 0))

    # ------------------------------------------------------------------
    # Navigation et dashboard
    # ------------------------------------------------------------------
    def show_page(self, key: str) -> None:
        if key not in self.pages:
            return
        self.active_page = key
        self.pages[key].tkraise()
        labels = dict((k, label) for label, k in self.NAV_ITEMS)
        subtitles = {
            "home": "Ton espace local de travail",
            "briefing": "Météo et actualités en lecture seule",
            "assistant": "Parle naturellement à AgentLocal",
            "pc": "Performances et diagnostic en lecture seule",
            "files": "Fichiers autorisés et analyses locales",
            "web": "Navigation Edge contrôlée",
            "routines": "Routines et habitudes locales",
            "settings": "Version, moteur et état de santé",
        }
        self.top_title.configure(text=labels.get(key, APP_TITLE))
        self.top_subtitle.configure(text=subtitles.get(key, ""))
        for page_key, button in self.nav_buttons.items():
            if page_key == key:
                button.configure(bg=COLORS["sidebar_active"], fg="white", font=("Segoe UI", 10, "bold"))
            else:
                button.configure(bg=COLORS["sidebar"], fg="#D9E1EC", font=("Segoe UI", 10))
        if key == "briefing" and not self.briefing_fetching and self.weather_var.get().startswith("Météo : chargement"):
            self._start_briefing_refresh(show_popup=False, force=False)
        if key == "assistant" and not self.busy:
            self.command_entry.focus_set()

    def _dashboard_loop(self) -> None:
        self._update_dashboard_metrics()
        try:
            self.root.after(DASHBOARD_REFRESH_MS, self._dashboard_loop)
        except tk.TclError:
            pass

    def _update_dashboard_metrics(self) -> None:
        cpu = None
        ram = None
        disk_free = None
        uptime = None
        proc_count = None
        try:
            if psutil is not None:
                cpu = float(psutil.cpu_percent(interval=None))
                mem = psutil.virtual_memory()
                ram = float(mem.percent)
                uptime = time.time() - float(psutil.boot_time())
                proc_count = len(psutil.pids())
            drive = os.environ.get("SystemDrive", "C:") + "\\" if os.name == "nt" else str(Path.home().anchor or "/")
            usage = shutil.disk_usage(drive)
            disk_free = usage.free
        except Exception:
            pass

        values = {
            "cpu": f"{cpu:.0f}%" if cpu is not None else "--",
            "ram": f"{ram:.0f}%" if ram is not None else "--",
            "disk": _format_bytes(disk_free),
            "uptime": _format_uptime(uptime),
            "pc_cpu": f"{cpu:.0f}%" if cpu is not None else "--",
            "pc_ram": f"{ram:.0f}%" if ram is not None else "--",
            "pc_disk": _format_bytes(disk_free),
            "pc_proc": str(proc_count) if proc_count is not None else "--",
        }
        for key, value in values.items():
            var = self.metric_vars.get(key)
            if var is not None:
                var.set(value)
        if hasattr(self, "home_greeting"):
            self.home_greeting.configure(text=f"{_greeting()} !")

    # ------------------------------------------------------------------
    # Briefing connecte V12
    # ------------------------------------------------------------------
    def _maybe_start_morning_briefing(self) -> None:
        try:
            # Une planification de briefing confirmée remplace le popup générique
            # afin d'éviter deux briefings le même matin.
            if has_active_schedule_kind("briefing"):
                return
            if should_show_morning_briefing():
                self._start_briefing_refresh(show_popup=True, force=False)
        except Exception as error:
            log_exception("gui.morning_briefing", error)

    def _start_briefing_refresh(self, show_popup: bool = False, force: bool = False) -> None:
        if self.briefing_fetching:
            return
        self.briefing_fetching = True
        self.weather_var.set("Météo : actualisation...")
        self.news_var.set("Actualités : actualisation...")
        self.briefing_worker = threading.Thread(
            target=self._briefing_worker,
            args=(show_popup, force),
            daemon=True,
            name="AgentLocalBriefing",
        )
        self.briefing_worker.start()

    def _briefing_worker(self, show_popup: bool, force: bool) -> None:
        try:
            data = build_daily_briefing(force=force)
        except Exception as error:
            log_exception("gui.briefing_worker", error)
            data = {"weather_ok": False, "weather": "Météo indisponible.", "news_ok": False, "news": "Actualités indisponibles."}
        try:
            self.briefing_queue.put_nowait((data, show_popup))
        except queue.Full:
            pass

    def _apply_briefing_data(self, data: dict, show_popup: bool) -> None:
        self.briefing_fetching = False
        weather = data.get("weather")
        news = data.get("news")
        if data.get("weather_ok") and isinstance(weather, dict):
            self.weather_var.set(format_weather(weather))
        else:
            self.weather_var.set(str(weather or "Météo indisponible. Mode local inchangé."))
        if data.get("news_ok") and isinstance(news, list):
            compact = []
            for index, item in enumerate(news[:5], start=1):
                title = str(item.get("title", "")).strip()
                source = str(item.get("source", "")).strip()
                compact.append(f"{index}. {title}" + (f" — {source}" if source else ""))
            self.news_var.set("\n".join(compact) if compact else "Aucune actualité récente.")
        else:
            self.news_var.set(str(news or "Actualités indisponibles. Mode local inchangé."))
        if show_popup:
            try:
                mark_morning_briefing_shown()
                self._show_morning_popup()
            except Exception as error:
                log_exception("gui.morning_popup", error)

    def _show_morning_popup(self) -> None:
        popup = tk.Toplevel(self.root)
        popup.title("AgentLocal - Bonjour")
        popup.geometry("620x420")
        popup.minsize(560, 360)
        popup.configure(bg=COLORS["bg"])
        popup.transient(self.root)
        popup.grab_set()

        card = tk.Frame(popup, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=18, pady=18)
        tk.Label(card, text=f"{_greeting()} 👋", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 19, "bold")).pack(anchor="w", padx=18, pady=(18, 3))
        tk.Label(card, text=_dt.datetime.now().strftime("%A %d %B %Y"), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=18)
        tk.Label(card, text="Météo", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=18, pady=(16, 3))
        tk.Label(card, textvariable=self.weather_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9), wraplength=550, justify="left").pack(anchor="w", padx=18)
        tk.Label(card, text="À la une", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=18, pady=(14, 3))
        tk.Label(card, textvariable=self.news_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8), wraplength=550, justify="left").pack(anchor="w", padx=18)
        buttons = tk.Frame(card, bg=COLORS["card"])
        buttons.pack(fill="x", padx=18, pady=(16, 18))
        tk.Button(buttons, text="Voir le briefing", command=lambda: (popup.destroy(), self.show_page("briefing")), relief="flat", bd=0, bg=COLORS["accent"], fg="white", activebackground=COLORS["accent_hover"], font=("Segoe UI", 9, "bold"), padx=13, pady=7, cursor="hand2").pack(side="left")
        tk.Button(buttons, text="Lancer ma routine", command=lambda: (popup.destroy(), self.run_shortcut("lance ma routine", "Lancer ma routine")), relief="flat", bd=0, bg=COLORS["soft_accent"], fg=COLORS["accent"], font=("Segoe UI", 9, "bold"), padx=13, pady=7, cursor="hand2").pack(side="left", padx=(8, 0))
        tk.Button(buttons, text="Fermer", command=popup.destroy, relief="flat", bd=0, bg=COLORS["soft_neutral"], fg=COLORS["muted"], font=("Segoe UI", 9), padx=13, pady=7, cursor="hand2").pack(side="right")

    # ------------------------------------------------------------------
    # Etat runtime
    # ------------------------------------------------------------------
    def _refresh_runtime_summary(self) -> None:
        backend_text, learning_text = get_runtime_summary()
        self.backend_var.set(backend_text)
        self.learning_var.set(learning_text)

    def _run_startup_health_check(self) -> None:
        try:
            report = startup_health_report()
        except Exception as error:
            log_exception("gui.startup_health", error)
            report = {"overall": "critical", "checks": []}

        if AGENT_IMPORT_ERROR is not None:
            report = dict(report)
            checks = list(report.get("checks", []))
            checks.append({"name": "coeur AgentLocal", "status": "critical", "critical": True, "detail": f"import impossible ({type(AGENT_IMPORT_ERROR).__name__})"})
            report["checks"] = checks
            report["overall"] = "critical"

        self.health_report = report
        self.safe_mode = report.get("overall") == "critical"
        summary = format_health_summary(report)
        self.health_var.set(summary)

        if self.safe_mode:
            self.health_badge.configure(text="Mode sûr", bg="#FDECEC", fg=COLORS["danger"])
            self.command_entry.configure(state="disabled")
            self.execute_button.configure(state="disabled")
            details = critical_health_messages(report)
            text = "AgentLocal a démarré en mode sûr : aucune action ne sera exécutée."
            if details:
                text += " Problème détecté : " + " ; ".join(details[:3])
            self._append_error(text)
        elif report.get("overall") == "degraded":
            self.health_badge.configure(text="Mode dégradé", bg=COLORS["soft_warning"], fg=COLORS["warning"])
            self._append_agent("Un composant optionnel est indisponible. Les fonctions locales disponibles restent utilisables.")
        else:
            self.health_badge.configure(text="Système prêt", bg=COLORS["soft_success"], fg=COLORS["success"])

    # ------------------------------------------------------------------
    # Conversation / suggestions
    # ------------------------------------------------------------------
    def _append_text(self, prefix: str, text: str, tag: str) -> None:
        self.conversation.configure(state="normal")
        self.conversation.insert("end", prefix, tag)
        self.conversation.insert("end", f"{text}\n", tag)
        self.conversation.configure(state="disabled")
        self.conversation.see("end")

    def _append_user(self, text: str) -> None:
        self._append_text("Vous : ", text, "user")

    def _append_agent(self, text: str) -> None:
        self._append_text("AgentLocal : ", text, "agent")

    def _append_error(self, text: str) -> None:
        self._append_text("AgentLocal : ", text, "error")

    def _refresh_suggestion_buttons(self) -> None:
        suggestions = []
        try:
            if agent is not None and hasattr(agent, "get_pending_action_suggestions"):
                suggestions = agent.get_pending_action_suggestions()
        except Exception as error:
            log_exception("gui.suggestions", error)
            suggestions = []

        for button in getattr(self, "suggestion_buttons", []):
            button.grid_remove()
        if not suggestions:
            if hasattr(self, "suggestion_frame"):
                self.suggestion_frame.grid_remove()
            return

        self.suggestion_frame.grid()
        for index, item in enumerate(suggestions[:3]):
            label = str(item.get("label", "")).strip()
            if not label:
                continue
            button = self.suggestion_buttons[index]
            button.configure(text=label, state="disabled" if self.busy else "normal")
            button.grid()

    def execute_suggestion(self, index: int) -> None:
        if self.busy or self.safe_mode or agent is None:
            return
        try:
            suggestions = agent.get_pending_action_suggestions()
        except Exception as error:
            log_exception("gui.execute_suggestion", error)
            return
        if not isinstance(index, int) or index < 0 or index >= len(suggestions):
            self._refresh_suggestion_buttons()
            return
        label = str(suggestions[index].get("label", "")).strip() or f"Suggestion {index + 1}"
        self._start_command(str(index + 1), display_text=label)

    def run_shortcut(self, command: str, label: str | None = None) -> None:
        if self.busy or self.safe_mode or agent is None:
            return
        self.show_page("assistant")
        self._start_command(command, display_text=label or command)

    def _start_command(self, command: str, display_text: str | None = None) -> None:
        self._append_user(display_text or command)
        self._set_busy(True)
        self.last_started_at = time.perf_counter()
        self.worker = threading.Thread(target=self._process_command_worker, args=(command, self.last_started_at), daemon=True, name="AgentLocalCommand")
        self.worker.start()

    def _set_busy(self, value: bool) -> None:
        self.busy = value
        state = "disabled" if value else "normal"
        self.command_entry.configure(state=state)
        self.execute_button.configure(state=state)
        self.clear_button.configure(state=state)
        self.status_var.set("Traitement..." if value else "Prêt")
        self.root.config(cursor="watch" if value else "")
        for button in getattr(self, "suggestion_buttons", []):
            try:
                if button.winfo_ismapped():
                    button.configure(state=state)
            except tk.TclError:
                pass
        if not value and self.active_page == "assistant":
            self.command_entry.focus_set()

    def _focus_command(self, _event=None):
        self.show_page("assistant")
        if not self.busy:
            self.command_entry.focus_set()
        return "break"

    def _on_enter(self, _event: tk.Event) -> str:
        self.execute_command()
        return "break"

    def _on_clear_shortcut(self, _event: tk.Event) -> str:
        if not self.busy:
            self.clear_conversation()
        return "break"

    def execute_command(self) -> None:
        if self.busy:
            return
        if self.safe_mode or agent is None:
            self.status_var.set("Mode sûr - action désactivée")
            return

        command = normalize_user_command(self.command_var.get())
        if not command:
            self.status_var.set("Écris une demande")
            self.command_entry.focus_set()
            return

        if len(command) > MAX_COMMAND_LENGTH:
            messagebox.showwarning(APP_TITLE, f"La commande est trop longue. Maximum : {MAX_COMMAND_LENGTH} caractères.", parent=self.root)
            return

        exit_text = command.lower().strip().replace("’", "'")
        if exit_text in {
            "sort", "stop", "quitte", "quitter", "ferme agentlocal",
            "ferme cette fenêtre", "ferme cette fenetre", "arrête", "arrete",
            "arrête agentlocal", "arrete agentlocal", "ferme-toi", "ferme toi",
        }:
            self.command_var.set("")
            self._append_user(command)
            self._append_agent("Ça marche, je ferme AgentLocal.")
            self.root.after(80, self.close)
            return

        self.command_var.set("")
        self._start_command(command)

    def _process_command_worker(self, command: str, started_at: float) -> None:
        try:
            result = agent.process_instruction(command)
            if not isinstance(result, str):
                result = str(result)
            elapsed = max(0.0, time.perf_counter() - started_at)
            self.result_queue.put_nowait(("ok", result, elapsed))
        except Exception as error:
            log_exception("gui.command_worker", error)
            elapsed = max(0.0, time.perf_counter() - started_at)
            try:
                self.result_queue.put_nowait(("error", "Une erreur locale a empêché le traitement. AgentLocal reste actif ; consulte logs/agentlocal.log si le problème se répète.", elapsed))
            except queue.Full:
                pass

    def _poll_worker_result(self) -> None:
        try:
            kind, text, elapsed = self.result_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            if kind == "ok":
                self._append_agent(text)
            else:
                self._append_error(text)
            self.response_time_var.set(f"{elapsed:.2f} s")
            self._set_busy(False)
            self._refresh_suggestion_buttons()
            self._update_dashboard_metrics()

        try:
            data, show_popup = self.briefing_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            self._apply_briefing_data(data, show_popup)

        while True:
            try:
                item, success, message, schedule_data = self.schedule_queue.get_nowait()
            except queue.Empty:
                break
            else:
                self._apply_scheduled_result(item, success, message, schedule_data)

        try:
            self.root.after(POLL_INTERVAL_MS, self._poll_worker_result)
        except tk.TclError:
            pass

    def _scheduler_loop(self) -> None:
        """Déclenche uniquement des planifications déjà confirmées et arrivées à échéance."""
        try:
            running = self.schedule_worker is not None and self.schedule_worker.is_alive()
            if not running:
                due = get_due_schedules()
                if due:
                    self.schedule_worker = threading.Thread(
                        target=self._scheduled_actions_worker,
                        args=(due,),
                        daemon=True,
                        name="AgentLocalScheduler",
                    )
                    self.schedule_worker.start()
            config = load_scheduler_config()
            seconds = int(config.get("poll_seconds", 20) or 20)
            seconds = max(10, min(seconds, 300))
        except Exception as error:
            log_exception("gui.scheduler_loop", error)
            seconds = 30
        try:
            self.root.after(seconds * 1000, self._scheduler_loop)
        except tk.TclError:
            pass

    def _scheduled_actions_worker(self, schedules: list[dict]) -> None:
        for item in schedules:
            schedule_id = str(item.get("id", ""))
            if not claim_scheduled_execution(schedule_id):
                # Une autre instance AgentLocal a deja reserve cette execution
                # pour aujourd'hui, ou le verrou de securite n'a pas pu etre cree.
                continue
            kind = str(item.get("kind", ""))
            name = str(item.get("name", schedule_id or "Planification"))
            success = False
            message = "Planification non exécutée."
            data = None
            try:
                if kind == "routine":
                    success, results = execute_scheduled_routine(str(item.get("target", "")))
                    message = "\n".join(results or ["Routine terminée."])
                elif kind == "briefing":
                    data = build_daily_briefing(force=False)
                    message = format_daily_briefing(data)
                    success = True
                elif kind == "habit_summary":
                    if agent is not None and hasattr(agent, "format_habit_summary"):
                        message = agent.format_habit_summary()
                        success = True
                    else:
                        message = "Le résumé des habitudes n'est pas disponible."
                else:
                    message = "Type de planification non autorisé."
            except Exception as error:
                log_exception("gui.scheduled_action", error)
                message = "Une erreur locale a empêché cette planification de s'exécuter."
            try:
                mark_schedule_run(schedule_id, success, message)
            except Exception as error:
                log_exception("gui.schedule_mark_run", error)
            try:
                self.schedule_queue.put_nowait((item, success, message, data))
            except queue.Full:
                pass

    def _apply_scheduled_result(self, item: dict, success: bool, message: str, data: dict | None) -> None:
        name = str(item.get("name", "Planification"))
        kind = str(item.get("kind", ""))
        if kind == "briefing" and isinstance(data, dict):
            self._apply_briefing_data(data, show_popup=True)
        prefix = "Planification exécutée" if success else "Planification en échec"
        try:
            self._append_agent(f"{prefix} — {name}\n{message}")
        except Exception as error:
            log_exception("gui.schedule_display", error)
        self.status_var.set(prefix)

    def clear_conversation(self) -> None:
        if self.busy:
            return
        self.conversation.configure(state="normal")
        self.conversation.delete("1.0", "end")
        self.conversation.configure(state="disabled")
        self.status_var.set("Affichage effacé")
        self.response_time_var.set("")
        self._refresh_suggestion_buttons()
        if self.active_page == "assistant":
            self.command_entry.focus_set()

    def close(self) -> None:
        if self.busy:
            should_close = messagebox.askyesno(APP_TITLE, "Une commande est en cours. Fermer quand même l'interface ?", parent=self.root)
            if not should_close:
                return
        try:
            if agent is not None and hasattr(agent, "clear_session_context"):
                agent.clear_session_context()
        except Exception as error:
            log_exception("gui.close", error)
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    AgentLocalGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
