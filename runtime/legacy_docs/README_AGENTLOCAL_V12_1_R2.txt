AGENTLOCAL V12.1 R2 - CORRECTION APPROFONDIE / DURCISSEMENT
=============================================================

Cette revision remplace le pack V12.1 precedent. Elle conserve les fonctions
V12.1 et ajoute une verification plus stricte des erreurs, de la persistance,
des services Internet et des planifications.

CORRECTIFS APPROFONDIS
- Validation de chaque planification relue depuis memory/schedules.json avant
  qu'elle puisse etre consideree pour execution.
- Une planification modifiee manuellement avec enabled=true mais jamais
  confirmee est automatiquement neutralisee.
- Les types/cibles/declarations horaires invalides sont ignores avant execution.
- Un schedules.json corrompu est sauvegarde sous schedules.corrupt-*.json puis
  remplace par une configuration sure, au lieu de faire echouer AgentLocal.
- Ecriture atomique et fsync du fichier de planifications.
- Limite a 64 planifications pour eviter une croissance non bornee.
- Une planification identique soumise deux fois n'est plus dupliquee.
- Verrou journalier inter-processus : deux interfaces AgentLocal ouvertes en
  meme temps ne peuvent pas executer deux fois la meme planification.
- Les resultats persistants sont bornes en taille.

SERVICES INTERNET DURCIS
- HTTPS et liste blanche existante conserves.
- Rejet des URL contenant des identifiants ou un port non autorise.
- Taille de reponse bornee, y compris via Content-Length.
- Cache copie les objets pour eviter qu'une reponse modifiee en memoire ne
  corrompe la valeur cachee.
- Validation plus stricte des valeurs meteo.
- Le rendu meteo reste stable meme en presence de donnees partielles.
- Rejet des flux RSS contenant un DOCTYPE.
- Validation du SHA renvoye par GitHub avant toute comparaison.
- Ecriture atomique de l'etat du briefing matinal.

SECURITE PLANIFICATEUR
- Actions planifiables : routine confirmee, briefing lecture seule, resume des
  habitudes.
- Confirmation humaine obligatoire avant activation.
- Aucune commande arbitraire, aucun shell, aucune action destructive planifiee.
- Le verrou d'execution privilegie l'absence de double action : si une instance
  reserve une execution puis s'arrete brutalement, cette execution n'est pas
  relancee automatiquement le meme jour.

TESTS
- 347 tests Python unittest valides dans le pack de production.
- Tous les verifier_*.py valides avec les diagnostics runtime en mode startup.
- Nouveau verifier_v12_1_r2_deep_hardening.py.

DONNEES LOCALES PRESERVEES
Le ZIP ne contient pas :
- llama.cpp ;
- modele GGUF ;
- .venv ;
- memory/schedules.json ;
- logs utilisateur.

INSTALLATION
1. Sauvegarder/commit Git de l'etat actuel.
2. Extraire le ZIP a la racine de C:\Users\cdn09\AgentLocal.
3. Accepter les remplacements.
4. Si Windows marque les fichiers Internet :
   Get-ChildItem "C:\Users\cdn09\AgentLocal" -Recurse -File | Unblock-File
5. Lancer AgentLocal.bat.
6. Choisir 4 - Verifier / finaliser l'installation.
7. Puis 1 - Lancer AgentLocal.

VERSION
- AGENTLOCAL_VERSION : 12.1
- Build R2 : deep-hardening / connected-services / controlled-scheduler
