AGENTLOCAL - PONT EDGE HTTP LOCAL
=================================

OBJECTIF
--------
Permettre à AgentLocal de voir et fermer précisément les onglets Microsoft Edge,
y compris ceux ouverts manuellement, sans Native Messaging et sans exécutable
non signé.

Cette version remplace l'ancien hôte natif agentlocal_native_host.exe.

ARCHITECTURE
------------
AgentLocal (Python)
    |
    | HTTP local authentifié
    | 127.0.0.1 uniquement
    v
Extension Edge
    |
    +-- chrome.tabs.query()
    +-- chrome.tabs.remove()

Aucun cloud.
Aucune API externe.
Aucun PowerShell ou CMD arbitraire.
Aucun taskkill.
Aucune désactivation de Smart App Control.

WINDOWS
-------
Compatible avec Windows 10 et Windows 11.

FICHIERS AJOUTES / MODIFIES
---------------------------
app/browser_bridge.py
app/browser_bridge_server.py
app/web_tools.py
browser_extension/manifest.json
browser_extension/background.js
browser_extension/bridge_config.example.js
config/browser_bridge.example.json
config/permissions.json
agent_tools/edge_bridge/setup_edge_bridge.py
agent_tools/edge_bridge/test_edge_bridge.py
requirements.txt
.gitignore

L'ancien dossier browser_native_host n'est plus utilisé et a été retiré du projet.

INSTALLATION
------------
Depuis :
C:\Users\cdn09\AgentLocal

1. Installer les dépendances Python :

.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt

2. Générer la configuration locale du pont :

.\.venv\Scripts\python.exe .\agent_tools\edge_bridge\setup_edge_bridge.py

Cette commande génère localement :
- config\browser_bridge.json
- browser_extension\bridge_config.js

Ces deux fichiers contiennent un secret local et sont ignorés par Git.

3. Dans Edge :

edge://extensions/

- Active "Mode développeur".
- Si l'ancienne extension AgentLocal est déjà chargée, clique sur "Recharger".
- Sinon clique sur "Charger l'extension décompressée".
- Sélectionne :
  C:\Users\cdn09\AgentLocal\browser_extension

ID attendu :
odhigmilcgpndpjgjkbfmpoiiblklcgf

4. Tester :

.\.venv\Scripts\python.exe .\agent_tools\edge_bridge\test_edge_bridge.py

Résultat attendu :

Ping : OK
Pont Edge HTTP AgentLocal opérationnel.

Lecture des onglets : OK

5. Lancer AgentLocal :

.\.venv\Scripts\python.exe .\app\agent.py

Puis tester :

ferme le site YouTube

YouTube peut avoir été ouvert manuellement.

SECURITE
--------
- Serveur lié uniquement à 127.0.0.1.
- Secret aléatoire de 256 bits généré par setup_edge_bridge.py.
- CORS limité à l'ID exact de l'extension.
- Extension ID transmis et vérifié à chaque requête.
- Schéma d'actions fermé : ping, list_tabs, close_site, activate_site.
- Aucun JavaScript arbitraire dans les pages.
- Aucun shell.
- Maximum de 10 onglets fermés par commande.
- Les URL sont vérifiées par l'extension via chrome.tabs.

GIT
---
Ne pas versionner :
config/browser_bridge.json
browser_extension/bridge_config.js

Ils sont déjà ajoutés à .gitignore.

SMART APP CONTROL
-----------------
Smart App Control peut rester activé.
Aucun agentlocal_native_host.exe n'est requis par cette architecture.
