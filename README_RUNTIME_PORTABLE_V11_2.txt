AgentLocal V11.2 - Runtime et modele portables
===============================================

Objectif
--------
AgentLocal ne doit dependre d'aucun chemin absolu lie au PC d'origine.
Le dossier complet peut etre deplace vers un autre emplacement ou un autre
PC Windows 10/11 sans modifier les chemins internes.

1. Modele local
---------------
Le modele actif est declare dans config/models.json avec un chemin relatif :
  models/Qwen3.5-0.8B-Q4_0.gguf

Les fichiers annexes d'un futur modele peuvent etre declares avec :
  "companions": ["models/fichier-annexe.gguf"]

Un modele multimodal peut aussi declarer :
  "mmproj": "models/mmproj.gguf"

Aucun chemin absolu n'est accepte par le gestionnaire de chemins.

2. Runtime llama.cpp
--------------------
Le runtime complet reste dans :
  tools/llama.cpp/

Il faut deplacer le dossier entier avec llama-cli.exe et toutes les DLL de la
meme build. Le diagnostic V11.2 lance "llama-cli.exe --version" sous Windows :
si une DLL manque, le runtime est signale comme inutilisable avant le chargement
du modele.

3. Python
---------
Le lanceur suit cet ordre :
  1) runtime/python/python.exe        (mode portable complet)
  2) .venv/Scripts/python.exe        (environnement local recreable)
  3) venv/Scripts/python.exe         (compatibilite ancienne)
  4) Python installe dans Windows    (dernier recours)

Le dossier .venv n'est PAS considere comme portable entre deux machines.

4. Construire un Python portable
--------------------------------
Sur le PC actuel :
  a) preparer_dependances_offline.bat
  b) preparer_runtime_python_portable.bat

Le premier script telecharge les wheels correspondant au Python/Windows actuel
dans vendor/wheels. Le second copie le runtime Python local dans runtime/python
et y installe les dependances. Une fois construit, runtime/python voyage avec
AgentLocal et le lanceur l'utilise automatiquement.

Pour reconstruire :
  preparer_runtime_python_portable.bat --force

Si aucun cache wheel n'a ete prepare et que l'acces Internet est autorise :
  preparer_runtime_python_portable.bat --allow-online

5. Nouvelle machine sans runtime Python embarque
-------------------------------------------------
Executer :
  preparer_agentlocal_nouveau_pc.bat

Le script cree .venv avec un Python deja installe sur la machine. S'il trouve
des wheels dans vendor/wheels, l'installation des dependances se fait sans
Internet.

6. Verification
---------------
Commande normale :
  .\.venv\Scripts\python.exe verifier_runtime_v11_2.py

Verification stricte (exige runtime/python) :
  .\.venv\Scripts\python.exe verifier_runtime_v11_2.py --strict-portable

Le diagnostic verifie : chemins relatifs, JSON, Tkinter, psutil, pypdf, runtime
Python portable, cache offline, modele actif, fichiers annexes et llama.cpp.

7. Elements a transporter pour un AgentLocal autonome
------------------------------------------------------
  app/
  backends/
  config/
  runtime/python/             si construit
  tools/llama.cpp/            dossier complet + DLL
  models/                     modele GGUF + annexes
  vendor/wheels/              recommande pour reinstallation offline
  requirements.txt
  lancer_agentlocal_gui.bat

Les chemins sont tous relatifs a la racine AgentLocal.

8. Elements lies a une machine/utilisateur
------------------------------------------
Ne pas recopier si l'objectif est une installation propre :
  memory/
  logs/
  .venv/
  secrets/tokens locaux du pont Edge

Ces elements doivent etre recrees sur la nouvelle machine selon les besoins.
