AGENTLOCAL V12.1 - PLANIFICATION LOCALE CONTROLEE
================================================

Cette version prolonge V12.0 avec des automatisations horaires persistantes
et confirmees par l'utilisateur.

NOUVEAUTES
- "programme mon briefing chaque matin à 7h"
- "programme ma routine chaque matin à 7h"
- "programme ma routine tous les lundis à 8h30"
- "enregistre mes habitudes chaque matin à 7h" : planifie un resume des habitudes
- "liste mes planifications"
- "confirme la planification <id ou numero>"
- "active/desactive/supprime la planification <id ou numero>"

REGLE DE SECURITE
Une demande de planification cree d'abord un brouillon desactive. Elle ne peut
s'executer qu'apres une confirmation explicite. Le planificateur refuse les
commandes arbitraires, les shells et les actions destructives.

ACTIONS PLANIFIABLES
1. Routine deja confirmee dans config/routines.json
2. Briefing en lecture seule (meteo + actualites)
3. Resume des habitudes

FONCTIONNEMENT
- Les horaires sont stockes localement dans memory/schedules.json.
- Ce fichier est cree automatiquement et n'est pas livre dans le ZIP, pour
  qu'une mise a jour future ne remplace jamais les horaires de l'utilisateur.
- Le planificateur s'execute uniquement tant qu'AgentLocal est lance.
- Une fenetre de rattrapage de 60 minutes est appliquee par defaut.
- Une planification ne s'execute qu'une seule fois par date locale.
- Si un briefing planifie est actif, le popup matinal generique V12 n'est pas
  duplique.

EXEMPLES
Vous : programme mon briefing chaque matin à 7h
AgentLocal : Brouillon de planification cree ... confirme la planification p-xxxxxxxx

Vous : confirme la planification p-xxxxxxxx
AgentLocal : Planification ... confirmee et activee.

Vous : liste mes planifications
AgentLocal : affiche les horaires, l'etat et les identifiants.

INSTALLATION
1. Extraire le ZIP a la racine de C:\Users\cdn09\AgentLocal
2. Accepter les remplacements.
3. Debloquer les fichiers si necessaire :
   Get-ChildItem "C:\Users\cdn09\AgentLocal" -Recurse -File | Unblock-File
4. Lancer AgentLocal.bat
5. Choisir 4 - Verifier / finaliser l'installation
6. Puis 1 - Lancer AgentLocal

LLAMA.CPP
Cette mise a jour ne contient pas et ne modifie pas llama.cpp, les modeles GGUF,
.venv, ni les donnees personnelles existantes.
