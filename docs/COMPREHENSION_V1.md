# AgentLocal — Compréhension V1 (branche `comprehension`)

## Objectif

Améliorer la compréhension *sans changer le modèle installé* : français, expressions courantes de Côte d'Ivoire, anglais et notions d'espagnol ; intentions, refus, ambiguïtés, negations et commandes contextualisées. Les expressions de nouchi incertaines conduisent à une question plutôt qu'à une action inventée.

## Modules

- `comprehension/data/train.jsonl` : exemples annotés pour apprentissage/prompt, sans données personnelles.
- `comprehension/data/eval.jsonl` : évaluations distinctes, jamais incorporées aux exemples de prompt.
- `comprehension/guide.py` : recherche locale d'exemples pour chaque demande (limite 3 exemples, taille bornée).
- `comprehension/data_quality.py` : validation du corpus, doublons, négations, catégories et champs.
- `comprehension/feedback.py` : correction proposée **puis approuvée explicitement**, uniquement vers une commande déjà connue ; stockage dans `memory/` ignoré par Git.
- `comprehension/sft.py` : export chat messages pour fine-tuning supervisé, avec train/validation distincts et **jeu de test final jamais utilisé pendant l'entraînement** ; n'exécute aucun entraînement.
- `comprehension/train_lora.py` : procédure LoRA expérimentale **à déclencher manuellement sur une machine avec GPU**, non exécutée lors des tests et non recommandée sur PC de 4 Go.
- `backends/llama_backend.py` : ajout d'exemples validés au prompt Qwen. Le moteur déterministe et `llm_fidelity` restent seuls décideurs de la validité des actions.

## Commandes (depuis le dossier AgentLocal)

```cmd
python -m comprehension validate
python -m unittest tests.test_comprehension_v1 -v
python -m comprehension examples "n'ouvre pas Word"
python -m comprehension evaluate-live --max-cases 20
python -m comprehension export-sft --output memory\sft_export
python -m comprehension.train_lora
```

**Note sur `evaluate-live` :** contacte le vrai Qwen via `llama.cpp` local et ne passe jamais par `process_instruction` ou `execute_action`; aucune action PC n'est exécutée. Il peut être lent ; commencer par 5-10 cas. Un modèle indisponible est signalé, pas considéré comme testé.

## Apprentissage volontaire des corrections

```cmd
python -m comprehension propose --phrase "tu me lances Excel stp" --canonical "ouvre Excel"
```

Copier l'identifiant obtenu, puis confirmer :

```cmd
python -m comprehension approve --id IDENTIFIANT_AFFICHE
```

Les corrections en attente ne sont pas utilisées. Les corrections approuvées sont enregistrées dans `memory/language_approved.json`, non commitées par Git. Les commandes nouvelles, les cibles modifiées, les phrases négatives et les valeurs altérées sont refusées.

## Attention : « entraînement » ≠ « modèle déjà entraîné »

L'ajout d'exemples au prompt et la validation d'expressions améliorent l'exploitation du Qwen existant **sans modifier les poids**. Un vrai fine-tuning LoRA nécessite les poids HF d'origine (pas le `.gguf`) et un GPU adapté. La conversion en GGUF et la validation sur Windows sont deux étapes ultérieures distinctes. Le script LoRA est expérimental et n'a pas été exécuté ici ; il faut valider ses dépendances et sa compatibilité architecturale avant usage.

## Critères de validation avant publication

1. Les tests de code et le corpus passent, sans déclencher d'actions.
2. Les négations ne produisent jamais d'actions (faux positifs = 0 sur la batterie adversariale).
3. Les noms de fichiers, chemins, destinations et valeurs numériques ne sont jamais inventés.
4. Qwen est évalué sur les **183 exemples réservés** (et des demandes humaines nouvelles). Résultats rapportés séparément par langue/type.
5. Les réponses naturelles sont évaluées humainement : pertinence, adaptation du ton, refus clair et demande de précision lorsque nécessaire.
6. Temps de réponse et mémoire sont comparés avant/après sur Windows 10/11 et PC de 4 Go.
7. Aucune modification à l'UAC, aux permissions et aux droits administrateur.

## Limites actuellement connues

- 353 exemples d'entraînement ne suffisent pas à eux seuls à rendre un 0.8B comparable à un grand assistant ; ils constituent une première base vérifiable.
- Les reformulations sont validées par les contrôles existants mais la compréhension du vrai modèle n'a pas été mesurée sur cette machine.
- Les langues locales autres que des expressions ivoiriennes courantes requièrent un corpus vérifié avec des locuteurs pour éviter les erreurs de traduction.
- La conversation long terme et la planification des actions sont hors du périmètre de cette première version ; les modules existants restent en place.
