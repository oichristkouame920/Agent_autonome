"""Controle lecture seule de la confidentialite Git de AgentLocal.

Ne lit pas les fichiers prives, ne modifie ni Git ni Windows.
"""
from pathlib import Path
from app.git_privacy import check_private_exclusions

ROOT = Path(__file__).resolve().parent
issues, mode = check_private_exclusions(ROOT)
if issues:
    for issue in issues:
        print("ERREUR -", issue)
    raise SystemExit(1)
print("CONFIDENTIALITE GIT : OK - methode :", mode)
if mode != "git":
    print("INFO - Hors depot Git : controle de couverture locale du .gitignore uniquement.")
