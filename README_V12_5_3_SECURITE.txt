AgentLocal V12.5.3 - Centre de securite et elevation UAC ponctuelle

1. Ouvrir AgentLocal.bat (double-clic), puis choisir [10] Securite et autorisations.
   Ou dans l interface AgentLocal : Parametres avances > Securite et autorisations.
2. Laisser les demandes UAC desactivees (par defaut) si non necessaires.
3. Pour autoriser une action systeme ponctuelle, cocher "Permettre les demandes UAC ponctuelles", puis enregistrer.
4. L action "Vider le cache DNS" necessite un clic et une confirmation explicites ; Windows peut ensuite demander l autorisation UAC.
5. Aucune elevation administrateur permanente n est accordee. Les commandes PowerShell/cmd arbitraires restent interdites.
6. On peut desactiver les demandes UAC depuis le meme ecran. Cela ne modifie pas les regles UAC de Windows.

Limitations :
- Pour cette premiere integration, la seule operation systeme elevee disponible est le vidage du cache DNS.
- Cette operation n est pas accessible aux commandes libres de l IA, routines ou notifications ; uniquement au bouton dedie.
- L execution reelle UAC et de ipconfig doit etre validee sur Windows 10/11.
- Une autorisation ponctuelle signifie une confirmation UAC possible a chaque demande admin. Windows ne permet pas d accorder un consentement global sans affaiblir la securite.
- Le contenu de config/permissions.json n est pas modifie.

Tests : AgentLocal.bat test (complet) ou python -m unittest discover -s tests -p test_v12_5_3_security.py -v
