AGENTLOCAL - INTERFACE GRAPHIQUE LEGERE
======================================

Objectif
--------
Cette interface est concue pour Windows 10/11 64 bits et pour une machine
avec seulement 4 Go de RAM.

Technologie
-----------
- Tkinter + ttk uniquement (bibliotheque standard Python)
- aucune dependance graphique externe
- aucun navigateur embarque
- aucun Electron
- aucun processus graphique secondaire permanent
- une seule commande AgentLocal a la fois

Securite
--------
L'interface ne dispose d'aucune permission supplementaire.
Elle transmet exactement le texte ecrit par l'utilisateur a app/agent.py.
Toutes les validations, listes blanches et preuves explicites existantes
restent obligatoires.

L'interface :
- ne lance aucune action toute seule ;
- n'execute aucune routine au demarrage ;
- n'ouvre aucune application automatiquement ;
- ne contourne pas les restrictions fichiers ;
- n'autorise pas PowerShell, CMD ou un shell arbitraire ;
- ne conserve pas de journal de conversation supplementaire sur disque.

Demarrage recommande
--------------------
Double-cliquer sur :
    lancer_agentlocal_gui.bat

Le lanceur utilise d'abord :
    venv\Scripts\pythonw.exe

Si aucun environnement venv n'est present, il tente pythonw.exe installe
sur Windows.

Mode console conserve
---------------------
La console historique reste disponible :
    python app\agent.py

Raccourcis
----------
- Entree : executer la commande
- Ctrl+L : effacer uniquement l'affichage de la conversation

Exemples
--------
    ouvre GitHub
    mets VS Code a gauche
    agrandis Edge
    retrouve rapport.pdf dans Documents
    liste mes Telechargements

Remarque RAM
------------
L'interface elle-meme est legere. La consommation memoire la plus importante
reste celle du modele local lorsqu'un backend LLM est utilise. L'interface
ne cree jamais plusieurs traitements AgentLocal simultanes.
