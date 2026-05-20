import os
# Creating the __init__.py for cloned plugins and updated config.py

# Plugins pour bots clonés
# Ce dossier contient les handlers pour les bots clonés


# ==========================================
# CONFIGURATION SYSTÈME DE CLONAGE
# ==========================================

# Username du bot mère (pour le bouton "Créer votre propre bot")
MOTHER_BOT_USERNAME = os.environ.get("MOTHER_BOT_USERNAME", "YumeFlowerBot")

# Gain par impression (en dollars)
EARNING_PER_IMPRESSION = float(os.environ.get("EARNING_PER_IMPRESSION", "0.01"))

# Seuil minimum de retrait (en dollars)
MIN_WITHDRAWAL_AMOUNT = float(os.environ.get("MIN_WITHDRAWAL_AMOUNT", "7.00"))

# Durée par défaut des sessions gratuites (minutes)
DEFAULT_FREE_SESSION_MINUTES = int(os.environ.get("DEFAULT_FREE_SESSION_MINUTES", "10"))
