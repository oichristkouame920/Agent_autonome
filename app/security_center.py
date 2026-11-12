"""Centre de securite AgentLocal : privilege minimal et elevation UAC ponctuelle.

Fonctionnement :
- AgentLocal reste en mode utilisateur standard.
- La preparation est faite une seule fois, dans des parametres locaux.
- Chaque demande UAC concerne UNE action fixe, confirmee explicitement.
- LLM, routines et commandes externes n'ont aucun point d'entree d'elevation.
- Ni PowerShell arbitraire, ni elevation permanente, ni suppression de l'UAC.
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

ROOT_DIR = Path(__file__).resolve().parents[1]
SETTINGS_FILE = ROOT_DIR / "config" / "security_center.json"
ADMIN_SCRIPT = Path(__file__).resolve().with_name("admin_tasks.py")
DEFAULT_SETTINGS = {"schema_version": 1, "allow_elevation_requests": False}
ALLOWED_REQUESTS = frozenset({"flush_dns_cache"})


def load_settings() -> dict:
    result = dict(DEFAULT_SETTINGS)
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and type(raw.get("allow_elevation_requests")) is bool:
            result["allow_elevation_requests"] = raw["allow_elevation_requests"]
    except (OSError, UnicodeError, json.JSONDecodeError):
        pass
    return result


def save_settings(allow_elevation_requests: bool) -> dict:
    if type(allow_elevation_requests) is not bool:
        raise ValueError("Configuration invalide.")
    settings = {"schema_version": 1, "allow_elevation_requests": allow_elevation_requests}
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="agentlocal_security_", suffix=".tmp", dir=SETTINGS_FILE.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(settings, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, SETTINGS_FILE)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return settings


def status() -> dict:
    try:
        from admin_tasks import is_windows_admin
        elevated = is_windows_admin()
    except ImportError:
        elevated = False
    policy = {}
    try:
        policy = json.loads((ROOT_DIR / "config" / "permissions.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        pass
    apps = policy.get("application_policy", {}) if isinstance(policy, dict) else {}
    shell = policy.get("shell", {}) if isinstance(policy, dict) else {}
    return {
        "windows": sys.platform == "win32",
        "administrator": elevated,
        "one_shot_requests_enabled": load_settings()["allow_elevation_requests"],
        "arbitrary_shell_disabled": shell.get("powershell_arbitrary") is False and shell.get("cmd_arbitrary") is False,
        "agent_elevation_disabled": apps.get("allow_elevation") is False,
    }


def request_one_shot_elevation(action_id: str, *, explicit_confirmation: bool = False) -> tuple[bool, str]:
    """Ne peut etre appele qu'apres un clic et une confirmation explicites de l'utilisateur.

    Aucun argument de shell, commande, URL, chemin executif ou texte IA n'est accepte.
    Retourne uniquement le statut de lancement UAC, PAS le resultat de la tache.
    """
    if action_id not in ALLOWED_REQUESTS:
        return False, "Action refusee : operation non autorisee."
    if not explicit_confirmation:
        return False, "Confirmation utilisateur indispensable."
    if not load_settings()["allow_elevation_requests"]:
        return False, "Active d'abord les demandes ponctuelles dans le centre de securite."
    if sys.platform != "win32":
        return False, "Elevation disponible uniquement sous Windows."
    if not ADMIN_SCRIPT.is_file():
        return False, "Module de securite introuvable."
    # Aucune creation de tache planifiee, service, persistence ou process admin resident.
    args = subprocess.list2cmdline(["-I", "-B", str(ADMIN_SCRIPT), "--action", action_id])
    try:
        # ShellExecuteW(run as) presente l'UAC Windows; aucun bypass.
        rc = int(ctypes.windll.shell32.ShellExecuteW(
            None, "runas", str(Path(sys.executable).resolve()), args, str(ROOT_DIR), 1
        ))
    except (AttributeError, OSError, ValueError):
        return False, "Impossible de presenter la demande UAC Windows."
    if rc <= 32:
        return False, "Operation non demarree (UAC refuse ou erreur Windows)."
    return True, "Operation demandee a Windows. Le resultat sera affiche par la fenetre elevee."


class SecurityCenter:
    def __init__(self, parent: tk.Misc | None = None):
        self.owns_window = parent is None
        self.root = tk.Tk() if self.owns_window else tk.Toplevel(parent)
        self.root.title("AgentLocal - Securite et autorisations")
        self.root.geometry("650x460")
        self.root.minsize(590, 430)
        self.root.configure(bg="#F6F8FC")
        self.enabled = tk.BooleanVar(master=self.root, value=load_settings()["allow_elevation_requests"])
        self.info = tk.StringVar(master=self.root)
        frame = ttk.Frame(self.root, padding=22)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Securite et autorisations", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Une configuration initiale, puis une autorisation Windows seulement si necessaire.", wraplength=580).pack(anchor="w", pady=(6, 14))
        ttk.Checkbutton(frame, text="Permettre les demandes UAC ponctuelles (desactive par defaut)", variable=self.enabled).pack(anchor="w", pady=6)
        ttk.Label(frame, text="Cette option n'accorde aucun droit administrateur permanent. L'agent IA ne peut pas demander librement une elevation.", wraplength=580).pack(anchor="w", pady=(3, 12))
        row = ttk.Frame(frame); row.pack(anchor="w", pady=(0, 14))
        ttk.Button(row, text="Enregistrer mes preferences", command=self.save).pack(side="left")
        ttk.Button(row, text="Verifier les autorisations", command=self.refresh).pack(side="left", padx=10)
        ttk.Separator(frame).pack(fill="x", pady=9)
        ttk.Label(frame, text="Action Windows ponctuelle autorisee", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(8, 4))
        ttk.Label(frame, text="Vider le cache DNS : operation systeme limitee, possible demande UAC. Aucune commande personnalisable.", wraplength=580).pack(anchor="w", pady=(0, 7))
        ttk.Button(frame, text="Vider le cache DNS...", command=self.flush_dns).pack(anchor="w", pady=(0, 14))
        ttk.Separator(frame).pack(fill="x", pady=8)
        ttk.Label(frame, textvariable=self.info, justify="left", wraplength=580).pack(anchor="w", pady=8)
        self.refresh()

    def save(self):
        try:
            save_settings(bool(self.enabled.get()))
            self.refresh()
            messagebox.showinfo("AgentLocal", "Preferences enregistrees. Aucun droit admin permanent n'a ete accorde.", parent=self.root)
        except OSError:
            messagebox.showerror("AgentLocal", "Impossible d'enregistrer les preferences locales.", parent=self.root)

    def refresh(self):
        info = status()
        lines = [
            "Windows : " + ("detecte" if info["windows"] else "non detecte"),
            "Processus actuel : " + ("administrateur" if info["administrator"] else "utilisateur standard"),
            "Demandes UAC ponctuelles : " + ("activees" if info["one_shot_requests_enabled"] else "desactivees"),
            "Commandes shell arbitraires : " + ("bloquees" if info["arbitrary_shell_disabled"] else "configuration a verifier"),
            "Elevation libre de l'agent : " + ("bloquee" if info["agent_elevation_disabled"] else "configuration a verifier"),
        ]
        self.info.set("\n".join(lines))

    def flush_dns(self):
        if not load_settings()["allow_elevation_requests"]:
            messagebox.showwarning("AgentLocal", "Enregistre d'abord l'activation des demandes UAC ponctuelles.", parent=self.root)
            return
        if not messagebox.askyesno(
            "AgentLocal - confirmation",
            "Autoriser uniquement le vidage du cache DNS Windows ?\nWindows pourra afficher une demande UAC.",
            parent=self.root,
        ):
            return
        ok, msg = request_one_shot_elevation("flush_dns_cache", explicit_confirmation=True)
        (messagebox.showinfo if ok else messagebox.showwarning)("AgentLocal", msg, parent=self.root)


def open_security_center(parent: tk.Misc | None = None):
    center = SecurityCenter(parent)
    if center.owns_window:
        center.root.mainloop()
    return center


if __name__ == "__main__":
    open_security_center()
