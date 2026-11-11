AgentLocal V12.1 R4 - Mise a jour atomique et correction approfondie

Cette revision corrige le probleme de fichiers legacy qui pouvaient survivre aux mises a jour par simple extraction.

Points principaux :
- AgentLocal.bat sans BOM UTF-8 pour que @echo off fonctionne correctement sous cmd.exe.
- Archivage generique de tous les anciens verifier_conformite_pack_*.py, sauf verifier_conformite_pack_v12.py.
- Le runner tester_agentlocal.ps1 ignore defensivement tous les anciens verificateurs de conformite.
- Installateur R4 recommande pour forcer le remplacement des fichiers critiques tout en preservant les reglages locaux.
- Aucun llama.cpp, modele GGUF, .venv, log ou memoire utilisateur n'est fourni dans le payload.

Lanceur utilisateur apres installation : AgentLocal.bat
