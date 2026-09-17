AgentLocal V10.5 - Batterie, réseau et vitesse de connexion
Date : 2026-09-17

Objectif
--------
Ajouter des informations locales utiles sans modifier Windows et sans lancer de test Internet externe automatiquement.

Nouvelles commandes prises en charge
-------------------------------------
Batterie / alimentation :
- il me reste combien de batterie ?
- ma batterie est à combien ?
- je suis branché au secteur ?

Réseau local :
- mon réseau est actif ?
- quelle est mon IP locale ?
- quelles connexions réseau sont actives ?

Vitesse :
- quelle est la vitesse de ma connexion ?
- ma connexion est à combien ?
- teste la vitesse de ma connexion
- vitesse de mon wifi
- quel est le débit réseau actuel ?

Différence importante
---------------------
1. "vitesse de ma connexion" lit la vitesse de liaison indiquée par Windows pour l'interface Wi-Fi/Ethernet.
   Exemple : 866 Mb/s en Wi-Fi ou 1 Gb/s en Ethernet.
   Ce n'est PAS une mesure du débit Internet réel.

2. "débit réseau actuel" observe pendant environ 1 seconde les octets réellement reçus/envoyés.
   Aucun trafic artificiel n'est généré. Le résultat indique l'activité actuelle, pas la capacité maximale.

3. "fais un speedtest" est compris, mais aucun serveur externe n'est contacté dans V10.5.
   AgentLocal explique que le test Internet réel n'est pas activé.

Sécurité
--------
- Lecture seule.
- Commande utilisateur explicite obligatoire.
- Interdit depuis les routines et habitudes.
- Aucun PowerShell, CMD ou terminal.
- Aucun changement Wi-Fi, carte réseau ou alimentation.
- Aucun serveur externe contacté pour mesurer la vitesse.
- Aucun paquet de test généré.

Compatibilité
-------------
- Windows 10 / Windows 11.
- PC 4 Go de RAM.
- Réutilise psutil déjà présent dans AgentLocal.
- Aucune nouvelle dépendance.
