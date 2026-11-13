#!/usr/bin/env python3
"""AgentLocal: diagnostic and safe tests across Windows Python environments.

Pure stdlib. No network/process actions beyond explicit dependency repair or
spawning the project's *test runner*. Never starts AgentLocal GUI/LLM.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / 'requirements.txt'
DEPENDENCIES = ('psutil', 'pypdf')
TIMEOUT_PROBE = 12
PROBE = r'''
import json, struct, sys
result = {"python":sys.version.split()[0], "bits":struct.calcsize('P')*8, "missing":[], "installed":{}}
for name in ('psutil', 'pypdf'):
    try:
        obj = __import__(name)
        result['installed'][name] = str(getattr(obj,'__version__', 'installed'))
    except Exception as exc:
        result['missing'].append(name)
print('AGENTLOCAL_ENV_JSON='+json.dumps(result, ensure_ascii=True))
'''


def candidates(root: Path = ROOT, current: str | None = None):
    """Runtime order matches AgentLocal.bat: portable, .venv, old venv, system."""
    items = [
        ('portable', root / 'runtime' / 'python' / 'python.exe'),
        ('venv', root / '.venv' / 'Scripts' / 'python.exe'),
        ('oldvenv', root / 'venv' / 'Scripts' / 'python.exe'),
    ]
    exe = current or sys.executable
    if exe:
        items.append(('system', Path(exe)))
    # Si le bootstrap vient d'un venv incomplet, tester aussi Python global.
    for external in (shutil.which('python.exe'), shutil.which('python')):
        if external:
            items.append(('system-path', Path(external)))
    seen = set()
    for label, exe_path in items:
        key = str(exe_path.resolve()) if exe_path.exists() else str(exe_path)
        if key not in seen:
            seen.add(key)
            yield label, exe_path


def probe(exe: Path, runner=subprocess.run):
    if not exe.is_file():
        return {'ok': False, 'reason': 'introuvable'}
    try:
        proc = runner([str(exe), '-c', PROBE], capture_output=True, text=True,
                      timeout=TIMEOUT_PROBE, cwd=str(ROOT))
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'ok': False, 'reason': type(exc).__name__}
    if proc.returncode:
        return {'ok': False, 'reason': 'Python ne demarre pas (code %s)' % proc.returncode}
    try:
        lines = [line.split('=', 1)[1] for line in proc.stdout.splitlines()
                 if line.startswith('AGENTLOCAL_ENV_JSON=')]
        details = json.loads(lines[-1])
    except (ValueError, IndexError, KeyError):
        return {'ok': False, 'reason': 'sonde Python invalide'}
    missing = details.get('missing') or []
    bits = details.get('bits')
    details['ok'] = not missing and bits == 64
    details['reason'] = ('dependencies: ' + ', '.join(missing)) if missing else (
        'Python 32 bits' if bits != 64 else 'OK')
    return details


def scan(root: Path = ROOT, current: str | None = None, runner=subprocess.run):
    return [(label, p, probe(p, runner)) for label, p in candidates(root, current)]


def select(root: Path = ROOT, current: str | None = None, runner=subprocess.run):
    for label, path, details in scan(root, current, runner):
        if details['ok']:
            return label, path, details
    return None


def available_memory():
    """Retourne la RAM disponible sous Windows, sans importer psutil."""
    if sys.platform != 'win32':
        return None
    try:
        import ctypes
        class Mem(ctypes.Structure):
            _fields_ = [('dwLength',ctypes.c_ulong),('dwMemoryLoad',ctypes.c_ulong),
                        ('ullTotalPhys',ctypes.c_ulonglong),('ullAvailPhys',ctypes.c_ulonglong),
                        ('ullTotalPageFile',ctypes.c_ulonglong),('ullAvailPageFile',ctypes.c_ulonglong),
                        ('ullTotalVirtual',ctypes.c_ulonglong),('ullAvailVirtual',ctypes.c_ulonglong),
                        ('ullAvailExtendedVirtual',ctypes.c_ulonglong)]
        mem = Mem()
        mem.dwLength = ctypes.sizeof(Mem)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
            return int(mem.ullTotalPhys), int(mem.ullAvailPhys)
    except (AttributeError, OSError, ValueError):
        return None
    return None


def show_doctor(root: Path = ROOT, current: str | None = None):
    print('=== AgentLocal - Diagnostic Python (sans installation) ===')
    memory = available_memory()
    if memory:
        total, avail = memory
        print('RAM physique : %.2f Go ; disponible : %.0f Mo' % (total/2**30,avail/2**20))
        if total <= 5 * 2**30 or avail < 1536 * 2**20:
            print('MODE PRUDENT: aucun test LLM reel ne sera lance par cet outil.')
    for label, path, info in scan(root, current):
        status = 'OK' if info['ok'] else 'NON PRET'
        print('%-8s %-9s %s' % (label, status, path))
        print('           %s' % info['reason'])
        if 'python' in info:
            print('           Python %s / %s bits' % (info['python'], info['bits']))
    selected = select(root, current)
    if selected:
        print('INTERPRETEUR CHOISI: %s (%s)' % (selected[1], selected[0]))
        print('INFO: pour les tests, eviter python -m unittest sans environnement explicite.')
        return 0
    print('AUCUN PYTHON PRET POUR LA SUITE COMPLETE.')
    print('REPARATION VOLONTAIRE: runtime\\TESTER_ENVIRONNEMENT.bat repair --online')
    print('OU HORS CONNEXION (si vendor\\wheels contient les wheels):')
    print('    runtime\\TESTER_ENVIRONNEMENT.bat repair --offline')
    return 3


def mode_commands(root: Path, mode: str, available=None):
    if mode == 'full':
        return [['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-q']]
    tests = root / 'tests'
    if mode == 'quick':
        names = ('test_agentlocal_test_manager', 'test_comprehension_v1',
                 'test_comprehension_audiences_v1_2', 'test_comprehension_terrain_v1_5',
                 'test_comprehension_terrain_v1_6')
        names = [f'tests.{name}' for name in names if (tests / (name + '.py')).is_file()]
        return [['-m', 'unittest', *names, '-q']] if names else []
    raise ValueError('Mode inconnu: ' + mode)


def safety_gate():
    memory = available_memory()
    if memory:
        total, avail = memory
        print('RAM disponible: %.0f Mo / %.1f Go physiques' % (avail/2**20, total/2**30))
        if avail < 512 * 2**20:
            print('SECURITE: moins de 512 Mo libres. Tests complets suspendus.', file=sys.stderr)
            return 6
    print('VERIFICATION RESSOURCES OK - aucune inference LLM lancee.')
    return 0


def run_tests(mode='full', root: Path = ROOT, current=None, runner=subprocess.run):
    chosen = select(root, current, runner)
    if not chosen:
        print('ERREUR: Aucun environnement Python 64 bits avec psutil et pypdf.', file=sys.stderr)
        print('Executez: runtime\\TESTER_ENVIRONNEMENT.bat doctor', file=sys.stderr)
        return 3
    label, exe, info = chosen
    memory = available_memory()
    if mode == 'full' and memory and memory[1] < 512 * 2**20:
        print('RAM disponible < 512 Mo : tests complets differes, utiliser --mode quick.', file=sys.stderr)
        return 6
    print('Python choisi: %s (%s, %s)' % (exe, label, info.get('python')), flush=True)
    print('Mode: %s | Aucun chargement volontaire de Qwen / aucune installation pip.' % mode, flush=True)
    commands = mode_commands(root, mode)
    if not commands:
        print('Aucun test correspondant au mode %s.' % mode, file=sys.stderr)
        return 4
    for args in commands:
        try:
            proc = runner([str(exe), *args], cwd=str(root), timeout=900)
        except subprocess.TimeoutExpired:
            print('ECHEC: le parcours de tests a depasse 15 minutes.', file=sys.stderr)
            return 124
        except OSError as exc:
            print('ECHEC: lancement impossible: %s' % type(exc).__name__, file=sys.stderr)
            return 5
        if proc.returncode:
            print('ECHEC: tests avec %s, code %s.' % (label, proc.returncode), file=sys.stderr)
            return proc.returncode
    print('TESTS TERMINES AVEC SUCCES.')
    return 0


def repair(root: Path = ROOT, offline=False, online=False, runner=subprocess.run, current=None):
    """Explicit opt-in repair: creates .venv or installs *only* requirements.txt."""
    if not (offline ^ online):
        print('Indiquer --offline ou --online (pas les deux).', file=sys.stderr)
        return 2
    if not REQUIREMENTS.is_file() and not (root / 'requirements.txt').is_file():
        print('requirements.txt introuvable: aucune installation.', file=sys.stderr)
        return 2
    env_python = root / '.venv' / 'Scripts' / 'python.exe'
    if not env_python.is_file():
        env_dir = root / '.venv'
        if env_dir.exists():
            print('Environnement .venv incomplet: sauvegarde/manipulation manuelle requise.', file=sys.stderr)
            return 3
        source = current or sys.executable
        print('Creation explicite de .venv avec %s ...' % source, flush=True)
        proc = runner([source, '-m', 'venv', str(env_dir)], cwd=str(root), timeout=180)
        if proc.returncode:
            print('Echec creation .venv. Rien d autre ne sera installe.', file=sys.stderr)
            return proc.returncode
    pip_args = [str(env_python), '-m', 'pip', 'install', '--disable-pip-version-check',
                '--retries', '1', '--timeout', '12']
    if offline:
        wheel_dir = root / 'vendor' / 'wheels'
        if not wheel_dir.is_dir() or not any(wheel_dir.glob('*.whl')):
            print('Cache offline absent ou vide. Aucune connexion tentee.', file=sys.stderr)
            return 3
        pip_args += ['--no-index', '--find-links', str(wheel_dir)]
    pip_args += ['-r', str(root / 'requirements.txt')]
    print('Installation des dependances dans .venv seulement.', flush=True)
    try:
        result = runner(pip_args, cwd=str(root), timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print('Installation interrompue: %s' % type(exc).__name__, file=sys.stderr)
        return 5
    if result.returncode:
        print('pip a echoue. L environnement existant a ete conserve.', file=sys.stderr)
        return result.returncode
    status = probe(env_python, runner)
    if not status['ok']:
        print('Dependances incompletes apres pip: ' + status['reason'], file=sys.stderr)
        return 3
    print('DEPENDANCES OK. Relancez le diagnostic puis les tests.')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='AgentLocal - tests et dependances sans charger Qwen')
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('doctor', help='diagnostic sans modification')
    sub.add_parser('guard', help='refuser les tests complets sous 512 Mo libres')
    sub.add_parser('select', help='sortie: chemin Python valide (pour le lanceur)')
    tests = sub.add_parser('test', help='unittest avec le bon Python')
    tests.add_argument('--mode', choices=['quick', 'full'], default='full')
    repair_parser = sub.add_parser('repair', help='installation des dependances apres demande explicite')
    opts = repair_parser.add_mutually_exclusive_group(required=True)
    opts.add_argument('--offline', action='store_true')
    opts.add_argument('--online', action='store_true')
    args = parser.parse_args(argv)
    if args.action == 'doctor':
        return show_doctor()
    if args.action == 'guard':
        return safety_gate()
    if args.action == 'select':
        found = select()
        if not found:
            print('DEPENDANCES MANQUANTES : runtime\\TESTER_ENVIRONNEMENT.bat doctor', file=sys.stderr)
            return 3
        print(str(found[1]))
        return 0
    if args.action == 'test':
        return run_tests(args.mode)
    if args.action == 'repair':
        return repair(offline=args.offline, online=args.online)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
