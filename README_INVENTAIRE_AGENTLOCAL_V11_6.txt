AGENTLOCAL - INVENTAIRE CONSOLIDE AU NIVEAU V11.5
==================================================

OBJECTIF GENERAL
----------------
AgentLocal est un assistant Windows local, leger et controle, cible pour Windows 10/11 64 bits avec une machine pouvant ne disposer que de 4 Go de RAM. L'objectif est d'obtenir un agent utile hors connexion, resilient, transportable et capable de comprendre du francais naturel sans lui donner une autonomie excessive.

PRINCIPE D'ARCHITECTURE
-----------------------
Utilisateur -> Interface Tkinter -> normalisation du langage -> moteur deterministe -> LLM local si necessaire -> validation de l'intention -> permissions -> outil local autorise -> Windows.

Le LLM aide a comprendre. Il n'a pas le droit de commander Windows directement. Toute action finale repasse par les contrats, permissions et outils controles.

1. INTERFACE ET DEMARRAGE
-------------------------
- Interface graphique Tkinter/ttk legere.
- Mode console conserve en secours.
- Une seule commande traitee a la fois pour limiter la RAM.
- Lanceur Windows lancer_agentlocal_gui.bat.
- Mode sur si un composant critique est casse.
- Mode degrade si un composant optionnel, notamment le LLM, est indisponible.
- Journal borne dans logs/agentlocal.log.
- Commandes de sortie GUI : stop, quitte, arrete, ferme AgentLocal, ferme-toi.

2. RESILIENCE
-------------
- Diagnostic au demarrage.
- Fallback automatique vers le backend deterministe.
- Circuit de protection du LLM apres echecs repetes.
- L'interface reste ouverte si un composant optionnel tombe.
- Les erreurs detaillees vont dans le journal plutot que dans l'interface.
- Les configurations principales sont controlees au demarrage.

3. BACKENDS ET IA LOCALE
------------------------
- Backend deterministe prioritaire pour les actions connues.
- Backend LLM local via llama.cpp.
- Backend LLM interchangeable a partir de config/models.json.
- Modele GGUF externe au code metier.
- Fallback deterministe si le modele ou llama-cli n'est pas disponible.
- Le LLM reformule vers une commande canonique qui doit ensuite etre validee par le deterministe.

4. PORTABILITE
--------------
- Chemins internes relatifs a la racine du projet.
- config/paths.json centralise les emplacements internes.
- Modele dans models/ avec chemin relatif.
- llama.cpp dans tools/llama.cpp/ avec chemin relatif.
- Support de fichiers annexes de modele, dont mmproj si necessaire.
- Support d'un runtime Python portable dans runtime/python/.
- Fallback vers .venv puis Python systeme.
- Cache de dependances hors ligne dans vendor/wheels/.
- Scripts de preparation d'un nouveau PC et d'un runtime portable.

5. SECURITE GENERALE
--------------------
- Aucun PowerShell arbitraire.
- Aucun CMD arbitraire.
- Aucun Windows Terminal, Bash ou WSL arbitraire.
- Pas d'elevation automatique.
- Pas de chemin executable libre fourni par l'utilisateur.
- Liste blanche d'applications et de sites.
- Actions destructrices controlees.
- Pas de suppression definitive de fichier autorisee.
- Pas d'ecrasement silencieux.
- Pas d'operation de masse implicite.
- Les commandes mixtes contenant une cible interdite sont refusees atomiquement.
- Les negations orales comme « ouvre pas Edge » ne declenchent aucune action.

6. LANGAGE NATUREL
------------------
- Francais naturel courant.
- Variantes conversationnelles et formulations indirectes.
- Plusieurs tournures ivoiriennes courantes sans caricature.
- Synonymes et quelques fautes connues sur applications/sites.
- Noms d'applications normalises : Bloc-notes, VS Code, Edge, Excel, Word, etc.
- Demandes ambigues transforme es en demandes de precision plutot qu'en actions devinees.
- V11.5 : ton plus simple et moins formel.
- V11.5 : comprend des formulations telles que « liste tout mes documents », « fais voir mes documents », « check moi si Teams est ouvert », « ca dit quoi le PC », « le volume c'est combien ».

7. APPLICATIONS WINDOWS
-----------------------
- Ouvrir une application autorisee.
- Verifier si elle est ouverte.
- Fermer proprement une application autorisee.
- Refus des shells interdits et de leurs alias, y compris « invite de commande ».
- Detection d'applications deja ouvertes.

