AgentLocal V11.7 - Correctifs terrain
Date : 09/11/2026

Base : ZIP backends(4).zip fourni par l'utilisateur.

Correctifs principaux :
- conserve la règle Edge V11.4.1 : une fenêtre existante, nouveaux sites en onglets via le pont local ;
- corrige le bug volume négatif : -20% n'est plus transformé en 20% ;
- les volumes hors 0..100 sont compris puis refusés par le contrat de sécurité ;
- reconnaît « mon réseau fonctionne ? » ;
- bloque PowerShell/CMD/Bash/WSL/Windows Terminal avant toute recherche de fichier,
  y compris chemins complets, petites fautes et formulations coercitives ;
- reconnaît « ne touche pas à mes fichiers » comme une négation atomique ;
- tolère « lsite » et « fhichiers » dans les commandes de listing ;
- reconnaît « ferme la fenetre formation python » comme fermeture ciblée d'une fenêtre Explorer ;
- reconnaît « va dans testAgent » comme ouverture d'un dossier nommé ;
- reconnaît « Documents\\TestAgentLocal, crée test.txt » pour un fichier vide dans un sous-dossier explicitement nommé ;
- « compresse X en Y.zip » sans racine n'est plus incompris : AgentLocal demande la racine au lieu de la deviner ;
- le lanceur global pytest cible maintenant uniquement tests/ et n'exécute plus les suites internes de llama.cpp.

Tests :
- tests/test_v11_7_regressions.py ajouté ;
- 311 tests Pytest + 248 sous-tests : OK ;
- exécuter : tester_agentlocal.bat
