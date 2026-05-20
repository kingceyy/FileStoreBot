# ==========================================
# SYSTÈME DE CLONAGE - COMMANDE /STATS
# ==========================================

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from config import OWNER_ID
from database.database import db


@Bot.on_message(filters.command('stats') & filters.private)
async def stats_command(client: Bot, message: Message):
    """
    Commande /stats - Affiche les statistiques pour MAITRE et ADMIN
    """
    user_id = message.from_user.id
    
    # Si OWNER, afficher stats globales
    if user_id == OWNER_ID:
        return await show_owner_stats(message)
    
    # Récupérer tous les bots où l'utilisateur est admin
    user_bots = []
    all_bots = await db.get_all_cloned_bots()
    
    for bot in all_bots:
        role = await db.get_user_bot_role(bot['_id'], user_id)
        if role:
            user_bots.append({**bot, 'role': role})
    
    if not user_bots:
        return await message.reply_text(
            "<b>📊 Aucune statistique disponible</b>\n\n"
            "Vous n'êtes associé à aucun bot.\n"
            "Créez un bot avec <code>/clone</code> ou demandez à être ajouté comme admin.",
            quote=True
        )
    
    # Si plusieurs bots, afficher un résumé
    if len(user_bots) > 1:
        await show_multiple_bots_stats(message, user_bots)
    else:
        await show_single_bot_stats(message, user_bots[0]['_id'], user_id)


async def show_owner_stats(message: Message):
    """Affiche les statistiques globales pour l'owner"""
    all_stats = await db.get_all_bots_stats()
    
    if not all_stats:
        return await message.reply_text(
            "<b>📭 Aucun bot cloné</b>\n\n"
            "Il n'y a pas encore de bots dans le système.",
            quote=True
        )
    
    # Calculer les totaux
    total_bots = len(all_stats)
    active_bots = len([s for s in all_stats if s['is_active']])
    total_users = sum(s['stats']['total_users'] for s in all_stats)
    total_files = sum(s['stats']['total_files_sent'] for s in all_stats)
    total_ads = sum(s['stats']['total_ads_watched'] for s in all_stats)
    total_balance = sum(s['earnings']['balance'] for s in all_stats if s['earnings'])
    total_earned = sum(s['earnings']['total_earned'] for s in all_stats if s['earnings'])
    
    text = (
        f"<b>📊 Statistiques Globales (Owner)</b>\n\n"
        f"<b>🤖 Bots:</b>\n"
        f"• Total: {total_bots}\n"
        f"• Actifs: {active_bots}\n"
        f"• Inactifs: {total_bots - active_bots}\n\n"
        f"<b>👥 Utilisateurs:</b>\n"
        f"• Total: {total_users:,}\n\n"
        f"<b>📁 Activité:</b>\n"
        f"• Fichiers envoyés: {total_files:,}\n"
        f"• Pubs regardées: {total_ads:,}\n\n"
        f"<b>💰 Finances:</b>\n"
        f"• Solde total: ${total_balance:,.2f}\n"
        f"• Total gagné: ${total_earned:,.2f}\n\n"
        f"<i>Utilisez /bots pour plus de détails</i>"
    )
    
    buttons = [
        [InlineKeyboardButton("📋 Voir tous les bots", callback_data="list_page_0")],
        [InlineKeyboardButton("💰 Finances détaillées", callback_data="owner_finances")]
    ]
    
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), quote=True)


async def show_multiple_bots_stats(message: Message, user_bots: list):
    """Affiche les stats pour un utilisateur avec plusieurs bots"""
    total_users = 0
    total_files = 0
    total_ads = 0
    total_balance = 0
    
    text = f"<b>📊 Vos Statistiques</b>\n\n"
    text += f"<b>Bots gérés:</b> {len(user_bots)}\n\n"
    
    for bot in user_bots:
        stats = bot.get('stats', {})
        earnings = await db.get_bot_earnings(bot['_id'])
        
        users = stats.get('total_users', 0)
        files = stats.get('total_files_sent', 0)
        ads = stats.get('total_ads_watched', 0)
        balance = earnings['balance'] if earnings else 0
        
        total_users += users
        total_files += files
        total_ads += ads
        total_balance += balance
        
        role_emoji = "👑" if bot['role'] == 'maitre' else "👤"
        
        text += (
            f"{role_emoji} <b>@{bot['bot_username']}</b>\n"
            f"   👥 {users} | 📁 {files} | 💵 ${balance:.2f}\n\n"
        )
    
    text += (
        f"<b>📈 Totaux:</b>\n"
        f"👥 {total_users} utilisateurs\n"
        f"📁 {total_files} fichiers envoyés\n"
        f"📺 {total_ads} pubs regardées\n"
        f"💵 ${total_balance:.2f} solde total\n\n"
        f"<i>Cliquez sur un bot pour voir les détails</i>"
    )
    
    buttons = []
    for bot in user_bots:
        buttons.append([InlineKeyboardButton(
            f"📊 @{bot['bot_username']}",
            callback_data=f"stats_detail_{bot['_id']}"
        )])
    
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), quote=True)


