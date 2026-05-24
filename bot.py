# =======================
# Imports standards
# =======================
import asyncio
import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
import os
from datetime import datetime
from config import *

name = """
 BY CODEFLIX BOTS
"""

# =======================
# Classe principale du Bot
# =======================
class Bot(Client):
    def __init__(self):
        # NE PAS supprimer la session à chaque démarrage
        # Cela force une réauthentification complète et bloque le bot
        # Si AUTH_KEY_DUPLICATED apparaît, supprime MANUELLEMENT via Koyeb console
        session_name = "Bot"
        
        super().__init__(
            name=session_name,
            api_hash=API_HASH,
            api_id=APP_ID,
            # ❌ SUPPRIMÉ : plugins auto-chargés car main.py les contrôle manuellement
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN
        )
        self.LOGGER = LOGGER
        # URL pour la Mini App (utilisé dans start.py)
        self.web_app_domain = ADSGRAM_WEBAPP_URL or f"https://{self.username}.onrender.com" if hasattr(self, 'username') else ""

    # =======================
    # Démarrage du bot
    # =======================
    async def start(self):
        await super().start()

        usr_bot_me = await self.get_me()
        self.uptime = datetime.now()
        
        # Mettre à jour le domaine web app avec le vrai username
        if not ADSGRAM_WEBAPP_URL:
            self.web_app_domain = f"https://{usr_bot_me.username}.onrender.com"

        # =======================
        # Vérification DB Channel - CRITIQUE POUR /genlink ET /batch
        # =======================
        try:
            print(f"[INIT] Connexion au canal DB (CHANNEL_ID: {CHANNEL_ID})...")
            db_channel = await self.get_chat(CHANNEL_ID)
            self.db_channel = db_channel
            
            # Test d'envoi pour vérifier les permissions
            test = await self.send_message(chat_id=db_channel.id, text="🔄 Test de connexion...")
            await test.delete()
            
            print(f"[INIT] ✅ Canal DB connecté: {db_channel.title} (ID: {db_channel.id})")
            print(f"[INIT]    Username: @{db_channel.username if db_channel.username else 'N/A'}")
            
        except Exception as e:
            self.LOGGER(__name__).error(f"[INIT] ❌ ERREUR CRITIQUE: {e}")
            self.LOGGER(__name__).error(
                f"Le bot doit être admin dans le canal DB. CHANNEL_ID={CHANNEL_ID}"
            )
            print(f"\n[ERREUR] Impossible de se connecter au canal DB. Vérifie:")
            print(f"  1. Que CHANNEL_ID ({CHANNEL_ID}) est correct")
            print(f"  2. Que le bot est admin du canal")
            print(f"  3. Que le canal existe\n")
            sys.exit(1)

        self.set_parse_mode(ParseMode.HTML)
        self.username = usr_bot_me.username

        self.LOGGER(__name__).info("Bot Running..!")
        self.LOGGER(__name__).info("BOT DEPLOYED BY @BotZFlix")
        self.LOGGER(__name__).info("Bot Running..! Made by @ZeeXDev")

        # =======================
        # Message au propriétaire
        # =======================
        try:
            await self.send_message(
                OWNER_ID,
                "<b>Bot redémarré avec succès.</b>"
            )
        except Exception as e:
            self.LOGGER(__name__).warning(f"Impossible d'envoyer message au propriétaire: {e}")

    # =======================
    # Arrêt du bot
    # =======================
    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")

    # =======================
    # Run loop
    # =======================
    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())

        self.LOGGER(__name__).info("Bot is now running. Thanks to @Kingcey")

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            self.LOGGER(__name__).info("Shutting down...")
        finally:
            loop.run_until_complete(self.stop())
