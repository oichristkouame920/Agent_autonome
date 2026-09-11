AgentLocal - langage naturel controle
=====================================

Objectif
--------
Cette version accepte des formulations francaises plus naturelles sans
ajouter de nouveaux droits a l'agent. La phrase originale reste toujours
prioritaire. Une reformulation locale n'est tentee que si la grammaire
stricte ne comprend pas la demande.

Exemples maintenant compris
---------------------------
- Peux-tu m'ouvrir GitHub s'il te plait ?
- Est-ce que tu peux ouvrir Word ?
- Tu peux me fermer Word, stp ?
- S'il te plait, cherche-moi le fichier rapport dans Documents.
- Tu peux me montrer ce qu'il y a dans mes Telechargements ?
- J'aimerais que tu ouvres le dossier Cours dans Documents.
- Je voudrais que tu lises le fichier budget dans Documents.
- Donne-moi le contenu du fichier notes.txt dans Documents.
- Peux-tu creer un dossier Factures dans Documents ?
- Est-ce que tu peux renommer rapport en rapport-final ?
- Tu peux effacer brouillon.txt ?
- Pourrais-tu dupliquer rapport.pdf de Documents vers Bureau ?
- Tu peux ranger rapport.pdf dans le dossier Archives ?
- Ou se trouve le fichier contrat ?
- Qu'est-ce qu'il y a dans mes Documents ?
- Peux-tu preparer mon environnement de travail ?
- Peux-tu lancer ma routine de travail ?
- Est-ce que tu peux verifier si Word est ouvert ?

Vocabulaire conversationnel ajoute
----------------------------------
Amorces de politesse et de demande :
- peux-tu / tu peux / pourrais-tu / est-ce que tu peux
- je voudrais / j'aimerais / je veux / j'ai besoin
- s'il te plait / s'il vous plait / stp / svp / merci de
- bonjour / salut / d'accord / alors

Pronoms naturels :
- ouvre-moi / m'ouvrir
- cherche-moi / me chercher
- montre-moi / me montrer
- etc., uniquement devant un verbe deja autorise

Synonymes explicites :
- retrouve / localise -> trouve
- efface -> supprime (toujours vers la Corbeille Windows)
- duplique -> copie
- range -> deplace
- donne-moi le contenu -> lis / affiche le contenu

Securite conservee
------------------
- aucun shell, CMD, PowerShell ou terminal arbitraire n'est ajoute ;
- aucune permission de fichiers n'est elargie ;
- aucune nouvelle application n'est autorisee ;
- les routines et habitudes gardent leurs restrictions existantes ;
- une suppression reste une suppression controlee vers la Corbeille ;
- une demande de suppression definitive reste refusee ;
- une phrase naturelle est reconvertie vers les parseurs deterministes
  existants puis validee par les memes controles de permissions ;
- les commandes contenant du texte a ecrire dans un fichier preservent ce
  texte sans supprimer la ponctuation ou une formule de politesse finale.

Tests
-----
Le fichier tests/test_natural_language.py contient 23 tests de non-regression,
de langage naturel et de securite.

Lancer les tests depuis la racine du projet :
    python -m unittest -v tests.test_natural_language

Version V2
----------
Une extension plus conversationnelle et plus stricte sur les references
ambigues est documentee dans README_NATURAL_LANGUAGE_V2.txt.