8. GESTION DES FENETRES
-----------------------
- Mettre au premier plan.
- Agrandir.
- Reduire.
- Restaurer.
- Positionner a gauche ou a droite.
- Refus de choisir arbitrairement entre plusieurs fenetres.
- Pas d'organisation automatique globale sans instruction precise.

9. EXPLORATEUR WINDOWS ET DOSSIERS
---------------------------------
- Ouvrir l'Explorateur.
- Fermer l'Explorateur proprement.
- Ouvrir un dossier autorise.
- Recherche recursive de dossier.
- V11.5 : « ouvre Formation JS » peut ouvrir un dossier si la reference unique correspond a un dossier.
- V11.5 : fermeture ciblee d'une fenetre Explorateur par nom de dossier.
- Si plusieurs fenetres correspondent, AgentLocal refuse de choisir.
- Suppression de dossiers non activee en V11.5 : la demande est comprise mais aucune action n'est realisee.

10. ACCES FICHIERS
------------------
Racines utilisateur controlees :
- Bureau
- Documents
- Telechargements
- Images
- Videos
- Musique

Fonctions :
- Lister.
- Rechercher recursivement.
- Lire des fichiers pris en charge.
- Creer certains fichiers.
- Modifier certains fichiers texte.
- Renommer.
- Copier.
- Deplacer.
- Envoyer un fichier a la Corbeille.
- Ouvrir un fichier avec une application approuvee.

Protections :
- Limite de profondeur.
- Limite de resultats/entrees.
- Refus des reparse points, symlinks et chemins proteges selon la politique.
- Types executables et sensibles bloques dans plusieurs operations.

11. RECHERCHE LOCALE AVANCEE
----------------------------
- Recherche par type : PDF, Word, Excel, PowerPoint, image, video, audio, texte.
- Recherche par date : aujourd'hui, hier, semaine, derniers jours.
- Recherche par taille.
- Recherche des fichiers les plus recents ou plus gros.
- Comptage de resultats.
- Recherche basee uniquement sur les metadonnees pour cette fonction.

12. ANALYSE DE FICHIERS
-----------------------
- Informations de fichier.
- SHA-256.
- Comparaison de deux fichiers.
- Detection de doublons exacts.
- Limites de taille et volume de donnees pour preserver les machines 4 Go.
- Aucun doublon n'est supprime automatiquement.

13. ANNULATION CONTROLEE
-----------------------
- Une seule operation fichier reversible memorisee temporairement.
- Annulation de renommage.
- Annulation de deplacement.
- Annulation de copie.
- Expiration courte de la possibilite d'annulation.
- Refus si le contexte du fichier a change.
- Une copie annulee va a la Corbeille, jamais en suppression definitive.

14. ARCHIVES ZIP
----------------
- Creer un ZIP controle.
- Extraire un ZIP controle.
- Protection contre chemins de traversal ../.
- Refus de liens symboliques dangereux.
- Refus de ZIP chiffres selon la politique.
- Limites contre archives anormalement compressees.
- Pas d'ecrasement silencieux.

15. CAPTURE D'ECRAN
-------------------
- Capture de tout le bureau.
- Capture de la fenetre active.
- Enregistrement PNG local dans Images/Captures AgentLocal.
- Commande manuelle obligatoire.
- Pas de capture automatique depuis routine ou habitude.

16. AUDIO
---------
- Lire le volume principal.
- Regler un pourcentage precis.
- Monter/baisser par pas controles.
- Couper/remettre le son.
- Limites de variation.
- Pas de controle microphone ajoute.

17. SYSTEME / BATTERIE / RESEAU
-------------------------------
- Etat global du PC.
- RAM.
- CPU.
- Espace disque libre.
- Uptime.
- Batterie et alimentation si disponibles.
- Interfaces reseau actives.
- IP locale.
- Vitesse de liaison reseau.
- Activite/debit reseau observe localement.
- Pas de vrai speedtest Internet automatique.

18. PRESSE-PAPIERS
------------------
- Lire le texte copie.
- Copier du texte.
- Copier le chemin d'un fichier.
- Limite de taille.
- Le contenu du presse-papiers n'est jamais execute automatiquement.