async def show_single_bot_stats(message_or_callback, bot_id: int, user_id: int):
    """Affiche les stats détaillées d'un bot spécifique"""
    bot_data = await db.get_cloned_bot(bot_id)
    
    if not bot_data:
        text = "<b>❌ Bot non trouvé</b>"
        if isinstance(message_or_callback, Message):
            return await message_or_callback.reply_text(text, quote=True)
        return await message_or_callback.message.edit_text(text)
    
    # Vérifier que l'utilisateur a accès
    role = await db.get_user_bot_role(bot_id, user_id)
    if not role and user_id != OWNER_ID:
        text = "<b>⛔ Accès refusé</b>"
        if isinstance(message_or_callback, Message):
            return await message_or_callback.reply_text(text, quote=True)
        return await message_or_callback.message.edit_text(text)
    
    stats = bot_data.get('stats', {})
    earnings = await db.get_bot_earnings(bot_id)
    id_codes = await db.get_id_codes(bot_id=bot_id)
    
    role_display = {
        'maitre': '👑 Maître',
        'admin': '👤 Admin',
        'owner': '👑 Propriétaire'
    }.get(role, '👤')
    
    text = (
        f"<b>📊 Statistiques Détaillées</b>\n\n"
        f"🤖 <b>@{bot_data['bot_username']}</b>\n"
        f"{role_display}\n\n"
        f"<b>📈 Activité:</b>\n"
        f"👥 Utilisateurs totaux: {stats.get('total_users', 0):,}\n"
        f"📁 Fichiers envoyés: {stats.get('total_files_sent', 0):,}\n"
        f"📺 Pubs regardées: {stats.get('total_ads_watched', 0):,}\n\n"
    )
    
    if earnings:
        text += (
            f"<b>💰 Finances:</b>\n"
            f"💵 Solde actuel: ${earnings['balance']:.2f}\n"
            f"💰 Total gagné: ${earnings['total_earned']:.2f}\n"
            f"💸 Total retiré: ${earnings['total_withdrawn']:.2f}\n\n"
        )
    
    text += (
        f"<b>🔗 Identifiants:</b>\n"
        f"🆔 ID_PUBS: <code>{id_codes['id_pubs'] if id_codes else 'N/A'}</code>\n"
    )
    
    if role in ['maitre', 'owner']:
        text += f"🔑 ID_CODE: <code>{id_codes['id_code'] if id_codes else 'N/A'}</code>\n"
    
    text += f"\n📅 <b>Créé le:</b> {bot_data['created_at'][:10]}"
    
    buttons = []
    
    if role in ['maitre', 'owner']:
        buttons.append([InlineKeyboardButton(
            "💰 Voir les gains",
            callback_data=f"gestion_earnings_{bot_id}"
        )])
    
    buttons.append([InlineKeyboardButton(
        "⚙️ Gestion du bot",
        callback_data=f"gestion_select_{bot_id}"
    )])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.reply_text(text, reply_markup=reply_markup, quote=True)
    else:
        await message_or_callback.message.edit_text(text, reply_markup=reply_markup)


@Bot.on_callback_query(filters.regex(r"^stats_detail_(\d+)$"))
async def stats_detail_callback(client: Bot, callback_query):
    """Callback pour voir les détails d'un bot"""
    bot_id = int(callback_query.matches[0].group(1))
    user_id = callback_query.from_user.id
    
    await show_single_bot_stats(callback_query, bot_id, user_id)
    await callback_query.answer()
