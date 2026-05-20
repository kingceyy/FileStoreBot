import os
from os import environ, getenv
import logging
from logging.handlers import RotatingFileHandler

# ==========================================
# CONFIGURATION BOT TELEGRAM
# ==========================================

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "8020965278:AAEdbGIXLo8s3PAhqzJSDnSRCS5UCq68qGU")
APP_ID       = int(os.environ.get("APP_ID", "25926022"))
API_HASH     = os.environ.get("API_HASH", "30db27d9e56d854fb5e943723268db32")

# ==========================================
# CONFIGURATION BASE DE DONNÉES & CHANNEL
# ==========================================

CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1003723207523"))
OWNER      = os.environ.get("OWNER", "YumeFlowerBot")
OWNER_ID   = int(os.environ.get("OWNER_ID", "8467461906"))

DB_URI  = os.environ.get("DATABASE_URL", "mongodb+srv://elisabethboko45_db_user:kmrLKNKnfe8lK1df@cluster0.isv90ao.mongodb.net/?appName=Cluster0")
DB_NAME = os.environ.get("DATABASE_NAME", "Cluster0")

# ==========================================
# CONFIGURATION SERVEUR WEB & MINI APP
# ==========================================

PORT = os.environ.get("PORT", "8001")

# URL de ta WebApp Vercel — à mettre à jour si tu changes de domaine
ADSGRAM_WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://jks-blond.vercel.app")

# Mot de passe pour la page /admin de la WebApp
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "kingcey00")

# Durée des sessions gratuites en minutes
FREE_SESSION_DURATION     = int(os.environ.get("FREE_SESSION_DURATION", "10"))
DEFAULT_FREE_SESSION_MINUTES = int(os.environ.get("DEFAULT_FREE_SESSION_MINUTES", "10"))

# ==========================================
# CONFIGURATION FORCE SUB & LIENS
# ==========================================

FSUB_LINK_EXPIRY = int(getenv("FSUB_LINK_EXPIRY", "840"))
BAN_SUPPORT      = os.environ.get("BAN_SUPPORT", "https://t.me/BTZF_CHAT")
TG_BOT_WORKERS   = int(os.environ.get("TG_BOT_WORKERS", "200"))

# ==========================================
# MÉDIAS & IMAGES
# ==========================================

START_PIC = os.environ.get("START_PIC", "https://files.catbox.moe/tor45x.jpg")
FORCE_PIC = os.environ.get("FORCE_PIC", "https://files.catbox.moe/42lm1v.jpg")

# ==========================================
# TEXTES & MESSAGES — Version professionnelle
# ==========================================

HELP_TXT = (
    "<b>Bienvenue sur YumeFlower</b>\n\n"
    "<blockquote>"
    "Bot de stockage et de partage de fichiers propulsé par @kingceyy.\n\n"
    "Partagez vos fichiers anime, manga et bien plus encore avec votre communauté.\n\n"
    "Créez votre propre bot de stockage avec la commande /clone."
    "</blockquote>"
)

ABOUT_TXT = (
    "<b>YumeFlower — Plateforme de partage de fichiers</b>\n\n"
    "<blockquote>"
    "YumeFlower est un bot open-source de stockage et de partage de fichiers Telegram.\n\n"
    "<b>Clonez votre propre bot</b>\n"
    "En une seule commande <code>/clone</code>, obtenez votre propre bot personnalisé.\n"
    "Votre nom, votre image, votre communauté.\n\n"
    "<b>Gagnez de l'argent</b>\n"
    "Chaque utilisateur qui regarde une publicité sur votre bot vous rapporte de l'argent automatiquement.\n"
    "CPM jusqu'à 2$ — jusqu'à 300$/mois selon votre trafic.\n\n"
    "<b>Entièrement gratuit</b>\n"
    "Aucune compétence requise. Votre bot, vos règles, vos revenus."
    "</blockquote>\n\n"
    "Tapez <b>/clone</b> pour démarrer."
)

START_MSG = os.environ.get(
    "START_MESSAGE",
    "<b>Bienvenue, {first}</b>\n\n"
    "<blockquote>"
    "YumeFlower est votre bot de stockage de fichiers.\n\n"
    "Vous pouvez créer votre propre bot et gagner de l'argent grâce aux publicités affichées à vos utilisateurs.\n\n"
    "Commande : /clone"
    "</blockquote>"
)

FORCE_MSG = os.environ.get(
    "FORCE_SUB_MESSAGE",
    "<b>Accès restreint</b>\n\n"
    "Pour accéder aux fichiers, vous devez rejoindre le(s) canal(aux) requis.\n\n"
    "Rejoignez-les ci-dessous puis réessayez."
)

CMD_TXT = """<b>Commandes administrateur</b>

<b>/dlt_time</b> — Définir le délai de suppression automatique
<b>/check_dlt_time</b> — Vérifier le délai actuel
<b>/dbroadcast</b> — Diffuser un document ou une vidéo
<b>/ban</b> — Bannir un utilisateur
<b>/unban</b> — Débannir un utilisateur
<b>/banlist</b> — Liste des utilisateurs bannis
<b>/addchnl</b> — Ajouter un canal d'abonnement obligatoire
<b>/delchnl</b> — Supprimer un canal d'abonnement obligatoire
<b>/listchnl</b> — Voir les canaux configurés
<b>/fsub_mode</b> — Activer ou désactiver le force-sub
<b>/pbroadcast</b> — Envoyer une photo à tous les utilisateurs
<b>/add_admin</b> — Ajouter un administrateur
<b>/deladmin</b> — Supprimer un administrateur
<b>/custom_batch</b> — Batch personnalisé
<b>/admins</b> — Liste des administrateurs
<b>/prime user_id durée</b> — Accorder une session premium (durée en secondes)
<b>/delprime user_id</b> — Supprimer la session d'un utilisateur

<b>/clone</b> — Cloner le bot
<b>/gestion</b> — Gérer votre bot cloné
<b>/list</b> — Liste des bots clonés (Owner uniquement)
<b>/bots</b> — Vue d'ensemble des bots (Owner uniquement)
<b>/stats</b> — Statistiques du bot
"""

# ==========================================
# OPTIONS DE PROTECTION & AFFICHAGE
# ==========================================

CUSTOM_CAPTION       = os.environ.get("CUSTOM_CAPTION", None)
PROTECT_CONTENT      = True if os.environ.get("PROTECT_CONTENT", "False") == "True" else False
DISABLE_CHANNEL_BUTTON = os.environ.get("DISABLE_CHANNEL_BUTTON", None) == "False"
FILE_AUTO_DELETE     = 0  # désactivé par défaut, configurable via /dlt_time

BOT_STATS_TEXT  = "<b>Temps de fonctionnement du bot</b>\n{uptime}"
USER_REPLY_TEXT = "Cette commande est réservée aux administrateurs."

# ==========================================
# CONFIGURATION LOGGING
# ==========================================

LOG_FILE_NAME = "filesharingbot.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler(LOG_FILE_NAME, maxBytes=50000000, backupCount=10),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)


# ==========================================
# CONFIGURATION SYSTÈME DE CLONAGE
# ==========================================

MOTHER_BOT_USERNAME      = os.environ.get("MOTHER_BOT_USERNAME", "YumeFlowerBot")
MOTHER_BOT_LINK          = f"https://t.me/{MOTHER_BOT_USERNAME}"
EARNING_PER_IMPRESSION   = float(os.environ.get("EARNING_PER_IMPRESSION", "0.001"))
MIN_WITHDRAWAL_AMOUNT    = float(os.environ.get("MIN_WITHDRAWAL_AMOUNT", "7.00"))
