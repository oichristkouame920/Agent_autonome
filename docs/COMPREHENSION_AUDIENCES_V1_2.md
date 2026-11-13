# AgentLocal — Compréhension V1.2 : professionnel et débutant

## Objectif

Ce correctif enrichit **le modèle Qwen déjà installé**, via des exemples validés et un aiguillage léger du style de réponse. Il prépare aussi des données SFT pour un **éventuel fine-tuning ultérieur**. Les poids du modèle GGUF ne sont **pas** modifiés.

### Utilisateur professionnel

- Réponses précises, adaptées aux demandes techniques, administratives, pédagogiques, RH, financières et de gestion de projet.
- Savoir distinguer un diagnostic *sur des éléments fournis* d'une hypothèse non confirmée.
- Demander les journaux, données ou contraintes indispensables plutôt que prétendre accéder à des services non connectés.
- Ne pas interpréter « prépare un plan » ou « explique » comme une autorisation d'agir sur Windows.

### Utilisateur novice habitué à ChatGPT

- Accueillir les demandes en langage courant, sans exiger une syntaxe de commande.
- Expliquer les termes, proposer des étapes courtes et un exemple concret, éviter le jargon inutile.
- Répondre à une question sans ouvrir une application ni modifier un fichier, sauf demande explicite.
- Clarifier « fais ça », « range le truc », « continue comme hier » si le contexte nécessaire manque.

Le niveau est détecté pour **le message courant seulement**. Il ne sert jamais à accorder des permissions.

## Jeux de données

- `comprehension/data/train_audiences.jsonl` : **155 exemples** supplémentaires.
- `comprehension/data/eval_audiences.jsonl` : **55 cas tenus à l'écart** pour l'évaluation.
- Total du corpus V1.2 : **508 apprentissage, 238 évaluation**, soit 746 exemples.
- Format identique à celui de V1, plus un champ optionnel `audience`.

La sélection de trois exemples maximum reste bornée en taille pour les petits PC. Les nouvelles règles de style sont intégrées dans le prompt local par `comprehension/guide.py` ; aucune action Windows n'est exécutée par ce guide.

## Tests après installation

Dans `C:\Users\cdn09\AgentLocal` :

```cmd
python -m comprehension validate
python -m unittest tests.test_comprehension_audiences_v1_2 -v
python -m comprehension examples "Je suis débutant, explique la RAM simplement"
python -m comprehension examples "En tant que développeur, comment auditer notre API ?"
```

Pour tester **Qwen réellement**, les appels restent en lecture seule :

```cmd
python -m comprehension evaluate-live --domain pro_action --max-cases 6
python -m comprehension evaluate-live --domain beginner_action --max-cases 7
```

Si le diagnostic V1.1 est installé : `--timeout-seconds 90 --report rapport_pro.json` peut aussi être ajouté.

**Remarque :** un bon score des tests Python ne démontre pas que le modèle Qwen comprend correctement des phrases inédites. Seul le benchmark local du vrai modèle peut l'établir. Il faut notamment mesurer les refus injustifiés et les commandes canoniques exactes.

## Sécurité et limites

- Pas de modification de `llama.cpp`, des poids Qwen, du système Windows, des permissions ou des secrets.
- Aucun privilège administrateur permanent.
- L'agent n'a pas accès automatiquement aux documents, aux clients, à la direction ou aux serveurs de l'utilisateur.
- Les réponses professionnelles doivent s'appuyer sur des données fournies et reconnaître les limites.
- Les corrections personnelles approuvées restent dans `memory/`, hors Git.
- Le fine-tuning sur GPU reste une étape distincte ; ne pas prétendre avoir entraîné les poids avec cette mise à jour.
