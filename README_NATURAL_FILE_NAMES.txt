AgentLocal - references naturelles de fichiers

Cette version permet de designer un fichier :
- sans extension : "ouvre rapport" peut trouver "rapport.pdf" ;
- avec une partie du nom : "ouvre rapport final" peut trouver "Rapport final 2026.docx" ;
- avec un emplacement explicite : "lis budget dans Documents" ;
- dans un sous-dossier : "ouvre rapport dans Documents\Cours".

Regles de securite :
- une correspondance exacte est toujours prioritaire ;
- un nom sans extension exact est prioritaire sur une correspondance partielle ;
- une correspondance partielle exige au moins 3 caracteres significatifs ;
- si plusieurs fichiers correspondent, AgentLocal refuse de choisir et demande de preciser ;
- aucune correction floue de faute de frappe n'est utilisee pour choisir un fichier ;
- la recherche reste limitee aux six racines utilisateur autorisees et a leurs sous-dossiers ;
- liens symboliques, junctions, reparse points, fichiers caches/systeme et zones protegees restent bloques ;
- les fichiers executables/scripts/raccourcis restent bloques.

Renommage :
"renomme test-modif en christ" localise par exemple test-modif.txt et le renomme christ.txt.
Si la nouvelle extension n'est pas ecrite, l'extension originale est conservee.
Une extension explicitement differente reste refusee.

Creation :
La creation d'un nouveau fichier continue a demander une extension, car il n'existe aucun fichier source dont AgentLocal pourrait deduire le format.
