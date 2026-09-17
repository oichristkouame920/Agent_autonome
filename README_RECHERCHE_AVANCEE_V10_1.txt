AgentLocal - V10.1 Recherche locale avancée contrôlée
====================================================

Base : V9 Langage naturel & sphère de parole.

OBJECTIF
--------
Ajouter une recherche de fichiers plus utile sans augmenter l'autonomie de l'agent.
Cette évolution est en LECTURE SEULE et travaille uniquement sur les métadonnées.

EXEMPLES RECONNUS
-----------------
- montre-moi les PDF téléchargés aujourd'hui
- retrouve les fichiers Word modifiés cette semaine
- quels sont mes derniers fichiers ?
- montre-moi les 5 fichiers les plus récents
- montre les 5 fichiers les plus gros dans Téléchargements
- montre les fichiers de plus de 100 Mo dans Téléchargements
- combien j'ai de PDF dans Documents ?
- j'ai combien de PDF dans Documents ?
- retrouve les images créées hier
- cherche les fichiers Excel dans Documents et ses sous-dossiers
- qu'est-ce que j'ai téléchargé aujourd'hui ?

FILTRES DISPONIBLES
-------------------
Types : tout fichier, PDF, Word, Excel, PowerPoint, image, vidéo, audio, texte.
Dates : aujourd'hui, hier, cette semaine, 7 derniers jours.
Date utilisée : modification ou création lorsque la phrase le demande.
Taille : plus de / moins de Ko, Mo ou Go.
Tri : fichiers récents, fichiers créés récemment, fichiers les plus gros, nom.
Comptage : ex. « combien j'ai de PDF dans Documents ? ».

GARDE-FOUS
----------
- Lecture seule : aucun fichier n'est ouvert, modifié, déplacé ou supprimé par cette fonction.
- Métadonnées uniquement : nom, extension, taille, dates et emplacement autorisé.
- Racines autorisées seulement : Bureau, Documents, Téléchargements, Images, Vidéos, Musique.
- Pas de chemin absolu fourni par l'utilisateur.
- Pas de fichiers cachés/système, reparse points, junctions ou symlinks suivis.
- Pas de routine ni d'habitude.
- Pas de recherche automatique : commande manuelle explicite obligatoire.
- Limite de 6 000 entrées scannées et 20 résultats affichables maximum.
- Profondeur maximale : 10.
- La commande brute doit reproduire exactement le contrat déterministe avant exécution.

COMPATIBILITÉ
-------------
- Windows 10 / Windows 11
- Conçu pour rester léger sur une machine de 4 Go de RAM
- Aucun indexeur permanent ajouté
- Aucun nouveau package Python requis

INSTALLATION
------------
1. Fermer AgentLocal.
2. Extraire directement le contenu du ZIP dans :
   C:\Users\cdn09\AgentLocal
3. Accepter le remplacement des fichiers concernés.
4. Vérifier :
   .\.venv\Scripts\python.exe .\verifier_recherche_avancee_v10_1.py
5. Relancer :
   .\lancer_agentlocal_gui.bat

Cette version ne remplace pas les fonctions existantes de recherche par nom :
« cherche rapport.pdf » continue d'utiliser la recherche de fichier normale.
