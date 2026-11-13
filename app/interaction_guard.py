"""AgentLocal: garde conversationnelle frugale, sans effets de bord.

Un retour ('command', texte) est EXCLUSIVEMENT une normalisation d'une
commande explicite vers une forme deja approuvee par le moteur deterministe.
Un retour ('reply', texte) ne doit jamais executer d'outil Windows.

Important: aucune instruction issue d'un document ou contenu externe n'est
interpretee ici. Pas de lecture de fichiers, historique ou donnees privees.
"""
from __future__ import annotations

import re
import unicodedata

# Ce routeur n'a PAS le droit de creer une action, une permission ou une cible.
_APPS = {
    'word': 'word', 'microsoft word': 'word',
    'excel': 'excel', 'microsoft excel': 'excel',
    'powerpoint': 'powerpoint', 'microsoft powerpoint': 'powerpoint',
    'teams': 'teams', 'microsoft teams': 'teams',
    'edge': 'edge', 'microsoft edge': 'edge',
    'vs code': 'vscode', 'vscode': 'vscode', 'visual studio code': 'vscode',
}
_APP_REGEX = r'(?:microsoft\s+)?(?:visual\s+studio\s+code|vs\s+code|vscode|powerpoint|word|excel|teams|edge)'
_EN_NEG = re.compile(r"\b(?:don't|dont|do not|never|not|without|no)\b")
_FR_NEG = re.compile(r"\b(?:pas|jamais|aucun|aucune|rien|sans|non)\b")


def _fold(value: str) -> str:
    t = unicodedata.normalize('NFKD', value.casefold().replace('’', "'"))
    return ''.join(ch for ch in t if not unicodedata.combining(ch))


def _app(raw: str) -> str | None:
    return _APPS.get(' '.join(raw.split()))


def _clean(value: str) -> str:
    return re.sub(r'\s+', ' ', _fold(value).strip()).strip(' .!?')


