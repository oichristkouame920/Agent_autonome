AGENTLOCAL V12.2.1 - LLM ADAPTATIF LOCAL

Nouveautes :
- sonde llama-cli en deux temps : 10 s puis 30 s ;
- suppression des faux negatifs lies a un demarrage Windows lent ;
- llama-server local sur 127.0.0.1 lorsque la RAM le permet ;
- modele conserve charge pendant 180 secondes apres usage ;
- arret automatique du serveur chaud apres inactivite ;
- fallback automatique vers llama-cli si le serveur chaud est indisponible ;
- fallback deterministe conserve si le LLM complet echoue ;
- filtrage des blocs <think>, [Start thinking] et Thinking Process avant affichage ;
- aucune ecoute reseau externe du serveur LLM ;
- le modele GGUF et llama.cpp existants ne sont pas remplaces.

Seuil RAM par defaut pour le serveur chaud : 850 Mo disponibles.
Les parametres sont ajoutes sans ecraser le modele actif dans config/models.json.
