AgentLocal - Langage naturel V6 CI
====================================

Objectif
--------
Cette evolution ajoute des tournures frequentes du francais oral en Cote d'Ivoire
sans augmenter l'autonomie de l'agent.

Exemples compris
----------------
- faut ouvrir Edge
- ouvre-moi GitHub la
- je veux aller sur Google la
- Teams est lance meme ?
- Word est ouvert ou bien ?
- regarde un peu si Excel est lance
- agrandis Edge la
- mets VS Code a gauche la
- ramene Word devant
- faut lancer ma routine
- prepare-moi pour le boulot la
- y a quoi dans Documents la ?
- on est ensemble
- y a pas drap
- c'est comment ?

Securite
--------
- Les negations orales comme "ouvre pas Edge" et "faut pas ouvrir Edge" ne font rien.
- PowerShell, CMD, Terminal, Bash et WSL restent interdits.
- Une commande mixte comme "ouvre Edge puis PowerShell" est refusee en entier.
- Les references vagues comme "ouvre ca la" ne declenchent aucune action.
- Pour une action destructive sur un fichier, un marqueur oral final ambigu
  (par exemple "supprime rapport la") provoque une demande de precision.
- Les phrases vagues comme "on commence le boulot" ou "faut gerer ca"
  ne lancent aucune routine automatiquement.

Validation
----------
- 146 tests unitaires complets passent.
- Les anciens tests de non-regression sont conserves.
- Nouveau fichier de tests : tests/test_natural_language_ci.py

Installation
------------
Copier le contenu du ZIP directement dans C:\Users\cdn09\AgentLocal
et accepter le remplacement des fichiers.

Verification
------------
Depuis PowerShell :

  cd C:\Users\cdn09\AgentLocal
  .\.venv\Scripts\python.exe .\verifier_langage_ci.py