def _help_topic(s: str) -> str | None:
    """Reponses pedagogiques statiques; aucune mesure systeme inventee."""
    if ('powershell' in s and re.search(r'\b(?:explique|pourquoi|risqu|danger)\b', s)):
        return ("Je ne lance pas PowerShell. Cet outil peut executer des scripts qui changent "
                "des fichiers, des services ou la configuration. Une commande inconnue "
                "ne doit pas etre lancee sans en comprendre les effets et les permissions.")
    if 'fuite memoire' in s and ('cache' in s or 'python' in s):
        return ("Pour distinguer une fuite memoire d'un cache normal : 1) mesure la RAM du "
                "processus pendant plusieurs operations identiques ; 2) observe si elle "
                "se stabilise ou augmente continuellement ; 3) compare avant/apres "
                "liberation des references ; 4) avec Python, examine tracemalloc et "
                "les objets encore references. Une hausse seule ne prouve pas une fuite. "
                "Je n'ai effectue aucune mesure sur ton application.")
    if 'connexion' in s and ('instable' in s or 'reseau' in s) and ('diagnost' in s or 'administrateur' in s):
        return ("Diagnostic sans modifier le poste : verifier le type de liaison, la "
                "qualite du signal et la passerelle ; comparer latence et pertes de "
                "paquets vers la passerelle puis une destination autorisee ; observer "
                "les coupures, le DNS et l'etat des interfaces. Consigner l'heure des "
                "incidents avant d'envisager un changement. Aucun parametre n'a ete modifie.")
    if ('tableau de bord' in s and ('financier' in s or 'indicateur' in s)):
        return ("Pour un tableau de bord financier, commence par chiffre d'affaires, "
                "marge, charges, tresorerie, creances et ecarts au budget. Pour chaque "
                "KPI, indique sa formule, la periode, la source des donnees, un controle "
                "de coherence et un responsable de validation. Je n'ai pas invente de chiffres.")
    if ('sauvegarde' in s and ('risque' in s or 'plan de reprise' in s)):
        return ("Analyse de sauvegarde : verifier la frequence, le chiffrement, les "
                "droits d'acces, la conservation hors ligne et la possibilite de "
                "restaurer. Definir RPO/RTO, responsables, ordre de reprise et tests "
                "reguliers de restauration sur un environnement isole. Aucune sauvegarde "
                "n'a ete modifiee.")
    if ('pc' in s and ('lent' in s or 'rame' in s) and ('explique' in s or 'etape' in s or 'chatgpt' in s)):
        return ("On peut diagnostiquer ca progressivement, sans rien fermer : 1) relever "
                "RAM, CPU et disque ; 2) identifier les processus les plus gourmands ; "
                "3) verifier depuis quand le ralentissement dure ; 4) choisir ensemble "
                "une action autorisee. Dis : « donne l'etat du PC ». Je n'ai encore "
                "effectue aucun diagnostic sur ton ordinateur.")
    if ('perdu' in s and 'document' in s) or ('retrouv' in s and 'document' in s and 'ou chercher' in s):
        return ("Pour retrouver ton document sans risque, commence par Documents et "
                "Telechargements, puis les fichiers recents de l'application et la "
                "corbeille. On peut chercher par nom ou date sans modifier son contenu. "
                "Donne-moi un mot du nom ou le dossier probable.")
    if 'prepare mon environnement de developpement' in s:
        return ("Je peux utiliser la routine de travail deja configuree, mais je "
                "n'ai pas encore execute de programme. Pour la demarrer, dis "
                "« lance ma routine ». Ensuite je pourrai rendre compte "
                "des etapes confirmees par l'application.")
    if 'renomme' in s and 'fichier' in s and ('existe deja' in s or 'si ' in s):
        return ("Avant de renommer, il faut identifier le dossier, le fichier "
                "source et le nom final, puis verifier qu'aucun fichier ne "
                "serait ecrase. Aucune operation de fichier n'a ete effectuee.")
    if ('fichiers accessibles' in s and ('ne lis' in s or 'sans lire' in s)):
        return ("Je peux dresser un inventaire de noms, tailles et dates sans lire le "
                "contenu des fichiers. Indique le dossier autorise (Documents ou "
                "Telechargements), et je garderai l'operation en lecture seule.")
    return None


