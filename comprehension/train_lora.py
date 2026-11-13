"""Preparation et fine-tuning LoRA EXPERIMENTAL sur machine avec GPU.

PAR DEFAUT : preflight et export uniquement. Ne touche pas au GGUF installe.
Le code de training doit etre adapte aux versions Transformers/TRL/Qwen disponibles.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .data_quality import validate_corpus
from .sft import export


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description='LoRA AgentLocal - GPU uniquement, execution explicite')
    p.add_argument('--execute',action='store_true',help='Executer reellement le fine tuning (GPU requis)')
    p.add_argument('--model',default='Qwen/Qwen3.5-0.8B',help='Modele HF, PAS un fichier .gguf')
    p.add_argument('--output',default='memory/lora_agentlocal')
    p.add_argument('--epochs',type=int,default=2)
    args=p.parse_args(argv)
    report=validate_corpus()
    if not report['ok']:
        print('Corpus invalide:',report['errors']);return 2
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    sft_dir=output.parent/'sft_export'
    counts=export(sft_dir)
    print('Corpus valide et exporte:',counts)
    if not args.execute:
        print('AUCUN ENTRAINEMENT EFFECTUE. Ajouter --execute sur une machine GPU compatible.')
        return 0
    if not 1 <= args.epochs <= 5:
        print('Nombre d epochs hors bornes (1..5)');return 2
    try:
        import torch
        if not torch.cuda.is_available():
            print('Refus: aucun GPU CUDA disponible. Le fine tuning CPU/4 Go est desactive.')
            return 2
        from datasets import load_dataset
        from peft import LoraConfig
        from trl import SFTConfig, SFTTrainer
    except ImportError as exc:
        print('Bibliotheque manquante pour le fine tuning:',exc)
        return 2
    if args.model.lower().endswith('.gguf'):
        print('Un GGUF quantifie ne peut pas etre utilise comme base SFT Hugging Face.');return 2
    train_data=load_dataset('json',data_files={'train':str(sft_dir/'train_sft.jsonl'), 'validation':str(sft_dir/'validation_sft.jsonl')})
    # L'utilisation du modele multimodal Qwen3.5 dans TRL peut necessiter une
    # version specifique de transformers/trl. Ne jamais remplacer le GGUF
    # local sans un benchmark et une conversion testes separement.
    config=SFTConfig(output_dir=str(output),learning_rate=0.00015,
                     per_device_train_batch_size=1,gradient_accumulation_steps=8,
                     num_train_epochs=args.epochs,max_length=1024,
                     logging_steps=10,eval_strategy='epoch',save_strategy='epoch',
                     save_total_limit=2,report_to='none',bf16=bool(torch.cuda.is_bf16_supported()),
                     fp16=not torch.cuda.is_bf16_supported())
    lora=LoraConfig(r=8,lora_alpha=16,lora_dropout=0.05,
                    task_type='CAUSAL_LM',target_modules='all-linear',bias='none')
    print('Debut de l entrainement LoRA experimental:',args.model)
    trainer=SFTTrainer(model=args.model,args=config,
                       train_dataset=train_data['train'],
                       eval_dataset=train_data['validation'],peft_config=lora)
    trainer.train()
    trainer.save_model(str(output/'adapter'))
    print('Adaptateur sauvegarde:',output/'adapter')
    print('LE GGUF INSTALLE N A PAS ETE MODIFIE.')
    return 0

if __name__=='__main__':
    sys.exit(main())
