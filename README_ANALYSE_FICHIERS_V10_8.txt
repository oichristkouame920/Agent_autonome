AgentLocal V10.8 - Analyse locale des fichiers
==============================================

Nouvelles commandes manuelles en lecture seule :

- donne moi les infos de rapport.pdf dans Documents
- calcule le sha256 de rapport.pdf dans Documents
- compare a.txt et b.txt dans Documents
- cherche les doublons dans Documents
- trouve les fichiers en double dans Téléchargements
- y a des doublons dans Documents

Sécurité :
- aucune suppression ni modification de fichier ;
- commandes manuelles explicites uniquement ;
- routines et habitudes interdites ;
- uniquement les six racines utilisateur autorisées ;
- aucune sélection automatique entre plusieurs fichiers du même nom ;
- hash calculé par blocs, sans charger le fichier entier en RAM ;
- fichiers protégés exclus du hash par défaut ;
- recherche de doublons bornée en profondeur, nombre d'entrées et volume total lu ;
- aucun doublon n'est supprimé automatiquement.

Limites par défaut :
- fichier individuel hashé : 512 Mo maximum ;
- recherche de doublons : 4000 entrées maximum ;
- volume total hashé : 2 Go maximum ;
- 20 groupes de doublons affichés maximum ;
- profondeur : 10 niveaux maximum.

Vérification :
  .\.venv\Scripts\python.exe .\verifier_analyse_fichiers_v10_8.py
