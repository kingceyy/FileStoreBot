# ==========================================
# plugins/cloned/commands.py
# COMMANDES ADMIN SUPPLÉMENTAIRES POUR BOTS CLONÉS
# ==========================================

import asyncio
import logging
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait

from database.database import db

logger = logging.getLogger(__name__)

# ============================================================
# FILTRE ADMIN POUR BOTS CLONÉS
# ============================================================

def cloned_admin_filter():
    async def func(flt, client, message):
        if not message.from_user:
            return False
        user_id = message.from_user.id
        bot_id = client.me.id
        
        bot_data = await db.get_cloned_bot(bot_id)
        if not bot_data:
            return False
        
        # Le maître a toujours accès
        master_id = bot_data.get('master_id') or bot_data.get('owner_id')
        if master_id and user_id == master_id:
            return True
        
        # Vérifier le rôle dans la DB
        role = await db.get_user_bot_role(bot_id, user_id)
        if role in ['maitre', 'admin']:
            return True
        
        return False
    return filters.create(func, name="ClonedAdminFilter")

cloned_admin = cloned_admin_filter()


# ============================================================
# /dlt_time - Définir le temps de suppression auto
# ============================================================

@Client.on_message(filters.command('dlt_time') & filters.private & cloned_admin)
async def dlt_time_command(client: Client, message: Message):
    """
    Définit le temps de suppression automatique des messages.
    Usage: /dlt_time 10 (en minutes, 0 pour désactiver)
    """
    bot_id = client.me.id
    
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/dlt_time 10</code>\n\n"
            "<i>Durée en minutes. 0 pour désactiver.</i>",
            quote=True, parse_mode=ParseMode.HTML
        )
    
    try:
        minutes = int(message.command[1])
        if minutes < 0:
            raise ValueError()
        
        # Sauvegarder dans les settings
        await db.update_bot_settings(bot_id, {'delete_timer': minutes})
        
        if minutes == 0:
            await message.reply_text(
                "<b>✅ Suppression automatique désactivée</b>",
                quote=True, parse_mode=ParseMode.HTML
            )
        else:
            await message.reply_text(
                f"<b>✅ Temps de suppression défini:</b> {minutes} minutes",
                quote=True, parse_mode=ParseMode.HTML
            )
            
    except ValueError:
        await message.reply_text(
            "<b>❌ Valeur invalide</b>\n"
            "Envoyez un nombre entier (ex: 10)",
            quote=True, parse_mode=ParseMode.HTML
        )


# ============================================================
# /check_dlt_time - Vérifier le temps de suppression
# ============================================================

@Client.on_message(filters.command('check_dlt_time') & filters.private & cloned_admin)
async def check_dlt_time_command(client: Client, message: Message):
    """Vérifie le temps de suppression actuel"""
    bot_id = client.me.id
    
    bot_data = await db.get_cloned_bot(bot_id)
    timer = bot_data.get('settings', {}).get('delete_timer', 0)
    
    if timer == 0:
        text = "<b>⏱️ Suppression automatique:</b> Désactivée"
    else:
        text = f"<b>⏱️ Temps de suppression:</b> {timer} minutes"
    
    await message.reply_text(text, quote=True, parse_mode=ParseMode.HTML)


# ============================================================
# /ban - Bannir un utilisateur
# ============================================================

