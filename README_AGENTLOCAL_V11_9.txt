AGENTLOCAL V11.9 - INTERFACE PROFESSIONNELLE
==========================================

Objectif
--------
La V11.9 refond l'experience utilisateur sans modifier le modele de securite.
Le moteur local, les permissions, les validations et le pont Edge restent les
mêmes : l'interface ne contourne jamais app/agent.py.

Nouveautes principales
----------------------
- Accueil chaleureux avec salutation selon l'heure.
- Navigation laterale : Accueil, Assistant, Mon PC, Fichiers, Web, Routines,
  Parametres.
- Cartes de performance locales : CPU, RAM, disque libre, uptime et processus.
- Actions rapides contextuelles vers les fonctions deja autorisees.
- Assistant modernise avec suggestions cliquables.
- Temps de reponse visible apres chaque commande.
- Indicateur clair de l'etat : Systeme pret / Mode degrade / Mode sur.
- Interface Tkinter uniquement : aucune dependance graphique lourde ajoutee.
- Les commandes rapides passent toujours par agent.process_instruction().

Securite
--------
- Aucune commande systeme n'est executee directement depuis le GUI.
- Aucun shell libre n'est expose.
- Les permissions existantes restent la source de verite.
- Les tableaux de bord locaux sont en lecture seule.
- llama.cpp n'est pas modifie par cette version.

Installation
------------
1. Extraire le pack a la racine du dossier AgentLocal.
2. Conserver les dossiers lourds/personnels existants : .venv, models,
   tools/llama.cpp, logs et donnees locales.
3. Lancer AgentLocal.bat.
4. Choisir 4 - Verifier / finaliser l'installation.
5. Puis choisir 1 - Lancer AgentLocal.

Raccourcis interface
--------------------
Ctrl+K : ouvrir l'Assistant et placer le curseur dans la zone de commande.
Entree : envoyer.
Ctrl+L : effacer uniquement l'affichage de la conversation.
