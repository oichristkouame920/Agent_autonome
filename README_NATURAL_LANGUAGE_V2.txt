AgentLocal - langage naturel controle V2
========================================
Date de reference : 11 septembre 2026

Objectif
--------
Rendre AgentLocal plus naturel a utiliser en francais tout en conservant
le meme modele de securite : aucune phrase naturelle ne cree un nouveau
droit. Les reformulations sont locales, deterministes et repassent par
les memes parseurs, contrats et permissions qu'avant.

Ce qui est ajoute
-----------------
1. Demandes indirectes simples
   - J'ai besoin du rapport que j'ai mis dans Documents
     -> recherche du fichier rapport dans Documents
   - Ouvre-moi le rapport qui est dans Documents
     -> ouverture controlee du fichier rapport dans Documents
   - Va me chercher rapport.pdf dans Telechargements
     -> recherche controlee

2. Formulations conversationnelles
   - Tu veux bien ouvrir Excel ?
   - Est-ce possible de fermer Word ?
   - Fais voir ce qu'il y a dans Documents
   - Je peux voir les documents ?
   - Est ce que Word tourne ?

3. Intentions fonctionnelles vers un catalogue ferme
   - ecrire/rediger un document -> Word
   - faire un tableur/tableau Excel -> Excel
   - preparer une presentation -> PowerPoint
   - faire des calculs -> Calculatrice
   - faire une capture d'ecran -> Outil Capture
   - dessiner/retoucher une image -> Paint

   Cette deduction reste volontairement limitee a ces cas explicites.
   Une demande fonctionnelle inconnue n'est pas executee.

4. Enchainements de cibles
   - ouvre Word puis GitHub
   - ouvre Word et ensuite GitHub
   - ouvre Word ainsi que GitHub

5. Quelques fautes connues sur des cibles autorisees
   - gitub / githb / gihub -> github
   - exel -> excel
   - vscod -> vscode
   - outlok -> outlook
   - teems -> teams
   - ondrive -> onedrive
   - chatgtp -> chatgpt

   Important : les noms de fichiers et dossiers ne sont jamais corriges
   automatiquement. "rapprot" reste "rapprot" si c'est le nom demande.

6. Petites conversations locales
   - bonjour / salut
   - merci
   - ca va ?
   - aide / tu sais faire quoi ?
   - tu es qui ?

   Ces reponses ne lancent aucune action.

7. Interface plus naturelle
   - invite : "Que veux-tu faire ?"
   - message d'incomprehension reformule
   - correction du texte d'arret de l'agent

Securite renforcee
------------------
- PowerShell, CMD, Windows Terminal, terminal, Bash et WSL ne peuvent pas
  etre interpretes comme de simples sites ou comme des noms de fichiers a
  ouvrir lorsqu'ils sont demandes comme outils d'execution.
- "ouvre ce fichier", "supprime le fichier", "renomme le fichier...",
  "deplace le fichier..." et autres references vagues sont refusees tant
  qu'un nom clair n'est pas donne.
- La suppression definitive reste refusee.
- Les suppressions autorisees restent dirigees vers la Corbeille Windows.
- Aucun shell arbitraire n'est ajoute.
- Aucune permission fichier n'est elargie.
- Aucune nouvelle application arbitraire n'est autorisee.
- Les routines et habitudes conservent leurs restrictions.
- Le texte utilisateur ecrit dans un fichier est preserve tel quel.

Exemples
--------
Peux-tu m'ouvrir le truc pour ecrire un document ?
Ouvre le rapport qui est dans Documents.
J'ai besoin du rapport que j'ai mis dans Documents.
Montre-moi mes fichiers dans Documents.
Est ce que Word tourne ?
Ouvre Word puis GitHub.
Mets rapport.pdf dans Archives.
Jette brouillon.txt.
Bonjour.
Tu sais faire quoi ?

References vagues volontairement refusees
------------------------------------------
ouvre ce fichier
supprime le fichier
lis le fichier
renomme le fichier en test.txt
deplace le fichier dans Archives

AgentLocal demande ainsi un nom clair au lieu de deviner une cible.

Tests
-----
- tests/test_natural_language.py : tests V1 et non-regression
- tests/test_natural_language_v2.py : tests V2, ambiguite et securite

Total valide au moment de la livraison : 73 tests.

Commande de test :
    python -m unittest -v tests.test_natural_language tests.test_natural_language_v2
