from pathlib import Path

from backends import backend_manager, llama_backend

print("=== AgentLocal V11 - LLM local interchangeable ===")
print()

config_path = Path(__file__).resolve().parent / "config" / "models.json"
print("OK - config/models.json présent" if config_path.is_file() else "ERREUR - config/models.json absent")

status = llama_backend.get_status()
print("Modèle actif :", status.get("active_model"))
print("Chemin modèle :", status.get("model_path"))
print("llama-cli :", status.get("llama_cli"))
print("Contexte :", status.get("context_size"))
print("Threads :", status.get("threads"))
print("LLM disponible :", "oui" if status.get("available") else "non")
if status.get("reason"):
    print("Information :", status["reason"])

manager = backend_manager.get_backend_status()
print("Backend sélectionné :", manager.get("selected"))
if manager.get("warning"):
    print("Information backend :", manager["warning"])

print()
print("V11 LLM INTERCHANGEABLE ACTIVE - vérification non destructive OK")
print("Aucun modèle n'a été lancé pendant cette vérification.")
