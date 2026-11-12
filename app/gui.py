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
from tkinter import colorchooser, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR / "app"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from project_version import AGENTLOCAL_VERSION  # noqa: E402
from project_version import AGENTLOCAL_PATCH  # noqa: E402
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
from theme_manager import build_palette, theme_names  # noqa: E402
from notification_policy import popup_allowed, mark_popup, digest_due, mark_digest, notification_mode_label  # noqa: E402
from language_profile import summary as language_summary, learned_expressions, clear_unrecognized, remember_expression  # noqa: E402
from response_style import decorate_response, decorate_suggestion_label, get_presentation_preferences  # noqa: E402
from user_profile import (  # noqa: E402
    load_profile, load_preferences, save_profile, save_preferences,
    load_declared_habits, save_declared_habits, is_onboarding_complete,
    reset_onboarding, get_display_name,
)
from learning_profile import learning_dashboard, restart_initial_learning, set_learning_enabled  # noqa: E402
from onboarding import OnboardingWizard  # noqa: E402
from security_center import open_security_center  # noqa: E402
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
APP_ICON_ICO = ROOT_DIR / "assets" / "agentlocal.ico"
APP_ICON_PNG = ROOT_DIR / "assets" / "agentlocal_icon.png"
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
try:
    COLORS.update(build_palette(load_preferences().get("appearance", {})))
except Exception:
    pass

