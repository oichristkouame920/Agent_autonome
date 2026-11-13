# AgentLocal - Compréhension V1.3 : sécurité et machines à 4 Go

## Portée
- Conserve Qwen et llama.cpp existants, ne modifie pas les poids du modèle.
- Ne change aucune permission administrateur et n'autorise pas de commande shell.
- Corrige les exemples contradictoires dans le prompt (ouverture/fermeture, conseil/action, négations, cibles et nombres).
- Protège contre une cible inventée par le LLM, tout en acceptant quelques expressions génériques explicites.
- Prépare une évaluation non destructive avec contraintes pour machines modestes.

## Vérifications rapides (aucune action sur Windows)
Depuis `C:\Users\cdn09\AgentLocal` :

```
python -m unittest tests.test_comprehension_security_4gb_v1_3 -v
python -m comprehension.resource_diagnostics --iterations 2000
```

## Test de résistance sans Qwen
```
python -m comprehension.resource_diagnostics --iterations 10000
```
Ce test mesure uniquement le code Python de sélection des exemples (pas la vitesse de génération du modèle).

## Essai du vrai modèle (facultatif, lecture seule)
Lancer seulement après avoir enregistré tout travail en cours :
```
python -m comprehension.resource_diagnostics --iterations 2000 --live --max-cases 2
```
- Ne déclenche AUCUNE action Windows à partir de la réponse : appelle seulement `llama_backend.interpret`.
- Ne démarre pas Qwen sous 1 536 Mo de RAM libre sur machine 4 Go (seuil de précaution, pas une garantie).
- 4 exemples au maximum; chaque test est séquentiel. Les tests n'ont pas besoin de privilèges administrateur.
- En cas de lenteur excessive ou de swap : fermer les applications gourmandes et réévaluer avant de modifier les paramètres de Qwen.
- Les conseils `threads <= 2`, `context <= 2048`, serveur chaud désactivé sur 4 Go ne changent PAS automatiquement la configuration de l'agent.

## Sécurité
- Les évaluations ordinaires ne chargent pas le modèle, ne lancent aucune application et ne font aucune requête réseau.
- L'installateur vérifie la branche `comprehension`, l'intégrité SHA-256, crée une sauvegarde sous `memory/backups/`, puis exécute des tests ciblés.
- Aucun script ne demande de désactiver UAC, Defender ou d'attribuer des droits administrateur permanents.
- Les mesures de RAM et CPU sur Linux ne garantissent pas les mêmes résultats sur Windows 4 Go; vérifier le test local.
