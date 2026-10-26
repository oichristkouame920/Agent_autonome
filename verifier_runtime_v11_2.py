from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import project_paths
import portable_runtime
from backends import llama_backend


def _absolute_any_platform(value: str) -> bool:
    raw = str(value or "").strip()
    return Path(raw).is_absolute() or PureWindowsPath(raw).is_absolute() or bool(PureWindowsPath(raw).drive)


def _walk_strings(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)
    elif isinstance(value, str):
        yield value


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_checks(strict_portable=False, quiet=False):
    errors = []
    warnings = []
    oks = []

    for name in ("config", "models", "tools", "llama_runtime", "runtime", "python_runtime", "vendor", "wheels", "memory", "logs"):
        try:
            resolved = project_paths.get_project_path(name)
        except Exception as exc:
            errors.append(f"Chemin {name} invalide : {exc}")
        else:
            try:
                resolved.resolve().relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"Chemin {name} sort de la racine AgentLocal : {resolved}")
            else:
                oks.append(f"chemin relatif {name}")

    for filename in ("paths.json", "runtime.json", "models.json"):
        path = ROOT / "config" / filename
        if not path.is_file():
            errors.append(f"Configuration manquante : config/{filename}")
            continue
        try:
            data = _load_json(path)
        except Exception as exc:
            errors.append(f"JSON invalide {filename} : {exc}")
            continue
        for text in _walk_strings(data):
            if _absolute_any_platform(text):
                errors.append(f"Chemin absolu interdit dans {filename} : {text}")
        oks.append(f"{filename} portable")

    req = portable_runtime.requirements_file()
    if req.is_file():
        oks.append("requirements.txt trouve")
    else:
        errors.append("requirements.txt est introuvable")

    # Le Python qui execute ce verificateur doit deja avoir les dependances utiles.
    for module_name in ("tkinter", "psutil", "pypdf"):
        try:
            __import__(module_name)
        except Exception as exc:
            errors.append(f"Dependance Python indisponible : {module_name} ({exc})")
        else:
            oks.append(f"dependance Python {module_name}")

    portable = project_paths.get_project_path("python_runtime") / "python.exe"
    if portable.is_file():
        ok, detail = portable_runtime.probe_python(portable)
        if ok:
            oks.append("runtime Python portable operationnel")
        else:
            errors.append(f"runtime Python portable present mais inutilisable : {detail}")
    elif strict_portable:
        errors.append("runtime/python/python.exe absent en mode strict portable")
    else:
        warnings.append("runtime Python portable absent : .venv ou Python systeme restera utilise")

    wheel_dir = portable_runtime.offline_wheels_dir()
    wheel_count = len(list(wheel_dir.glob("*.whl"))) if wheel_dir.is_dir() else 0
    if wheel_count:
        oks.append(f"cache offline Python : {wheel_count} wheel(s)")
    else:
        warnings.append("vendor/wheels est vide : recreer .venv hors connexion ne sera pas possible tant que le cache n'est pas prepare")

    active_name, model, _ = llama_backend.get_active_model_config()
    if not active_name or model is None:
        warnings.append("aucun modele actif valide; backend deterministe seulement")
    else:
        if model["path"].is_file():
            oks.append(f"modele actif trouve : {active_name}")
        else:
            warnings.append(f"modele GGUF absent : {model['path'].relative_to(ROOT)}")
        missing_companions = [p for p in model.get("companion_paths", []) if not p.is_file()]
        if model.get("mmproj_path") and not model["mmproj_path"].is_file():
            missing_companions.append(model["mmproj_path"])
        if missing_companions:
            warnings.append("fichier(s) annexe(s) du modele absent(s) : " + ", ".join(str(p.relative_to(ROOT)) for p in missing_companions))
        elif model.get("companion_paths") or model.get("mmproj_path"):
            oks.append("fichiers annexes du modele trouves")

    llama_dir, llama_exe, _, _ = portable_runtime.llama_runtime_paths()
    if not llama_dir.is_dir() or not llama_exe.is_file():
        warnings.append("runtime llama.cpp incomplet ou absent; fallback deterministe disponible")
    else:
        ok, detail = portable_runtime.probe_llama_runtime()
        if ok:
            oks.append("runtime llama.cpp operationnel (DLL incluses)")
        else:
            warnings.append(f"runtime llama.cpp present mais non operationnel : {detail}")

    if not quiet:
        for message in oks:
            print(f"OK - {message}")
        for message in warnings:
            print(f"ATTENTION - {message}")
        for message in errors:
            print(f"ERREUR - {message}")

        if errors:
            print("\nV11.2 PORTABILITE RUNTIME : ECHEC")
        elif warnings:
            print("\nV11.2 PORTABILITE RUNTIME : OK AVEC AVERTISSEMENTS")
        else:
            print("\nV11.2 PORTABILITE RUNTIME : OK")

    return 2 if errors else (1 if warnings else 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict-portable", action="store_true")
    parser.add_argument("--startup", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    code = run_checks(strict_portable=args.strict_portable, quiet=args.quiet)
    # Au demarrage, les avertissements (ex: modele absent) ne doivent pas bloquer
    # le backend deterministe. Seules les erreurs structurelles sont fatales.
    if args.startup and code == 1:
        code = 0
    raise SystemExit(code)


if __name__ == "__main__":
    main()
