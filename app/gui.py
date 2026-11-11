"""Interface graphique AgentLocal V12.3 UX Premium.

Objectifs :
- Windows 10/11 64 bits.
- Interface professionnelle, chaleureuse et intuitive.
- Faible empreinte memoire : Tkinter/ttk uniquement.
- Aucun contournement de securite : toutes les actions passent par agent.py.
- Les informations de l'accueil restent en lecture seule.
"""

from __future__ import annotations

import datetime as _dt
import json
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
    list_schedules,
    load_config as load_scheduler_config,
    mark_run as mark_schedule_run,
)
from routine_tools import execute_routine as execute_scheduled_routine  # noqa: E402

from alerts import (  # noqa: E402
    get_alert_summary,
    list_alerts,
    mark_seen as mark_alert_seen,
    raise_alert,
    resolve_missing as resolve_missing_alerts,
)
from morning_automation import (  # noqa: E402
    load_config as load_morning_config,
    mark_completed as mark_morning_completed,
    mark_late_prompted,
    morning_status,
    should_prompt_late,
    should_trigger as should_trigger_morning,
)
from system_monitor import SystemHealthMonitor, collect_snapshot, is_session_unlocked, load_monitor_config  # noqa: E402
from windows_startup import is_startup_enabled, set_startup_enabled, status_text as startup_status_text  # noqa: E402
from single_instance import InstanceGuard, focus_existing_window  # noqa: E402
from daily_quotes import quote_of_day  # noqa: E402
from response_style import decorate_response, decorate_suggestion_label  # noqa: E402
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
MORNING_CHECK_MS = 10000

# Palette sobre, contraste eleve, aucun framework externe.
COLORS = {
    "bg": "#F6F8FC",
    "sidebar": "#101A2E",
    "sidebar_hover": "#192946",
    "sidebar_active": "#214A7B",
    "card": "#FFFFFF",
    "card_alt": "#FBFCFF",
    "border": "#E4E9F2",
    "text": "#172033",
    "muted": "#68758A",
    "accent": "#356AE6",
    "accent_hover": "#2859C6",
    "accent_2": "#6D5CE7",
    "teal": "#0E9384",
    "gold": "#D69E2E",
    "success": "#16845B",
    "warning": "#B86E16",
    "danger": "#B43C39",
    "soft_accent": "#EBF1FF",
    "soft_lavender": "#F0EEFF",
    "soft_teal": "#E8F7F4",
    "soft_gold": "#FFF7E4",
    "soft_success": "#EAF8F1",
    "soft_warning": "#FFF4E5",
    "soft_neutral": "#F1F4F8",
    "quote_bg": "#FFF9EC",
    "conversation": "#FCFDFF",
}

