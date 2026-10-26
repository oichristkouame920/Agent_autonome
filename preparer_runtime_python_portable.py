"""Construit localement un runtime Python portable pour AgentLocal.

A executer sur Windows depuis le dossier AgentLocal. Le script copie le Python
reel sous-jacent a l'environnement courant dans runtime/python puis installe
les dependances depuis vendor/wheels. Aucun chemin absolu n'est conserve.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from project_paths import PROJECT_ROOT, get_project_path
from portable_runtime import offline_wheels_dir, requirements_file


def _copytree_filtered(src: Path, dst: Path, *, exclude=()):
    excluded = {x.casefold() for x in exclude}

    def ignore(_directory, names):
        return [name for name in names if name.casefold() in excluded]

    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore)


def _copy_runtime(base: Path, destination: Path):
    destination.mkdir(parents=True, exist_ok=True)

    # Executables et DLL principales de Python.
    for pattern in ("python*.exe", "python*.dll", "vcruntime*.dll"):
        for source in base.glob(pattern):
            if source.is_file():
                shutil.copy2(source, destination / source.name)

    for directory in ("DLLs", "tcl"):
        source = base / directory
        if source.is_dir():
            _copytree_filtered(source, destination / directory)

    lib_source = base / "Lib"
    if not lib_source.is_dir():
        raise RuntimeError(f"Bibliotheque standard Python introuvable : {lib_source}")
    _copytree_filtered(lib_source, destination / "Lib", exclude=("site-packages", "__pycache__"))
    (destination / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)

    for optional in ("LICENSE.txt", "LICENSE"):
        source = base / optional
        if source.is_file():
            shutil.copy2(source, destination / source.name)


def _portable_python(destination: Path) -> Path:
    exe = destination / "python.exe"
    if not exe.is_file():
        raise RuntimeError("python.exe n'a pas ete copie dans le runtime portable.")
    return exe


def _install_requirements(destination: Path, allow_online: bool):
    req = requirements_file()
    if not req.is_file():
        raise RuntimeError(f"requirements.txt introuvable : {req}")

    target = destination / "Lib" / "site-packages"
    wheels = offline_wheels_dir()
    wheel_files = list(wheels.glob("*.whl")) if wheels.is_dir() else []

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--target",
        str(target),
        "-r",
        str(req),
    ]

    if wheel_files:
        command[5:5] = ["--no-index", "--find-links", str(wheels)]
    elif not allow_online:
        raise RuntimeError(
            "Aucun wheel hors ligne n'est present dans vendor/wheels. "
            "Lance d'abord preparer_dependances_offline.bat, ou relance avec --allow-online."
        )

    subprocess.run(command, cwd=PROJECT_ROOT, check=True, shell=False)


def _verify(destination: Path):
    python_exe = _portable_python(destination)
    code = "import tkinter, psutil, pypdf, sys; print(sys.version); print('PORTABLE_OK')"
    completed = subprocess.run(
        [str(python_exe), "-c", code],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        shell=False,
    )
    if completed.returncode != 0 or "PORTABLE_OK" not in (completed.stdout or ""):
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"Le runtime Python portable ne passe pas le test : {detail[-1000:]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Recreer runtime/python s'il existe deja.")
    parser.add_argument(
        "--allow-online",
        action="store_true",
        help="Autoriser pip a Internet si vendor/wheels est vide.",
    )
    args = parser.parse_args()

    if os.name != "nt":
        raise SystemExit("Ce preparateur de runtime portable cible Windows 10/11.")

    destination = get_project_path("python_runtime")
    if destination.exists() and any(destination.iterdir()):
        if not args.force:
            raise SystemExit(
                "runtime/python contient deja des fichiers. Utilise --force pour le reconstruire."
            )
        shutil.rmtree(destination)

    base = Path(sys.base_prefix).resolve()
    print(f"Source Python : {base}")
    print(f"Destination   : {destination}")
    _copy_runtime(base, destination)
    _install_requirements(destination, allow_online=args.allow_online)
    _verify(destination)
    print("RUNTIME PYTHON PORTABLE PRET")


if __name__ == "__main__":
    main()
