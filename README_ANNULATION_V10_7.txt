AgentLocal V10.7 - Annulation contrôlée de la dernière opération fichier

Fonctions :
- annuler le dernier renommage ;
- annuler le dernier déplacement ;
- annuler la dernière copie.

Exemples :
- annule la dernière opération fichier
- annule le dernier déplacement
- annule la dernière copie
- annule le dernier renommage
- remets le dernier fichier comme avant

Sécurité :
- une seule opération réversible mémorisée ;
- mémoire uniquement en RAM, jamais persistée ;
- expiration après 15 minutes ;
- routines et habitudes interdites ;
- refus si le fichier a changé depuis l'opération ;
- refus si l'emplacement d'origine est désormais occupé ;
- une copie annulée est envoyée à la Corbeille Windows, jamais supprimée définitivement ;
- création, modification de contenu, suppression et extraction ZIP ne sont pas annulées par cette fonction.
