"""Banc d'essai non destructif et profil frugal pour AgentLocal.

Par defaut: ne charge aucun LLM et ne lance aucun outil Windows.
--live: demande explicite, minimum de RAM libre, au maximum 4 requetes locales,
uniquement llama_backend.interpret() (jamais execute_action()).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

from .guide import closest_examples, few_shot_hint

_MIB = 1024 * 1024
_MESSAGES = (
    "ouvre Word", "tu me lances Excel un peu", "ne lance pas Word",
    "could you launch Excel?", "comment ouvrir Word sans me tromper ?",
    "Je suis debutant, explique comment utiliser Excel",
    "En tant que technicien, ouvre Teams pour la reunion",
    "ouvre Excel puis ferme Word", "no abras Word", "regle le volume a 20%",
)
_LIVE_MESSAGES = (
    "ouvre-moi Word maintenant", "could you launch Excel?",
    "faut pas ouvrir Word hein", "comment ouvrir Excel ?",
)


def memory_snapshot() -> dict:
    """Mesure lecture seule sans bibliotheque supplementaire."""
    if os.name == "nt":
        try:
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            st = MemoryStatus()
            st.dwLength = ctypes.sizeof(st)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
                return {"total_mb": int(st.ullTotalPhys // _MIB),
                        "available_mb": int(st.ullAvailPhys // _MIB),
                        "source": "Windows GlobalMemoryStatusEx"}
        except (AttributeError, OSError, ValueError):
            pass
    else:
        try:
            fields = {}
            for line in Path('/proc/meminfo').read_text(encoding='ascii').splitlines():
                key, _, value = line.partition(':')
                fields[key] = int(value.strip().split()[0]) // 1024
            if 'MemTotal' in fields and 'MemAvailable' in fields:
                return {"total_mb": fields['MemTotal'], "available_mb": fields['MemAvailable'],
                        "source": "Linux /proc/meminfo"}
        except (OSError, ValueError, IndexError):
            pass
    return {"total_mb": None, "available_mb": None, "source": "unavailable"}


def plan_for_memory(total_mb: int | None, available_mb: int | None) -> dict:
    """Conseil conservateur, PAS une reconfiguration automatique du modele.

    La RAM libre, non la RAM installee, determine si un diagnostic LLM est
    prudent. Le seuil est volontairement conservateur; pas de promesse de FPS.
    """
    if not isinstance(total_mb, int) or not isinstance(available_mb, int) or total_mb <= 0 or available_mb < 0:
        return {"profile": "unknown", "live_allowed": False, "reason": "RAM inconnue; test LLM refuse par precaution"}
    is_small = total_mb <= 5120
    min_available = 1536 if is_small else 1200
    eligible = available_mb >= min_available
    return {
        "profile": "4gb_cautious" if is_small else "standard",
        "live_allowed": eligible,
        "required_free_mb": min_available,
        "reason": "marge libre suffisante pour un essai prudent" if eligible else "RAM libre insuffisante; rester en mode hors LLM",
        "advisory_only": True,
        "suggested_context": 2048 if is_small else None,
        "suggested_threads_max": 2 if is_small else None,
        "warm_server_recommended": False if is_small else None,
    }


def offline_benchmark(iterations: int = 2000) -> dict:
    """Tests statiques bornes: aucune application, aucun serveur, aucun LLM."""
    iterations = max(1, min(int(iterations), 10000))
    # Chauffe le cache des exemples de REFERENCE seulement.
    closest_examples(_MESSAGES[0])
    tracemalloc.start()
    started = time.perf_counter()
    cpu_started = time.process_time()
    max_prompt = 0
    anomalies = []
    for i in range(iterations):
        message = _MESSAGES[i % len(_MESSAGES)]
        examples = closest_examples(message)
        prompt = few_shot_hint(message, max_chars=1050)
        max_prompt = max(max_prompt, len(prompt))
        if len(examples) > 4 or len(prompt) > 1050:
            anomalies.append('prompt_budget_violation')
        if message.startswith(('ne ', 'no ')) and any(x['output']['type'] == 'command' for x in examples):
            anomalies.append('negation_leak')
        if message.startswith('comment ') and any(x['output']['type'] == 'command' for x in examples):
            anomalies.append('advice_leak')
    wall = time.perf_counter() - started
    cpu = time.process_time() - cpu_started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        'test': 'offline_non_destructive', 'iterations': iterations, 'elapsed_seconds': round(wall, 3),
        'process_python_cpu_seconds': round(cpu, 3),
        'requests_per_second': round(iterations / max(wall, 1e-9), 1),
        'peak_python_heap_mb': round(peak / _MIB, 3),
        'max_example_prompt_chars': max_prompt,
        'anomalies': sorted(set(anomalies)), 'passed': not anomalies,
        'caveat': 'Mesure la selection des exemples seulement; ne mesure pas la RAM native ni la vitesse de Qwen.',
    }


def live_benchmark(max_cases: int = 2) -> dict:
    """Interpretation LLM locale explicite; aucune action Windows executee."""
    max_cases = max(1, min(int(max_cases), 4))
    snap = memory_snapshot()
    decision = plan_for_memory(snap['total_mb'], snap['available_mb'])
    if not decision['live_allowed']:
        return {'test': 'live_interpretation_only', 'status': 'skipped_insufficient_ram',
                'memory': snap, 'policy': decision, 'results': []}
    # Protection supplementaire: pas de benchmark non borne sur les autres OS.
    # Le travail definitif de validation LLM doit avoir lieu sur Windows.
    if os.name != 'nt':
        return {'test': 'live_interpretation_only', 'status': 'skipped_non_windows',
                'memory': snap, 'policy': decision, 'results': []}
    from backends import llama_backend

    results = []
    for message in _LIVE_MESSAGES[:max_cases]:
        before = memory_snapshot()
        if not plan_for_memory(before['total_mb'], before['available_mb'])['live_allowed']:
            results.append({'status': 'skipped_low_ram_during_run'})
            break
        begin = time.perf_counter()
        try:
            result = llama_backend.interpret(message)  # Ne PAS appeler execute_action.
            record = {'status': 'ok', 'type': result.get('llm_type') or ('command' if result.get('actions') else 'unknown'),
                      'canonical': result.get('llm_canonical_command', ''),
                      'confidence': result.get('llm_confidence')}
        except Exception as exc:
            record = {'status': 'error', 'exception': type(exc).__name__}
        record['elapsed_seconds'] = round(time.perf_counter() - begin, 3)
        record['free_ram_after_mb'] = memory_snapshot()['available_mb']
        results.append(record)
        if record['status'] == 'error':
            break
    timings = [x['elapsed_seconds'] for x in results if x.get('status') == 'ok']
    return {'test': 'live_interpretation_only', 'status': 'completed', 'memory_initial': snap,
            'policy': decision, 'results': results,
            'median_latency_seconds': round(statistics.median(timings), 3) if timings else None,
            'caveat': 'Interpretation seulement, zero action; conditions reelles et autres processus influencent les temps.'}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description='Test securite/performance pour AgentLocal 4 Go')
    p.add_argument('--iterations', type=int, default=2000)
    p.add_argument('--live', action='store_true', help='Charge Qwen si RAM libre suffisante (consentement explicite)')
    p.add_argument('--max-cases', type=int, default=2)
    args = p.parse_args(argv)
    snap = memory_snapshot()
    report = {
        'platform': platform.system(), 'ram': snap,
        'memory_policy': plan_for_memory(snap['total_mb'], snap['available_mb']),
        'offline': offline_benchmark(args.iterations),
        'live': live_benchmark(args.max_cases) if args.live else {'status': 'not_requested'},
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report['offline']['passed']:
        return 1
    if args.live and (report['live']['status'] != 'completed' or
                      not all(x.get('status') == 'ok' for x in report['live'].get('results', []))):
        return 2  # Ne jamais declarer un essai live reussi s'il a ete saute / interrompu.
    return 0


if __name__ == '__main__':
    sys.exit(main())
