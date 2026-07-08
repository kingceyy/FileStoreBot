# ==========================================
# SYSTÈME DE CLONAGE - COMMANDE /CLONE
# ==========================================

import asyncio
import os
import sys
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from pyrogram.errors import AccessTokenInvalid, FloodWait
from bot import Bot
from config import OWNER_ID, APP_ID, API_HASH
from helper_func import admin
from database.database import db

logger = logging.getLogger(__name__)

# Stockage des clients clonés en mémoire
cloned_clients = {}


async def get_bot_info(token: str):
    """Récupère les informations d'un bot à partir de son token"""
    import hashlib, os

    # ✅ FIX : nom de session unique par token pour éviter la réutilisation
    # de la session du bot précédent (fichier temp_bot.session)
    token_hash = hashlib.md5(token.encode()).hexdigest()[:8]
    session_name = f"temp_verify_{token_hash}"
    session_file = f"{session_name}.session"

    temp_client = Client(
        name=session_name,
        api_id=APP_ID,
        api_hash=API_HASH,
        bot_token=token,
        no_updates=True,
        in_memory=True  # ✅ pas de fichier .session sur disque
    )
    
    try:
        await temp_client.start()
        me = await temp_client.get_me()
        await temp_client.stop()
        # Nettoyer le fichier session si créé quand même
        try:
            if os.path.exists(session_file):
                os.remove(session_file)
        except:
            pass
        return {
            'success': True,
            'id': me.id,
            'username': me.username,
            'first_name': me.first_name
        }
    except AccessTokenInvalid:
        try:
            if os.path.exists(session_file):
                os.remove(session_file)
        except:
            pass
        return {'success': False, 'error': 'Token invalide'}
    except Exception as e:
        try:
            if os.path.exists(session_file):
                os.remove(session_file)
        except:
            pass
        return {'success': False, 'error': str(e)}


@Bot.on_message(filters.command('clone') & filters.private)
async def clone_bot_command(client: Bot, message: Message):
    """
    Commande /clone - Permet de cloner le bot
    Usage: /clone {BOT_TOKEN}
    """
    user_id = message.from_user.id
    
    # Vérifier les arguments
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>Format incorrect</b>\n\n"
            "<b>Usage:</b> <code>/clone {BOT_TOKEN}</code>\n\n"
            "<b>Exemple:</b>\n"
            "<code>/clone 89171999:HKqjakakxxxxxxxxxxxxx</code>\n\n"
            "<i>Obtenez votre token depuis @BotFather.</i>",
            quote=True
        )
    
    bot_token = message.command[1].strip()
    
    try:
        current_count = await db.count_user_cloned_bots(user_id)
    except Exception as e:
        logger.error(f"Erreur comptage bots: {e}")
        current_count = 0
    
    # Vérifier si le token est déjà utilisé
    existing_bot = await db.get_cloned_bot_by_token(bot_token)
    if existing_bot:
        return await message.reply_text(
            "<b>Ce bot est déjà cloné</b>\n\n"
            f"Le bot @{existing_bot['bot_username']} existe déjà dans le système.",
            quote=True
        )
    
    # Message de traitement
    processing_msg = await message.reply_text(
        "<b>🔄 Vérification du token...</b>\n"
        "<i>Veuillez patienter</i>",
        quote=True
    )
    
    # Vérifier le token et récupérer les infos
    bot_info = await get_bot_info(bot_token)
    
    if not bot_info['success']:
        return await processing_msg.edit_text(
            f"<b>❌ Erreur lors de la vérification</b>\n\n"
            f"<code>{bot_info['error']}</code>\n\n"
            "<i>Vérifiez que le token est correct et que le bot n'est pas déjà utilisé ailleurs.</i>"
        )
    
    await processing_msg.edit_text(
        "<b>Token valide</b>\n"
        f"<b>Bot:</b> @{bot_info['username']}\n"
        f"<b>ID:</b> <code>{bot_info['id']}</code>\n"
        "<i>Création du clone...</i>"
    )
    
    try:
        # Créer l'entrée dans la base de données
        clone_data = await db.create_cloned_bot(
            bot_token=bot_token,
            master_id=user_id,
            bot_username=bot_info['username'],
            bot_id=bot_info['id'],
            api_id=APP_ID,
            api_hash=API_HASH
        )
        
        # Démarrer le bot cloné
        success = await start_cloned_bot(bot_info['id'])
        
        if success:
            await processing_msg.edit_text(
                f"<b>Bot cloné avec succès</b>\n\n"
                f"<b>Bot :</b> @{bot_info['username']}\n"
                f"<b>ID :</b> <code>{bot_info['id']}</code>\n"
                f"<b>Maître :</b> <code>{user_id}</code>\n"
                f"<b>ID_PUBS :</b> <code>{clone_data['id_pubs']}</code>\n"
                f"<b>ID_CODE :</b> <code>{clone_data['id_code']}</code>\n\n"
                f"<b>Important :</b>\n"
                f"• Conservez votre <code>ID_CODE</code> précieusement\n"
                f"• Il permet d'accéder à la page Maître\n"
                f"• Ne le partagez avec personne\n\n"
                f"<b>Prochaines étapes :</b>\n"
                f"1. Utilisez <code>/gestion</code> pour personnaliser\n"
                f"2. Configurez votre canal DB\n"
                f"3. Partagez votre <code>ID_PUBS</code> aux utilisateurs",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Gérer mon bot", callback_data=f"gestion_select_{bot_info['id']}")],
                    [InlineKeyboardButton("Guide complet", callback_data="clone_guide")]
                ])
            )
        else:
            await processing_msg.edit_text(
                f"<b>Bot créé mais non démarré</b>\n\n"
                f"Le bot @{bot_info['username']} a été enregistré mais n'a pas pu démarrer.\n"
                f"Contactez l'administrateur @kingcey ou utilisez /restart pour réessayer."
            )
            
    except Exception as e:
        logger.error(f"Erreur création bot cloné: {e}")
        await processing_msg.edit_text(
            f"<b>Erreur lors du clonage</b>\n\n"
            f"<code>{str(e)}</code>\n\n"
            f"Si la limite est atteinte, supprimez un bot existant."
        )


