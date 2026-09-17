AgentLocal V10.4 - Contrôle audio Windows
=========================================

Objectif
--------
Ajouter un contrôle léger et explicite du volume principal Windows 10/11,
sans PowerShell, CMD, shell, ni dépendance Python supplémentaire.

Commandes prises en charge
--------------------------
- quel est le volume ?
- le son est à combien ?
- mets le volume à 30%
- règle le son sur 55
- monte le son
- monte le son de 10%
- baisse le volume
- baisse le volume de 15%
- coupe le son
- mets le son en sourdine
- remets le son
- enlève le mode muet

Garde-fous
----------
- commande manuelle explicite obligatoire ;
- interdit aux routines et habitudes ;
- aucune modification automatique ;
- volume absolu limité à 0..100% ;
- variation relative limitée à 25% par commande ;
- "monte/baisse" sans valeur = pas de 5% ;
- le changement de volume ne modifie pas implicitement le mode muet ;
- aucun contrôle du microphone ;
- aucun shell ni argument exécutable utilisateur.

Technique
---------
Utilise Windows Core Audio / IAudioEndpointVolume via ctypes et la bibliothèque
standard Python. Aucun package supplémentaire n'est ajouté à requirements.txt.

Vérification non destructive
-----------------------------
.\.venv\Scripts\python.exe .\verifier_audio_v10_4.py

Puis tester réellement dans AgentLocal, par exemple :
  quel est le volume
  mets le volume à 30%
  monte le son
  coupe le son
  remets le son
