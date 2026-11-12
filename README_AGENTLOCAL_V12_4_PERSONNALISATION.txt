AGENTLOCAL V12.4 - PERSONNALISATION DE L'HOTE
================================================

Objectif
--------
AgentLocal devient un produit installable sur plusieurs postes sans embarquer le profil
ou les habitudes d'un utilisateur precedent.

Nouveautes principales
----------------------
- Assistant visuel de premier demarrage en 6 etapes.
- Profil local : nom affiche, nom de machine, usage Travail/Personnel/Mixte.
- Configuration graphique du comportement de l'assistant.
- Niveau d'emoji, citation quotidienne et suggestions intelligentes configurables.
- Briefing personnalisable par themes.
- Fenetre de routine matinale configurable, avec declencheur securise au premier deverrouillage.
- Page Habitudes avec phase initiale de 2 jours, progression et propositions a examiner.
- Mode recommande : questions + observation locale pendant 2 jours.
- Une habitude detectee ne cree jamais une routine active sans validation utilisateur.

Donnees locales creees sur chaque hote
--------------------------------------
memory/user_profile.json
memory/user_preferences.json
memory/onboarding_state.json
memory/declared_habits.json

Ces fichiers ne sont pas inclus dans le pack distribue et memory/ est ignore par Git.

Confidentialite de l'apprentissage
----------------------------------
AgentLocal peut observer uniquement les metadonnees d'actions qu'il execute deja :
type d'action, cible et horaire. Il n'enregistre pas les frappes clavier et n'utilise
pas le contenu des e-mails, messages, mots de passe ou autres contenus prives pour
apprendre des habitudes.

Comportement de securite
------------------------
- Pas de commande shell arbitraire.
- Pas d'action sensible automatiquement autorisee par une preference utilisateur.
- Les donnees Web restent de simples donnees d'affichage.
- Les habitudes detectees deviennent uniquement des propositions.
- Les garanties de confidentialite ne peuvent pas etre affaiblies depuis l'interface.

Mise a jour depuis V12.3
------------------------
Utiliser INSTALLER_AGENTLOCAL_V12_4.bat depuis le dossier extrait.
L'installateur conserve les reglages, le modele, les routines et les donnees memory/
de l'hote existant.

Premier lancement sur un hote sans profil
------------------------------------------
AgentLocal affiche automatiquement l'assistant de configuration lorsque l'interface
est ouverte. Un demarrage Windows en arriere-plan reste silencieux ; l'onboarding
apparait lorsque l'utilisateur ouvre ensuite AgentLocal.