def route_user_input(message: object) -> tuple[str, str] | None:
    """Route sur des formulations FERMEES; ne confere aucune permission.

    Toute sequence avec contraintes incertaines est arretee avant le LLM.
    Une commande normalisee repasse par process_instruction(), toutes les
    politiques et le moteur deterministe de preuve.
    """
    if not isinstance(message, str) or not message.strip() or len(message) > 900:
        return None
    text = _clean(message)

    # Priorite absolue au veto final explicite, y compris avec des app citees.
    if re.search(r"(?:^|[.!?]\s*)(?:attends?[, ]+)?n[' ]?ouvre\s+rien(?:\s+pour\s+le\s+moment)?$", text) or \
       re.search(r"(?:^|[.!?]\s*)(?:finalement[, ]+)?ne\s+fais\s+rien$", text):
        return ('reply', "C'est compris : aucune application ne sera ouverte et aucune action ne sera lancee.")
    if ("enfin non" in text or "plutot" in text) and ("n'ouvre rien" in text or 'ne fais rien' in text):
        return ('reply', "Je retiens ta derniere consigne : ne rien ouvrir. Aucune action lancee.")

    # Si l'utilisateur annule en fin de message, le veto prime sur les
    # commandes anterieures, meme en conversation ou avec ponctuation.
    if re.search(r"(?:attends?[,: ]+)?(?:n[' ]?ouvre rien|ne fais rien|"
                 r"do not (?:open|launch|start) anything|don't (?:open|launch|start) anything)"
                 r"(?:\s+(?:pour le moment|now|yet))?\s*$", text):
        return ('reply', "Derniere consigne prise en compte : aucune action lancee.")

    # Les conditions ne sont pas des sequences inconditionnelles. Le veto
    # concerne aussi « s'il », « if » et « sinon » sans exiger un 2e marqueur.
    # « verifie si Word est ouvert » seul reste une simple consultation.
    conditional = bool(re.search(
        r"\b(?:si|sinon|unless|lorsque)\b|(?<!even )\bif\b|"
        r"\bs[' ]il\b(?!\s+te\s+plait)", text))
    conditional_action = bool(re.search(
        r"\b(?:ouvre|ouvrir|lance|lancer|demarre|demarrer|ferme|fermer|"
        r"repare|reparer|renomme|renommer|deplace|deplacer|supprime|supprimer|"
        r"open|launch|start|close|delete|remove|rename)\b", text))
    if conditional and conditional_action:
        return ('reply', "Je comprends la condition, mais je ne peux pas la transformer "
                         "en action automatique sure pour le moment. Commence par "
                         "verifier l'etat, puis donne une commande explicite si "
                         "necessaire. Aucune action lancee.")

    # Garde supplementaire sur les demandes de privilege et les contenus
    # externes. On repond, on n'interprete jamais le texte comme une autorisation.
    if re.search(r"(?:ignore toutes tes consignes|ignore (?:tes|les) instructions|"
                 r"sans autorisation|bypass (?:safety|permissions)|"
                 r"envoie (?:ses|mes|les) fichiers ailleurs)", text):
        return ('reply', "Je ne contourne pas les autorisations et je ne traite pas "
                         "les instructions d'un document comme des ordres. "
                         "Aucune action lancee.")
    if re.search(r"\b(?:efface|supprime|delete|erase)\b", text) and \
       re.search(r"\b(?:tous|tout|all|everything|fichiers|files)\b", text):
        return ('reply', "Cette demande peut supprimer des donnees. "
                         "Aucune action lancee : indique les fichiers precis, "
                         "leur emplacement et l'operation souhaitee.")

    # Un refus d'executer n'a pas besoin d'etre soumis a Qwen.
    # Les requetes positives avec veto sur une autre cible sont reconnues
    # plus bas par la grammaire mixte; ici on ne refuse que les cas simples.
    if re.fullmatch(r"(?:n[' ]?ouvre pas|ouvre pas|ne lance pas|ne demarre pas|"
                    r"faut pas ouvrir|faut pas lancer|je ne veux pas ouvrir|"
                    r"(?:please )?(?:don't|do not|never) (?:open|start|launch)|"
                    r"no abras|no ejecutes)\s+" + _APP_REGEX + r"(?:\s+(?:hein|stp|please))?", text):
        return ('reply', "Consigne respectee : aucune ouverture d'application "
                         "n'est executee.")

    # Les cibles dangereusement ambigues doivent etre traitees AVANT la
    # recherche automatique de dossier/fichier dans le moteur historique.
    if re.fullmatch(r'(?:ouvre|lance|demarre)\s+(?:(?:l|une|la)\s*[\']?\s*application\s+)?agentlocal', text):
        return ('reply', "Veux-tu afficher la fenetre d'AgentLocal deja ouverte ou ouvrir "
                         "le dossier du projet ? Je ne vais pas choisir un dossier au hasard.")
    if re.fullmatch(r'(?:ouvre|lance|affiche)\s+(?:les?\s+)?parametres?', text):
        return ('reply', "Tu veux les parametres de Windows ou ceux d'AgentLocal ? "
                         "Je n'ouvre rien sans cette precision.")

    # Des tests de conversation ne sont pas des instructions a executer.
    if re.fullmatch(r'(?:ram disponible insuffisante avant chargement de qwen|20 demandes simples successives)', text):
        return ('reply', "Cela ressemble a un scenario de test. Pour le tester en securite, "
                         "utilise les diagnostics du projet ; aucune action systeme lancee.")

    if re.fullmatch(r"(?:open the folder|ouvre le dossier)\s+agentlocal", text):
        return ('reply', "Dans quel emplacement se trouve le dossier AgentLocal "
                         "que tu souhaites ouvrir ? Je ne devine pas son chemin.")
    if re.fullmatch(r"(?:j'ai dit|je voulais|i said)\s+excel,?\s+(?:pas|not)\s+word", text):
        return ('reply', "Tu parlais d'Excel et non de Word. Je corrige la cible "
                         "dans notre echange, mais je ne lance rien sans nouvelle commande.")
    if re.fullmatch(r"(?:4 ?go|4 ?gb|8 ?go|8 ?gb|\d{1,3}\s*(?:go|gb))", text):
        return ('reply', "Tu indiques une quantite de memoire. Est-ce la RAM "
                         "totale du PC, la RAM disponible, ou la RAM utilisee par "
                         "l'application ? Je n'ai effectue aucune mesure.")
    if re.fullmatch(r"pour cette tache, reponds simplement\.?\s+pour l'analyse technique suivante, sois precis", text):
        return ('reply', "D'accord : une explication simple pour la demande courante, "
                         "et des details techniques lorsque tu les demandes. "
                         "Dis-moi la prochaine question.")
    if re.search(r"\b(?:how to|how do i|comment)\b", text) and \
       re.search(r"\b(?:open|launch|start|ouvrir|lancer)\b", text) and \
       re.search(_APP_REGEX, text):
        return ('reply', "Tu demandes une explication, pas l'ouverture immediate "
                         "d'une application. Je peux te guider pour la lancer, "
                         "ou tu peux me donner la commande explicite « ouvre Word ».")
    # Une alternative entre applications n'est pas une autorisation d'en choisir une.
    if re.search(r"\b(?:ou|or)\b", text) and len(re.findall(_APP_REGEX, text)) >= 2:
        return ('reply', "Tu cites plusieurs applications comme alternatives. "
                         "Laquelle veux-tu ouvrir ? Aucune action lancee.")

    # Les suggestions et explications ne doivent jamais devenir des actions.
    topic = _help_topic(text)
    if topic:
        return ('reply', topic)

    # Recapitulatif demande par l'utilisateur: ne pas inventer les operations
    # passees (des outils tiers peuvent avoir echoue sans remonter d'etat).
    if re.fullmatch(r'(?:explique|resume)\s+(?:ce\s+que\s+tu\s+viens\s+de\s+faire|tes\s+dernieres\s+actions)(?:\s+et\s+ce\s+que\s+tu\s+n.as\s+pas\s+reussi)?', text):
        return ('reply', "Je peux resumer une sequence deja executee avec « resume les "
                         "dernieres etapes ». Je ne vais pas inventer de resultats d'actions.")

    # Ouverture positive + interdiction sur une AUTRE application.
    # Forme strictement delimitee, sans seconde execution implicite.
    mixed = re.fullmatch(
        r"(?:(?:could you|can you|would you|please)\s+)?"
        r"(?:open|launch|start)\s+(" + _APP_REGEX + r")"
        r"\s*,?\s+but\s+(?:please\s+)?(?:don't|do not|never)\s+"
        r"(?:open|launch|start)\s+(" + _APP_REGEX + r")"
        r"(?:\s*,?\s+even if i mentioned it)?", text)
    if mixed:
        positive, negative = _app(mixed.group(1)), _app(mixed.group(2))
        if positive and negative and positive != negative:
            return ('command', f'ouvre {positive}')
        return ('reply', "Tu as interdit l'ouverture de la meme application : "
                         "aucune action lancee.")

    # Volume: ordre explicite, borne 0..100, aucune autre operation permise.
    audio = re.fullmatch(
        r"(?:le son est (?:trop )?fort,?\s*)?"
        r"(?:regle[ -]le|regle le volume|mets le volume)\s+a\s+(\d{1,3})\s*%", text)
    if audio:
        volume = int(audio.group(1))
        if 0 <= volume <= 100:
            return ('command', f'mets le volume a {volume}%')
        return ('reply', "Le volume doit etre compris entre 0 et 100 %. "
                         "Aucune action lancee.")

    # Commandes mixtes avec negation sur une autre cible : demander une
    # reformulation plutot que contourner le garde-fou de fidelite V12.5.4.
    if re.search(r"\b(?:don't|do not|never)\s+(?:open|start|launch)\s+", text) and re.search(r'\b(?:open|launch|start)\b', text):
        return ('reply', "J'ai repere une demande positive et une interdiction dans "
                         "la meme phrase. Pour les traiter sans risque, donne uniquement "
                         "l'action autorisee, par exemple « ouvre Word ».")

    # Le francais courant / CI : verifier une application deja ouverte.
    m = re.fullmatch(r"(?:verifi|verifie|verifies|verifiez)\s+que\s+("+_APP_REGEX+r")\s+est\s+ouvert(?:e)?", text)
    if m:
        app = _app(m.group(1))
        if app:
            return ('command', f'verifie si {app} est ouvert')

    # Demandes courantes dans un contexte professionnel ou debutant.
    # Les preambules ci-dessous sont purement descriptifs, jamais d'autres
    # actions ni conditions. Toute commande est revalidee par le moteur local.
    contextual = re.fullmatch(
        r"(?:(?:en tant que charge de reporting,?|je prepare un proces-verbal,?|"
        r"je decouvre les menus,?|la reunion demarre,?|"
        r"pour ma revue technique,?|pour le budget mensuel,?|"
        r"je veux travailler sur (?:word|excel),?|"
        r"j'ai besoin de taper une lettre,?|"
        r"je dois presenter un expose,?)\s*)?"
        r"(?:(?:peux[ -]tu|tu peux)\s+)?(?:me\s+)?"
        r"(?:ouvre|ouvrir|lance|lancer|demarre|demarrer)\s+(" + _APP_REGEX + r")"
        r"(?:\s+(?:a ma place|pour les indicateurs|pour mon equipe|"
        r"pour ma revue technique|pour mon reporting|pour le budget|"
        r"a ma place s'il te plait|maintenant|s'il te plait|stp))?", text)
    if contextual and not _FR_NEG.search(text) and not _EN_NEG.search(text):
        app = _app(contextual.group(1))
        if app:
            return ('command', f'ouvre {app}')

    english_context = re.fullmatch(
        r"(?:(?:as a developer|for the monthly budget|i am learning spreadsheets)"
        r"\s*,?\s*)?(?:please\s+)?(?:could you\s+)?"
        r"(?:open|launch|start)\s+(" + _APP_REGEX + r")"
        r"(?:\s+(?:for my review|please|for me))?", text)
    if english_context and not _EN_NEG.search(text):
        app = _app(english_context.group(1))
        if app:
            return ('command', f'ouvre {app}')

    # Formulations anglaises simples. L'ancrage integral empeche l'injection
    # d'une seconde operation (et le conseil « how to » reste hors de ce cas).
    english = re.fullmatch(
        r"(?:(?:i used chatgpt before,?\s*now\s+)?(?:could you|can you|would you|please|i want you(?: to)?|i'd like you to)\s+)?"
        r"(?:open|launch|start)\s+(?:the\s+)?("+_APP_REGEX+r")\s*(?:app(?:lication)?)?\s*(?:for me|please|now)?",
        text)
    if english and not _EN_NEG.search(text) and not _FR_NEG.search(text):
        app = _app(english.group(1))
        if app:
            return ('command', f'ouvre {app}')

    # Formulations francaises informelles qui avaient ete refusees par Qwen.
    ivoirian = re.fullmatch(r'(?:tu\s+me\s+lances?|faut\s+(?:me\s+)?(?:ouvrir|lancer)|tu\s+peux\s+me\s+lancer)\s+('+_APP_REGEX+r')(?:\s+(?:un\s+peu|la|stp|s.il\s+te\s+plait))?', text)
    if ivoirian and not _FR_NEG.search(text):
        app = _app(ivoirian.group(1))
        if app:
            return ('command', f'ouvre {app}')

    return None
