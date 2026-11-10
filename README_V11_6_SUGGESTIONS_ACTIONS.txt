AgentLocal V11.6 - Suggestions d'actions contrôlées

Objectif : proposer une prochaine action utile sans jamais l'exécuter automatiquement.

Règles :
- au plus une suggestion à la fois ;
- aucune suggestion destructive ;
- aucune suggestion après un échec ou une commande multi-actions ;
- expiration en mémoire de session après 5 minutes ;
- l'utilisateur doit dire explicitement « fais la suggestion » pour l'exécuter ;
- « oui » seul ne suffit pas ;
- la commande suggérée repasse dans toutes les validations AgentLocal normales ;
- aucune suggestion persistante, aucune nouvelle habitude automatique.

Exemple :
Vous : liste mes documents
AgentLocal : ...
Suggestion : Si tu veux, je peux aussi te montrer les fichiers les plus récents dans Documents.
Commande proposée : « montre-moi les 5 fichiers les plus récents dans Documents »
Si tu veux que je la lance, dis simplement : « fais la suggestion ».

Tests :
- tester_agentlocal.ps1 : compilation + JSON + tous les verifier_*.py + pytest
- tester_agentlocal.bat : lance le script PowerShell ci-dessus
