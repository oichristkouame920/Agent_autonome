AgentLocal V11.8.3 - Stabilisation terrain
Build : 2026-11-10-v11.8.3-terrain-stabilization

Objectif : corriger les anomalies observées lors des tests réels sans encore activer les services Internet de la future phase connectée.

Correctifs principaux :
- état de la connexion compris en langage naturel ;
- performance d’AgentLocal consultable ;
- liste des fenêtres visibles ;
- météo reconnue et bloquée proprement tant que le service Internet n’est pas activé ;
- mises à jour reconnues sans exécution implicite ;
- demande de planification d’habitudes reconnue sans créer automatiquement une tâche ;
- CPU des processus ramené à 0..100 % machine et System Idle Process masqué ;
- numéro d’onglet >3 utilisable après une liste pour les sites connus ;
- fermeture Pense-bêtes renforcée par détection sûre du titre visible ;
- message technique de suivi de fenêtre Edge retiré des réponses utilisateur.

Sécurité :
- aucune nouvelle action destructive ;
- météo / mises à jour non connectées dans cette version ;
- lecture des fenêtres et performances uniquement ;
- llama.cpp et modèles non modifiés.