@Client.on_message(filters.command('ban') & filters.private & cloned_admin)
async def ban_command(client: Client, message: Message):
    """
    Bannit un utilisateur du bot.
    Usage: /ban USER_ID [raison]
    """
    bot_id = client.me.id
    
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/ban USER_ID [raison]</code>",
            quote=True, parse_mode=ParseMode.HTML
        )
    
    try:
        user_id_to_ban = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ ID invalide", quote=True)
    
    # Vérifier que ce n'est pas le maître
    bot_data = await db.get_cloned_bot(bot_id)
    master_id = bot_data.get('master_id') or bot_data.get('owner_id')
    if user_id_to_ban == master_id:
        return await message.reply_text("❌ Impossible de bannir le maître!", quote=True)
    
    reason = " ".join(message.command[2:]) if len(message.command) > 2 else "Non spécifiée"
    
    try:
        await db.ban_user_from_bot(bot_id, user_id_to_ban, reason)
        await message.reply_text(
            f"<b>✅ Utilisateur banni</b>\n\n"
            f"🆔 ID: <code>{user_id_to_ban}</code>\n"
            f"📝 Raison: {reason}",
            quote=True, parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.reply_text(f"❌ Erreur: {e}", quote=True)


# ============================================================
# /unban - Débannir un utilisateur
# ============================================================

@Client.on_message(filters.command('unban') & filters.private & cloned_admin)
async def unban_command(client: Client, message: Message):
    """Débannit un utilisateur"""
    bot_id = client.me.id
    
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/unban USER_ID</code>",
            quote=True, parse_mode=ParseMode.HTML
        )
    
    try:
        user_id_to_unban = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ ID invalide", quote=True)
    
    try:
        await db.unban_user_from_bot(bot_id, user_id_to_unban)
        await message.reply_text(
            f"<b>✅ Utilisateur débanni</b>\n\n"
            f"🆔 ID: <code>{user_id_to_unban}</code>",
            quote=True, parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.reply_text(f"❌ Erreur: {e}", quote=True)


# ============================================================
# /banlist - Liste des bannis
# ============================================================

@Client.on_message(filters.command('banlist') & filters.private & cloned_admin)
async def banlist_command(client: Client, message: Message):
    """Affiche la liste des utilisateurs bannis"""
    bot_id = client.me.id
    
    try:
        banned = await db.get_banned_users(bot_id)
        
        if not banned:
            return await message.reply_text(
                "<b>📋 Liste des bannis:</b>\n\n<i>Aucun utilisateur banni</i>",
                quote=True, parse_mode=ParseMode.HTML
            )
        
        text = f"<b>📋 Liste des bannis ({len(banned)}):</b>\n\n"
        for ban in banned[:50]:  # Limiter à 50
            user_id = ban.get('user_id', 'Inconnu')
            reason = ban.get('reason', 'Non spécifiée')
            date = ban.get('banned_at', 'Inconnue')[:10]
            text += f"• <code>{user_id}</code> - {reason} ({date})\n"
        
        if len(banned) > 50:
            text += f"\n<i>... et {len(banned) - 50} autres</i>"
        
        await message.reply_text(text, quote=True, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await message.reply_text(f"❌ Erreur: {e}", quote=True)


# ============================================================
# /add_admin - Ajouter un admin (pour le bot cloné)
# ============================================================

@Client.on_message(filters.command('add_admin') & filters.private & cloned_admin)
async def add_admin_command(client: Client, message: Message):
    """
    Ajoute un admin au bot cloné (commande rapide).
    Usage: /add_admin USER_ID
    """
    bot_id = client.me.id
    
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/add_admin USER_ID</code>",
            quote=True, parse_mode=ParseMode.HTML
        )
    
    try:
        new_admin_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ ID invalide", quote=True)
    
    # Vérifier permissions (seul maitre peut ajouter des admins)
    bot_data = await db.get_cloned_bot(bot_id)
    master_id = bot_data.get('master_id') or bot_data.get('owner_id')
    
    if message.from_user.id != master_id:
        return await message.reply_text("⛔ Seul le MAITRE peut ajouter des admins", quote=True)
    
    try:
        # Ajouter dans le vrai systeme de permissions (collection bot_admins)
        existing_role = await db.get_user_bot_role(bot_id, new_admin_id)
        if existing_role:
            return await message.reply_text("❌ Cet utilisateur est déjà admin", quote=True)
        
        await db.add_bot_admin(bot_id, new_admin_id, "admin", message.from_user.id)
        
        # Essayer de récupérer les infos
        try:
            user = await client.get_users(new_admin_id)
            name = user.first_name
        except:
            name = f"ID:{new_admin_id}"
        
        await message.reply_text(
            f"<b>✅ Administrateur ajouté</b>\n\n"
            f"👤 {name} (<code>{new_admin_id}</code>)",
            quote=True, parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Erreur: {e}", quote=True)


# ============================================================
# /deladmin - Retirer un admin
# ============================================================

@Client.on_message(filters.command('deladmin') & filters.private & cloned_admin)
async def deladmin_command(client: Client, message: Message):
    """Retire un admin du bot cloné"""
    bot_id = client.me.id
    
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/deladmin USER_ID</code>",
            quote=True, parse_mode=ParseMode.HTML
        )
    
    try:
        admin_id_to_remove = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ ID invalide", quote=True)
    
    # Vérifier permissions
    bot_data = await db.get_cloned_bot(bot_id)
    master_id = bot_data.get('master_id') or bot_data.get('owner_id')
    
    if message.from_user.id != master_id:
        return await message.reply_text("⛔ Seul le MAITRE peut retirer des admins", quote=True)
    
    if admin_id_to_remove == master_id:
        return await message.reply_text("❌ Impossible de retirer le maître", quote=True)
    
    try:
        existing_role = await db.get_user_bot_role(bot_id, admin_id_to_remove)
        if not existing_role:
            return await message.reply_text("❌ Cet utilisateur n'est pas admin", quote=True)
        
        await db.remove_bot_admin(bot_id, admin_id_to_remove)
        
        await message.reply_text(
            f"<b>✅ Administrateur retiré</b>\n\n"
            f"🆔 ID: <code>{admin_id_to_remove}</code>",
            quote=True, parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Erreur: {e}", quote=True)


# ============================================================
# /admins - Liste des admins
# ============================================================

@Client.on_message(filters.command('admins') & filters.private & cloned_admin)
async def admins_command(client: Client, message: Message):
    """Liste tous les admins du bot"""
    bot_id = client.me.id
    
    bot_data = await db.get_cloned_bot(bot_id)
    admins_list = await db.get_bot_admins(bot_id)
    master_id = bot_data.get('master_id') or bot_data.get('owner_id')
    admins = [a['user_id'] for a in admins_list if a.get('role') == 'admin']
    
    text = "<b>👥 Liste des Administrateurs</b>\n\n"
    
    # Maître
    try:
        master = await client.get_users(master_id)
        text += f"👑 <b>Maître:</b> {master.first_name} (<code>{master_id}</code>)\n"
    except:
        text += f"👑 <b>Maître:</b> <code>{master_id}</code>\n"
    
    # Admins
    if admins:
        text += f"\n<b>Admins ({len(admins)}):</b>\n"
        for admin_id in admins:
            try:
                user = await client.get_users(admin_id)
                text += f"• {user.first_name} (<code>{admin_id}</code>)\n"
            except:
                text += f"• <code>{admin_id}</code>\n"
    else:
        text += "\n<i>Aucun admin supplémentaire</i>"
    
    await message.reply_text(text, quote=True, parse_mode=ParseMode.HTML)


# ============================================================
# /pbroadcast - Diffuser une photo
# ============================================================

@Client.on_message(filters.command('pbroadcast') & filters.private & cloned_admin)
async def pbroadcast_command(client: Client, message: Message):
    """
    Diffuse une photo à tous les utilisateurs.
    Répondez à une photo avec /pbroadcast
    """
    bot_id = client.me.id
    
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.reply_text(
            "<b>❌ Répondez à une photo avec /pbroadcast</b>",
            quote=True, parse_mode=ParseMode.HTML
        )
    
    # Récupérer la légende si présente
    caption = message.reply_to_message.caption or ""
    
    try:
        users = await db.get_bot_users(bot_id)
    except Exception:
        users = []
    
    if not users:
        return await message.reply_text("❌ Aucun utilisateur", quote=True)
    
    photo = message.reply_to_message.photo[-1].file_id
    total = len(users)
    sent = 0
    failed = 0
    
    status = await message.reply_text(f"📤 Diffusion en cours... 0/{total}", quote=True)
    
    for user in users:
        try:
            user_id = user['user_id'] if isinstance(user, dict) else user
            await client.send_photo(user_id, photo=photo, caption=caption)
            sent += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            failed += 1
        
        if (sent + failed) % 50 == 0:
            try:
                await status.edit_text(f"📤 {sent + failed}/{total} | ✅ {sent} | ❌ {failed}")
            except:
                pass
        
        await asyncio.sleep(0.05)
    
    await status.edit_text(
        f"<b>✅ Diffusion terminée</b>\n\n"
        f"📊 Total: {total}\n"
        f"✅ Envoyés: {sent}\n"
        f"❌ Échoués: {failed}",
        parse_mode=ParseMode.HTML
    )


# ============================================================
# /dbroadcast - Diffuser un document/vidéo
# ============================================================

@Client.on_message(filters.command('dbroadcast') & filters.private & cloned_admin)
async def dbroadcast_command(client: Client, message: Message):
    """
    Diffuse un document ou vidéo à tous les utilisateurs.
    Répondez avec /dbroadcast
    """
    bot_id = client.me.id
    
    if not message.reply_to_message:
        return await message.reply_text(
            "<b>❌ Répondez à un document/vidéo avec /dbroadcast</b>",
            quote=True, parse_mode=ParseMode.HTML
        )
    
    reply = message.reply_to_message
    if not (reply.document or reply.video):
        return await message.reply_text("❌ Le message doit contenir un document ou vidéo", quote=True)
    
    try:
        users = await db.get_bot_users(bot_id)
    except Exception:
        users = []
    
    if not users:
        return await message.reply_text("❌ Aucun utilisateur", quote=True)
    
    total = len(users)
    sent = 0
    failed = 0
    
    status = await message.reply_text(f"📤 Diffusion en cours... 0/{total}", quote=True)
    
    for user in users:
        try:
            user_id = user['user_id'] if isinstance(user, dict) else user
            await reply.copy(user_id)
            sent += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            failed += 1
        
        if (sent + failed) % 50 == 0:
            try:
                await status.edit_text(f"📤 {sent + failed}/{total} | ✅ {sent} | ❌ {failed}")
            except:
                pass
        
        await asyncio.sleep(0.05)
    
    await status.edit_text(
        f"<b>✅ Diffusion terminée</b>\n\n"
        f"📊 Total: {total}\n"
        f"✅ Envoyés: {sent}\n"
        f"❌ Échoués: {failed}",
        parse_mode=ParseMode.HTML
    )


# ============================================================
# /custom_batch - Batch personnalisée
# ============================================================

@Client.on_message(filters.command('custom_batch') & filters.private & cloned_admin)
async def custom_batch_command(client: Client, message: Message):
    """
    Crée un lien batch personnalisé.
    Usage: /custom_batch START_ID END_ID
    """
    bot_id = client.me.id
    
    if len(message.command) < 3:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/custom_batch START_ID END_ID</code>\n\n"
            "<i>Les IDs sont les numéros de messages dans le canal DB</i>",
            quote=True, parse_mode=ParseMode.HTML
        )
    
    try:
        start_id = int(message.command[1])
        end_id = int(message.command[2])
    except ValueError:
        return await message.reply_text("❌ IDs invalides", quote=True)
    
    if start_id > end_id:
        return await message.reply_text("❌ START_ID doit être inférieur à END_ID", quote=True)
    
    if end_id - start_id > 200:
        return await message.reply_text("❌ Maximum 200 fichiers par batch", quote=True)
    
    # Récupérer le canal DB
    bot_data = await db.get_cloned_bot(bot_id)
    channel_id = bot_data.get('settings', {}).get('channel_id')
    
    if not channel_id:
        return await message.reply_text("❌ Canal DB non configuré", quote=True)
    
    # Générer le lien (même logique que /batch)
    import base64
    
    string = f"get-{start_id * abs(channel_id)}-{end_id * abs(channel_id)}"
    base64_bytes = base64.urlsafe_b64encode(string.encode()).decode().rstrip("=")
    link = f"https://t.me/{client.me.username}?start={base64_bytes}"
    
    await message.reply_text(
        f"<b>✅ Lien batch personnalisé</b>\n\n"
        f"📁 Fichiers: {start_id} à {end_id} ({end_id - start_id + 1} total)\n\n"
        f"<code>{link}</code>",
        quote=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Partager", url=f"https://telegram.me/share/url?url={link}")]
        ]),
        parse_mode=ParseMode.HTML
    )