@Bot.on_callback_query(filters.regex(r"^clone_guide$"))
async def clone_guide_callback(client: Bot, callback):
    """Affiche le guide de clonage"""
    text = (
        "<b>Guide du système de clonage</b>\n\n"
        "<b>1. Créer un bot:</b>\n"
        "• Allez sur @BotFather\n"
        "• Créez un nouveau bot (/newbot)\n"
        "• Copiez le token reçu\n\n"
        "<b>2. Cloner:</b>\n"
        "• Envoyez <code>/clone VOTRE_TOKEN</code>\n"
        "• Le bot démarre automatiquement\n\n"
        "<b>3. Configurer:</b>\n"
        "• Utilisez <code>/gestion</code>\n"
        "• Configurez la photo, message, canal DB\n\n"
        "<b>4. Partager:</b>\n"
        "• Donnez votre ID_PUBS aux utilisateurs\n"
        "• Ils pourront utiliser votre bot\n\n"
        "<b>💰 Gains:</b>\n"
        "• Gagnez de l'argent avec les pubs\n"
        "• Seuil de retrait: $7\n"
        "• CPM: $2 par 1000 vues"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Retour", callback_data="close")
        ]]),
        parse_mode="HTML"
    )
    await callback.answer()


async def start_cloned_bot(bot_id: int) -> bool:
    """Démarre un bot cloné"""
    try:
        bot_data = await db.get_cloned_bot(bot_id)
        if not bot_data:
            logger.error(f"Bot {bot_id} non trouvé dans la DB")
            return False
        
        # Arrêter si déjà en cours
        if bot_id in cloned_clients:
            try:
                await cloned_clients[bot_id].stop()
            except:
                pass
            del cloned_clients[bot_id]
        
        # Créer le client
        # ✅ in_memory=True : pas de fichier .session sur disque
        # Render efface les fichiers à chaque redémarrage donc on ne peut pas
        # compter sur les fichiers de session. Le bot_token suffit à se reconnecter.
        client = Client(
            name=f"cloned_bot_{bot_id}",
            api_id=APP_ID,
            api_hash=API_HASH,
            bot_token=bot_data['bot_token'],
            plugins={"root": "plugins/cloned"},
            in_memory=True
        )
        
        await client.start()
        cloned_clients[bot_id] = client
        
        # Définir les commandes du menu automatiquement
        try:
            commands = [
                BotCommand("start", "Démarrer le bot"),
                BotCommand("addchnl", "Configurer le canal DB"),
                BotCommand("genlink", "Générer un lien de partage"),
                BotCommand("batch", "Créer un lien batch"),
                BotCommand("addfsub", "Ajouter canal force-sub"),
                BotCommand("delfsub", "Retirer canal force-sub"),
                BotCommand("fsub_mode", "Gérer force-sub"),
                BotCommand("dlt_time", "Temps suppression auto"),
                BotCommand("check_dlt_time", "Vérifier temps suppression"),
                BotCommand("ban", "Bannir un utilisateur"),
                BotCommand("unban", "Débannir un utilisateur"),
                BotCommand("banlist", "Liste des bannis"),
                BotCommand("add_admin", "Ajouter un admin"),
                BotCommand("deladmin", "Retirer un admin"),
                BotCommand("admins", "Liste des admins"),
                BotCommand("broadcast", "Diffuser un message"),
                BotCommand("pbroadcast", "Diffuser un message en l'épinglant"),
                BotCommand("dbroadcast", "Diffuser un document"),
                BotCommand("custom_batch", "Batch personnalisé"),
                BotCommand("stats", "Statistiques du bot"),
                BotCommand("users", "Nombre d'utilisateurs"),
            ]
            
            await client.set_bot_commands(commands)
            logger.info(f"[CLONE] Commandes définies pour @{bot_data['bot_username']}")
            
        except Exception as e:
            logger.warning(f"[CLONE] Impossible de définir les commandes: {e}")
        
        logger.info(f"[CLONE] Bot @{bot_data['bot_username']} démarré (ID: {bot_id})")
        return True
        
    except Exception as e:
        logger.error(f"[CLONE ERROR] Impossible de démarrer le bot {bot_id}: {e}")
        return False


