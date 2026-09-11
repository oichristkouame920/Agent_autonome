"""Interface graphique légère pour AgentLocal.

Objectifs :
- Windows 10/11 64 bits.
- Faible empreinte mémoire pour les machines avec 4 Go de RAM.
- Aucune dépendance graphique externe : Tkinter/ttk uniquement.
- Une seule commande exécutée à la fois.
- Aucun gain d'autonomie : toutes les actions continuent de passer par agent.py.
"""

from __future__ import annotations

import queue
import sys
import threading
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

import agent  # noqa: E402


APP_TITLE = "AgentLocal"
MAX_COMMAND_LENGTH = 2000
POLL_INTERVAL_MS = 80


# L'interface ne doit pas remplir une console de messages de debug.
# Cela ne change ni le backend, ni les validations, ni les permissions.
agent.DEBUG = False


def normalize_user_command(value: str) -> str:
    """Nettoie uniquement les bords sans réécrire la demande utilisateur."""
    if not isinstance(value, str):
        return ""
    return value.strip()


def get_runtime_summary() -> tuple[str, str]:
    """Lit la configuration sans charger volontairement un modèle LLM."""
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


class AgentLocalGUI:
    """Fenêtre principale, volontairement simple et peu gourmande."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.result_queue: queue.Queue[tuple[str, str]] = queue.Queue(maxsize=1)
        self.worker: threading.Thread | None = None
        self.busy = False

        self.command_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Prêt")
        self.backend_var = tk.StringVar()
        self.learning_var = tk.StringVar()

        self._configure_window()
        self._configure_styles()
        self._build_interface()
        self._refresh_runtime_summary()

        self.root.after(POLL_INTERVAL_MS, self._poll_worker_result)
        self.command_entry.focus_set()

    def _configure_window(self) -> None:
        self.root.title(APP_TITLE)
        self.root.geometry("820x560")
        self.root.minsize(700, 460)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)

        # Les thèmes natifs disponibles sont privilégiés pour limiter les coûts.
        available = set(style.theme_names())
        for candidate in ("vista", "xpnative", "clam", "default"):
            if candidate in available:
                try:
                    style.theme_use(candidate)
                    break
                except tk.TclError:
                    continue

        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 9))
        style.configure("Status.TLabel", font=("Segoe UI", 9))
        style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 7))
        style.configure("Secondary.TButton", font=("Segoe UI", 9), padding=(10, 7))

    def _build_interface(self) -> None:
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text=APP_TITLE, style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Assistant local Windows - actions uniquement sur commande explicite",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        status_frame = ttk.Frame(outer)
        status_frame.grid(row=1, column=0, sticky="ew", pady=(12, 10))
        status_frame.columnconfigure(0, weight=1)
        status_frame.columnconfigure(1, weight=1)

        ttk.Label(status_frame, textvariable=self.backend_var, style="Status.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(status_frame, textvariable=self.learning_var, style="Status.TLabel").grid(
            row=0, column=1, sticky="e"
        )

        conversation_frame = ttk.LabelFrame(outer, text="Échanges", padding=8)
        conversation_frame.grid(row=2, column=0, sticky="nsew")
        conversation_frame.rowconfigure(0, weight=1)
        conversation_frame.columnconfigure(0, weight=1)

        self.conversation = ScrolledText(
            conversation_frame,
            wrap="word",
            state="disabled",
            font=("Segoe UI", 10),
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=10,
            undo=False,
            maxundo=0,
        )
        self.conversation.grid(row=0, column=0, sticky="nsew")
        self.conversation.tag_configure("user", font=("Segoe UI", 10, "bold"), spacing1=7)
        self.conversation.tag_configure("agent", font=("Segoe UI", 10), spacing1=4, spacing3=8)
        self.conversation.tag_configure("error", font=("Segoe UI", 10, "bold"), spacing1=4, spacing3=8)

        input_frame = ttk.Frame(outer)
        input_frame.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        input_frame.columnconfigure(0, weight=1)

        self.command_entry = ttk.Entry(
            input_frame,
            textvariable=self.command_var,
            font=("Segoe UI", 11),
        )
        self.command_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=4)
        self.command_entry.bind("<Return>", self._on_enter)

        self.execute_button = ttk.Button(
            input_frame,
            text="Exécuter",
            style="Action.TButton",
            command=self.execute_command,
        )
        self.execute_button.grid(row=0, column=1, padx=(0, 6))

        self.clear_button = ttk.Button(
            input_frame,
            text="Effacer",
            style="Secondary.TButton",
            command=self.clear_conversation,
        )
        self.clear_button.grid(row=0, column=2)

        help_frame = ttk.Frame(outer)
        help_frame.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        help_frame.columnconfigure(0, weight=1)

        ttk.Label(
            help_frame,
            text="Exemple : Mets VS Code à gauche   |   Entrée = exécuter   |   Ctrl+L = effacer",
            style="Subtitle.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(help_frame, textvariable=self.status_var, style="Status.TLabel").grid(
            row=0, column=1, sticky="e"
        )

        self.root.bind("<Control-l>", self._on_clear_shortcut)
        self.root.bind("<Control-L>", self._on_clear_shortcut)

        self._append_agent(
            "Bonjour. Écris simplement ce que tu veux faire. "
            "Je n'exécute que les actions explicitement autorisées."
        )

    def _refresh_runtime_summary(self) -> None:
        backend_text, learning_text = get_runtime_summary()
        self.backend_var.set(backend_text)
        self.learning_var.set(learning_text)

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

    def _set_busy(self, value: bool) -> None:
        self.busy = value
        state = "disabled" if value else "normal"
        self.command_entry.configure(state=state)
        self.execute_button.configure(state=state)
        self.clear_button.configure(state=state)
        self.status_var.set("Traitement..." if value else "Prêt")
        self.root.config(cursor="watch" if value else "")

        if not value:
            self.command_entry.focus_set()

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

        command = normalize_user_command(self.command_var.get())
        if not command:
            self.status_var.set("Écris une commande")
            self.command_entry.focus_set()
            return

        if len(command) > MAX_COMMAND_LENGTH:
            messagebox.showwarning(
                APP_TITLE,
                f"La commande est trop longue. Maximum : {MAX_COMMAND_LENGTH} caractères.",
                parent=self.root,
            )
            return

        self.command_var.set("")
        self._append_user(command)
        self._set_busy(True)

        self.worker = threading.Thread(
            target=self._process_command_worker,
            args=(command,),
            daemon=True,
            name="AgentLocalCommand",
        )
        self.worker.start()

    def _process_command_worker(self, command: str) -> None:
        try:
            result = agent.process_instruction(command)
            if not isinstance(result, str):
                result = str(result)
            self.result_queue.put_nowait(("ok", result))
        except Exception as error:
            # L'interface ne révèle pas de trace complète ni de détails sensibles.
            try:
                self.result_queue.put_nowait(
                    ("error", f"Une erreur locale a empêché le traitement : {error}")
                )
            except queue.Full:
                pass

    def _poll_worker_result(self) -> None:
        try:
            kind, text = self.result_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            if kind == "ok":
                self._append_agent(text)
            else:
                self._append_error(text)
            self._set_busy(False)

        try:
            self.root.after(POLL_INTERVAL_MS, self._poll_worker_result)
        except tk.TclError:
            pass

    def clear_conversation(self) -> None:
        if self.busy:
            return
        self.conversation.configure(state="normal")
        self.conversation.delete("1.0", "end")
        self.conversation.configure(state="disabled")
        self.status_var.set("Affichage effacé")
        self.command_entry.focus_set()

    def close(self) -> None:
        if self.busy:
            should_close = messagebox.askyesno(
                APP_TITLE,
                "Une commande est en cours. Fermer quand même l'interface ?",
                parent=self.root,
            )
            if not should_close:
                return
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    AgentLocalGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
