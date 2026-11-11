AGENTLOCAL V12.2 - INTERFACE VISUELLE + ALERTES + ROUTINE MATINALE
=================================================================

Nouveautes principales
----------------------
- Interface Tkinter legere et epuree, sans framework graphique externe.
- Nouvelle page Alertes avec niveaux Information / Avertissement / Critique.
- Badge d'alertes toujours visible dans la barre superieure.
- Routine matinale : premier deverrouillage observe entre 07:00 et 09:30.
- Une seule execution automatique de la routine par jour.
- Si la plage horaire est depassee, AgentLocal signale la routine manquee au lieu de la lancer en retard.
- Controle matinal : CPU, RAM, disque, interface reseau, processus suspendus, applications non repondantes, taches AgentLocal en attente, briefing du jour.
- Briefing prioritaire conserve : Moyen-Orient, Ukraine, petrole/energie, technologie, defense et geopolitique majeure.
- Aucun processus n'est termine automatiquement et aucun fichier n'est supprime par le moniteur.

Seuils par defaut
-----------------
RAM >= 80 % : avertissement
RAM >= 92 % : critique
Disque < 15 Go libres : avertissement
Disque < 5 Go libres : critique
CPU >= 85 % pendant environ 2 minutes : avertissement
Reseau sans interface active : avertissement
Application non repondante : avertissement
Processus suspendu : information

Configuration
-------------
config\automation.json
  - plage matinale 07:00-09:30
  - seuils du moniteur
  - frequence de controle

memory\alerts.json
  - cree automatiquement sur le PC
  - historique local des alertes

memory\morning_automation_state.json
  - cree automatiquement
  - evite plusieurs executions de la routine le meme jour

Important
---------
AgentLocal doit etre lance pour observer le deverrouillage et executer la routine.
Cette version ne cree pas encore automatiquement une tache Windows au demarrage.
Les fonctions locales restent disponibles sans Internet.
