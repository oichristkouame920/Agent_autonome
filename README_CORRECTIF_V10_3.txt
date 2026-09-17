AgentLocal V10.3 - Correctif d'intégration
=========================================

Ce paquet corrige l'erreur:
ImportError: cannot import name 'open_site_via_bridge' from 'browser_bridge'

Cause:
Le premier ZIP V10.3 n'embarquait pas app/browser_bridge.py de la V10.2,
alors que app/controlled_local_tools.py utilise open_site_via_bridge.

Ce paquet inclut désormais ensemble:
- app/agent.py
- app/controlled_local_tools.py
- app/browser_bridge.py
- backends/backend_manager.py
- backends/deterministic_backend.py
- browser_extension/background.js et manifest.json
- config/permissions.json
- tests/test_screenshot_v10_3.py
- verifier_capture_v10_3.py
- verifier_v10_3_corrige.py

Il ne contient pas:
- memory/
- logs/
- .venv/
- modèles
- secrets du pont Edge

Installation:
1. Fermer AgentLocal.
2. Extraire le contenu directement dans C:\Users\cdn09\AgentLocal.
3. Accepter le remplacement.
4. Recharger l'extension AgentLocal dans edge://extensions/.
5. Exécuter:
   .\.venv\Scripts\python.exe .\verifier_v10_3_corrige.py
6. Puis lancer:
   .\lancer_agentlocal_gui.bat
