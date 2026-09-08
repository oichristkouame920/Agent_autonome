AgentLocal - Pont Microsoft Edge local
======================================

Objectif
--------
Permettre à AgentLocal de fermer de façon ciblée un onglet Edge,
même lorsque cet onglet a été ouvert manuellement par l'utilisateur.

Architecture
------------
AgentLocal -> app/browser_bridge.py -> fichiers IPC locaux sous
%LOCALAPPDATA%\AgentLocalBridge -> hôte Native Messaging -> extension Edge
-> API chrome.tabs.

Aucune API cloud n'est utilisée.

Installation une seule fois
----------------------------
Depuis la racine AgentLocal :

  .\.venv\Scripts\python.exe .\agent_tools\edge_bridge\setup_edge_bridge.py

Le script :
- compile browser_native_host\agentlocal_native_host.c ;
- crée agentlocal_native_host.exe ;
- enregistre le manifeste Native Messaging sous HKCU seulement ;
- crée la configuration locale du pont.

Ensuite dans Microsoft Edge :

1. Ouvrir edge://extensions/
2. Activer Mode développeur.
3. Cliquer Charger l'extension décompressée.
4. Sélectionner le dossier :

   C:\Users\<utilisateur>\AgentLocal\browser_extension

5. Vérifier l'ID :

   odhigmilcgpndpjgjkbfmpoiiblklcgf

Test
----
Fermer puis rouvrir Edge si nécessaire, puis exécuter :

  .\.venv\Scripts\python.exe .\agent_tools\edge_bridge\test_edge_bridge.py

Le test doit afficher :

  Ping : OK
  Lecture des onglets : OK

Utilisation
-----------
Dans AgentLocal :

  ferme le site YouTube
  ferme le site GitHub
  ferme le site ChatGPT

L'extension vérifie l'URL réelle des onglets avant fermeture.

Sécurité
--------
- Hôte enregistré sous HKEY_CURRENT_USER, pas besoin d'administrateur.
- Extension autorisée explicitement dans le manifeste Native Messaging.
- Uniquement les actions close_site, list_tabs et ping sont implémentées.
- Les URL edge://, file:// et autres protocoles non HTTP(S) sont ignorées.
- Maximum 10 onglets fermés par commande, même si la configuration est modifiée.
- AgentLocal conserve sa validation de commande explicite avant fermeture.
- Le pont n'utilise ni taskkill, ni PowerShell, ni CMD à l'exécution.

Désinstallation du pont natif
-----------------------------

  .\.venv\Scripts\python.exe .\agent_tools\edge_bridge\setup_edge_bridge.py --uninstall

L'extension Edge doit ensuite être retirée manuellement depuis edge://extensions/.
