AGENTLOCAL - LANCEUR UNIQUE
==========================

Fichier utilisateur principal : AgentLocal.bat

Double-clic : ouvre le menu principal.

Commandes directes :
- AgentLocal.bat start    : lancer AgentLocal
- AgentLocal.bat diag     : diagnostic technique
- AgentLocal.bat test     : suite complete de tests
- AgentLocal.bat verify   : nettoyage + verification complete
- AgentLocal.bat setup    : preparation d'un nouveau PC
- AgentLocal.bat offline  : preparation des dependances hors connexion
- AgentLocal.bat runtime  : construction/mise a jour du runtime Python portable
- AgentLocal.bat version  : version courante

Au premier lancement, les anciens fichiers .bat de la racine sont ranges dans :
runtime\legacy_launchers\

Ils ne sont plus necessaires pour l'utilisation normale.
Le script PowerShell tester_agentlocal.ps1 reste un composant interne de la suite de tests ; il ne doit pas etre lance manuellement.