19. EDGE ET WEB
---------------
- Extension AgentLocal Browser Bridge en Manifest V3.
- Pont HTTP local securise sur 127.0.0.1.
- Ouverture de sites autorises.
- Liste d'onglets.
- Activation d'un onglet/site existant.
- Verification d'un site ouvert.
- Fermeture ciblee de site selon les capacites existantes.
- WhatsApp Web normalise vers web.whatsapp.com.
- V11.4.1 : une fenetre Edge cible unique pour les ouvertures AgentLocal.
- Si Edge est deja ouvert et que le pont ne repond pas, AgentLocal refuse de disperser les sites via un fallback non garanti.
- Nouvelle fenetre Edge uniquement sur demande explicite ou lorsqu'aucune fenetre n'existe selon la politique.

20. ROUTINES
------------
- Routines configurees dans config/routines.json.
- Routine de travail pouvant inclure VS Code et plusieurs sites.
- Les sites de routine doivent reutiliser la fenetre Edge cible unique.
- Les fonctions sensibles recentes ne sont pas automatiquement utilisables depuis les routines.

21. HABITUDES ET APPRENTISSAGE
-----------------------------
- Observation locale d'activite.
- Propositions d'habitudes.
- Brouillons.
- Validation/refus utilisateur.
- Pas d'activation silencieuse.
- V11.5 : « mes habitudes » affiche maintenant un resume : validees, propositions en attente, brouillons.
- La liste « habitudes en attente » reste accessible explicitement.

22. MEMOIRE CONVERSATIONNELLE TEMPORAIRE
----------------------------------------
- Une reference de session peut etre retenue pour « ouvre-le », « lis-le » ou « copie son chemin ».
- Memoire en RAM uniquement.
- Effacement a la fermeture.
- Invalidation apres certaines operations qui changent le chemin.
- Pas de suppression/deplacement via pronom seul.

23. GIT ET METHODE DE DEVELOPPEMENT
----------------------------------
- main = branche stable.
- modification = branche de travail.
- Une evolution = commit identifiable autant que possible.
- Tests avant fusion.
- Les correctifs sont prepares sans memoire utilisateur, logs, gros modele ni secrets locaux.

24. TESTS ET VERIFICATION
-------------------------
- Compilation Python recurrente.
- Validation JSON AgentLocal.
- Verificateurs non destructifs par version.
- Tests unitaires et non-regression.
- Au niveau V11.5 : 297 tests reussis + 248 sous-tests reussis dans l'environnement de verification.

25. V11.5 - CORRECTIONS TERRAIN
-------------------------------
- « liste tout mes documents » -> liste Documents.
- « ouvre Formation JS » -> reference unique fichier ou dossier ; dossier ouvert si c'est un dossier.
- « ferme le dossier Formation JS » -> fermeture ciblee d'une seule fenetre Explorateur.
- « ouvre l'invite de commande » -> refus de securite explicite.
- « mes habitudes » -> resume global au lieu des seules propositions en attente.
- « supprime le dossier AnyDesk » -> demande comprise, aucune suppression de dossier activee.
- « stop » / « arrete » / « ferme-toi » -> fermeture de l'interface AgentLocal.
- Ton conversationnel simplifie : reponses plus directes et moins administratives.

26. V11.6 - SUGGESTIONS D'ACTIONS CONTROLEES
-------------------------------------------
- Une seule suggestion contextuelle a la fois.
- Aucune suggestion destructive.
- Aucune execution automatique.
- L'utilisateur doit dire explicitement « fais la suggestion ».
- « oui » seul ne suffit pas.
- La suggestion expire apres 5 minutes et reste uniquement en RAM.
- La commande suggeree repasse dans toutes les validations et permissions AgentLocal.
- Pas de suggestion apres un echec ou une commande multi-actions.
- Exemples : apres une liste de Documents, proposer les fichiers recents ; apres un etat PC, proposer un controle reseau ; apres ouverture d'un site, proposer de lister les onglets.

27. TEST GLOBAL EN UNE COMMANDE
--------------------------------
- tester_agentlocal.ps1 : compilation Python + JSON AgentLocal + tous les verifier_*.py + pytest.
- tester_agentlocal.bat : lance le script PowerShell ci-dessus.
- Les fichiers tiers de llama.cpp ne sont pas valides comme JSON strict par ce test.

28. ETAT DE VALIDATION V11.6
----------------------------
- 302 tests reussis + 248 sous-tests reussis.
- Compilation Python OK.
- Verificateur V11.6 non destructif OK.
- JSON AgentLocal valides.

FIN DE L'INVENTAIRE V11.6