async def stop_cloned_bot(bot_id: int) -> bool:
    """Arrête un bot cloné"""
    try:
        if bot_id in cloned_clients:
            await cloned_clients[bot_id].stop()
            del cloned_clients[bot_id]
            logger.info(f"[CLONE] Bot {bot_id} arrêté")
        
        # Mettre à jour le statut dans la DB
        await db.update_bot_settings(bot_id, {'is_active': False})
        return True
        
    except Exception as e:
        logger.error(f"[CLONE ERROR] Erreur arrêt bot {bot_id}: {e}")
        return False


async def restart_cloned_bot(bot_id: int) -> bool:
    """Redémarre un bot cloné"""
    await stop_cloned_bot(bot_id)
    await asyncio.sleep(2)
    return await start_cloned_bot(bot_id)


async def restart_all_cloned_bots():
    """Redémarre tous les bots clonés au démarrage du bot mère"""
    logger.info("[CLONE] Redémarrage des bots clonés...")

    # ✅ FIX : attendre que MongoDB soit connecté avant de lire les bots
    for attempt in range(15):
        try:
            if db._initialized:
                break
            await db.init()
            break
        except Exception as e:
            logger.warning(f"[CLONE] MongoDB pas encore prêt (tentative {attempt+1}/15): {e}")
            await asyncio.sleep(2)

    bots = await db.get_all_cloned_bots()
    
    started = 0
    failed = 0
    
    for bot_data in bots:
        if bot_data.get('is_active', True):
            # CORRECTION: utiliser bot_id (int) et non _id (string ObjectId)
            real_bot_id = bot_data.get('bot_id')
            if real_bot_id is None:
                logger.warning(f"[CLONE] Bot sans bot_id ignoré: {bot_data.get('_id')}")
                failed += 1
                continue
            success = await start_cloned_bot(int(real_bot_id))
            if success:
                started += 1
            else:
                failed += 1
            await asyncio.sleep(1)  # Éviter le flood
    
    logger.info(f"[CLONE] {started} bots démarrés, {failed} échecs")
    return started, failed


# Démarrer tous les bots clonés au lancement
async def init_cloned_bots():
    """Initialise tous les bots clonés au démarrage"""
    await restart_all_cloned_bots()


# Commande /restart pour redémarrer un bot spécifique (OWNER uniquement)
@Bot.on_message(filters.command('restart') & filters.private & filters.user(OWNER_ID))
async def restart_bot_command(client: Bot, message: Message):
    """Redémarre un bot cloné spécifique"""
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>Format incorrect</b>\n\n"
            "<b>Usage:</b> <code>/restart BOT_ID</code>\n\n"
            "Exemple: <code>/restart 123456789</code>",
            quote=True
        )
    
    try:
        bot_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ ID invalide. Doit être un nombre.", quote=True)
    
    processing = await message.reply_text(f"<b>🔄 Redémarrage du bot {bot_id}...</b>", quote=True)
    
    success = await restart_cloned_bot(bot_id)
    
    if success:
        await processing.edit_text(f"<b>✅ Bot {bot_id} redémarré avec succès!</b>")
    else:
        await processing.edit_text(f"<b>❌ Échec du redémarrage du bot {bot_id}</b>\n\nVérifiez les logs.")
