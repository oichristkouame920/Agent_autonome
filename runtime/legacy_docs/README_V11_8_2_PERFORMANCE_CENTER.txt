AgentLocal V11.8.2 - Centre de performances
Build : 2026-11-10-v11.8.2-performance-center

Objectif
- Transformer « état du PC » en point d'entrée de diagnostic, inspiré du panneau Performance de Windows + G.
- Rester léger, local et en lecture seule.
- Proposer des actions concrètes sur les performances, les processus et les fichiers.

Nouveautés
1. Après « état du PC », AgentLocal propose :
   - Voir les processus les plus gourmands.
   - Chercher les fichiers les plus lourds.
   - Ouvrir le tableau de performances.
2. Nouveau tableau de performances : CPU, RAM, disque système, nombre de processus et uptime.
3. Nouveau diagnostic processus en lecture seule :
   - processus les plus gourmands ;
   - tri CPU ;
   - tri RAM ;
   - nombre de processus actifs.
4. Les diagnostics processus passent par le fast-path déterministe et ne sondent pas llama.cpp.
5. Les suggestions restent limitées à trois actions concrètes et interprétables.
6. Aucune permission de fermeture/arrêt de processus n'est accordée par ce module.
7. llama.cpp n'est pas modifié.

Sécurité
- process_information_policy est strictement read_only.
- allow_process_termination = false.
- aucune routine ou habitude ne peut déclencher automatiquement ce diagnostic.