NAV_ICONS = {
    "home": "⌂", "briefing": "📰", "assistant": "✦", "pc": "🖥",
    "alerts": "⚠", "files": "📁", "web": "🌐", "routines": "↻",
    "habits": "🧠", "configuration": "⚙", "settings": "⋯",
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



def _set_windows_app_id() -> None:
    """Force une identite AgentLocal stable dans la barre des taches Windows."""
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AgentLocal.Desktop")
    except Exception:
        pass


def _apply_window_icon(window: tk.Misc) -> None:
    """Applique l'icone AgentLocal sans rendre Pillow obligatoire."""
    try:
        if APP_ICON_ICO.exists():
            window.iconbitmap(default=str(APP_ICON_ICO))
    except Exception:
        pass
    try:
        if APP_ICON_PNG.exists():
            icon = tk.PhotoImage(file=str(APP_ICON_PNG))
            window.iconphoto(True, icon)
            setattr(window, "_agentlocal_icon_ref", icon)
    except Exception:
        pass


def _show_startup_splash(root: tk.Tk, duration_ms: int = 850) -> None:
    """Petit ecran de demarrage local, affiche uniquement lors d'un lancement manuel."""
    try:
        splash = tk.Toplevel(root)
        splash.overrideredirect(True)
        splash.configure(bg="#101A2E")
        splash.attributes("-topmost", True)
        width, height = 430, 250
        sw = splash.winfo_screenwidth()
        sh = splash.winfo_screenheight()
        splash.geometry(f"{width}x{height}+{max(0,(sw-width)//2)}+{max(0,(sh-height)//2)}")
        frame = tk.Frame(splash, bg="#101A2E", highlightthickness=1, highlightbackground="#214A7B")
        frame.pack(fill="both", expand=True)
        if APP_ICON_PNG.exists():
            image = tk.PhotoImage(file=str(APP_ICON_PNG))
            # 512 -> environ 128 px, sans dependance externe.
            image = image.subsample(4, 4)
            splash._agentlocal_splash_image = image
            tk.Label(frame, image=image, bg="#101A2E", bd=0).pack(pady=(26, 8))
        tk.Label(frame, text="AgentLocal", bg="#101A2E", fg="#F6FAFF", font=("Segoe UI", 20, "bold")).pack()
        tk.Label(frame, text="Assistant local prêt à travailler", bg="#101A2E", fg="#AFC4E8", font=("Segoe UI", 9)).pack(pady=(4, 0))
        tk.Label(frame, text="Démarrage…", bg="#101A2E", fg="#43D0C8", font=("Segoe UI", 9, "bold")).pack(pady=(13, 0))
        _apply_window_icon(splash)
        splash.after(max(350, int(duration_ms)), splash.destroy)
    except Exception:
        pass


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
    try:
        learning_enabled = bool(load_preferences().get("learning", {}).get("enabled", learning_enabled))
    except Exception:
        pass

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
        ("Habitudes", "habits"),
        ("Configuration", "configuration"),
        ("Paramètres avancés", "settings"),
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
        self.profile = load_profile()
        self.preferences = load_preferences()
        self.onboarding_window = None

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
        self.profile_name_var = tk.StringVar(value=self.profile.get("display_name") or "Nouvel hôte")
        self.host_name_var = tk.StringVar(value=self.profile.get("machine_name") or "--")
        self.learning_progress_var = tk.StringVar(value="Configuration à terminer")
        self.learning_count_var = tk.StringVar(value="0")
        self.config_summary_var = tk.StringVar(value="À personnaliser")
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
        self._refresh_personalization_state()
        self.show_page("home")

        self.root.after(POLL_INTERVAL_MS, self._poll_worker_result)
        self.root.after(DASHBOARD_REFRESH_MS, self._dashboard_loop)
        self.root.after(900, self._maybe_start_morning_briefing)
        self.root.after(1600, self._health_monitor_loop)
        self.root.after(2200, self._morning_automation_loop)
        self.root.after(2500, self._scheduler_loop)
        self.root.after(5000, self._notification_digest_loop)
        if not self.start_hidden:
            self.root.after(1250, self._maybe_show_onboarding)
        self.root.after(1800, self._onboarding_visibility_loop)

    def _refresh_daily_quote(self) -> None:
        prefs = get_presentation_preferences()
        if not bool(prefs.get("daily_quote", True)):
            self.quote_var.set("")
            self.quote_author_var.set("")
            return
        item = quote_of_day()
        self.quote_var.set(f"« {item.get('text', '')} »")
        self.quote_author_var.set(f"— {item.get('author', 'AgentLocal')}")

    # ------------------------------------------------------------------
    # Fenetre et style
    # ------------------------------------------------------------------
    def _configure_window(self) -> None:
        self.root.title(f"{APP_TITLE} - Espace de travail local")
        _apply_window_icon(self.root)
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
        style.configure(
            "Learning.Horizontal.TProgressbar",
            troughcolor=COLORS["soft_neutral"],
            background=COLORS["teal"],
            bordercolor=COLORS["border"],
            lightcolor=COLORS["teal"],
            darkcolor=COLORS["teal"],
            thickness=8,
        )

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
        self._build_habits_page()
        self._build_configuration_page()
        self._build_settings_page()

        self.root.bind("<Control-k>", self._focus_command)
        self.root.bind("<Control-K>", self._focus_command)
        self.root.bind("<Control-l>", self._on_clear_shortcut)
        self.root.bind("<Control-L>", self._on_clear_shortcut)

    def _build_sidebar(self, parent: tk.Widget) -> None:
        sidebar = tk.Frame(parent, bg=COLORS["sidebar"], width=205)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(len(self.NAV_ITEMS) + 1, weight=1)

        brand = tk.Frame(sidebar, bg=COLORS["sidebar"])
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(22, 24))
        tk.Label(brand, text="AgentLocal", bg=COLORS["sidebar"], fg="white", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(brand, text=f"Version {AGENTLOCAL_PATCH}", bg=COLORS["sidebar"], fg="#AAB4C4", font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 0))

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
        footer.grid(row=len(self.NAV_ITEMS) + 2, column=0, sticky="sew", padx=18, pady=18)
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
        self.quick_config_button = tk.Button(right, text="⚙  Personnaliser", command=lambda: self.show_page("configuration"), relief="flat", bd=0, bg=COLORS["soft_accent"], fg=COLORS["accent"], activebackground="#DDE8FF", font=("Segoe UI", 8, "bold"), padx=10, pady=6, cursor="hand2", highlightthickness=0)
        self.quick_config_button.pack(side="right", padx=(8, 0))
        self.host_chip = tk.Label(right, textvariable=self.profile_name_var, bg=COLORS["soft_lavender"], fg=COLORS["accent_2"], font=("Segoe UI", 8, "bold"), padx=9, pady=6, cursor="hand2")
        self.host_chip.pack(side="right", padx=(8, 0)); self.host_chip.bind("<Button-1>", lambda _e: self.show_page("configuration"))
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
        self.home_greeting = tk.Label(hero, text=self._personalized_greeting_text(), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 21, "bold"))
        self.home_greeting.grid(row=0, column=0, sticky="w", padx=22, pady=(18, 2))
        self.home_date = tk.Label(hero, text=_french_date_label(), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9))
        self.home_date.grid(row=1, column=0, sticky="w", padx=22)
        self.home_personalization_label = tk.Label(hero, textvariable=self.config_summary_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10))
        self.home_personalization_label.grid(row=2, column=0, sticky="w", padx=22, pady=(5, 18))
        hero_actions = tk.Frame(hero, bg=COLORS["card"]); hero_actions.grid(row=0, column=2, rowspan=3, padx=(8, 22))
        tk.Button(hero_actions, text="✦  Assistant", command=lambda: self.show_page("assistant"), relief="flat", bd=0, bg=COLORS["accent"], fg="white", activebackground=COLORS["accent_hover"], activeforeground="white", font=("Segoe UI", 9, "bold"), padx=15, pady=9, cursor="hand2", highlightthickness=0).pack(fill="x")
        tk.Button(hero_actions, text="⚙  Personnaliser", command=lambda: self.show_page("configuration"), relief="flat", bd=0, bg=COLORS["soft_accent"], fg=COLORS["accent"], activebackground="#DDE8FF", font=("Segoe UI", 8, "bold"), padx=15, pady=7, cursor="hand2", highlightthickness=0).pack(fill="x", pady=(6, 0))
        motif = tk.Canvas(hero, width=110, height=72, bg=COLORS["card"], highlightthickness=0); self.home_motif_canvas = motif
        motif.grid(row=0, column=1, rowspan=3, padx=4)
        motif.create_oval(10, 12, 46, 48, fill=COLORS["soft_accent"], outline="")
        motif.create_oval(44, 28, 74, 58, fill=COLORS["soft_lavender"], outline="")
        motif.create_oval(68, 8, 100, 40, fill=COLORS["soft_teal"], outline="")
        motif.create_line(22, 58, 92, 58, fill=COLORS["border"], width=2)

        quote = tk.Frame(page, bg=COLORS["quote_bg"], highlightbackground="#F0DFC0", highlightthickness=1)
        self.home_quote_card = quote
        quote.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        tk.Label(quote, text="💡  Citation du jour", bg=COLORS["quote_bg"], fg=COLORS["gold"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=16, pady=(10, 2))
        tk.Label(quote, textvariable=self.quote_var, bg=COLORS["quote_bg"], fg=COLORS["text"], font=("Segoe UI", 10, "italic"), wraplength=820, justify="left").pack(anchor="w", padx=16)
        tk.Label(quote, textvariable=self.quote_author_var, bg=COLORS["quote_bg"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(anchor="w", padx=16, pady=(2, 10))

        stats = tk.Frame(page, bg=COLORS["bg"]); self.home_stats_frame = stats
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

        day_status = tk.Frame(page, bg=COLORS["bg"]); self.home_day_status_frame = day_status
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

        quick = tk.Frame(page, bg=COLORS["bg"]); self.home_quick_frame = quick
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
        self.briefing_quote_card = quote_card
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

    # ------------------------------------------------------------------
    # Personnalisation hôte V12.4
    # ------------------------------------------------------------------
    def _personalized_greeting_text(self) -> str:
        name = str(getattr(self, "profile", {}).get("display_name", "") or "").strip()
        return f"{_greeting()} {name} 👋" if name else f"{_greeting()} 👋"

    def _refresh_personalization_state(self) -> None:
        try:
            self.profile = load_profile()
            self.preferences = load_preferences()
            dashboard = learning_dashboard()
        except Exception as error:
            log_exception("gui.personalization_refresh", error)
            return

        display = str(self.profile.get("display_name") or "Nouvel hôte")
        machine = str(self.profile.get("machine_name") or "--")
        self.profile_name_var.set(display)
        self.host_name_var.set(machine)
        initial = dashboard.get("initial", {})
        self.learning_progress_var.set(str(initial.get("label", "Apprentissage local")))
        summary = dashboard.get("summary", {})
        self.learning_count_var.set(str(int(summary.get("pending", 0) or 0)))

        if not is_onboarding_complete():
            self.config_summary_var.set("⚙ Configuration initiale à terminer")
        elif initial.get("status") == "learning":
            self.config_summary_var.set(f"🧠 AgentLocal apprend vos habitudes · {initial.get('label', '')}")
        else:
            self.config_summary_var.set(f"Profil local : {display} · {machine}")

        if hasattr(self, "home_greeting"):
            self.home_greeting.configure(text=self._personalized_greeting_text())

        self._refresh_daily_quote()
        home_cards = self.preferences.get("appearance", {}).get("home_cards", {})
        show_quote = bool(self.preferences.get("assistant", {}).get("daily_quote", True)) and bool(home_cards.get("quote", True))
        for attr in ("home_quote_card", "briefing_quote_card"):
            widget = getattr(self, attr, None)
            if widget is not None:
                try:
                    if show_quote:
                        widget.grid()
                    else:
                        widget.grid_remove()
                except tk.TclError:
                    pass


        try:
            motif = getattr(self, "home_motif_canvas", None)
            if motif is not None:
                (motif.grid if self.preferences.get("appearance", {}).get("patterns", True) else motif.grid_remove)()
        except tk.TclError:
            pass

        try:
            if hasattr(self, "home_stats_frame"):
                (self.home_stats_frame.grid if home_cards.get("pc", True) else self.home_stats_frame.grid_remove)()
            if hasattr(self, "home_day_status_frame"):
                show_day = any(bool(home_cards.get(k, True)) for k in ("routine", "alerts"))
                (self.home_day_status_frame.grid if show_day else self.home_day_status_frame.grid_remove)()
        except tk.TclError:
            pass

        self._refresh_configuration_page()
        self._refresh_habits_page()

    def _onboarding_visibility_loop(self) -> None:
        try:
            visible = bool(self.root.winfo_viewable()) and self.root.state() != "withdrawn"
            if visible and not is_onboarding_complete():
                self._maybe_show_onboarding(force=True)
            self.root.after(1800, self._onboarding_visibility_loop)
        except tk.TclError:
            pass

    def _maybe_show_onboarding(self, force: bool = False) -> None:
        if not force and is_onboarding_complete():
            return
        try:
            if self.onboarding_window is not None and self.onboarding_window.window.winfo_exists():
                self.onboarding_window.window.lift()
                return
        except Exception:
            self.onboarding_window = None
        try:
            self.reveal_main()
            self.onboarding_window = OnboardingWizard(self.root, COLORS, on_complete=self._on_onboarding_complete)
        except Exception as error:
            log_exception("gui.onboarding", error)
            messagebox.showwarning(APP_TITLE, "Impossible d’ouvrir la configuration initiale.", parent=self.root)

    def _on_onboarding_complete(self) -> None:
        self.onboarding_window = None
        self._refresh_personalization_state()
        self.show_page("home")
        self.status_var.set("Profil local configuré")

    def _restart_onboarding(self) -> None:
        if not messagebox.askyesno(APP_TITLE, "Relancer l’assistant de configuration ? Vos réglages actuels resteront modifiables.", parent=self.root):
            return
        reset_onboarding()
        self._maybe_show_onboarding(force=True)

    def _config_card(self, parent: tk.Widget, title: str, icon: str, description_var: tk.StringVar, action_text: str, command, accent: str) -> tk.Frame:
        card = tk.Frame(parent, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1, height=142)
        card.grid_propagate(False)
        tk.Frame(card, bg=accent, height=3).pack(fill="x")
        head = tk.Frame(card, bg=COLORS["card"]); head.pack(fill="x", padx=15, pady=(12, 4))
        tk.Label(head, text=icon, bg=COLORS["card"], fg=accent, font=("Segoe UI Emoji", 13)).pack(side="left")
        tk.Label(head, text=title, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).pack(side="left", padx=(7, 0))
        tk.Label(card, textvariable=description_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8), wraplength=330, justify="left").pack(anchor="w", padx=15, pady=(2, 8))
        tk.Button(card, text=action_text, command=command, relief="flat", bd=0, bg=COLORS["soft_accent"], fg=COLORS["accent"], activebackground="#DDE8FF", font=("Segoe UI", 8, "bold"), padx=10, pady=5, cursor="hand2", highlightthickness=0).pack(anchor="w", padx=15, pady=(0, 12))
        return card

    def _build_configuration_page(self) -> None:
        page = self._new_page("configuration")
        self._section_title(page, "Personnalisation", "Chaque hôte peut adapter l'apparence, la communication, les habitudes et les notifications sans modifier le code.").grid(row=0, column=0, sticky="ew")

        keys = ("profile", "appearance", "communication", "understanding", "learning", "morning", "briefing", "alerts", "notifications", "privacy")
        self.config_vars = {key: tk.StringVar(value="Chargement...") for key in keys}
        grid = tk.Frame(page, bg=COLORS["bg"]); grid.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        for col in range(3):
            grid.grid_columnconfigure(col, weight=1, uniform="config")
        cards = [
            ("Profil de l’hôte", "👤", self.config_vars["profile"], "Modifier", self._open_profile_editor, COLORS["accent"]),
            ("Apparence", "🎨", self.config_vars["appearance"], "Personnaliser", self._open_appearance_editor, COLORS["accent_2"]),
            ("Communication", "💬", self.config_vars["communication"], "Configurer", self._open_behavior_editor, COLORS["teal"]),
            ("Compréhension", "🧠", self.config_vars["understanding"], "Voir le profil", self._open_understanding_editor, COLORS["gold"]),
            ("Habitudes", "📚", self.config_vars["learning"], "Configurer", self._open_learning_editor, COLORS["teal"]),
            ("Automatisations", "☀", self.config_vars["morning"], "Configurer", self._open_morning_editor, COLORS["gold"]),
            ("Briefing", "📰", self.config_vars["briefing"], "Choisir les thèmes", self._open_briefing_editor, COLORS["accent"]),
            ("Alertes", "🚨", self.config_vars["alerts"], "Configurer", self._open_alerts_editor, COLORS["warning"]),
            ("Notifications", "🔔", self.config_vars["notifications"], "Fréquence & calme", self._open_notifications_editor, COLORS["accent_2"]),
            ("Confidentialité", "🔒", self.config_vars["privacy"], "Voir les garanties", self._show_privacy_dialog, COLORS["success"]),
        ]
        for i, item in enumerate(cards):
            card = self._config_card(grid, *item)
            col = i % 3; row = i // 3
            left = 0 if col == 0 else 5; right = 0 if col == 2 else 5
            card.grid(row=row, column=col, sticky="ew", padx=(left, right), pady=(0, 9))

        actions = tk.Frame(page, bg=COLORS["bg"]); actions.grid(row=2, column=0, sticky="ew", pady=(3, 0))
        tk.Button(actions, text="🧭 Relancer l’assistant", command=self._restart_onboarding, relief="flat", bd=0, bg=COLORS["soft_neutral"], fg=COLORS["text"], font=("Segoe UI", 8, "bold"), padx=12, pady=7, cursor="hand2").pack(side="left")
        tk.Button(actions, text="🧠 Voir les habitudes", command=lambda: self.show_page("habits"), relief="flat", bd=0, bg=COLORS["soft_teal"], fg=COLORS["teal"], font=("Segoe UI", 8, "bold"), padx=12, pady=7, cursor="hand2").pack(side="left", padx=(8, 0))

    def _refresh_configuration_page(self) -> None:
        if not hasattr(self, "config_vars"):
            return
        try:
            profile = load_profile(); prefs = load_preferences(); learn = learning_dashboard(); lang = language_summary()
            usage = {"work": "Travail", "personal": "Personnel", "mixed": "Mixte"}.get(profile.get("usage_mode"), "Travail")
            self.config_vars["profile"].set(f"{profile.get('display_name') or 'Nom à renseigner'} · {profile.get('machine_name') or '--'} · {usage}")
            appearance = prefs["appearance"]
            theme_label = {"agentlocal":"AgentLocal", "blue_night":"Bleu nuit", "dark":"Dark", "nature":"Nature", "violet":"Violet", "enterprise":"Entreprise", "windows":"Windows", "minimal":"Minimal"}.get(appearance.get("theme"), "AgentLocal")
            self.config_vars["appearance"].set(f"{theme_label} · {appearance.get('density', 'comfortable')} · accent {appearance.get('accent_color')}")
            assistant = prefs["assistant"]
            style = {"natural": "Naturel", "professional": "Professionnel", "concise": "Très concis"}.get(assistant.get("response_style"), "Naturel")
            emoji = {"none": "sans emoji", "light": "emoji légers", "expressive": "emoji expressifs"}.get(assistant.get("emoji_level"), "emoji légers")
            detail = {"short":"réponses courtes", "balanced":"réponses équilibrées", "detailed":"réponses détaillées"}.get(assistant.get("response_detail"), "réponses équilibrées")
            self.config_vars["communication"].set(f"{style} · {emoji} · {detail}")
            understanding = prefs.get("understanding", {})
            self.config_vars["understanding"].set(f"Tolérance fautes {understanding.get('typo_tolerance', 2)}/3 · {lang.get('learned',0)} expression(s) · {lang.get('unrecognized',0)} incompréhension(s)")
            self.config_vars["learning"].set(f"{learn['initial'].get('label')} · {learn['summary'].get('pending', 0)} proposition(s)")
            morning = prefs["morning"]
            self.config_vars["morning"].set(f"{'Activée' if morning.get('enabled') else 'Désactivée'} · premier déverrouillage · {morning.get('start_time')} → {morning.get('end_time')}")
            brief = prefs["briefing"]; selected = sum(1 for v in brief.get("topics", {}).values() if v)
            self.config_vars["briefing"].set(f"{'Activé' if brief.get('enabled') else 'Désactivé'} · {selected} thème(s)")
            alert_cfg = prefs.get("alerts", {})
            self.config_vars["alerts"].set(f"{'Actives' if alert_cfg.get('enabled', True) else 'Désactivées'} · historique local · diagnostic non destructif")
            notif = prefs.get("notifications", {})
            quiet = notif.get("quiet_hours", {})
            quiet_label = f" · calme {quiet.get('start')}–{quiet.get('end')}" if quiet.get("enabled") else ""
            self.config_vars["notifications"].set(f"{notification_mode_label()} · anti-spam {notif.get('repeat_cooldown_minutes',60)} min{quiet_label}")
            self.config_vars["privacy"].set("Local · aucune frappe clavier · aucun contenu privé · actions sensibles confirmées")
        except Exception as error:
            log_exception("gui.configuration_refresh", error)

    def _build_habits_page(self) -> None:
        page = self._new_page("habits")
        self._section_title(page, "Habitudes", "AgentLocal peut apprendre des métadonnées d’actions locales, puis proposer une routine sans jamais l’activer seul.").grid(row=0, column=0, sticky="ew")

        status = tk.Frame(page, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        status.grid(row=1, column=0, sticky="ew", pady=(14, 0)); status.grid_columnconfigure(0, weight=1)
        tk.Label(status, text="🧠  Phase d’apprentissage", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 3))
        self.habit_status_var = tk.StringVar(value="Chargement...")
        tk.Label(status, textvariable=self.habit_status_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=16)
        self.habit_progress_var = tk.DoubleVar(value=0)
        self.habit_progress = ttk.Progressbar(status, variable=self.habit_progress_var, maximum=100, mode="determinate", style="Learning.Horizontal.TProgressbar")
        self.habit_progress.grid(row=2, column=0, sticky="ew", padx=16, pady=(10, 14))
        controls = tk.Frame(status, bg=COLORS["card"]); controls.grid(row=0, column=1, rowspan=3, padx=16)
        tk.Button(controls, text="Relancer 2 jours", command=self._restart_learning, relief="flat", bd=0, bg=COLORS["soft_accent"], fg=COLORS["accent"], font=("Segoe UI", 8, "bold"), padx=10, pady=6, cursor="hand2").pack(pady=(0, 5))
        self.learning_toggle_btn = tk.Button(controls, text="Désactiver", command=self._toggle_learning, relief="flat", bd=0, bg=COLORS["soft_neutral"], fg=COLORS["muted"], font=("Segoe UI", 8), padx=10, pady=6, cursor="hand2")
        self.learning_toggle_btn.pack()

        grid = tk.Frame(page, bg=COLORS["bg"]); grid.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        grid.grid_columnconfigure(0, weight=1, uniform="habits"); grid.grid_columnconfigure(1, weight=1, uniform="habits")
        declared_card = tk.Frame(grid, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        declared_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        tk.Label(declared_card, text="📌  Habitudes déclarées", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(13, 4))
        self.declared_habits_var = tk.StringVar(value="Aucune")
        tk.Label(declared_card, textvariable=self.declared_habits_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9), justify="left", wraplength=330).pack(anchor="w", padx=15, pady=(0, 10))
        tk.Button(declared_card, text="Modifier", command=self._open_declared_habits_editor, relief="flat", bd=0, bg=COLORS["soft_accent"], fg=COLORS["accent"], font=("Segoe UI", 8, "bold"), padx=10, pady=5, cursor="hand2").pack(anchor="w", padx=15, pady=(0, 13))

        observed_card = tk.Frame(grid, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        observed_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        tk.Label(observed_card, text="👁  Observé localement", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(13, 4))
        self.observed_habits_var = tk.StringVar(value="Pas encore assez de données")
        tk.Label(observed_card, textvariable=self.observed_habits_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9), justify="left", wraplength=330).pack(anchor="w", padx=15, pady=(0, 13))

        proposals = tk.Frame(page, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        proposals.grid(row=3, column=0, sticky="ew", pady=(12, 0)); proposals.grid_columnconfigure(0, weight=1)
        tk.Label(proposals, text="✨  Propositions à examiner", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", padx=15, pady=(13, 4))
        self.habit_proposals_var = tk.StringVar(value="Aucune proposition pour le moment.")
        tk.Label(proposals, textvariable=self.habit_proposals_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9), justify="left", wraplength=700).grid(row=1, column=0, sticky="w", padx=15, pady=(0, 13))
        tk.Button(proposals, text="Examiner dans l’Assistant", command=lambda: self.run_shortcut("liste mes habitudes", "Mes habitudes détectées"), relief="flat", bd=0, bg=COLORS["soft_teal"], fg=COLORS["teal"], font=("Segoe UI", 8, "bold"), padx=10, pady=6, cursor="hand2").grid(row=0, column=1, rowspan=2, padx=15)

    def _refresh_habits_page(self) -> None:
        if not hasattr(self, "habit_status_var"):
            return
        try:
            data = learning_dashboard(); initial = data["initial"]; prefs = load_preferences()
            self.habit_status_var.set(initial.get("label", "Apprentissage local"))
            self.habit_progress_var.set(float(initial.get("progress", 0) or 0))
            enabled = bool(prefs["learning"].get("enabled", True))
            self.learning_toggle_btn.configure(text="Désactiver" if enabled else "Activer")
            declared = data.get("declared", {}); apps = declared.get("frequent_apps", [])
            declared_text = f"Début habituel : {declared.get('typical_start_time', '--')}\nOutils fréquents : {', '.join(apps) if apps else 'à découvrir'}"
            self.declared_habits_var.set(declared_text)
            observed = data.get("observed_targets", [])
            self.observed_habits_var.set("\n".join(f"• {row['target']} · {row['count']} fois" for row in observed[:6]) if observed else "Pas encore assez de données d’action.")
            pending = data.get("pending", [])
            if pending:
                self.habit_proposals_var.set("\n".join(f"• {row.get('title', 'Habitude')} · vers {row.get('typical_time', '--')}" for row in pending[:4]))
            else:
                self.habit_proposals_var.set("Aucune proposition automatique pour le moment. L’apprentissage n’active jamais une routine seul.")
        except Exception as error:
            log_exception("gui.habits_refresh", error)

    def _restart_learning(self) -> None:
        restart_initial_learning(); self._refresh_personalization_state(); self.status_var.set("Phase d’apprentissage initial relancée pour 2 jours")

    def _toggle_learning(self) -> None:
        enabled = bool(load_preferences().get("learning", {}).get("enabled", True))
        set_learning_enabled(not enabled); self._refresh_personalization_state(); self.status_var.set("Apprentissage activé" if not enabled else "Apprentissage désactivé")

    def _dialog_base(self, title: str, geometry: str = "560x520") -> tuple[tk.Toplevel, tk.Frame]:
        popup = tk.Toplevel(self.root); popup.title(title); popup.geometry(geometry); popup.resizable(False, False); popup.transient(self.root); popup.grab_set(); popup.configure(bg=COLORS["bg"])
        body = tk.Frame(popup, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1); body.pack(fill="both", expand=True, padx=18, pady=18)
        return popup, body

    def _open_profile_editor(self) -> None:
        profile = load_profile(); popup, body = self._dialog_base("Profil de l’hôte", "540x390")
        name = tk.StringVar(value=profile.get("display_name", "")); machine = tk.StringVar(value=profile.get("machine_name", "")); usage = tk.StringVar(value=profile.get("usage_mode", "work"))
        tk.Label(body, text="👤 Profil de l’hôte", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=18, pady=(18, 4))
        tk.Label(body, text="Ces informations restent sur cette machine.", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=18, pady=(0, 14))
        for label, var in (("Nom affiché", name), ("Nom de la machine", machine)):
            tk.Label(body, text=label, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(7, 4)); tk.Entry(body, textvariable=var, relief="flat", bg=COLORS["soft_neutral"], font=("Segoe UI", 10)).pack(fill="x", padx=18, ipady=7)
        row = tk.Frame(body, bg=COLORS["card"]); row.pack(fill="x", padx=18, pady=(14, 10))
        for value, label in (("work", "Travail"), ("personal", "Personnel"), ("mixed", "Mixte")):
            tk.Radiobutton(row, text=label, variable=usage, value=value, bg=COLORS["card"], activebackground=COLORS["card"], selectcolor="white", font=("Segoe UI", 9)).pack(side="left", padx=(0, 12))
        def save():
            profile.update({"display_name": name.get().strip(), "machine_name": machine.get().strip(), "usage_mode": usage.get(), "configured": True}); save_profile(profile); popup.destroy(); self._refresh_personalization_state()
        tk.Button(body, text="Enregistrer", command=save, relief="flat", bd=0, bg=COLORS["accent"], fg="white", font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2").pack(anchor="e", padx=18, pady=(6, 18))

    def _rebuild_ui_after_theme_change(self) -> None:
        """Reconstruit uniquement l'interface Tkinter après un changement de thème."""
        try:
            COLORS.clear(); COLORS.update(build_palette(load_preferences().get("appearance", {})))
            self.root.configure(bg=COLORS["bg"])
            for child in list(self.root.winfo_children()):
                try: child.destroy()
                except tk.TclError: pass
            self.nav_buttons = {}; self.pages = {}; self.metric_vars = {}
            self._configure_styles(); self._build_interface()
            self._refresh_daily_quote(); self._refresh_runtime_summary(); self._refresh_startup_status()
            self._update_dashboard_metrics(); self._refresh_personalization_state(); self.show_page("configuration")
            self.status_var.set("Apparence appliquée")
        except Exception as error:
            log_exception("gui.theme_rebuild", error)
            messagebox.showwarning(APP_TITLE, "Le thème a été enregistré. Il sera pleinement appliqué au prochain lancement.", parent=self.root)

    def _open_appearance_editor(self) -> None:
        prefs = load_preferences(); block = prefs["appearance"]
        popup, body = self._dialog_base("Apparence", "720x650")
        theme = tk.StringVar(value=block.get("theme", "agentlocal")); density = tk.StringVar(value=block.get("density", "comfortable"))
        accent = tk.StringVar(value=block.get("accent_color", "#356AE6")); sidebar = tk.StringVar(value=block.get("sidebar_color", "#101A2E")); card = tk.StringVar(value=block.get("card_color", "#FFFFFF"))
        patterns = tk.BooleanVar(value=block.get("patterns", True)); animations = tk.BooleanVar(value=block.get("animations", True))
        home = block.get("home_cards", {}); home_vars = {k: tk.BooleanVar(value=bool(home.get(k, False))) for k in ("pc","briefing","routine","alerts","quote","habits","network","processes")}
        tk.Label(body, text="🎨 Apparence", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=18, pady=(18, 4))
        tk.Label(body, text="Les couleurs et cartes sont propres à cet hôte. L'application du thème est immédiate.", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=18, pady=(0, 12))
        row = tk.Frame(body, bg=COLORS["card"]); row.pack(fill="x", padx=18)
        tk.Label(row, text="Thème", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9, "bold")).grid(row=0,column=0,sticky="w")
        combo = ttk.Combobox(row, textvariable=theme, values=list(theme_names()), state="readonly", width=20); combo.grid(row=1,column=0,sticky="w",pady=(4,10))
        tk.Label(row, text="Densité", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9, "bold")).grid(row=0,column=1,sticky="w",padx=(28,0))
        ttk.Combobox(row, textvariable=density, values=["comfortable","compact"], state="readonly", width=18).grid(row=1,column=1,sticky="w",padx=(28,0),pady=(4,10))
        colors = tk.Frame(body, bg=COLORS["card"]); colors.pack(fill="x", padx=18, pady=(4,6))
        def chooser(var):
            selected = colorchooser.askcolor(color=var.get(), parent=popup)
            if selected and selected[1]: var.set(selected[1].upper())
        for i,(label,var) in enumerate((("Accent",accent),("Barre latérale",sidebar),("Cartes",card))):
            box=tk.Frame(colors,bg=COLORS["card"]); box.grid(row=0,column=i,sticky="w",padx=(0 if i==0 else 16,0))
            tk.Label(box,text=label,bg=COLORS["card"],fg=COLORS["muted"],font=("Segoe UI",8,"bold")).pack(anchor="w")
            tk.Button(box,textvariable=var,command=lambda v=var:chooser(v),relief="flat",bd=0,bg=COLORS["soft_neutral"],fg=COLORS["text"],font=("Consolas",9),padx=10,pady=6,cursor="hand2").pack(anchor="w",pady=(4,0))
        toggles=tk.Frame(body,bg=COLORS["card"]); toggles.pack(fill="x",padx=18,pady=(8,6))
        tk.Checkbutton(toggles,text="Motifs décoratifs légers",variable=patterns,bg=COLORS["card"],activebackground=COLORS["card"],selectcolor="white",font=("Segoe UI",9)).pack(side="left")
        tk.Checkbutton(toggles,text="Animations légères",variable=animations,bg=COLORS["card"],activebackground=COLORS["card"],selectcolor="white",font=("Segoe UI",9)).pack(side="left",padx=(18,0))
        tk.Label(body,text="Cartes visibles sur l’accueil",bg=COLORS["card"],fg=COLORS["text"],font=("Segoe UI",9,"bold")).pack(anchor="w",padx=18,pady=(10,4))
        grid=tk.Frame(body,bg=COLORS["card"]); grid.pack(fill="x",padx=18)
        labels={"pc":"État du PC","briefing":"Briefing","routine":"Routine","alerts":"Alertes","quote":"Citation","habits":"Habitudes","network":"Réseau","processes":"Processus"}
        for i,key in enumerate(home_vars):
            tk.Checkbutton(grid,text=labels[key],variable=home_vars[key],bg=COLORS["card"],activebackground=COLORS["card"],selectcolor="white",font=("Segoe UI",9)).grid(row=i//4,column=i%4,sticky="w",padx=(0,16),pady=3)
        preview=tk.Frame(body,bg=COLORS["soft_neutral"],highlightbackground=COLORS["border"],highlightthickness=1); preview.pack(fill="x",padx=18,pady=(14,0))
        tk.Label(preview,text="Aperçu",bg=COLORS["soft_neutral"],fg=COLORS["muted"],font=("Segoe UI",8,"bold")).pack(anchor="w",padx=10,pady=(8,2))
        tk.Label(preview,text="AgentLocal  •  mini-cartes  •  configuration personnalisée",bg=COLORS["soft_neutral"],fg=COLORS["text"],font=("Segoe UI",10,"bold")).pack(anchor="w",padx=10,pady=(0,8))
        def save():
            block.update({"theme":theme.get(),"density":density.get(),"accent_color":accent.get(),"sidebar_color":sidebar.get(),"card_color":card.get(),"patterns":patterns.get(),"animations":animations.get(),"home_cards":{k:v.get() for k,v in home_vars.items()}})
            save_preferences(prefs); popup.destroy(); self._rebuild_ui_after_theme_change()
        tk.Button(body,text="Appliquer maintenant",command=save,relief="flat",bd=0,bg=COLORS["accent"],fg="white",font=("Segoe UI",9,"bold"),padx=15,pady=8,cursor="hand2").pack(anchor="e",padx=18,pady=(16,18))

    def _open_understanding_editor(self) -> None:
        prefs=load_preferences(); block=prefs["understanding"]; popup,body=self._dialog_base("Compréhension", "620x535")
        typo=tk.IntVar(value=int(block.get("typo_tolerance",2))); turns=tk.IntVar(value=int(block.get("context_turns",4)))
        store=tk.BooleanVar(value=block.get("store_unrecognized",True)); learn=tk.BooleanVar(value=block.get("learn_confirmed_expressions",True)); stats=language_summary()
        tk.Label(body,text="🧠 Compréhension individualisée",bg=COLORS["card"],fg=COLORS["text"],font=("Segoe UI",16,"bold")).pack(anchor="w",padx=18,pady=(18,5))
        tk.Label(body,text=f"Expressions confirmées : {stats.get('learned',0)}   •   demandes non comprises : {stats.get('unrecognized',0)}",bg=COLORS["soft_teal"],fg=COLORS["teal"],font=("Segoe UI",9,"bold"),padx=10,pady=8).pack(fill="x",padx=18,pady=(4,12))
        row=tk.Frame(body,bg=COLORS["card"]); row.pack(fill="x",padx=18)
        tk.Label(row,text="Tolérance aux fautes (0 à 3)",bg=COLORS["card"],fg=COLORS["muted"],font=("Segoe UI",8,"bold")).grid(row=0,column=0,sticky="w")
        tk.Spinbox(row,from_=0,to=3,textvariable=typo,width=6,relief="flat",bg=COLORS["soft_neutral"]).grid(row=1,column=0,sticky="w",pady=(4,10))
        tk.Label(row,text="Contexte conversationnel (tours)",bg=COLORS["card"],fg=COLORS["muted"],font=("Segoe UI",8,"bold")).grid(row=0,column=1,sticky="w",padx=(26,0))
        tk.Spinbox(row,from_=1,to=8,textvariable=turns,width=6,relief="flat",bg=COLORS["soft_neutral"]).grid(row=1,column=1,sticky="w",padx=(26,0),pady=(4,10))
        tk.Checkbutton(body,text="Conserver localement les demandes non comprises",variable=store,bg=COLORS["card"],activebackground=COLORS["card"],selectcolor="white",font=("Segoe UI",9)).pack(anchor="w",padx=18,pady=3)
        tk.Checkbutton(body,text="Apprendre les expressions uniquement après confirmation",variable=learn,bg=COLORS["card"],activebackground=COLORS["card"],selectcolor="white",font=("Segoe UI",9)).pack(anchor="w",padx=18,pady=3)
        tk.Label(body,text="Expressions apprises",bg=COLORS["card"],fg=COLORS["text"],font=("Segoe UI",9,"bold")).pack(anchor="w",padx=18,pady=(14,4))
        rows=learned_expressions(6); text="\n".join(f"• {phrase} → {intent}" for phrase,intent in rows) if rows else "Aucune expression personnelle confirmée pour le moment."
        tk.Label(body,text=text,bg=COLORS["soft_neutral"],fg=COLORS["muted"],font=("Segoe UI",8),justify="left",wraplength=540,padx=10,pady=8).pack(fill="x",padx=18)
        def clear_failures(): clear_unrecognized(); messagebox.showinfo(APP_TITLE,"Historique des incompréhensions effacé.",parent=popup)
        action_row = tk.Frame(body, bg=COLORS["card"]); action_row.pack(fill="x", padx=18, pady=(10,0))
        tk.Button(action_row,text="Effacer les incompréhensions",command=clear_failures,relief="flat",bd=0,bg=COLORS["soft_neutral"],fg=COLORS["muted"],font=("Segoe UI",8),padx=10,pady=6,cursor="hand2").pack(side="left")
        def add_expression():
            win = tk.Toplevel(popup); win.title("Ajouter une expression"); win.geometry("500x310"); win.resizable(False,False); win.transient(popup); win.grab_set(); win.configure(bg=COLORS["bg"])
            box=tk.Frame(win,bg=COLORS["card"],highlightbackground=COLORS["border"],highlightthickness=1); box.pack(fill="both",expand=True,padx=16,pady=16)
            phrase=tk.StringVar(); command=tk.StringVar()
            tk.Label(box,text="🧠 Expression personnelle",bg=COLORS["card"],fg=COLORS["text"],font=("Segoe UI",14,"bold")).pack(anchor="w",padx=14,pady=(14,8))
            tk.Label(box,text="Ce que tu dis",bg=COLORS["card"],fg=COLORS["muted"],font=("Segoe UI",8,"bold")).pack(anchor="w",padx=14)
            tk.Entry(box,textvariable=phrase,relief="flat",bg=COLORS["soft_neutral"],font=("Segoe UI",10)).pack(fill="x",padx=14,pady=(4,10),ipady=6)
            tk.Label(box,text="Commande AgentLocal correspondante",bg=COLORS["card"],fg=COLORS["muted"],font=("Segoe UI",8,"bold")).pack(anchor="w",padx=14)
            tk.Entry(box,textvariable=command,relief="flat",bg=COLORS["soft_neutral"],font=("Segoe UI",10)).pack(fill="x",padx=14,pady=(4,8),ipady=6)
            tk.Label(box,text="Exemple : “fais le point” → “quel est l'état de mon PC”. La commande repassera toujours par les contrôles de sécurité.",bg=COLORS["card"],fg=COLORS["muted"],font=("Segoe UI",8),wraplength=440,justify="left").pack(anchor="w",padx=14)
            def commit():
                if not remember_expression(phrase.get(), command.get()):
                    messagebox.showwarning(APP_TITLE,"Renseigne une expression et une commande.",parent=win); return
                win.destroy(); popup.destroy(); self._open_understanding_editor()
            tk.Button(box,text="Enregistrer",command=commit,relief="flat",bd=0,bg=COLORS["accent"],fg="white",font=("Segoe UI",9,"bold"),padx=12,pady=7,cursor="hand2").pack(anchor="e",padx=14,pady=(12,14))
        tk.Button(action_row,text="+ Ajouter une expression",command=add_expression,relief="flat",bd=0,bg=COLORS["soft_teal"],fg=COLORS["teal"],font=("Segoe UI",8,"bold"),padx=10,pady=6,cursor="hand2").pack(side="left",padx=(8,0))
        def save():
            block.update({"typo_tolerance":typo.get(),"context_turns":turns.get(),"store_unrecognized":store.get(),"learn_confirmed_expressions":learn.get()}); save_preferences(prefs); popup.destroy(); self._refresh_personalization_state()
        tk.Button(body,text="Appliquer",command=save,relief="flat",bd=0,bg=COLORS["accent"],fg="white",font=("Segoe UI",9,"bold"),padx=14,pady=8,cursor="hand2").pack(anchor="e",padx=18,pady=(12,18))

    def _open_alerts_editor(self) -> None:
        prefs=load_preferences(); block=prefs["alerts"]; popup,body=self._dialog_base("Alertes", "540x360")
        enabled=tk.BooleanVar(value=block.get("enabled",True)); background=tk.BooleanVar(value=block.get("background_notifications",True))
        tk.Label(body,text="🚨 Alertes",bg=COLORS["card"],fg=COLORS["text"],font=("Segoe UI",16,"bold")).pack(anchor="w",padx=18,pady=(18,7))
        tk.Label(body,text="Le diagnostic reste non destructif : une alerte ne ferme jamais une application et ne supprime jamais un fichier.",bg=COLORS["card"],fg=COLORS["muted"],font=("Segoe UI",9),wraplength=480,justify="left").pack(anchor="w",padx=18,pady=(0,12))
        tk.Checkbutton(body,text="Activer le suivi des alertes",variable=enabled,bg=COLORS["card"],activebackground=COLORS["card"],selectcolor="white",font=("Segoe UI",9,"bold")).pack(anchor="w",padx=18,pady=4)
        tk.Checkbutton(body,text="Autoriser les fenêtres de notification",variable=background,bg=COLORS["card"],activebackground=COLORS["card"],selectcolor="white",font=("Segoe UI",9)).pack(anchor="w",padx=18,pady=4)
        tk.Label(body,text="La fréquence et les heures calmes se règlent dans Notifications.",bg=COLORS["soft_warning"],fg=COLORS["warning"],font=("Segoe UI",8,"bold"),padx=10,pady=8).pack(fill="x",padx=18,pady=(12,0))
        def save(): block.update({"enabled":enabled.get(),"background_notifications":background.get()}); save_preferences(prefs); popup.destroy(); self._refresh_personalization_state()
        tk.Button(body,text="Appliquer",command=save,relief="flat",bd=0,bg=COLORS["accent"],fg="white",font=("Segoe UI",9,"bold"),padx=14,pady=8,cursor="hand2").pack(anchor="e",padx=18,pady=(18,18))

    def _open_notifications_editor(self) -> None:
        prefs=load_preferences(); block=prefs["notifications"]; popup,body=self._dialog_base("Notifications", "650x650")
        mode=tk.StringVar(value=block.get("mode","balanced")); summary=tk.IntVar(value=int(block.get("summary_minutes",60))); critical=tk.BooleanVar(value=block.get("critical_immediate",True)); cooldown=tk.IntVar(value=int(block.get("repeat_cooldown_minutes",60)))
        quiet=block.get("quiet_hours",{}); quiet_enabled=tk.BooleanVar(value=quiet.get("enabled",False)); quiet_start=tk.StringVar(value=quiet.get("start","18:30")); quiet_end=tk.StringVar(value=quiet.get("end","07:00")); quiet_critical=tk.BooleanVar(value=quiet.get("allow_critical",True))
        categories=block.get("categories",{}); cat_vars={k:tk.BooleanVar(value=bool(categories.get(k,True))) for k in ("system","briefing","routine","habits","updates")}
        tk.Label(body,text="🔔 Notifications",bg=COLORS["card"],fg=COLORS["text"],font=("Segoe UI",16,"bold")).pack(anchor="w",padx=18,pady=(18,4))
        tk.Label(body,text="Choisissez quand AgentLocal doit vous interrompre. L’historique des alertes reste disponible même en mode silencieux.",bg=COLORS["card"],fg=COLORS["muted"],font=("Segoe UI",9),wraplength=570,justify="left").pack(anchor="w",padx=18,pady=(0,10))
        tk.Label(body,text="Mode",bg=COLORS["card"],fg=COLORS["text"],font=("Segoe UI",9,"bold")).pack(anchor="w",padx=18)
        modes=(("realtime","Temps réel"),("balanced","Équilibré"),("discreet","Discret"),("periodic","Résumé périodique"),("silent","Silencieux"))
        mode_row=tk.Frame(body,bg=COLORS["card"]); mode_row.pack(fill="x",padx=18,pady=(3,8))
        for value,label in modes: tk.Radiobutton(mode_row,text=label,variable=mode,value=value,bg=COLORS["card"],activebackground=COLORS["card"],selectcolor="white",font=("Segoe UI",8)).pack(side="left",padx=(0,10))
        freq=tk.Frame(body,bg=COLORS["card"]); freq.pack(fill="x",padx=18,pady=(4,8))
        tk.Label(freq,text="Résumé périodique",bg=COLORS["card"],fg=COLORS["muted"],font=("Segoe UI",8,"bold")).grid(row=0,column=0,sticky="w")
        ttk.Combobox(freq,textvariable=summary,values=[30,60,120,240],state="readonly",width=8).grid(row=1,column=0,sticky="w",pady=(3,0))
        tk.Label(freq,text="minutes",bg=COLORS["card"],fg=COLORS["muted"],font=("Segoe UI",8)).grid(row=1,column=1,sticky="w",padx=(6,25))
        tk.Label(freq,text="Rappel même problème",bg=COLORS["card"],fg=COLORS["muted"],font=("Segoe UI",8,"bold")).grid(row=0,column=2,sticky="w")
        tk.Spinbox(freq,from_=5,to=1440,textvariable=cooldown,width=7,relief="flat",bg=COLORS["soft_neutral"]).grid(row=1,column=2,sticky="w",pady=(3,0))
        tk.Label(freq,text="minutes",bg=COLORS["card"],fg=COLORS["muted"],font=("Segoe UI",8)).grid(row=1,column=3,sticky="w",padx=(6,0))
        tk.Checkbutton(body,text="Toujours notifier immédiatement une alerte critique",variable=critical,bg=COLORS["card"],activebackground=COLORS["card"],selectcolor="white",font=("Segoe UI",9,"bold")).pack(anchor="w",padx=18,pady=(4,8))
        quiet_box=tk.Frame(body,bg=COLORS["soft_neutral"],highlightbackground=COLORS["border"],highlightthickness=1); quiet_box.pack(fill="x",padx=18,pady=(4,10))
        tk.Checkbutton(quiet_box,text="🌙 Heures calmes",variable=quiet_enabled,bg=COLORS["soft_neutral"],activebackground=COLORS["soft_neutral"],selectcolor="white",font=("Segoe UI",9,"bold")).grid(row=0,column=0,columnspan=4,sticky="w",padx=10,pady=(8,4))
        tk.Label(quiet_box,text="De",bg=COLORS["soft_neutral"],fg=COLORS["muted"],font=("Segoe UI",8)).grid(row=1,column=0,sticky="w",padx=10); tk.Entry(quiet_box,textvariable=quiet_start,width=8,relief="flat",bg=COLORS["card"]).grid(row=1,column=1,sticky="w")
        tk.Label(quiet_box,text="à",bg=COLORS["soft_neutral"],fg=COLORS["muted"],font=("Segoe UI",8)).grid(row=1,column=2,sticky="w",padx=(12,4)); tk.Entry(quiet_box,textvariable=quiet_end,width=8,relief="flat",bg=COLORS["card"]).grid(row=1,column=3,sticky="w")
        tk.Checkbutton(quiet_box,text="Autoriser les critiques pendant les heures calmes",variable=quiet_critical,bg=COLORS["soft_neutral"],activebackground=COLORS["soft_neutral"],selectcolor="white",font=("Segoe UI",8)).grid(row=2,column=0,columnspan=4,sticky="w",padx=10,pady=(6,8))
        tk.Label(body,text="Types de notifications",bg=COLORS["card"],fg=COLORS["text"],font=("Segoe UI",9,"bold")).pack(anchor="w",padx=18,pady=(3,4))
        cat_grid=tk.Frame(body,bg=COLORS["card"]); cat_grid.pack(fill="x",padx=18)
        labels={"system":"Système / PC","briefing":"Briefing","routine":"Routines","habits":"Habitudes","updates":"Mises à jour"}
        for i,key in enumerate(cat_vars): tk.Checkbutton(cat_grid,text=labels[key],variable=cat_vars[key],bg=COLORS["card"],activebackground=COLORS["card"],selectcolor="white",font=("Segoe UI",9)).grid(row=i//3,column=i%3,sticky="w",padx=(0,18),pady=3)
        def save():
            block.update({"mode":mode.get(),"summary_minutes":summary.get(),"critical_immediate":critical.get(),"repeat_cooldown_minutes":cooldown.get(),"quiet_hours":{"enabled":quiet_enabled.get(),"start":quiet_start.get(),"end":quiet_end.get(),"allow_critical":quiet_critical.get()},"categories":{k:v.get() for k,v in cat_vars.items()}}); save_preferences(prefs); popup.destroy(); self._refresh_personalization_state(); self.status_var.set("Préférences de notifications appliquées")
        tk.Button(body,text="Appliquer",command=save,relief="flat",bd=0,bg=COLORS["accent"],fg="white",font=("Segoe UI",9,"bold"),padx=14,pady=8,cursor="hand2").pack(anchor="e",padx=18,pady=(14,18))

    def _open_behavior_editor(self) -> None:
        prefs = load_preferences(); block = prefs["assistant"]; popup, body = self._dialog_base("Comportement de l’agent", "560x475")
        style = tk.StringVar(value=block.get("response_style", "natural")); emoji = tk.StringVar(value=block.get("emoji_level", "light")); detail = tk.StringVar(value=block.get("response_detail", "balanced")); quote = tk.BooleanVar(value=block.get("daily_quote", True)); suggestions = tk.BooleanVar(value=block.get("smart_suggestions", True))
        tk.Label(body, text="🤖 Comportement de l’agent", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=18, pady=(18, 12))
        tk.Label(body, text="Ton des réponses", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18)
        for value, label in (("natural", "Naturel"), ("professional", "Professionnel"), ("concise", "Très concis")):
            tk.Radiobutton(body, text=label, variable=style, value=value, bg=COLORS["card"], activebackground=COLORS["card"], selectcolor="white", font=("Segoe UI", 9)).pack(anchor="w", padx=18)
        tk.Label(body, text="Niveau d’emoji", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=(12, 0))
        for value, label in (("none", "Aucun"), ("light", "Léger"), ("expressive", "Plus expressif")):
            tk.Radiobutton(body, text=label, variable=emoji, value=value, bg=COLORS["card"], activebackground=COLORS["card"], selectcolor="white", font=("Segoe UI", 9)).pack(anchor="w", padx=18)
        tk.Label(body, text="Niveau de détail", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=(12, 0))
        detail_row = tk.Frame(body, bg=COLORS["card"]); detail_row.pack(anchor="w", padx=18)
        for value, label in (("short", "Court"), ("balanced", "Équilibré"), ("detailed", "Détaillé")):
            tk.Radiobutton(detail_row, text=label, variable=detail, value=value, bg=COLORS["card"], activebackground=COLORS["card"], selectcolor="white", font=("Segoe UI", 9)).pack(side="left", padx=(0, 12))
        tk.Checkbutton(body, text="Citation quotidienne", variable=quote, bg=COLORS["card"], activebackground=COLORS["card"], selectcolor="white", font=("Segoe UI", 9)).pack(anchor="w", padx=18, pady=(12, 0))
        tk.Checkbutton(body, text="Suggestions intelligentes", variable=suggestions, bg=COLORS["card"], activebackground=COLORS["card"], selectcolor="white", font=("Segoe UI", 9)).pack(anchor="w", padx=18)
        def save():
            block.update({"response_style": style.get(), "emoji_level": emoji.get(), "response_detail": detail.get(), "daily_quote": quote.get(), "smart_suggestions": suggestions.get()}); save_preferences(prefs); popup.destroy(); self._refresh_personalization_state(); self._refresh_suggestion_buttons()
        tk.Button(body, text="Appliquer", command=save, relief="flat", bd=0, bg=COLORS["accent"], fg="white", font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2").pack(anchor="e", padx=18, pady=(14, 18))

    def _open_learning_editor(self) -> None:
        prefs = load_preferences(); block = prefs["learning"]; popup, body = self._dialog_base("Apprentissage", "560x440")
        enabled = tk.BooleanVar(value=block.get("enabled", True)); mode = tk.StringVar(value=block.get("onboarding_mode", "hybrid")); continuous = tk.BooleanVar(value=block.get("continuous_learning", True))
        tk.Label(body, text="🧠 Apprentissage local", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=18, pady=(18, 5))
        tk.Label(body, text="AgentLocal observe uniquement les types d’actions et leurs cibles déjà exécutées via lui.", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9), wraplength=500, justify="left").pack(anchor="w", padx=18, pady=(0, 12))
        tk.Checkbutton(body, text="Activer l’apprentissage", variable=enabled, bg=COLORS["card"], activebackground=COLORS["card"], selectcolor="white", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18)
        for value, label in (("questions", "Questions uniquement"), ("observe", "Observation locale"), ("hybrid", "Questions + observation")):
            tk.Radiobutton(body, text=label, variable=mode, value=value, bg=COLORS["card"], activebackground=COLORS["card"], selectcolor="white", font=("Segoe UI", 9)).pack(anchor="w", padx=18, pady=2)
        tk.Checkbutton(body, text="Continuer à apprendre après la phase initiale de 2 jours", variable=continuous, bg=COLORS["card"], activebackground=COLORS["card"], selectcolor="white", font=("Segoe UI", 9)).pack(anchor="w", padx=18, pady=(10, 0))
        def save():
            block.update({"enabled": enabled.get(), "onboarding_mode": mode.get(), "continuous_learning": continuous.get(), "initial_days": 2}); save_preferences(prefs); popup.destroy(); self._refresh_personalization_state()
        tk.Button(body, text="Appliquer", command=save, relief="flat", bd=0, bg=COLORS["accent"], fg="white", font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2").pack(anchor="e", padx=18, pady=(18, 18))

    def _open_morning_editor(self) -> None:
        prefs = load_preferences(); block = prefs["morning"]; popup, body = self._dialog_base("Routine matinale", "540x360")
        enabled = tk.BooleanVar(value=block.get("enabled", True)); start = tk.StringVar(value=block.get("start_time", "07:00")); end = tk.StringVar(value=block.get("end_time", "09:30"))
        tk.Label(body, text="☀ Routine matinale", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=18, pady=(18, 6))
        tk.Checkbutton(body, text="Activer au premier déverrouillage", variable=enabled, bg=COLORS["card"], activebackground=COLORS["card"], selectcolor="white", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(0, 12))
        row = tk.Frame(body, bg=COLORS["card"]); row.pack(fill="x", padx=18)
        tk.Label(row, text="Début", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w"); tk.Entry(row, textvariable=start, width=8, relief="flat", bg=COLORS["soft_neutral"], font=("Segoe UI", 10)).grid(row=1, column=0, padx=(0, 20), ipady=6)
        tk.Label(row, text="Fin", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8, "bold")).grid(row=0, column=1, sticky="w"); tk.Entry(row, textvariable=end, width=8, relief="flat", bg=COLORS["soft_neutral"], font=("Segoe UI", 10)).grid(row=1, column=1, ipady=6)
        tk.Label(body, text="Format HH:MM. Le déclencheur reste obligatoirement le premier déverrouillage observé.", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8), wraplength=480, justify="left").pack(anchor="w", padx=18, pady=(12, 0))
        def save():
            block.update({"enabled": enabled.get(), "start_time": start.get().strip(), "end_time": end.get().strip()}); save_preferences(prefs); popup.destroy(); self._refresh_personalization_state()
        tk.Button(body, text="Appliquer", command=save, relief="flat", bd=0, bg=COLORS["accent"], fg="white", font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2").pack(anchor="e", padx=18, pady=(18, 18))

    def _open_briefing_editor(self) -> None:
        prefs = load_preferences(); block = prefs["briefing"]; popup, body = self._dialog_base("Briefing", "580x500")
        enabled = tk.BooleanVar(value=block.get("enabled", True)); topics = block.get("topics", {}); vars_ = {key: tk.BooleanVar(value=bool(topics.get(key, False))) for key in topics}
        labels = {"middle_east": "Moyen-Orient", "ukraine": "Ukraine", "oil_energy": "Pétrole & énergie", "technology": "Technologie", "military_defense": "Défense & militaire", "major_geopolitics": "Géopolitique majeure", "france_domestic": "France intérieure", "protests": "Manifestations", "sports": "Sport", "entertainment": "Culture / divertissement"}
        tk.Label(body, text="📰 Centres d’intérêt", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=18, pady=(18, 5))
        tk.Checkbutton(body, text="Activer le briefing", variable=enabled, bg=COLORS["card"], activebackground=COLORS["card"], selectcolor="white", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(0, 10))
        grid = tk.Frame(body, bg=COLORS["card"]); grid.pack(fill="x", padx=18)
        for i, key in enumerate(vars_):
            tk.Checkbutton(grid, text=labels.get(key, key), variable=vars_[key], bg=COLORS["card"], activebackground=COLORS["card"], selectcolor="white", font=("Segoe UI", 9)).grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 28), pady=4)
        tk.Label(body, text="Les choix filtrent les thèmes récupérés. Les données Web restent en lecture seule et ne deviennent jamais des commandes.", bg=COLORS["soft_success"], fg=COLORS["success"], font=("Segoe UI", 8, "bold"), wraplength=500, justify="left", padx=10, pady=8).pack(fill="x", padx=18, pady=(14, 0))
        def save():
            block["enabled"] = enabled.get(); block["topics"] = {key: var.get() for key, var in vars_.items()}; save_preferences(prefs); popup.destroy(); self._refresh_personalization_state(); self.weather_var.set("Météo : chargement à la demande"); self.news_var.set("Actualités : chargement à la demande")
        tk.Button(body, text="Appliquer", command=save, relief="flat", bd=0, bg=COLORS["accent"], fg="white", font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2").pack(anchor="e", padx=18, pady=(18, 18))

    def _open_declared_habits_editor(self) -> None:
        declared = load_declared_habits(); popup, body = self._dialog_base("Habitudes déclarées", "580x430")
        start = tk.StringVar(value=declared.get("typical_start_time", "07:30")); apps_current = set(declared.get("frequent_apps", [])); labels = [("edge", "Edge"), ("outlook", "Outlook"), ("teams", "Teams"), ("word", "Word"), ("excel", "Excel"), ("vscode", "VS Code"), ("github", "GitHub"), ("chatgpt", "ChatGPT"), ("whatsapp", "WhatsApp")]; vars_ = {k: tk.BooleanVar(value=k in apps_current) for k, _ in labels}
        tk.Label(body, text="📌 Habitudes déclarées", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=18, pady=(18, 10))
        tk.Label(body, text="Heure habituelle de début", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18); tk.Entry(body, textvariable=start, width=8, relief="flat", bg=COLORS["soft_neutral"], font=("Segoe UI", 10)).pack(anchor="w", padx=18, pady=(4, 12), ipady=6)
        grid = tk.Frame(body, bg=COLORS["card"]); grid.pack(fill="x", padx=18)
        for i, (key, label) in enumerate(labels): tk.Checkbutton(grid, text=label, variable=vars_[key], bg=COLORS["card"], activebackground=COLORS["card"], selectcolor="white", font=("Segoe UI", 9)).grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 18), pady=3)
        def save():
            declared["typical_start_time"] = start.get().strip(); declared["frequent_apps"] = [k for k, var in vars_.items() if var.get()]; save_declared_habits(declared); popup.destroy(); self._refresh_personalization_state()
        tk.Button(body, text="Enregistrer", command=save, relief="flat", bd=0, bg=COLORS["accent"], fg="white", font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2").pack(anchor="e", padx=18, pady=(18, 18))

    def _show_privacy_dialog(self) -> None:
        popup, body = self._dialog_base("Confidentialité", "590x420")
        tk.Label(body, text="🔒 Confidentialité & contrôle", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=18, pady=(18, 10))
        items = [
            ("✓", "Apprentissage local", "Les habitudes restent dans memory/ sur cette machine."),
            ("✓", "Aucune frappe clavier", "AgentLocal n’installe aucun keylogger et n’apprend pas à partir de vos frappes."),
            ("✓", "Aucun contenu privé", "Le contenu des e-mails, messages et mots de passe n’est pas utilisé pour apprendre."),
            ("✓", "Automatisation contrôlée", "Une habitude détectée devient une proposition ; elle n’est jamais activée automatiquement."),
        ]
        for icon, title, desc in items:
            row = tk.Frame(body, bg=COLORS["soft_success"]); row.pack(fill="x", padx=18, pady=4)
            tk.Label(row, text=icon, bg=COLORS["soft_success"], fg=COLORS["success"], font=("Segoe UI", 10, "bold")).pack(side="left", padx=(10, 8), pady=8)
            text = tk.Frame(row, bg=COLORS["soft_success"]); text.pack(side="left", fill="x", expand=True)
            tk.Label(text, text=title, bg=COLORS["soft_success"], fg=COLORS["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
            tk.Label(text, text=desc, bg=COLORS["soft_success"], fg=COLORS["muted"], font=("Segoe UI", 8), wraplength=460, justify="left").pack(anchor="w")
        tk.Button(body, text="Fermer", command=popup.destroy, relief="flat", bd=0, bg=COLORS["soft_neutral"], fg=COLORS["text"], font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2").pack(anchor="e", padx=18, pady=(14, 18))


    def _build_settings_page(self) -> None:
        page = self._new_page("settings")
        self._section_title(page, "Paramètres avancés", "Informations techniques. La personnalisation quotidienne se fait maintenant depuis la page Configuration.").grid(row=0, column=0, sticky="ew")

        card = tk.Frame(page, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        card.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        card.grid_columnconfigure(1, weight=1)
        rows = [
            ("Version", AGENTLOCAL_PATCH),
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
        tk.Button(actions, text="Securite et autorisations", command=lambda: open_security_center(self.root), relief="flat", bd=0, bg=COLORS["soft_accent"], fg=COLORS["accent"], font=("Segoe UI", 9, "bold"), padx=14, pady=8, cursor="hand2").pack(side="left", padx=(8, 0))

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
        if not is_onboarding_complete():
            try:
                self.root.after(120, lambda: self._maybe_show_onboarding(force=True))
            except tk.TclError:
                pass

    def _main_window_hidden(self) -> bool:
        try:
            return self.root.state() == "withdrawn" or not bool(self.root.winfo_viewable())
        except tk.TclError:
            return False

    def _show_background_alert_popup(self, items: list[dict]) -> None:
        if not bool(load_preferences().get("alerts", {}).get("background_notifications", True)):
            return
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
            "routines": "Routines locales et planifications confirmées",
            "habits": "Ce qu’AgentLocal apprend et propose",
            "configuration": "Profil, comportement, briefing et confidentialité",
            "settings": "Version, moteur et paramètres techniques avancés",
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
        if key == "habits":
            self._refresh_habits_page()
        if key == "configuration":
            self._refresh_configuration_page()
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
            self.home_greeting.configure(text=self._personalized_greeting_text())

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
        if not bool(load_preferences().get("assistant", {}).get("smart_suggestions", True)):
            for button in getattr(self, "suggestion_buttons", []):
                button.grid_remove()
            if hasattr(self, "suggestion_frame"):
                self.suggestion_frame.grid_remove()
            return
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
                stored = raise_alert(code, str(item.get("level", "info")), str(item.get("title", "Alerte")), str(item.get("message", "")), "system_monitor")
                if code not in self.notified_alert_codes and popup_allowed(stored):
                    notify_items.append(stored)
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
                try: mark_popup(item)
                except Exception: pass
        self._refresh_alerts_page()
        if notify_items and self._main_window_hidden():
            self._show_background_alert_popup(notify_items)

    def _notification_digest_loop(self) -> None:
        try:
            active = list_alerts("active", 100)
            if self._main_window_hidden() and digest_due(active):
                self._show_notification_digest_popup(active)
                mark_digest()
        except Exception as error:
            log_exception("gui.notification_digest", error)
        try:
            self.root.after(60000, self._notification_digest_loop)
        except tk.TclError:
            pass

    def _show_notification_digest_popup(self, items: list[dict]) -> None:
        if not items:
            return
        popup = tk.Toplevel(self.root); popup.title("AgentLocal - Résumé des notifications"); popup.geometry("540x320"); popup.resizable(False, False); popup.configure(bg=COLORS["bg"])
        try:
            popup.attributes("-topmost", True); popup.after(1000, lambda: popup.attributes("-topmost", False))
        except tk.TclError:
            pass
        card = tk.Frame(popup, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1); card.pack(fill="both", expand=True, padx=16, pady=16)
        critical = sum(1 for x in items if x.get("level") == "critical"); warning = sum(1 for x in items if x.get("level") == "warning"); info = sum(1 for x in items if x.get("level") == "info")
        tk.Label(card, text="🔔 Résumé AgentLocal", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=16, pady=(16,4))
        tk.Label(card, text=f"{len(items)} alerte(s) actives · {critical} critique(s) · {warning} avertissement(s) · {info} information(s)", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=16)
        for item in items[:4]:
            level = str(item.get("level", "info")); symbol = "🔴" if level == "critical" else ("⚠" if level == "warning" else "ℹ")
            tk.Label(card, text=f"{symbol} {item.get('title','Alerte')}", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9, "bold"), wraplength=470, justify="left").pack(anchor="w", padx=16, pady=(8,0))
        buttons = tk.Frame(card, bg=COLORS["card"]); buttons.pack(fill="x", padx=16, pady=(16,14))
        tk.Button(buttons, text="Voir les alertes", command=lambda:(popup.destroy(), self.reveal_main("alerts")), relief="flat", bd=0, bg=COLORS["accent"], fg="white", font=("Segoe UI",9,"bold"), padx=12, pady=7, cursor="hand2").pack(side="left")
        tk.Button(buttons, text="Fermer", command=popup.destroy, relief="flat", bd=0, bg=COLORS["soft_neutral"], fg=COLORS["muted"], font=("Segoe UI",9), padx=12, pady=7, cursor="hand2").pack(side="right")

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
    _set_windows_app_id()
    guard = InstanceGuard()
    if guard.already_running:
        if not start_hidden:
            focus_existing_window()
        guard.close()
        return
    root = tk.Tk()
    AgentLocalGUI(root, start_hidden=start_hidden)
    if not start_hidden:
        _show_startup_splash(root)
    try:
        root.mainloop()
    finally:
        guard.close()


if __name__ == "__main__":
    main()
