AGENTLOCAL - CORRECTIF V12.5.2 : COMPORTEMENT EN PLUSIEURS ETAPES
=================================================================

Ce correctif se superpose a la version V12.5.1 existante.
Il ne remplace pas le modele IA et ne modifie pas les permissions.

Ameliorations
- Execution encadree des demandes enchainant des commandes explicites avec
  « puis », « ensuite », « et apres » ou « ; » (4 etapes maximum).
- Verification de TOUTES les etapes avant la premiere execution : une
  etape incomprise, non autorisee ou ambigue bloque l'ensemble.
- Seules les actions de consultation et les ouvertures d'applications ou
  sites sont autorisees dans ce mode. Operations sur fichiers, fermetures,
  routines et autres operations sensibles restent en commandes individuelles.
- Respect de la politique de preuve explicite pour chaque etape.
- Arret a la premiere erreur d'execution, avec restitution etape par etape.
- Resume de la derniere sequence en memoire vive (pas de persistance).
- Reprises conversationnelles plus naturelles pour les applications et sites
  deja manipules ("rouvre-le", "relance-la", "reviens dessus").
- Les connecteurs incomplets en fin de commande ("ouvre Word puis",
  "ouvre Word ensuite", "ouvre Word et apres") sont bloques sans action.
- Pas de changement de fonctionnement pour les commandes simples ou celles
  qui contiennent uniquement "et".

Exemples
- « ouvre Word puis ouvre Excel »
- « liste mes Documents, ensuite montre l'etat de mon PC »
- « ouvre GitHub puis ouvre Teams »
- « resume les dernieres etapes »

LIMITES
- Ce patch n'ajoute pas la saisie automatique de texte dans Word/Excel.
- Les actions de modification et de suppression restent unitaires.
- Le modele local GGUF et le runtime Windows ne peuvent etre testes sous Linux.
- Tests sur une copie avant installation sur le PC recommandees.

INSTALLATION
Extraire le ZIP dans le dossier AgentLocal, sans ecraser ses fichiers.
Fermer AgentLocal et executer depuis le sous-dossier AgentLocal_V12_5_2_PATCH le fichier
INSTALLER_V12_5_2.bat. Le programme verifie les empreintes SHA-256 du correctif,
garde une sauvegarde et peut restaurer (option --rollback).
Une version locale modifiee n est pas ecrasee.

TESTS
Depuis le dossier AgentLocal : AgentLocal.bat test
Le patch ajoute tests/test_v12_5_2_behavior.py et tests/test_v12_5_2_stress.py.
