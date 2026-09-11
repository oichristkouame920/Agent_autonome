AgentLocal - Accès récursif contrôlé aux sous-dossiers

Nouveauté
---------
AgentLocal peut maintenant travailler dans les sous-dossiers situés sous :
- Bureau
- Documents
- Téléchargements
- Images
- Vidéos
- Musique

Exemples
--------
liste Documents\Cours\Master1
liste le dossier Fiscalité dans Documents\Cours\Master1
trouve rapport.docx
trouve le dossier Cours
lis rapport.docx
lis rapport.docx dans Documents\Cours\Master1
lis Documents\Cours\Master1\rapport.docx
renomme rapport.docx en final.docx
renomme rapport.docx en final.docx dans Documents\Cours
supprime rapport.docx
supprime rapport.docx dans Documents\Cours
copie rapport.pdf de Documents\Cours vers Bureau\Archives
déplace rapport.pdf de Documents\Cours vers Téléchargements\Travail
crée dossier Archives dans Documents\Cours
crée notes.txt dans Documents\Cours avec le contenu Bonjour
remplace le contenu de notes.txt dans Documents\Cours par Nouveau contenu
ajoute une ligne à notes.txt dans Documents\Cours avec le contenu Deuxième ligne

Sécurité
--------
- Aucun chemin absolu C:\... n'est accepté.
- Aucun chemin réseau UNC n'est accepté.
- Les composants . et .. sont refusés.
- Les jokers * et ? sont refusés.
- Les liens symboliques, junctions et reparse points sont refusés.
- Les éléments cachés et système sont refusés.
- Les opérations restent limitées aux six racines utilisateur autorisées.
- Les suppressions restent envoyées vers la Corbeille Windows uniquement.
- Les opérations de masse restent interdites.
- Les commandes fichiers restent manuelles et explicitement vérifiées.
- La recherche automatique agit seulement si une correspondance unique est trouvée pour une opération sensible.
- Profondeur maximale par défaut : 10 niveaux.
- Recherche bornée par défaut : 6000 entrées et 20 résultats.

Remarque
--------
Cette évolution concerne l'accès et la gestion contrôlée des fichiers/dossiers.
L'ouverture arbitraire d'un fichier dans son application associée n'est pas ajoutée ici,
car certains types de fichiers peuvent exécuter du contenu. Cette capacité doit rester une étape distincte.

LANGAGE NATUREL - ACCES AUX DOSSIERS
------------------------------------
Les formulations suivantes sont reconnues par le backend deterministe et
ouvrent logiquement le dossier dans AgentLocal en affichant son contenu :

- accede au dossier Jean dans Documents
- accede au dossier Jean dans Documents\Cours
- accede a Documents\Cours\Jean
- va dans le dossier Jean dans Documents
- entre dans le dossier Jean
- ouvre le dossier Jean dans Documents
- montre-moi le dossier Jean dans Documents

Si le dossier n'est pas localise dans la commande, AgentLocal effectue une
recherche recursive uniquement dans les six racines autorisees. Si plusieurs
dossiers ont le meme nom, l'agent refuse de choisir arbitrairement et demande
de preciser l'emplacement.

Cette commande ne lance pas automatiquement l'Explorateur Windows : elle
permet de naviguer dans le contenu depuis AgentLocal tout en conservant les
barrieres de securite.
