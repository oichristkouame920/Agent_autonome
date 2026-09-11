AgentLocal - ouverture controlee de fichiers et dossiers
=========================================================

Cette version ajoute l'ouverture manuelle controlee d'elements situes dans :
- Bureau
- Documents
- Telechargements
- Images
- Videos
- Musique
et leurs sous-dossiers autorises.

Exemples de commandes :
- accede au dossier Jean dans Documents
- accede au dossier Jean dans docuements
- ouvre le dossier Jean
- va dans le dossier Jean dans Documents\Cours
- ouvre rapport.pdf
- ouvre le fichier rapport.docx dans Documents\Cours
- ouvre Documents\Cours\rapport.pdf

Comportement :
- Un dossier est ouvert avec l'Explorateur Windows approuve.
- Un fichier est ouvert uniquement avec une application du catalogue ferme.
- Une recherche sans emplacement agit seulement si une correspondance unique est trouvee.
- Si plusieurs elements portent le meme nom, AgentLocal demande de preciser l'emplacement.

Associations controlees principales :
- DOCX/ODT -> Microsoft Word
- XLSX/ODS -> Microsoft Excel
- PPTX/ODP -> Microsoft PowerPoint
- PDF/HTML -> Microsoft Edge
- TXT/MD/CSV/JSON/XML/... -> Bloc-notes
- Images -> Paint
- Audio/video -> Lecteur multimedia Win32 approuve

Protections maintenues :
- aucun os.startfile
- aucun ShellExecute
- aucun shell=True
- aucune association Windows arbitraire
- aucun executable fourni par l'utilisateur
- aucun chemin absolu utilisateur
- aucun acces hors des six racines autorisees
- aucun symlink, junction ou reparse point
- aucun fichier executable, script ou raccourci
- aucune ouverture depuis une routine ou une habitude
- un seul element par commande

Note : si l'application approuvee correspondant au type de fichier n'est pas
installee sous une forme approuvee, AgentLocal refuse l'ouverture au lieu
d'utiliser une association Windows inconnue.
