AgentLocal V10.3 - Capture d'écran contrôlée
============================================

Base : AgentLocal V10.2 - Retours terrain.

Nouveauté
---------
AgentLocal peut désormais effectuer une capture locale uniquement après une
commande utilisateur explicite.

Commandes exemples :
- fais une capture d'écran
- capture tout l'écran
- capture mon écran
- prends une capture de tout l'écran
- capture la fenêtre active
- fais une capture de la fenêtre active
- capture cette fenêtre

Destination
-----------
Les images sont enregistrées en PNG dans :
Images\\Captures AgentLocal\\

Sécurité
--------
- Windows 10/11.
- Aucun PowerShell, CMD ou shell.
- Aucune dépendance Python supplémentaire.
- Capture réalisée par API Windows GDI.
- Commande manuelle explicite obligatoire.
- Interdite aux routines et habitudes.
- Aucune capture automatique.
- Deux modes uniquement : écran complet / fenêtre active.
- Limite de pixels configurée dans permissions.json.
- La capture n'est ni envoyée sur Internet ni placée automatiquement dans le
  presse-papiers.

Remarque multi-écrans
---------------------
"capture tout l'écran" utilise le bureau virtuel Windows. Si plusieurs écrans
sont connectés, ils peuvent donc apparaître dans une même capture.

Vérification non destructive
-----------------------------
Depuis C:\\Users\\cdn09\\AgentLocal :

.\\.venv\\Scripts\\python.exe .\\verifier_capture_v10_3.py

Le vérificateur ne prend aucune vraie capture.
