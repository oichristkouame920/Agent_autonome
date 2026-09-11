AgentLocal - Actions locales V1 controlees
Date : 11 septembre 2026

OBJECTIF
=======
Elargir le champ d'action sans augmenter l'autonomie implicite.
Toutes les nouvelles actions exigent une commande manuelle explicite.
Elles ne sont ni lancees par une routine, ni apprises comme habitudes.

1) INFORMATIONS SYSTEME - LECTURE SEULE
=======================================
Exemples :
- j'utilise combien de RAM ?
- regarde un peu combien d'espace il reste sur mon disque
- mon processeur travaille a combien ?
- depuis combien de temps le PC est allume ?
- donne-moi l'etat du PC

Aucune modification du systeme n'est effectuee.

2) PRESSE-PAPIERS TEXTE CONTROLE
================================
Exemples :
- qu'est-ce que j'ai copie ?
- copie ce texte : Bonjour
- copie dans le presse-papiers : https://example.com/
- copie le chemin de rapport.pdf dans Documents

Limites :
- texte uniquement ;
- 8192 caracteres maximum ;
- aucun contenu du presse-papiers n'est execute ;
- aucun lien du presse-papiers n'est ouvert automatiquement ;
- les chemins de fichiers sont limites aux racines utilisateur autorisees ;
- les types de fichiers proteges restent bloques.

3) ONGLETS EDGE VIA LE PONT LOCAL EXISTANT
==========================================
Exemples :
- liste mes onglets
- y a quoi d'ouvert dans Edge ?
- passe sur l'onglet GitHub

Limites :
- Edge uniquement ;
- pont HTTP local AgentLocal obligatoire ;
- 20 onglets maximum affiches ;
- le listing affiche le titre et le domaine, pas l'URL complete ;
- cette politique n'ajoute pas de droit de fermeture d'onglet.

4) MEMOIRE CONVERSATIONNELLE TEMPORAIRE
========================================
Exemple :
- retrouve rapport.pdf dans Documents
- ouvre-le
- lis-le
- copie son chemin

La memoire :
- garde une seule reference ;
- reste uniquement en RAM ;
- n'est jamais ecrite dans memory/ ;
- disparait a la fermeture d'AgentLocal ;
- ne permet pas "supprime-le", "deplace-le" ou "renomme-le".

SECURITE
========
Les nouvelles politiques se trouvent dans config/permissions.json :
- system_information_policy
- clipboard_policy
- browser_tab_policy
- session_context_policy

Toutes utilisent require_explicit_user_command=true et interdisent routines/habitudes.
La politique presse-papiers interdit explicitement l'execution et l'ouverture de son contenu.

COMPATIBILITE
=============
- Windows 10/11 64 bits
- objectif 4 Go de RAM
- aucune interface graphique supplementaire
- presse-papiers via API Windows, sans PowerShell/CMD
- psutil est deja utilise par windows_tools.py ; requirements.txt le declare maintenant explicitement

VERIFICATION
============
Depuis C:\Users\cdn09\AgentLocal :

.\.venv\Scripts\python.exe .\verifier_actions_locales_v1.py

Puis lancer l'interface :

.\lancer_agentlocal_gui.bat
