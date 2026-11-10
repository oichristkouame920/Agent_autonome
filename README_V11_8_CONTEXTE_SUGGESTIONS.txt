AgentLocal V11.8 - Contexte conversationnel et suggestions actionnables
Date : 10 novembre 2026
Build : 2026-11-10-v11.8-contexte-suggestions

OBJECTIF
- Rendre AgentLocal plus naturel sans augmenter ses permissions.
- Transformer les anciennes suggestions textuelles en actions contextuelles réelles.
- Aligner les fichiers du pack, les permissions, le backend, Edge et les tests.

PRINCIPAUX CORRECTIFS
1. Contexte de session
   - « ferme ça » peut viser la dernière application explicitement manipulée.
   - Les choix courts après une question sont compris : « Excel », « Word », etc.
   - Les suggestions acceptent : 1/2/3, « le premier », « oui », « vas-y ».

2. Suggestions V11.8
   - Jusqu'à 3 suggestions concrètes maximum.
   - Boutons cliquables dans le GUI.
   - Chaque suggestion possède un identifiant, un libellé et une commande canonique.
   - Aucune suggestion destructive automatique.
   - Une nouvelle demande sans rapport invalide les anciennes suggestions.

3. Langage terrain
   - « salut chef tu es là ? »
   - « tu peux gérer un truc pour moi ? »
   - « ouvrre bloc note »
   - « donne moi letat du pc »
   - « ouvre whatsap »
   - « lance fire fox » / « vérifie que fire fox est lancé »
   - extensions docx/pptx/xls et fautes simples observées.

4. Fichiers
   - « liste tout ce que j'ai dans Documents »
   - « liste le dossier Images » vise correctement la racine Images.
   - « liste mes captures d'écran » vise Images\Captures AgentLocal.
   - « montre-moi les plus gros fichiers dans Téléchargements ».
   - « donne les infos de rapport.pdf » effectue une résolution unique dans les racines autorisées ; aucun homonyme n'est choisi automatiquement.

5. Sécurité des opérations de masse
   - « ouvre tous les fichiers trouvés » : aucune ouverture en masse.
   - « supprime tous les gros fichiers » : aucune suppression en masse.
   - « déplace tous les PDF » : aucun déplacement en masse automatique.
   Les réponses expliquent comment poursuivre avec une cible précise.

6. Edge
   - « passe sur WhatsApp » active l'onglet via le pont local.
   - La règle V11.4.1 reste prioritaire : si Edge est déjà ouvert et que le pont échoue, aucun fallback natif ne doit risquer de créer une seconde fenêtre.
   - L'ancien vérificateur V10.9.1 a été aligné sur cette règle.

7. Firefox
   - Alias, permissions, PROCESS_MAP, recherche de l'exécutable et gestion de fenêtre alignés.
   - Firefox reste une application manuelle, non ajoutée aux routines automatiquement.

8. Cohérence du pack
   - project_version.py devient la source de vérité V11.8.
   - verifier_conformite_pack_v11_8.py contrôle les références croisées.
   - tester_agentlocal.ps1 tolère correctement les avertissements runtime/LLM en mode dégradé, tout en bloquant les erreurs structurelles.

INSTALLATION DU PATCH
1. Faire une copie de sauvegarde du dossier AgentLocal actuel.
2. Extraire le contenu du patch V11.8 directement à la racine AgentLocal et accepter le remplacement des fichiers.
3. Exécuter finaliser_patch_v11_8.bat.
   - il supprime deux anciens fichiers de travail obsolètes s'ils existent ;
   - il lance ensuite tester_agentlocal.bat.
4. Si tous les tests passent, lancer AgentLocal normalement.

FICHIERS OBSOLETES SUPPRIMES PAR LA FINALISATION
- agent_tail.txt
- tests\test_natural_language_v2.py.tmp

VALIDATION DE PRODUCTION
- Validation de production effectuée : 324 tests Pytest + 248 sous-tests réussis.
- 21 verifier_*.py vérifiés ; les avertissements de runtime optionnel ne bloquent pas le mode déterministe.
- Le vérificateur de conformité doit afficher :
  « Conformité pack AgentLocal V11.8 : OK ».