NAV_ICONS = {
    "home": "⌂", "briefing": "📰", "assistant": "✦", "pc": "🖥",
    "alerts": "⚠", "files": "📁", "web": "🌐", "routines": "↻", "settings": "⚙",
}
CARD_META = {
    "CPU": ("⚡", "accent"), "RAM": ("◫", "accent_2"), "Disque libre": ("💾", "teal"),
    "Temps actif": ("⏱", "gold"), "Session": ("🔓", "teal"), "Routine du matin": ("☀", "gold"),
    "Alertes actives": ("⚠", "warning"), "Processus": ("▦", "accent_2"),
    "Actives": ("●", "accent"), "Critiques": ("!", "danger"), "Avertissements": ("⚠", "warning"),
    "Informations": ("i", "teal"),
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

    adaptive = False
    idle_seconds = 180
    try:
        models = json.loads((ROOT_DIR / "config" / "models.json").read_text(encoding="utf-8-sig"))
        runtime = models.get("runtime", {}) if isinstance(models, dict) else {}
        if isinstance(runtime, dict):
            adaptive = bool(runtime.get("warm_server_enabled", False))
            idle_seconds = int(runtime.get("warm_server_idle_seconds", 180) or 180)
    except Exception:
        pass

    if adaptive and mode in {"auto", "llama"}:
        backend_text = f"Moteur : {mode} - LLM local adaptatif, chargé à la demande (veille {max(1, idle_seconds // 60)} min)"
    else:
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


def _french_date_label(value: _dt.datetime | None = None) -> str:
    current = value or _dt.datetime.now()
    days = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
    months = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre")
    return f"{days[current.weekday()].capitalize()} {current.day} {months[current.month - 1]} {current.year}"


class AgentLocalGUI:
    """Interface principale AgentLocal V12.1."""

    NAV_ITEMS = (
        ("Accueil", "home"),
        ("Briefing", "briefing"),
        ("Assistant", "assistant"),
        ("Mon PC", "pc"),
        ("Alertes", "alerts"),
        ("Fichiers", "files"),
        ("Web", "web"),
        ("Routines", "routines"),
        ("Paramètres", "settings"),
    )

    def __init__(self, root: tk.Tk, start_hidden: bool = False) -> None:
        self.root = root
        self.start_hidden = bool(start_hidden)
        if self.start_hidden:
            try:
                self.root.withdraw()
            except tk.TclError:
                pass
        self.result_queue: queue.Queue[tuple[str, str, float]] = queue.Queue(maxsize=1)
        self.briefing_queue: queue.Queue[tuple[dict, bool]] = queue.Queue(maxsize=1)
        self.schedule_queue: queue.Queue[tuple[dict, bool, str, dict | None]] = queue.Queue()
        self.health_queue: queue.Queue[tuple[dict, list[dict]]] = queue.Queue(maxsize=1)
        self.morning_queue: queue.Queue[dict] = queue.Queue(maxsize=1)
        self.worker: threading.Thread | None = None
        self.briefing_worker: threading.Thread | None = None
        self.schedule_worker: threading.Thread | None = None
        self.health_worker: threading.Thread | None = None
        self.morning_worker: threading.Thread | None = None
        self.health_monitor = SystemHealthMonitor()
        self.last_snapshot: dict = {}
        self.briefing_fetching = False
        self.busy = False
        self.active_page = "home"
        self.nav_buttons: dict[str, tk.Button] = {}
        self.pages: dict[str, tk.Frame] = {}
        self.metric_vars: dict[str, tk.StringVar] = {}
        self.last_started_at = 0.0
        self.notified_alert_codes: set[str] = set()

        self.command_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Prêt")
        self.response_time_var = tk.StringVar(value="")
        self.backend_var = tk.StringVar()
        self.learning_var = tk.StringVar()
        self.health_var = tk.StringVar(value="État : vérification...")
        self.alert_count_var = tk.StringVar(value="0")
        self.morning_status_var = tk.StringVar(value="En attente")
        self.session_var = tk.StringVar(value="--")
        self.weather_var = tk.StringVar(value="Météo : chargement à la demande")
        self.news_var = tk.StringVar(value="Actualités : chargement à la demande")
        self.startup_var = tk.StringVar(value="Vérification...")
        self.quote_var = tk.StringVar(value="")
        self.quote_author_var = tk.StringVar(value="")
        self._refresh_daily_quote()
        self.health_report = None
        self.safe_mode = False

        self._configure_window()
        self._configure_styles()
        self._build_interface()
        self._refresh_runtime_summary()
        self._run_startup_health_check()
        self._refresh_startup_status()
        self._update_dashboard_metrics()
        self.show_page("home")

        self.root.after(POLL_INTERVAL_MS, self._poll_worker_result)
        self.root.after(DASHBOARD_REFRESH_MS, self._dashboard_loop)
        self.root.after(900, self._maybe_start_morning_briefing)
        self.root.after(1600, self._health_monitor_loop)
        self.root.after(2200, self._morning_automation_loop)
        self.root.after(2500, self._scheduler_loop)

    def _refresh_daily_quote(self) -> None:
        item = quote_of_day()
        self.quote_var.set(f"« {item.get('text', '')} »")
        self.quote_author_var.set(f"— {item.get('author', 'AgentLocal')}")

    # ------------------------------------------------------------------
    # Fenetre et style
    # ------------------------------------------------------------------
    def _configure_window(self) -> None:
        self.root.title(f"{APP_TITLE} - Espace de travail local")
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
        self._build_alerts_page()
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
        sidebar.grid_rowconfigure(10, weight=1)

        brand = tk.Frame(sidebar, bg=COLORS["sidebar"])
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(22, 24))
        tk.Label(brand, text="AgentLocal", bg=COLORS["sidebar"], fg="white", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(brand, text=f"Version {AGENTLOCAL_VERSION}", bg=COLORS["sidebar"], fg="#AAB4C4", font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 0))

        for row, (label, key) in enumerate(self.NAV_ITEMS, start=1):
            button = tk.Button(
                sidebar,
                text=f"{NAV_ICONS.get(key, '•')}  {label}",
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
        footer.grid(row=11, column=0, sticky="sew", padx=18, pady=18)
        tk.Label(footer, text="●  100 % local par défaut", bg=COLORS["sidebar"], fg="#8D9AAF", font=("Segoe UI", 8)).pack(anchor="w")
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
        self.alert_badge = tk.Label(right, text="0 alerte", bg=COLORS["soft_success"], fg=COLORS["success"], font=("Segoe UI", 9, "bold"), padx=10, pady=6, cursor="hand2")
        self.alert_badge.pack(side="right", padx=(0, 8))
        self.alert_badge.bind("<Button-1>", lambda _e: self.show_page("alerts"))

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
        icon, accent_key = CARD_META.get(title, ("•", "accent"))
        accent = COLORS.get(accent_key, COLORS["accent"])
        card = tk.Frame(parent, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1, bd=0, width=width, height=112)
        card.grid_propagate(False)
        tk.Frame(card, bg=accent, height=3).pack(fill="x")
        head = tk.Frame(card, bg=COLORS["card"])
        head.pack(fill="x", padx=14, pady=(11, 3))
        tk.Label(head, text=icon, bg=COLORS["card"], fg=accent, font=("Segoe UI Emoji", 10, "bold")).pack(side="left")
        tk.Label(head, text=title, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=(6, 0))
        if value_var is not None:
            tk.Label(card, textvariable=value_var, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=15)
        elif text is not None:
            tk.Label(card, text=text, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 10, "bold"), wraplength=max(140, width - 30), justify="left").pack(anchor="w", padx=15)
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
        tk.Label(card, text=f"{decorate_suggestion_label(text)}", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 10, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(11, 2))
        if description:
            tk.Label(card, text=description, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8), anchor="w", wraplength=220, justify="left").grid(row=1, column=0, sticky="ew", padx=14)
        tk.Button(
            card,
            text="Ouvrir  →",
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
        self.home_greeting = tk.Label(hero, text=f"{_greeting()} 👋", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 21, "bold"))
        self.home_greeting.grid(row=0, column=0, sticky="w", padx=22, pady=(18, 2))
        self.home_date = tk.Label(hero, text=_french_date_label(), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9))
        self.home_date.grid(row=1, column=0, sticky="w", padx=22)
        tk.Label(hero, text="Ton espace local est prêt. Voici l'essentiel de ta journée.", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", padx=22, pady=(5, 18))
        tk.Button(hero, text="✦  Ouvrir l'Assistant", command=lambda: self.show_page("assistant"), relief="flat", bd=0, bg=COLORS["accent"], fg="white", activebackground=COLORS["accent_hover"], activeforeground="white", font=("Segoe UI", 9, "bold"), padx=15, pady=9, cursor="hand2", highlightthickness=0).grid(row=0, column=2, rowspan=3, padx=(8, 22))
        motif = tk.Canvas(hero, width=110, height=72, bg=COLORS["card"], highlightthickness=0)
        motif.grid(row=0, column=1, rowspan=3, padx=4)
        motif.create_oval(10, 12, 46, 48, fill=COLORS["soft_accent"], outline="")
        motif.create_oval(44, 28, 74, 58, fill=COLORS["soft_lavender"], outline="")
        motif.create_oval(68, 8, 100, 40, fill=COLORS["soft_teal"], outline="")
        motif.create_line(22, 58, 92, 58, fill=COLORS["border"], width=2)

        quote = tk.Frame(page, bg=COLORS["quote_bg"], highlightbackground="#F0DFC0", highlightthickness=1)
        quote.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        tk.Label(quote, text="💡  Citation du jour", bg=COLORS["quote_bg"], fg=COLORS["gold"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=16, pady=(10, 2))
        tk.Label(quote, textvariable=self.quote_var, bg=COLORS["quote_bg"], fg=COLORS["text"], font=("Segoe UI", 10, "italic"), wraplength=820, justify="left").pack(anchor="w", padx=16)
        tk.Label(quote, textvariable=self.quote_author_var, bg=COLORS["quote_bg"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(anchor="w", padx=16, pady=(2, 10))

        stats = tk.Frame(page, bg=COLORS["bg"])
        stats.grid(row=2, column=0, sticky="ew", pady=(14, 0))
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

        day_status = tk.Frame(page, bg=COLORS["bg"])
        day_status.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        for i in range(3):
            day_status.grid_columnconfigure(i, weight=1, uniform="daystatus")
        self._card(day_status, "Session", self.session_var).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._card(day_status, "Routine du matin", self.morning_status_var).grid(row=0, column=1, sticky="ew", padx=6)
        alert_card = self._card(day_status, "Alertes actives", self.alert_count_var)
        alert_card.grid(row=0, column=2, sticky="ew", padx=(6, 0))
        alert_card.bind("<Button-1>", lambda _e: self.show_page("alerts"))

        section = self._section_title(page, "Actions rapides", "Les commandes les plus utiles restent locales et contrôlées.")
        section.grid(row=4, column=0, sticky="ew", pady=(20, 10))

        quick = tk.Frame(page, bg=COLORS["bg"])
        quick.grid(row=5, column=0, sticky="ew")
        quick.grid_columnconfigure(0, weight=1)
        quick.grid_columnconfigure(1, weight=1)
        self._quick_button(quick, "État du PC", "quel est l'état de mon PC", "CPU, RAM, disque, uptime").grid(row=0, column=0, sticky="ew", padx=(0, 7), pady=(0, 8))
        self._quick_button(quick, "Fichiers lourds", "montre-moi les plus gros fichiers", "Repérer ce qui occupe de l'espace").grid(row=0, column=1, sticky="ew", padx=(7, 0), pady=(0, 8))
        self._quick_button(quick, "Ma routine", "lance ma routine", "Préparer ton environnement de travail").grid(row=1, column=0, sticky="ew", padx=(0, 7), pady=(0, 8))
        self._quick_button(quick, "Onglets Edge", "liste mes onglets", "Voir les onglets accessibles par le pont local").grid(row=1, column=1, sticky="ew", padx=(7, 0), pady=(0, 8))

    def _build_briefing_page(self) -> None:
        page = self._new_page("briefing")
        self._section_title(page, "Briefing du jour", "Internet est optionnel : si la connexion manque, AgentLocal reste entièrement utilisable en local.").grid(row=0, column=0, sticky="ew")

        quote_card = tk.Frame(page, bg=COLORS["quote_bg"], highlightbackground="#F0DFC0", highlightthickness=1)
        quote_card.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        tk.Label(quote_card, text="💡  Citation du jour", bg=COLORS["quote_bg"], fg=COLORS["gold"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=16, pady=(10, 2))
        tk.Label(quote_card, textvariable=self.quote_var, bg=COLORS["quote_bg"], fg=COLORS["text"], font=("Segoe UI", 10, "italic"), wraplength=780, justify="left").pack(anchor="w", padx=16, pady=(0, 10))

        weather_card = tk.Frame(page, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        weather_card.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        tk.Label(weather_card, text="🌤️  Météo", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(13, 4))
        tk.Label(weather_card, textvariable=self.weather_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9), wraplength=760, justify="left").pack(anchor="w", padx=16, pady=(0, 13))

        news_card = tk.Frame(page, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        news_card.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        tk.Label(news_card, text="📰  Actualités", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(13, 4))
        tk.Label(news_card, textvariable=self.news_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9), wraplength=780, justify="left").pack(anchor="w", padx=16, pady=(0, 13))

        actions = tk.Frame(page, bg=COLORS["bg"])
        actions.grid(row=4, column=0, sticky="w", pady=(14, 0))
        tk.Button(actions, text="Actualiser le briefing", command=lambda: self._start_briefing_refresh(show_popup=False, force=True), relief="flat", bd=0, bg=COLORS["accent"], fg="white", activebackground=COLORS["accent_hover"], activeforeground="white", font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2", highlightthickness=0).pack(side="left")
        tk.Button(actions, text="Demander dans l'Assistant", command=lambda: self.run_shortcut("briefing du jour", "Briefing du jour"), relief="flat", bd=0, bg=COLORS["soft_accent"], fg=COLORS["accent"], activebackground="#DDE8FF", font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2", highlightthickness=0).pack(side="left", padx=(8, 0))

        security = tk.Frame(page, bg=COLORS["soft_success"], highlightbackground="#CBE7D3", highlightthickness=1)
        security.grid(row=5, column=0, sticky="ew", pady=(18, 0))
        tk.Label(security, text="🔒  Sécurité Internet", bg=COLORS["soft_success"], fg=COLORS["success"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(12, 3))
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

    def _build_alerts_page(self) -> None:
        page = self._new_page("alerts")
        self._section_title(page, "Alertes", "AgentLocal signale les problèmes détectés sans lancer d'action destructive automatiquement.").grid(row=0, column=0, sticky="ew")

        summary = tk.Frame(page, bg=COLORS["bg"])
        summary.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        for i in range(4):
            summary.grid_columnconfigure(i, weight=1, uniform="alertstats")
        self.alert_metric_vars = {k: tk.StringVar(value="0") for k in ("active", "critical", "warning", "info")}
        labels = (("active", "Actives"), ("critical", "Critiques"), ("warning", "Avertissements"), ("info", "Informations"))
        for col, (key, label) in enumerate(labels):
            self._card(summary, label, self.alert_metric_vars[key]).grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 5, 0 if col == 3 else 5))

        toolbar = tk.Frame(page, bg=COLORS["bg"])
        toolbar.grid(row=2, column=0, sticky="ew", pady=(14, 8))
        tk.Button(toolbar, text="Actualiser", command=self._refresh_alerts_page, relief="flat", bd=0, bg=COLORS["accent"], fg="white", activebackground=COLORS["accent_hover"], font=("Segoe UI", 9, "bold"), padx=13, pady=7, cursor="hand2").pack(side="left")
        tk.Button(toolbar, text="Voir les processus", command=lambda: self.run_shortcut("voir les processus les plus gourmands", "Processus"), relief="flat", bd=0, bg=COLORS["soft_accent"], fg=COLORS["accent"], font=("Segoe UI", 9, "bold"), padx=13, pady=7, cursor="hand2").pack(side="left", padx=(8, 0))

        host = tk.Frame(page, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        host.grid(row=3, column=0, sticky="nsew")
        page.grid_rowconfigure(3, weight=1)
        host.grid_rowconfigure(0, weight=1)
        host.grid_columnconfigure(0, weight=1)
        canvas = tk.Canvas(host, bg=COLORS["card"], highlightthickness=0)
        scroll = ttk.Scrollbar(host, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.alerts_list_frame = tk.Frame(canvas, bg=COLORS["card"])
        self.alerts_window = canvas.create_window((0, 0), window=self.alerts_list_frame, anchor="nw")
        self.alerts_list_frame.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(self.alerts_window, width=e.width))
        self._refresh_alerts_page()

    def _refresh_alerts_page(self) -> None:
        if not hasattr(self, "alerts_list_frame"):
            return
        for child in self.alerts_list_frame.winfo_children():
            child.destroy()
        summary = get_alert_summary()
        self.alert_count_var.set(str(summary.get("active", 0)))
        for key, var in getattr(self, "alert_metric_vars", {}).items():
            var.set(str(summary.get(key, 0)))
        if hasattr(self, "alert_badge"):
            total = int(summary.get("active", 0) or 0)
            critical = int(summary.get("critical", 0) or 0)
            warning = int(summary.get("warning", 0) or 0)
            if critical:
                self.alert_badge.configure(text=f"{total} alerte(s)", bg="#FDECEC", fg=COLORS["danger"])
            elif warning:
                self.alert_badge.configure(text=f"{total} alerte(s)", bg=COLORS["soft_warning"], fg=COLORS["warning"])
            elif total:
                self.alert_badge.configure(text=f"{total} info", bg=COLORS["soft_accent"], fg=COLORS["accent"])
            else:
                self.alert_badge.configure(text="Aucune alerte", bg=COLORS["soft_success"], fg=COLORS["success"])
        items = list_alerts("active", 100)
        if not items:
            tk.Label(self.alerts_list_frame, text="Aucun problème actif détecté.", bg=COLORS["card"], fg=COLORS["success"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=18, pady=22)
            return
        level_style = {
            "critical": ("Critique", COLORS["danger"], "#FDECEC"),
            "warning": ("Avertissement", COLORS["warning"], COLORS["soft_warning"]),
            "info": ("Information", COLORS["accent"], COLORS["soft_accent"]),
        }
        for item in items:
            label, fg, soft = level_style.get(item.get("level"), level_style["info"])
            card = tk.Frame(self.alerts_list_frame, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
            card.pack(fill="x", padx=14, pady=(12, 0))
            head = tk.Frame(card, bg=COLORS["card"]); head.pack(fill="x", padx=14, pady=(12, 4))
            tk.Label(head, text=label, bg=soft, fg=fg, font=("Segoe UI", 8, "bold"), padx=8, pady=3).pack(side="left")
            tk.Label(head, text=str(item.get("title", "Alerte")), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).pack(side="left", padx=(9, 0))
            tk.Label(card, text=str(item.get("message", "")), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9), wraplength=760, justify="left").pack(anchor="w", padx=14)
            foot = tk.Frame(card, bg=COLORS["card"]); foot.pack(fill="x", padx=14, pady=(8, 12))
            tk.Label(foot, text=str(item.get("updated_at", ""))[:19].replace("T", " "), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(side="left")
            tk.Button(foot, text="Marquer comme vu", command=lambda aid=item.get("id"): self._mark_alert_seen(aid), relief="flat", bd=0, bg=COLORS["soft_neutral"], fg=COLORS["muted"], font=("Segoe UI", 8), padx=8, pady=4, cursor="hand2").pack(side="right")

    def _mark_alert_seen(self, alert_id: str) -> None:
        mark_alert_seen(str(alert_id or ""))
        self._refresh_alerts_page()

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
            ("Routine matinale", "briefing du jour", "Auto : premier déverrouillage entre 07:00 et 09:30"),
        ]
        for i, item in enumerate(items):
            self._quick_button(grid, *item).grid(row=i // 2, column=i % 2, sticky="ew", padx=(0 if i % 2 == 0 else 7, 0 if i % 2 == 1 else 7), pady=(0, 8))

        note = tk.Frame(page, bg=COLORS["soft_warning"], highlightbackground="#F1D8A6", highlightthickness=1)
        note.grid(row=2, column=0, sticky="ew", pady=(18, 0))
        tk.Label(note, text="Sécurité des habitudes", bg=COLORS["soft_warning"], fg="#7A5611", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(12, 3))
        tk.Label(note, text="La routine matinale vérifie automatiquement le PC au premier déverrouillage observé entre 07:00 et 09:30. Les autres planifications horaires restent soumises à confirmation explicite et ne peuvent utiliser que des actions autorisées.", bg=COLORS["soft_warning"], fg="#7A5611", font=("Segoe UI", 9), wraplength=720, justify="left").pack(anchor="w", padx=15, pady=(0, 12))

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
            ("Routine matinale", "Premier déverrouillage observé entre 07:00 et 09:30"),
            ("Démarrage Windows", self.startup_var),
        ]
        for i, (label, value) in enumerate(rows):
            tk.Label(card, text=label, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).grid(row=i, column=0, sticky="w", padx=16, pady=(12 if i == 0 else 7, 12 if i == len(rows)-1 else 7))
            if isinstance(value, tk.StringVar):
                tk.Label(card, textvariable=value, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9)).grid(row=i, column=1, sticky="w", padx=10)
            else:
                tk.Label(card, text=str(value), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9)).grid(row=i, column=1, sticky="w", padx=10)

        actions = tk.Frame(page, bg=COLORS["bg"])
        actions.grid(row=2, column=0, sticky="w", pady=(16, 0))
        tk.Button(actions, text="Lancer un diagnostic complet", command=lambda: self.run_shortcut("quel est l'état de mon PC", "Diagnostic du PC"), relief="flat", bd=0, bg=COLORS["accent"], fg="white", activebackground=COLORS["accent_hover"], activeforeground="white", font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2", highlightthickness=0).pack(side="left")
        self.startup_toggle_button = tk.Button(actions, text="Activer au démarrage", command=self._toggle_windows_startup, relief="flat", bd=0, bg=COLORS["soft_neutral"], fg=COLORS["text"], font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2", highlightthickness=0)
        self.startup_toggle_button.pack(side="left", padx=(8, 0))

    def _refresh_startup_status(self) -> None:
        try:
            enabled = is_startup_enabled()
            self.startup_var.set(startup_status_text())
            if hasattr(self, "startup_toggle_button"):
                self.startup_toggle_button.configure(text="Désactiver au démarrage" if enabled else "Activer au démarrage")
        except Exception as error:
            log_exception("gui.startup_status", error)
            self.startup_var.set("Indisponible")

    def _toggle_windows_startup(self) -> None:
        try:
            target = not is_startup_enabled()
            ok, message = set_startup_enabled(target)
            self._refresh_startup_status()
            if ok:
                self.status_var.set(message)
            else:
                messagebox.showwarning(APP_TITLE, message, parent=self.root)
        except Exception as error:
            log_exception("gui.startup_toggle", error)
            messagebox.showwarning(APP_TITLE, "Impossible de modifier le démarrage automatique.", parent=self.root)

    def reveal_main(self, page: str | None = None) -> None:
        try:
            self.root.deiconify()
            self.root.state("normal")
            self.root.lift()
            self.root.focus_force()
        except tk.TclError:
            pass
        if page:
            self.show_page(page)

    def _main_window_hidden(self) -> bool:
        try:
            return self.root.state() == "withdrawn" or not bool(self.root.winfo_viewable())
        except tk.TclError:
            return False

    def _show_background_alert_popup(self, items: list[dict]) -> None:
        if not items:
            return
        item = items[0]
        popup = tk.Toplevel(self.root)
        popup.title("AgentLocal - Alerte")
        popup.geometry("500x245")
        popup.resizable(False, False)
        popup.configure(bg=COLORS["bg"])
        try:
            popup.attributes("-topmost", True)
            popup.after(1200, lambda: popup.attributes("-topmost", False))
        except tk.TclError:
            pass
        card = tk.Frame(popup, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        level = str(item.get("level", "warning"))
        title = str(item.get("title", "Problème détecté"))
        message = str(item.get("message", ""))
        color = COLORS["danger"] if level == "critical" else COLORS["warning"]
        tk.Label(card, text="Problème détecté", bg=COLORS["card"], fg=color, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16, pady=(16, 3))
        tk.Label(card, text=title, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 15, "bold"), wraplength=440, justify="left").pack(anchor="w", padx=16)
        tk.Label(card, text=message, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9), wraplength=440, justify="left").pack(anchor="w", padx=16, pady=(8, 12))
        buttons = tk.Frame(card, bg=COLORS["card"]); buttons.pack(fill="x", padx=16, pady=(0, 14))
        tk.Button(buttons, text="Voir les alertes", command=lambda: (popup.destroy(), self.reveal_main("alerts")), relief="flat", bd=0, bg=COLORS["accent"], fg="white", font=("Segoe UI", 9, "bold"), padx=12, pady=7, cursor="hand2").pack(side="left")
        tk.Button(buttons, text="Fermer", command=popup.destroy, relief="flat", bd=0, bg=COLORS["soft_neutral"], fg=COLORS["muted"], font=("Segoe UI", 9), padx=12, pady=7, cursor="hand2").pack(side="right")

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
            "alerts": "Problèmes détectés et historique local",
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
        if key == "alerts":
            self._refresh_alerts_page()
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
        try:
            unlocked = is_session_unlocked()
            self.session_var.set("Déverrouillée" if unlocked else "Verrouillée")
            status = morning_status(unlocked=unlocked)
            status_label = {
                "done": "Terminée", "due": "À lancer", "waiting_unlock": "Attend déverrouillage",
                "waiting_window": "Avant 07:00", "missed": "Non exécutée", "disabled": "Désactivée",
            }.get(status.get("status"), "En attente")
            self.morning_status_var.set(status_label)
            self.alert_count_var.set(str(get_alert_summary().get("active", 0)))
        except Exception:
            pass
        if hasattr(self, "home_greeting"):
            self.home_greeting.configure(text=f"{_greeting()} !")

    # ------------------------------------------------------------------
    # Briefing connecte V12
    # ------------------------------------------------------------------
    def _maybe_start_morning_briefing(self) -> None:
        try:
            if load_morning_config().get("enabled", True):
                return
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
        tk.Button(buttons, text="Voir le briefing", command=lambda: (popup.destroy(), self.reveal_main("briefing")), relief="flat", bd=0, bg=COLORS["accent"], fg="white", activebackground=COLORS["accent_hover"], font=("Segoe UI", 9, "bold"), padx=13, pady=7, cursor="hand2").pack(side="left")
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
        self._append_text("AgentLocal : ", decorate_response(text), "agent")

    def _append_error(self, text: str) -> None:
        self._append_text("AgentLocal : ", decorate_response(text, error=True), "error")

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
            button.configure(text=decorate_suggestion_label(label), state="disabled" if self.busy else "normal")
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
        self.status_var.set("⚡ Traitement..." if value else "● Prêt")
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
            snapshot, generated = self.health_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            self.last_snapshot = snapshot
            self._apply_health_alerts(generated)

        try:
            result = self.morning_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            self._apply_morning_result(result)

        try:
            self.root.after(POLL_INTERVAL_MS, self._poll_worker_result)
        except tk.TclError:
            pass

    def _health_monitor_loop(self) -> None:
        try:
            running = self.health_worker is not None and self.health_worker.is_alive()
            if not running:
                self.health_worker = threading.Thread(target=self._health_monitor_worker, daemon=True, name="AgentLocalHealthMonitor")
                self.health_worker.start()
            cfg = load_monitor_config()
            seconds = max(10, min(int(cfg.get("scan_seconds", 15) or 15), 300))
        except Exception as error:
            log_exception("gui.health_monitor_loop", error)
            seconds = 30
        try:
            self.root.after(seconds * 1000, self._health_monitor_loop)
        except tk.TclError:
            pass

    def _health_monitor_worker(self) -> None:
        try:
            snapshot = collect_snapshot()
            generated = self.health_monitor.evaluate(snapshot)
            self.health_queue.put_nowait((snapshot, generated))
        except Exception as error:
            log_exception("gui.health_monitor_worker", error)

    def _apply_health_alerts(self, generated: list[dict]) -> None:
        active_codes = set()
        notify_items = []
        for item in generated:
            try:
                code = str(item.get("code", "")); active_codes.add(code)
                raise_alert(code, str(item.get("level", "info")), str(item.get("title", "Alerte")), str(item.get("message", "")), "system_monitor")
                if str(item.get("level", "info")) in {"warning", "critical"} and code not in self.notified_alert_codes:
                    notify_items.append(item)
            except Exception as error:
                log_exception("gui.raise_health_alert", error)
        try:
            resolve_missing_alerts(("health.", "process."), active_codes)
        except Exception:
            pass
        self.notified_alert_codes.intersection_update(active_codes)
        for item in notify_items:
            code = str(item.get("code", ""))
            if code:
                self.notified_alert_codes.add(code)
        self._refresh_alerts_page()
        if notify_items and self._main_window_hidden():
            self._show_background_alert_popup(notify_items)

    def _morning_automation_loop(self) -> None:
        try:
            unlocked = is_session_unlocked()
            running = self.morning_worker is not None and self.morning_worker.is_alive()
            if not running and should_trigger_morning(unlocked=unlocked):
                self.morning_worker = threading.Thread(target=self._morning_worker, daemon=True, name="AgentLocalMorningAutomation")
                self.morning_worker.start()
            elif not running and should_prompt_late(unlocked=unlocked):
                raise_alert("morning.missed", "info", "Routine matinale non exécutée", "La plage 07:00-09:30 est dépassée. Tu peux lancer la routine manuellement depuis l'accueil.", "morning_automation")
                mark_late_prompted()
                self._refresh_alerts_page()
        except Exception as error:
            log_exception("gui.morning_automation_loop", error)
        try:
            self.root.after(MORNING_CHECK_MS, self._morning_automation_loop)
        except tk.TclError:
            pass

    def _morning_worker(self) -> None:
        result = {"success": False, "briefing": None, "snapshot": None, "pending": [], "alerts": []}
        try:
            snapshot = collect_snapshot()
            generated = self.health_monitor.evaluate(snapshot)
            active_codes = set()
            for item in generated:
                code = str(item.get("code", "")); active_codes.add(code)
                raise_alert(code, str(item.get("level", "info")), str(item.get("title", "Alerte")), str(item.get("message", "")), "morning_automation")
            resolve_missing_alerts(("health.", "process."), active_codes)
            today = _dt.date.today().isoformat()
            pending = []
            for item in list_schedules(include_pending=True):
                if not item.get("confirmed"):
                    pending.append(item)
                elif item.get("enabled") and item.get("last_run_local_date") != today:
                    pending.append(item)
            briefing = build_daily_briefing(force=False)
            if not briefing.get("weather_ok"):
                raise_alert("service.weather", "warning", "Météo indisponible", str(briefing.get("weather") or "Le service météo n'a pas répondu."), "briefing")
            else:
                resolve_missing_alerts(("service.weather",), set())
            if not briefing.get("news_ok"):
                raise_alert("service.news", "warning", "Actualités indisponibles", str(briefing.get("news") or "Le service actualités n'a pas répondu."), "briefing")
            else:
                resolve_missing_alerts(("service.news",), set())
            summary = get_alert_summary()
            mark_morning_completed(True, summary=f"{summary.get('active', 0)} alerte(s), {len(pending)} tâche(s) en attente")
            result.update({"success": True, "briefing": briefing, "snapshot": snapshot, "pending": pending, "alerts": list_alerts("active", 20)})
        except Exception as error:
            log_exception("gui.morning_worker", error)
            raise_alert("morning.failure", "warning", "Routine matinale incomplète", "Une erreur locale a empêché la routine matinale de se terminer.", "morning_automation")
            mark_morning_completed(False, summary="Erreur locale")
            result["error"] = type(error).__name__
        try:
            self.morning_queue.put_nowait(result)
        except queue.Full:
            pass

    def _apply_morning_result(self, result: dict) -> None:
        briefing = result.get("briefing")
        if isinstance(briefing, dict):
            self._apply_briefing_data(briefing, show_popup=False)
        self._update_dashboard_metrics()
        self._refresh_alerts_page()
        if load_morning_config().get("show_popup", True):
            self._show_morning_routine_popup(result)

    def _show_morning_routine_popup(self, result: dict) -> None:
        popup = tk.Toplevel(self.root)
        popup.title("AgentLocal - Routine du matin")
        popup.geometry("680x500")
        popup.minsize(620, 430)
        popup.configure(bg=COLORS["bg"]); popup.transient(self.root)
        card = tk.Frame(popup, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=18, pady=18)
        tk.Label(card, text=f"{_greeting()} 👋", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 19, "bold")).pack(anchor="w", padx=18, pady=(18, 3))
        tk.Label(card, text="Routine matinale terminée", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=18)
        snapshot = result.get("snapshot") or {}
        status = tk.Frame(card, bg=COLORS["soft_neutral"]); status.pack(fill="x", padx=18, pady=(15, 8))
        ram = snapshot.get("ram_percent"); cpu = snapshot.get("cpu_percent")
        line = f"CPU : {cpu:.0f}%   •   RAM : {ram:.0f}%   •   Réseau : {'actif' if snapshot.get('network_interface_up') else 'indisponible'}" if isinstance(cpu, (int,float)) and isinstance(ram,(int,float)) else "État du PC vérifié"
        tk.Label(status, text=line, bg=COLORS["soft_neutral"], fg=COLORS["text"], font=("Segoe UI", 10, "bold"), padx=12, pady=10).pack(anchor="w")
        alerts = result.get("alerts") or []
        critical = sum(1 for a in alerts if a.get("level") == "critical"); warnings = sum(1 for a in alerts if a.get("level") == "warning")
        alert_text = "Aucun problème important détecté." if not alerts else f"{len(alerts)} alerte(s) active(s) — {critical} critique(s), {warnings} avertissement(s)."
        tk.Label(card, text=alert_text, bg=COLORS["card"], fg=COLORS["danger"] if critical else (COLORS["warning"] if warnings else COLORS["success"]), font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=18, pady=(8, 3))
        pending = result.get("pending") or []
        tk.Label(card, text=f"Tâches AgentLocal en attente : {len(pending)}", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=18, pady=(0, 8))
        tk.Label(card, text="📰 Le briefing du jour est prêt dans l'onglet Briefing.", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=18)
        quote_box = tk.Frame(card, bg=COLORS["quote_bg"], highlightbackground="#F0DFC0", highlightthickness=1)
        quote_box.pack(fill="x", padx=18, pady=(12, 0))
        tk.Label(quote_box, text="💡 Citation du jour", bg=COLORS["quote_bg"], fg=COLORS["gold"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(quote_box, textvariable=self.quote_var, bg=COLORS["quote_bg"], fg=COLORS["text"], font=("Segoe UI", 9, "italic"), wraplength=580, justify="left").pack(anchor="w", padx=10, pady=(0, 8))
        buttons = tk.Frame(card, bg=COLORS["card"]); buttons.pack(fill="x", padx=18, pady=(18, 18))
        tk.Button(buttons, text="Voir le briefing", command=lambda: (popup.destroy(), self.reveal_main("briefing")), relief="flat", bd=0, bg=COLORS["accent"], fg="white", font=("Segoe UI", 9, "bold"), padx=13, pady=7, cursor="hand2").pack(side="left")
        tk.Button(buttons, text="Voir les alertes", command=lambda: (popup.destroy(), self.reveal_main("alerts")), relief="flat", bd=0, bg=COLORS["soft_warning"], fg=COLORS["warning"], font=("Segoe UI", 9, "bold"), padx=13, pady=7, cursor="hand2").pack(side="left", padx=(8, 0))
        tk.Button(buttons, text="Fermer", command=popup.destroy, relief="flat", bd=0, bg=COLORS["soft_neutral"], fg=COLORS["muted"], font=("Segoe UI", 9), padx=13, pady=7, cursor="hand2").pack(side="right")

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
    start_hidden = "--background" in sys.argv or "--autostart" in sys.argv
    guard = InstanceGuard()
    if guard.already_running:
        if not start_hidden:
            focus_existing_window()
        guard.close()
        return
    root = tk.Tk()
    AgentLocalGUI(root, start_hidden=start_hidden)
    try:
        root.mainloop()
    finally:
        guard.close()


if __name__ == "__main__":
    main()
