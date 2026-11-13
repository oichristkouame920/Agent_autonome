"""Adaptation prudente au niveau de langage du message courant.

Ne fait aucune action. Ne stocke ni identite, ni niveau permanent. Un utilisateur peut
etre expert dans un domaine et novice dans un autre : le niveau est lie a la demande.
"""
from __future__ import annotations

import re
import unicodedata


def _normalize(text: object) -> str:
    text = unicodedata.normalize('NFKD', str(text or '').casefold())
    return ''.join(c for c in text if not unicodedata.combining(c)).replace('’', "'")


_BEGINNER = (
    'je debute', 'je suis debutant', 'je suis novice', 'je connais rien',
    'je ne comprends pas', 'je ne sais pas', 'je suis nouveau',
    "j'y connais rien", 'je ne connais pas', 'je comprends pas',
    'explique moi simplement', 'explique simplement', 'comme a un debutant',
    'pas trop technique', 'sans jargon', 'pas a pas', 'etape par etape',
    'je suis perdu', 'je sais pas comment', 'comme sur chatgpt',
    'i am new to', 'i am a beginner', 'explain simply', 'step by step',
    'soy principiante', 'explicame facil',
)
_PROFESSIONAL = (
    'en tant que professionnel', 'en tant que responsable', 'en tant que developpeur',
    'en tant qu administrateur', 'en tant que comptable',
    'je suis responsable', 'je suis developpeur', 'je suis administrateur',
    'je suis technicien', 'pour mon client', 'pour notre equipe',
    'pour la direction', 'dans mon entreprise', 'dans mon service',
    'en production', 'audit de', 'analyse de risques', 'analyse de cause racine',
    'plan de remediation', 'indicateurs de performance',
    'root cause analysis', 'production incident', 'for my team',
    'as a developer', 'as an administrator', 'for our clients',
    'en mi trabajo', 'para nuestro equipo',
)
_TECHNICAL = re.compile(
    r'\b(?:kpi|sla|slo|api|sql|vlan|dns|tcp|http|https|json|csv|etl|git|ci/cd|'
    r'pipeline|requete|schema|journalisation|journal|logs?|tableau de bord|'
    r'migration|sauvegarde|recuperation|latence|deploiement|production|'
    r'ecart type|regression|compliance|audit|controle interne)\b', re.I,
)


def audience_for(message: object) -> str:
    """beginner, professional ou neutral ; aucune decision de permission."""
    text = _normalize(message)
    if not text.strip():
        return 'neutral'
    beginner = any(marker in text for marker in _BEGINNER)
    professional = any(marker in text for marker in _PROFESSIONAL)
    if beginner and professional:
        # Un professionnel debutant sur ce sujet prefere une explication claire.
        return 'beginner'
    if beginner:
        return 'beginner'
    if professional:
        return 'professional'
    if len(_TECHNICAL.findall(text)) >= 2:
        return 'professional'
    return 'neutral'


def audience_hint(message: object) -> str:
    """Indication de style pour les sorties de conversation, pas les commandes."""
    audience = audience_for(message)
    if audience == 'beginner':
        return (
            'Niveau utilisateur pour CETTE demande: debutant. En cas de conversation, '
            'explique clairement les termes, avance pas a pas, avec un exemple concret; '
            'ne suppose pas les connaissances techniques. Ne declare aucune action executee.'
        )
    if audience == 'professional':
        return (
            'Niveau utilisateur pour CETTE demande: professionnel. En cas de conversation, '
            'sois precis et structure, donne hypothese, verification et limites si utiles; '
            'ne pretends pas avoir consulte des donnees non fournies ni execute une action.'
        )
    return ''
