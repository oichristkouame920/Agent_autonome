AgentLocal V11 - LLM local interchangeable
============================================

Objectif
--------
Découpler complètement le modèle GGUF du code Python.
Le modèle actif se choisit dans config/models.json.

Principe de sécurité
--------------------
Le LLM ne produit jamais directement une action Windows.
Il reformule d'abord la demande en commande canonique.
Cette commande est ensuite réinterprétée et validée par le backend déterministe.
Si le déterministe ne reconnaît pas la commande, aucune action n'est créée.

Fichiers ajoutés / modifiés
---------------------------
- backends/llama_backend.py
- backends/backend_manager.py
- config/models.json
- tests/test_llm_interchangeable_v11.py
- verifier_llm_v11.py

Changer de modèle
-----------------
1. Copier le nouveau fichier .gguf dans models/
2. Ajouter son entrée dans config/models.json
3. Modifier active_model
4. Redémarrer AgentLocal

Aucune modification de code Python n'est nécessaire.

Compatibilité visée
-------------------
- Windows 10 / Windows 11 64 bits
- llama.cpp local
- machines à partir de 4 Go de RAM : privilégier un modèle ~0.5B à 1.5B quantifié Q4
- aucune API cloud obligatoire
