"""Outils d'apprentissage et d'evaluation AgentLocal, sans action sur Windows."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .data_quality import load_split, validate_corpus
from .guide import closest_examples, few_shot_hint
from .sft import export


def live_evaluate(max_cases: int, subset: str) -> int:
    # Interpretation uniquement. Jamais process_instruction / execute_action.
    from backends import llama_backend
    rows=load_split('eval')
    if subset!='all':
        rows=[r for r in rows if r['domain']==subset]
    rows=rows[:min(200,max_cases)]
    if not rows:
        print('Aucun cas correspondant.');return 2
    correct=0; failed=[]
    for row in rows:
        expected=row['output']['type']
        try:
            result=llama_backend.interpret(row['input'])
        except Exception as exc:
            got='error:'+type(exc).__name__
        else:
            if result.get('actions'):
                got='command'
            else:
                got=result.get('llm_type') or 'unknown'
            if expected=='command' and got=='command':
                # Contrat complet: comparer aussi la commande normalisee, si exposee.
                proposed=result.get('llm_canonical_command','').casefold().strip()
                desired=row['output']['canonical_command'].casefold().strip()
                matched=bool(proposed and proposed==desired)
            else:
                matched=got==expected
            if matched:
                correct+=1
                continue
        failed.append({'id':row['id'],'expected':expected,'observed':got,'input':row['input']})
        print(f"{row['id']} - ATTENDU {expected}; OBTENU {got}")
    report={'total':len(rows),'pass':correct,'failed':len(rows)-correct,'examples':failed[:20]}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if correct==len(rows) else 1


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description='Apprentissage linguistique AgentLocal, actions desactivees')
    sub=parser.add_subparsers(dest='mode',required=True)
    sub.add_parser('validate',help='Valider le corpus et le jeu devaluation')
    hint=sub.add_parser('examples',help='Montrer les exemples du prompt local')
    hint.add_argument('message',nargs='+')
    exp=sub.add_parser('export-sft',help='Preparer les donnees de fine-tuning LoRA (sans entrainer)')
    exp.add_argument('--output',default='memory/sft_export')
    live=sub.add_parser('evaluate-live',help='Tester Qwen en lecture seule, sans actions')
    live.add_argument('--max-cases',type=int,default=20)
    live.add_argument('--domain',default='all')
    fb=sub.add_parser('propose',help='Proposer une correction locale, sans l appliquer')
    fb.add_argument('--phrase',required=True)
    fb.add_argument('--canonical',required=True)
    ok=sub.add_parser('approve',help='Approuver explicitement une correction')
    ok.add_argument('--id',required=True)
    args=parser.parse_args(argv)
    if args.mode=='validate':
        report=validate_corpus()
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0 if report['ok'] else 1
    if args.mode=='examples':
        print(few_shot_hint(' '.join(args.message)))
        return 0
    if args.mode=='export-sft':
        print('Fichiers crees:',export(Path(args.output)))
        return 0
    if args.mode=='propose':
        from .feedback import propose
        try:
            print('Correction en attente. ID:', propose(args.phrase,args.canonical))
            return 0
        except ValueError as exc:
            print('Refus:',exc)
            return 1
    if args.mode=='approve':
        from .feedback import approve
        accepted=approve(args.id)
        print('Correction approuvee.' if accepted else 'Correction non validee.')
        return 0 if accepted else 1
    if args.mode=='evaluate-live':
        return live_evaluate(max(1,args.max_cases), args.domain)
    return 2

if __name__=='__main__':
    sys.exit(main())
