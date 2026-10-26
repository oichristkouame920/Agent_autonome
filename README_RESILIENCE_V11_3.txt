AgentLocal V11.3 - Resilience et demarrage sur
================================================

Objectif
--------
Garder AgentLocal operationnel meme lorsqu'un composant optionnel echoue.
Le LLM local n'est jamais indispensable a l'execution des actions controlees.

Ajouts principaux
-----------------
1. Diagnostic leger au demarrage.
2. Mode degrade si le LLM est indisponible.
3. Mode sur si un composant critique (ex. permissions) est invalide.
4. Circuit breaker LLM : apres 2 echecs consecutifs, le LLM est mis en pause
   120 secondes et le moteur deterministe reste disponible.
5. Journal local borne : logs/agentlocal.log, 512 Ko maximum par fichier,
   3 sauvegardes. Les commandes utilisateur ne sont pas journalisees par
   cette couche de resilience.
6. La GUI reste visible si le coeur AgentLocal ne peut pas etre importe ;
   les actions sont alors desactivees plutot que de provoquer un crash silencieux.
7. Les erreurs de commande sont journalisees localement et l'interface affiche
   un message generique sans trace Python complete.

Verification
------------
python verifier_resilience_v11_3.py

Au demarrage :
python verifier_resilience_v11_3.py --startup --quiet

Un avertissement n'empeche pas le demarrage. Une erreur critique lance la GUI
uniquement si elle peut etre chargee, mais aucune action ne doit etre executee.
