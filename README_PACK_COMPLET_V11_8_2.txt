AgentLocal V11.8.2 - PACK COMPLET UNIFIE
========================================

Ce pack consolide en une seule version cohérente :
- les correctifs terrain V11.7 ;
- le contexte conversationnel et les suggestions V11.8 ;
- les optimisations de performance V11.8.1 ;
- le centre de performances V11.8.2 ;
- le lanceur utilisateur unique AgentLocal.bat ;
- le contrôle structurel avant tests ;
- les tests globaux basés sur unittest (pytest non requis).

INSTALLATION SUR TON PROJET ACTUEL
----------------------------------
1. Sauvegarde ou commit Git de l'état actuel.
2. Débloque ce ZIP dans Propriétés Windows si l'option est affichée.
3. Extrais tout à la racine de C:\Users\cdn09\AgentLocal.
4. Accepte les remplacements.
5. Lance uniquement AgentLocal.bat.
6. Choisis [4] Vérifier / finaliser l'installation.
7. Si tout passe, choisis [1] Lancer AgentLocal.

CE PACK N'ECRASE PAS
--------------------
- tools\llama.cpp ;
- .venv ;
- les modèles GGUF ;
- memory\agent_memory.db ;
- les logs existants ;
- ton dépôt .git.

Les dossiers memory, logs, vendor/wheels et runtime/python sont seulement
présents avec des fichiers .gitkeep afin de conserver une arborescence propre.

LANCEUR UNIQUE
--------------
AgentLocal.bat est le seul fichier .bat utilisateur à la racine.
Les anciens lanceurs présents dans ton installation sont archivés automatiquement
au premier lancement dans runtime\legacy_launchers.

Commandes directes facultatives :
  AgentLocal.bat start
  AgentLocal.bat diag
  AgentLocal.bat test
  AgentLocal.bat verify
  AgentLocal.bat setup
  AgentLocal.bat offline
  AgentLocal.bat runtime
  AgentLocal.bat version

Version : 11.8.2
Build : 2026-11-10-v11.8.2-performance-center

REVISION PACK R2 - 10/11/2026
-----------------------------
Correction de la suite de tests LLM : les scénarios "modèle absent" simulent
maintenant explicitement un modèle indisponible au lieu de dépendre de la
présence réelle du modèle GGUF sur le PC. Le test reste donc valide aussi bien
sur une machine avec llama.cpp + modèle installé que sur une machine sans modèle.

Aucun changement n'est apporté à llama.cpp ni au modèle GGUF.
