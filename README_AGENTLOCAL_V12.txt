AGENTLOCAL V12.0 - SERVICES CONNECTES OPTIONNELS
=================================================

Objectif
--------
Ajouter des informations Internet utiles sans rendre AgentLocal dependant du reseau.
Le coeur local reste operationnel hors connexion.

Nouveautes
----------
- Meteo du jour via Open-Meteo, sans cle API.
- Actualites du jour via un flux RSS Google Actualites configure pour la Cote d'Ivoire.
- Briefing du jour dans l'interface.
- Petite fenetre matinale, une fois par jour, configurable.
- Verification distante AgentLocal via GitHub en lecture seule, sans installation automatique.
- Nouvelle page Briefing dans l'interface V11.9.
- Cache court pour limiter les appels reseau et ameliorer le temps de reponse.

Securite Internet
-----------------
- HTTPS uniquement.
- GET uniquement.
- Domaines en liste blanche dans config/permissions.json.
- Aucun cookie, aucun jeton, aucune authentification.
- Taille des reponses et timeout bornes.
- Le contenu Internet est du texte d'affichage : il n'est jamais reinterprete comme commande.
- Aucune actualite, titre, meteo ou reponse distante ne peut ouvrir une application,
  modifier un fichier ou lancer une commande systeme.
- En cas d'erreur Internet, AgentLocal continue en mode local.

Configuration
-------------
config/connected_services.json
- weather.city : ville meteo (Abidjan par defaut)
- weather.country_code : CI par defaut
- news.query : recherche d'actualites
- morning_briefing.enabled : active/desactive la fenetre du matin
- morning_briefing.start_hour / end_hour : plage d'affichage
- updates.github_repository / branch : depot a verifier en lecture seule

Interface
---------
Une page "Briefing" est ajoutee dans la barre laterale.
Au premier lancement le matin, AgentLocal peut afficher une petite fenetre contenant
la meteo, les titres du jour et des raccourcis vers la routine ou le briefing complet.

Important
---------
Les flux Google Actualites RSS ne sont pas une API publique garantie. Si ce flux change,
le service actualites doit echouer proprement sans affecter le reste d'AgentLocal.
