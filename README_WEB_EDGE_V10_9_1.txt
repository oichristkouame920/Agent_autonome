AgentLocal V10.9.1 - Correctif ouverture Web dans Edge existant

Comportement manuel :
- Si Edge est déjà ouvert, AgentLocal essaie d'abord le pont local pour créer un nouvel onglet dans la fenêtre Edge existante.
- Si le pont local ne répond pas, AgentLocal utilise msedge.exe avec l'URL SANS --new-window. Edge transmet normalement l'URL à son instance existante.
- Si aucune fenêtre Edge n'existe, AgentLocal peut ouvrir une nouvelle fenêtre Edge.
- Une politique explicitement désactivée dans permissions.json reste prioritaire.
- Les routines conservent leur logique antérieure.

Sécurité :
- shell=False
- aucune commande PowerShell/CMD
- URL déjà résolue et validée par AgentLocal
- aucun argument libre utilisateur transmis à Edge
