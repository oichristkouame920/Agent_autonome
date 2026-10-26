from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

from runtime_resilience import startup_health_report
from verifier_runtime_v11_2 import run_checks as run_runtime_checks


def run_checks(*, startup=False, quiet=False):
    runtime_code = run_runtime_checks(strict_portable=False, quiet=True)
    report = startup_health_report()

    errors = []
    warnings = []
    oks = []

    for item in report.get("checks", []):
        status = item.get("status")
        text = f"{item.get('name')} - {item.get('detail')}"
        if status == "critical":
            errors.append(text)
        elif status == "warning":
            warnings.append(text)
        else:
            oks.append(text)

    if runtime_code == 2:
        errors.append("le diagnostic runtime V11.2 contient une erreur structurelle")
    elif runtime_code == 1:
        warnings.append("le diagnostic runtime V11.2 contient un avertissement")

    if not quiet:
        for value in oks:
            print(f"OK - {value}")
        for value in warnings:
            print(f"ATTENTION - {value}")
        for value in errors:
            print(f"ERREUR - {value}")

        if errors:
            print("\nV11.3 RESILIENCE : ECHEC - DEMARRAGE EN MODE SUR")
        elif warnings:
            print("\nV11.3 RESILIENCE : OPERATIONNEL EN MODE DEGRADE")
        else:
            print("\nV11.3 RESILIENCE : OPERATIONNEL")

    code = 2 if errors else (1 if warnings else 0)
    if startup and code == 1:
        return 0
    return code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--startup", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    raise SystemExit(run_checks(startup=args.startup, quiet=args.quiet))


if __name__ == "__main__":
    main()
