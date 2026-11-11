AgentLocal V11.8.3 - STABILISATION TERRAIN - PACK COMPLET UNIFIE
Build : 2026-11-10-v11.8.3-terrain-stabilization

Cette version consolide V11.8.2 et corrige les anomalies observées en usage réel.

CORRECTIFS V11.8.3
- « quel est l'état de ma connexion ? » compris directement.
- « quelle est ta performance ? » affiche l'état d'AgentLocal lui-même.
- « quelles sont les fenêtres actives ? » liste les fenêtres visibles en lecture seule.
- météo reconnue sans être détournée vers une recherche de fichiers.
- demandes de mises à jour reconnues sans exécution implicite.
- demandes de planification d'habitudes reconnues sans créer automatiquement une tâche.
- CPU des processus normalisé à 0..100 % machine.
- System Idle Process exclu des processus gourmands.
- sélection numérique d'un onglet > 3 après la liste, pour les sites connus.
- détection/fermeture de Pense-bêtes renforcée.
- messages techniques Edge inutiles retirés des réponses utilisateur.

CE QUI N'EST PAS ENCORE ACTIVE
- météo Internet réelle ;
- actualités ;
- contrôle centralisé des mises à jour ;
- planification horaire autonome.
Ces éléments sont réservés à la phase connectée suivante.

SECURITE
- aucune nouvelle action destructive ;
- lecture seule pour performances, processus, fenêtres et réseau ;
- aucun shell arbitraire ;
- aucune modification de llama.cpp ou des modèles GGUF.

INSTALLATION
1. Sauvegarder le projet actuel avec Git.
2. Extraire ce pack à la racine de C:\Users\cdn09\AgentLocal.
3. Accepter les remplacements.
4. Si Windows marque les fichiers comme téléchargés, débloquer le dossier.
5. Lancer uniquement AgentLocal.bat.
6. Choisir 4 - Vérifier / finaliser l'installation.

VALIDATION AVANT LIVRAISON
- 307 tests unittest : OK
- 25 vérificateurs AgentLocal : OK
- compilation Python : OK
- JSON : OK
