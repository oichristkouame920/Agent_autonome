AgentLocal - Gestion controlee des fenetres
Version : 11 septembre 2026

Objectif
--------
Ajouter un controle simple de la disposition des fenetres Windows sans donner a
l'agent une autonomie generale sur le Bureau.

Commandes prises en charge
--------------------------
- Mets VS Code a gauche
- Place Edge a droite
- Agrandis Word
- Reduis Excel
- Restaure PowerPoint
- Mets Outlook au premier plan
- Passe sur VS Code
- Mets VS Code a gauche et Edge a droite

Operations techniques autorisees
---------------------------------
- focus
- maximize
- minimize
- restore
- snap_left
- snap_right

Garde-fous
----------
1. Une commande utilisateur explicite est obligatoire.
2. Seules les applications presentes dans la liste blanche de
   config/permissions.json peuvent etre gerees.
3. Une application fermee n'est jamais lancee automatiquement par une commande
   de gestion de fenetre.
4. Si plusieurs fenetres visibles de la meme application sont ouvertes,
   AgentLocal refuse de choisir arbitrairement laquelle modifier.
5. Les routines ne peuvent pas deplacer ou redimensionner les fenetres.
6. Les habitudes ne peuvent pas apprendre ces actions.
7. Les commandes globales comme "reduis toutes les fenetres" ne sont pas prises
   en charge.
8. "Mets VS Code et Edge cote a cote" est volontairement refuse : l'utilisateur
   doit preciser quelle application va a gauche et laquelle va a droite.
9. Aucun shell, PowerShell, CMD, terminal, taskkill ou lancement arbitraire n'est
   utilise.
10. Avant l'action, le handle de fenetre est revalide avec le PID et le temps de
    creation du processus lorsque disponible.

Applications autorisees dans cette version
------------------------------------------
Edge, VS Code, Explorateur, Android Studio, Bloc-notes, Calculatrice, Paint,
Teams, Word, Excel, PowerPoint, Outlook et OneNote.

Configuration
-------------
La section "window_management" de config/permissions.json controle la fonction.
Elle est activee mais reste deny-by-default, manuelle uniquement, sans routines,
sans habitudes et sans auto-lancement d'application.
