AgentLocal V10.9 - Ouverture Web dans une fenêtre Edge existante

Nouvelle règle pour les demandes manuelles :
- si une fenêtre Microsoft Edge existe déjà, AgentLocal ouvre le site demandé
  dans un nouvel onglet de cette fenêtre via le pont local Edge ;
- si aucune fenêtre Edge n'existe, AgentLocal ouvre une nouvelle fenêtre Edge ;
- si Edge est déjà ouvert mais que le pont local/extension n'est pas disponible,
  AgentLocal refuse de créer une seconde fenêtre et explique quoi vérifier.

Exemples :
- ouvre GitHub
- ouvre ChatGPT
- ouvre Google
- ouvre UDMCI

La commande explicite "ouvre une nouvelle fenêtre Edge" conserve son rôle :
elle crée une nouvelle fenêtre Edge.

Les routines conservent leur comportement précédent afin de ne pas modifier
silencieusement leur organisation.
