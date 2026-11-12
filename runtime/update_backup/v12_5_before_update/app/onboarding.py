"""Assistant visuel de premier démarrage AgentLocal V12.4."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from user_profile import (
    begin_onboarding,
    complete_onboarding,
    default_machine_name,
    load_declared_habits,
    load_preferences,
    load_profile,
)

APP_CHOICES = [
    ("edge", "Edge"), ("outlook", "Outlook"), ("teams", "Teams"),
    ("word", "Word"), ("excel", "Excel"), ("powerpoint", "PowerPoint"),
    ("vscode", "VS Code"), ("github", "GitHub"), ("chatgpt", "ChatGPT"),
    ("whatsapp", "WhatsApp"),
]

TOPIC_CHOICES = [
    ("middle_east", "Moyen-Orient"), ("ukraine", "Ukraine"),
    ("oil_energy", "Pétrole & énergie"), ("technology", "Technologie"),
    ("military_defense", "Défense"), ("major_geopolitics", "Géopolitique"),
    ("sports", "Sport"), ("entertainment", "Culture / divertissement"),
]


class OnboardingWizard:
    def __init__(self, parent: tk.Misc, colors: dict, *, on_complete=None) -> None:
        self.parent = parent
        self.colors = colors
        self.on_complete = on_complete
        begin_onboarding()

        self.profile = load_profile()
        self.preferences = load_preferences()
        self.declared = load_declared_habits()
        self.step = 0

        self.display_name = tk.StringVar(value=self.profile.get("display_name", ""))
        self.machine_name = tk.StringVar(value=self.profile.get("machine_name") or default_machine_name())
        self.usage_mode = tk.StringVar(value=self.profile.get("usage_mode", "work"))
        self.learning_mode = tk.StringVar(value=self.preferences["learning"].get("onboarding_mode", "hybrid"))
        self.start_time = tk.StringVar(value=self.declared.get("typical_start_time", "07:30"))
        self.response_style = tk.StringVar(value=self.preferences["assistant"].get("response_style", "natural"))
        self.emoji_level = tk.StringVar(value=self.preferences["assistant"].get("emoji_level", "light"))
        self.daily_quote = tk.BooleanVar(value=bool(self.preferences["assistant"].get("daily_quote", True)))
        self.briefing_enabled = tk.BooleanVar(value=bool(self.preferences["briefing"].get("enabled", True)))
        self.app_vars = {key: tk.BooleanVar(value=key in self.declared.get("frequent_apps", [])) for key, _ in APP_CHOICES}
        topics = self.preferences["briefing"].get("topics", {})
        self.topic_vars = {key: tk.BooleanVar(value=bool(topics.get(key, False))) for key, _ in TOPIC_CHOICES}

        self.window = tk.Toplevel(parent)
        self.window.title("Bienvenue dans AgentLocal")
        self.window.geometry("820x610")
        self.window.minsize(760, 560)
        self.window.transient(parent)
        self.window.grab_set()
        self.window.configure(bg=colors["bg"])
        self.window.protocol("WM_DELETE_WINDOW", self._close_guarded)

        self.shell = tk.Frame(self.window, bg=colors["bg"])
        self.shell.pack(fill="both", expand=True, padx=28, pady=22)
        self.shell.grid_rowconfigure(1, weight=1)
        self.shell.grid_columnconfigure(0, weight=1)

        self._build_header()
        self.body = tk.Frame(self.shell, bg=colors["bg"])
        self.body.grid(row=1, column=0, sticky="nsew", pady=(16, 14))
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)
        self._build_footer()
        self._render_step()

        try:
            self.window.update_idletasks()
            x = parent.winfo_rootx() + max(0, (parent.winfo_width() - self.window.winfo_width()) // 2)
            y = parent.winfo_rooty() + max(0, (parent.winfo_height() - self.window.winfo_height()) // 2)
            self.window.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    def _build_header(self) -> None:
        header = tk.Frame(self.shell, bg=self.colors["bg"])
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        tk.Label(header, text="AgentLocal", bg=self.colors["bg"], fg=self.colors["text"], font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w")
        self.step_label = tk.Label(header, text="", bg=self.colors["soft_accent"], fg=self.colors["accent"], font=("Segoe UI", 8, "bold"), padx=10, pady=5)
        self.step_label.grid(row=0, column=1, sticky="e")
        self.progress = tk.Canvas(header, height=5, bg=self.colors["border"], highlightthickness=0)
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))

    def _build_footer(self) -> None:
        footer = tk.Frame(self.shell, bg=self.colors["bg"])
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(1, weight=1)
        self.back_btn = tk.Button(footer, text="← Retour", command=self._previous, relief="flat", bd=0, bg=self.colors["soft_neutral"], fg=self.colors["text"], font=("Segoe UI", 9, "bold"), padx=14, pady=9, cursor="hand2")
        self.back_btn.grid(row=0, column=0, sticky="w")
        self.next_btn = tk.Button(footer, text="Continuer →", command=self._next, relief="flat", bd=0, bg=self.colors["accent"], fg="white", activebackground=self.colors["accent_hover"], activeforeground="white", font=("Segoe UI", 9, "bold"), padx=16, pady=9, cursor="hand2")
        self.next_btn.grid(row=0, column=2, sticky="e")

    def _clear_body(self) -> tk.Frame:
        for child in self.body.winfo_children():
            child.destroy()
        frame = tk.Frame(self.body, bg=self.colors["bg"])
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        return frame

    def _title(self, parent, title: str, subtitle: str) -> None:
        tk.Label(parent, text=title, bg=self.colors["bg"], fg=self.colors["text"], font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(parent, text=subtitle, bg=self.colors["bg"], fg=self.colors["muted"], font=("Segoe UI", 10), wraplength=700, justify="left").pack(anchor="w", pady=(6, 18))

    def _card(self, parent, title: str, subtitle: str = "", *, selected_var=None, value=None, icon="•") -> tk.Frame:
        selected = bool(selected_var is not None and selected_var.get() == value)
        bg = self.colors["soft_accent"] if selected else self.colors["card"]
        border = self.colors["accent"] if selected else self.colors["border"]
        frame = tk.Frame(parent, bg=bg, highlightbackground=border, highlightthickness=2 if selected else 1, cursor="hand2")
        inner = tk.Frame(frame, bg=bg)
        inner.pack(fill="both", expand=True, padx=14, pady=12)
        tk.Label(inner, text=icon, bg=bg, fg=self.colors["accent"], font=("Segoe UI Emoji", 16)).pack(side="left", padx=(0, 10))
        texts = tk.Frame(inner, bg=bg); texts.pack(side="left", fill="both", expand=True)
        tk.Label(texts, text=title, bg=bg, fg=self.colors["text"], font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        if subtitle:
            tk.Label(texts, text=subtitle, bg=bg, fg=self.colors["muted"], font=("Segoe UI", 8), anchor="w", justify="left", wraplength=540).pack(fill="x", pady=(3, 0))
        if selected_var is not None:
            def choose(_event=None):
                selected_var.set(value)
                self._render_step()
            for widget in (frame, inner, texts):
                widget.bind("<Button-1>", choose)
            for child in inner.winfo_children():
                child.bind("<Button-1>", choose)
                try:
                    for grand in child.winfo_children():
                        grand.bind("<Button-1>", choose)
                except Exception:
                    pass
        return frame

    def _render_step(self) -> None:
        total = 6
        self.step_label.configure(text=f"Étape {self.step + 1} / {total}")
        self.progress.delete("all")
        self.progress.update_idletasks()
        width = max(100, self.progress.winfo_width())
        self.progress.create_rectangle(0, 0, width * ((self.step + 1) / total), 5, fill=self.colors["accent"], outline="")
        self.back_btn.configure(state="normal" if self.step > 0 else "disabled")
        self.next_btn.configure(text="Terminer ✓" if self.step == total - 1 else "Continuer →")
        renderer = [self._step_welcome, self._step_identity, self._step_usage, self._step_habits, self._step_preferences, self._step_summary][self.step]
        renderer()

    def _step_welcome(self) -> None:
        frame = self._clear_body()
        hero = tk.Frame(frame, bg=self.colors["card"], highlightbackground=self.colors["border"], highlightthickness=1)
        hero.pack(fill="both", expand=True)
        motif = tk.Canvas(hero, width=120, height=90, bg=self.colors["card"], highlightthickness=0)
        motif.pack(pady=(45, 10))
        motif.create_oval(12, 16, 62, 66, fill=self.colors["soft_accent"], outline="")
        motif.create_oval(48, 30, 94, 76, fill=self.colors["soft_lavender"], outline="")
        motif.create_oval(78, 10, 112, 44, fill=self.colors["soft_teal"], outline="")
        tk.Label(hero, text="Bienvenue dans AgentLocal 👋", bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 24, "bold")).pack()
        tk.Label(hero, text="Configurons un assistant local adapté à cette machine et à vos habitudes, sans envoyer vos données privées ailleurs.", bg=self.colors["card"], fg=self.colors["muted"], font=("Segoe UI", 10), wraplength=610, justify="center").pack(pady=(8, 18))
        badges = tk.Frame(hero, bg=self.colors["card"]); badges.pack()
        for label in ("🔒 Local", "🧠 Personnalisable", "✓ Actions contrôlées"):
            tk.Label(badges, text=label, bg=self.colors["soft_neutral"], fg=self.colors["muted"], font=("Segoe UI", 8, "bold"), padx=10, pady=5).pack(side="left", padx=4)

    def _step_identity(self) -> None:
        frame = self._clear_body()
        self._title(frame, "Faisons connaissance", "Ces informations restent sur cette machine et servent uniquement à personnaliser l’interface.")
        card = tk.Frame(frame, bg=self.colors["card"], highlightbackground=self.colors["border"], highlightthickness=1)
        card.pack(fill="x")
        tk.Label(card, text="Comment souhaitez-vous être appelé ?", bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(16, 5))
        tk.Entry(card, textvariable=self.display_name, font=("Segoe UI", 11), relief="flat", bg=self.colors["soft_neutral"], fg=self.colors["text"]).pack(fill="x", padx=18, ipady=8)
        tk.Label(card, text="Nom de cette machine", bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(16, 5))
        tk.Entry(card, textvariable=self.machine_name, font=("Segoe UI", 11), relief="flat", bg=self.colors["soft_neutral"], fg=self.colors["text"]).pack(fill="x", padx=18, pady=(0, 18), ipady=8)

    def _step_usage(self) -> None:
        frame = self._clear_body()
        self._title(frame, "Quel sera l’usage principal ?", "AgentLocal adapte ses raccourcis et la manière de présenter les informations selon ce contexte.")
        grid = tk.Frame(frame, bg=self.colors["bg"]); grid.pack(fill="x")
        for i, (value, title, desc, icon) in enumerate([
            ("work", "Travail", "Routines professionnelles, productivité et état du poste.", "💼"),
            ("personal", "Personnel", "Usage quotidien, fichiers et navigation personnelle.", "🏠"),
            ("mixed", "Mixte", "Un équilibre entre travail et usage personnel.", "◫"),
        ]):
            card = self._card(grid, title, desc, selected_var=self.usage_mode, value=value, icon=icon)
            card.pack(fill="x", pady=(0, 9))

    def _step_habits(self) -> None:
        frame = self._clear_body()
        self._title(frame, "Comment AgentLocal doit-il apprendre ?", "Le mode hybride est recommandé : quelques réponses maintenant, puis une observation locale des métadonnées d’actions pendant 2 jours.")
        modes = tk.Frame(frame, bg=self.colors["bg"]); modes.pack(fill="x")
        for value, title, desc, icon in [
            ("questions", "Questions uniquement", "Vous déclarez vos habitudes. Aucune phase d’observation initiale.", "💬"),
            ("observe", "Observer pendant 2 jours", "AgentLocal observe seulement les applications/sites lancés via lui, jamais les frappes ou contenus privés.", "👁"),
            ("hybrid", "Les deux — recommandé", "Une base immédiate, puis 2 jours pour affiner les propositions.", "🧠"),
        ]:
            self._card(modes, title, desc, selected_var=self.learning_mode, value=value, icon=icon).pack(fill="x", pady=(0, 7))

        details = tk.Frame(frame, bg=self.colors["card"], highlightbackground=self.colors["border"], highlightthickness=1)
        details.pack(fill="x", pady=(8, 0))
        tk.Label(details, text="Heure habituelle de début", bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=14, pady=12)
        tk.Entry(details, textvariable=self.start_time, width=8, font=("Segoe UI", 10), relief="flat", bg=self.colors["soft_neutral"]).grid(row=0, column=1, sticky="w", padx=8)
        tk.Label(details, text="Outils fréquents", bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="nw", padx=14, pady=(0, 12))
        apps = tk.Frame(details, bg=self.colors["card"]); apps.grid(row=1, column=1, sticky="w", padx=8, pady=(0, 12))
        for i, (key, label) in enumerate(APP_CHOICES):
            tk.Checkbutton(apps, text=label, variable=self.app_vars[key], bg=self.colors["card"], fg=self.colors["text"], activebackground=self.colors["card"], selectcolor="white", font=("Segoe UI", 8)).grid(row=i // 5, column=i % 5, sticky="w", padx=(0, 10), pady=2)

    def _step_preferences(self) -> None:
        frame = self._clear_body()
        self._title(frame, "Votre expérience AgentLocal", "Ces réglages restent modifiables à tout moment dans Configuration.")
        columns = tk.Frame(frame, bg=self.colors["bg"]); columns.pack(fill="both", expand=True)
        columns.grid_columnconfigure(0, weight=1); columns.grid_columnconfigure(1, weight=1)

        style = tk.Frame(columns, bg=self.colors["card"], highlightbackground=self.colors["border"], highlightthickness=1)
        style.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        tk.Label(style, text="💬 Style de l’assistant", bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(14, 8))
        for value, label in (("natural", "Naturel"), ("professional", "Professionnel"), ("concise", "Très concis")):
            tk.Radiobutton(style, text=label, variable=self.response_style, value=value, bg=self.colors["card"], activebackground=self.colors["card"], selectcolor="white", font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=2)
        tk.Label(style, text="Emoji", bg=self.colors["card"], fg=self.colors["muted"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(12, 3))
        for value, label in (("none", "Aucun"), ("light", "Léger"), ("expressive", "Expressif")):
            tk.Radiobutton(style, text=label, variable=self.emoji_level, value=value, bg=self.colors["card"], activebackground=self.colors["card"], selectcolor="white", font=("Segoe UI", 8)).pack(anchor="w", padx=14)
        tk.Checkbutton(style, text="Citation quotidienne", variable=self.daily_quote, bg=self.colors["card"], activebackground=self.colors["card"], selectcolor="white", font=("Segoe UI", 8)).pack(anchor="w", padx=14, pady=(10, 14))

        briefing = tk.Frame(columns, bg=self.colors["card"], highlightbackground=self.colors["border"], highlightthickness=1)
        briefing.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        tk.Checkbutton(briefing, text="📰 Briefing du matin", variable=self.briefing_enabled, bg=self.colors["card"], activebackground=self.colors["card"], selectcolor="white", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(14, 8))
        for key, label in TOPIC_CHOICES:
            tk.Checkbutton(briefing, text=label, variable=self.topic_vars[key], bg=self.colors["card"], activebackground=self.colors["card"], selectcolor="white", font=("Segoe UI", 8)).pack(anchor="w", padx=14, pady=1)

    def _step_summary(self) -> None:
        frame = self._clear_body()
        self._title(frame, "Tout est prêt", "Vérifiez le résumé. Vous pourrez tout modifier ensuite depuis la page Configuration.")
        card = tk.Frame(frame, bg=self.colors["card"], highlightbackground=self.colors["border"], highlightthickness=1)
        card.pack(fill="x")
        apps = [label for key, label in APP_CHOICES if self.app_vars[key].get()]
        topics = [label for key, label in TOPIC_CHOICES if self.topic_vars[key].get()]
        rows = [
            ("Nom", self.display_name.get().strip() or "Non renseigné"),
            ("Machine", self.machine_name.get().strip() or default_machine_name()),
            ("Usage", {"work": "Travail", "personal": "Personnel", "mixed": "Mixte"}.get(self.usage_mode.get(), "Travail")),
            ("Apprentissage", {"questions": "Questions", "observe": "Observation 2 jours", "hybrid": "Questions + observation 2 jours"}.get(self.learning_mode.get(), "Hybride")),
            ("Début habituel", self.start_time.get().strip() or "07:30"),
            ("Outils", ", ".join(apps[:6]) or "À découvrir"),
            ("Briefing", ", ".join(topics[:5]) if self.briefing_enabled.get() else "Désactivé"),
        ]
        for i, (label, value) in enumerate(rows):
            tk.Label(card, text=label, bg=self.colors["card"], fg=self.colors["muted"], font=("Segoe UI", 9, "bold")).grid(row=i, column=0, sticky="nw", padx=16, pady=(12 if i == 0 else 7, 12 if i == len(rows)-1 else 7))
            tk.Label(card, text=value, bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 9), wraplength=520, justify="left").grid(row=i, column=1, sticky="nw", padx=12, pady=(12 if i == 0 else 7, 12 if i == len(rows)-1 else 7))
        card.grid_columnconfigure(1, weight=1)
        privacy = tk.Frame(frame, bg=self.colors["soft_success"], highlightbackground="#CBE7D3", highlightthickness=1)
        privacy.pack(fill="x", pady=(12, 0))
        tk.Label(privacy, text="🔒 Apprentissage local : aucune frappe clavier, aucun mot de passe, aucun contenu privé n’est collecté pour apprendre vos habitudes.", bg=self.colors["soft_success"], fg=self.colors["success"], font=("Segoe UI", 8, "bold"), wraplength=700, justify="left").pack(anchor="w", padx=14, pady=10)

    def _validate_current(self) -> bool:
        if self.step == 1:
            if not self.machine_name.get().strip():
                messagebox.showwarning("AgentLocal", "Le nom de la machine est requis.", parent=self.window)
                return False
        if self.step == 3:
            value = self.start_time.get().strip()
            try:
                h, m = map(int, value.split(":"))
                if not (0 <= h <= 23 and 0 <= m <= 59):
                    raise ValueError
            except Exception:
                messagebox.showwarning("AgentLocal", "Utilisez une heure au format HH:MM, par exemple 07:30.", parent=self.window)
                return False
        return True

    def _next(self) -> None:
        if not self._validate_current():
            return
        if self.step < 5:
            self.step += 1
            self._render_step()
            return
        self._finish()

    def _previous(self) -> None:
        if self.step > 0:
            self.step -= 1
            self._render_step()

    def _finish(self) -> None:
        profile = dict(self.profile)
        profile.update({
            "display_name": self.display_name.get().strip(),
            "machine_name": self.machine_name.get().strip() or default_machine_name(),
            "usage_mode": self.usage_mode.get(),
        })
        prefs = self.preferences
        prefs["assistant"].update({
            "response_style": self.response_style.get(),
            "emoji_level": self.emoji_level.get(),
            "daily_quote": bool(self.daily_quote.get()),
        })
        mode = self.learning_mode.get()
        prefs["learning"].update({
            "enabled": mode in {"observe", "hybrid"},
            "onboarding_mode": mode,
            "initial_days": 2,
        })
        prefs["briefing"]["enabled"] = bool(self.briefing_enabled.get())
        for key, var in self.topic_vars.items():
            if key in prefs["briefing"]["topics"]:
                prefs["briefing"]["topics"][key] = bool(var.get())
        declared = dict(self.declared)
        declared["typical_start_time"] = self.start_time.get().strip()
        declared["frequent_apps"] = [key for key, var in self.app_vars.items() if var.get()]
        complete_onboarding(profile=profile, preferences=prefs, declared_habits=declared)
        try:
            self.window.grab_release()
        except tk.TclError:
            pass
        self.window.destroy()
        if callable(self.on_complete):
            self.on_complete()

    def _close_guarded(self) -> None:
        if messagebox.askyesno("AgentLocal", "Quitter la configuration maintenant ? Vous pourrez la reprendre plus tard.", parent=self.window):
            try:
                self.window.grab_release()
            except tk.TclError:
                pass
            self.window.destroy()
