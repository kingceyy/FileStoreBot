# ==========================================
# SYSTÈME DE CLONAGE - COMMANDES /LIST ET /BOTS
# ==========================================

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot import Bot
from config import OWNER_ID
from database.database import db


# ============================================================
# COMMANDE /LIST (OWNER UNIQUEMENT)
# ============================================================

@Bot.on_message(filters.command('list') & filters.private & filters.user(OWNER_ID))
async def list_bots_command(client: Bot, message: Message):
    """
    Commande /list - Liste tous les bots clonés avec pagination
    Accessible uniquement par l'OWNER
    """
    bots = await db.get_all_cloned_bots()
    
    if not bots:
        return await message.reply_text(
            "<b>Aucun bot cloné</b>\n\nAucun bot n'a encore été créé dans le système.",
            quote=True
        )
    
    # Afficher la première page
    await show_bots_list(message, bots, page=0)


async def show_bots_list(message_or_callback, bots: list, page: int = 0, per_page: int = 5):
    """Affiche la liste des bots avec pagination"""
    total_bots = len(bots)
    total_pages = (total_bots - 1) // per_page + 1 if total_bots > 0 else 1
    
    # Calculer les indices
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, total_bots)
    current_bots = bots[start_idx:end_idx]
    
    text = f"<b>Bots clonés</b>\n\n"
    text += f"<b>Total :</b> {total_bots} | <b>Page :</b> {page + 1}/{total_pages}\n\n"
    
    buttons = []
    
    for i, bot in enumerate(current_bots, start_idx + 1):
        # Récupérer les infos supplémentaires
        id_codes = await db.get_id_codes(bot_id=bot['bot_id'])
        earnings = await db.get_bot_earnings(bot['bot_id'])
        
        status = "🟢" if bot.get('is_active', True) else "🔴"
        
        balance = earnings['balance'] if earnings else 0.0
        text += (
            f"{i}. {status} @{bot['bot_username']}\n"
            f"   Maître : <code>{bot['master_id']}</code>\n"
            f"   ID_PUBS : <code>{id_codes['id_pubs'] if id_codes else 'N/A'}</code>\n"
            f"   Solde : ${balance:.2f}\n"
            f"   Créé le : {bot['created_at'][:10]}\n\n"
        )
        
        # Bouton pour voir les détails
        buttons.append([InlineKeyboardButton(
            f"Détails @{bot['bot_username']}",
            callback_data=f"list_details_{bot['bot_id']}"
        )])
    
    # Boutons de pagination
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("Précédent", callback_data=f"list_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Suivant", callback_data=f"list_page_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton("Fermer", callback_data="close")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=reply_markup)
    else:
        await message_or_callback.reply_text(text, reply_markup=reply_markup)


@Bot.on_callback_query(filters.regex(r"^list_page_(\d+)$"))
async def list_page_callback(client: Bot, callback: CallbackQuery):
    """Gère la pagination de la liste"""
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Accès refusé", show_alert=True)
    
    page = int(callback.matches[0].group(1))
    bots = await db.get_all_cloned_bots()
    
    await show_bots_list(callback, bots, page=page)
    await callback.answer()


@Bot.on_callback_query(filters.regex(r"^list_details_(\d+)$"))
async def list_details_callback(client: Bot, callback: CallbackQuery):
    """Affiche les détails d'un bot"""
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Accès refusé", show_alert=True)
    
    bot_id = int(callback.matches[0].group(1))
    bot_data = await db.get_cloned_bot(bot_id)
    
    if not bot_data:
        return await callback.answer("❌ Bot non trouvé", show_alert=True)
    
    id_codes = await db.get_id_codes(bot_id=bot_id)
    earnings = await db.get_bot_earnings(bot_id)
    stats = bot_data.get('stats', {})
    
    # Récupérer les admins du bot
    admins = await db.get_bot_admins(bot_id)
    admins_text = ""
    for admin in admins:
        role_emoji = "👑" if admin['role'] == 'maitre' else "👤"
        admins_text += f"{role_emoji} <code>{admin['user_id']}</code>\n"
    
    text = (
        f"<b>📋 Détails du Bot</b>\n\n"
        f"🤖 <b>Username:</b> @{bot_data['bot_username']}\n"
        f"🆔 <b>ID:</b> <code>{bot_id}</code>\n"
        f"👤 <b>Maître:</b> <code>{bot_data['master_id']}</code>\n"
        f"📅 <b>Créé le:</b> {bot_data['created_at'][:19].replace('T', ' ')}\n"
        f"{'🟢 Actif' if bot_data.get('is_active') else '🔴 Inactif'}\n\n"
        f"<b>🔗 Identifiants:</b>\n"
        f"🆔 ID_PUBS: <code>{id_codes['id_pubs'] if id_codes else 'N/A'}</code>\n"
        f"🔑 ID_CODE: <code>{id_codes['id_code'] if id_codes else 'N/A'}</code>\n\n"
        f"<b>💰 Gains:</b>\n"
        f"💵 Solde: ${earnings['balance']:.2f if earnings else 0:.2f}\n"
        f"💰 Total gagné: ${earnings['total_earned']:.2f if earnings else 0:.2f}\n"
        f"💸 Total retiré: ${earnings['total_withdrawn']:.2f if earnings else 0:.2f}\n\n"
        f"<b>📊 Statistiques:</b>\n"
        f"👥 Utilisateurs: {stats.get('total_users', 0)}\n"
        f"📁 Fichiers envoyés: {stats.get('total_files_sent', 0)}\n"
        f"📺 Pubs regardées: {stats.get('total_ads_watched', 0)}\n\n"
        f"<b>👥 Admins ({len(admins)}):</b>\n"
        f"{admins_text if admins_text else 'Aucun admin'}"
    )
    
    buttons = [
        [InlineKeyboardButton("💰 Modifier solde", callback_data=f"admin_credit_{bot_id}")],
        [InlineKeyboardButton("🔄 Redémarrer", callback_data=f"admin_restart_{bot_id}")],
        [InlineKeyboardButton("🗑️ Supprimer", callback_data=f"admin_delete_{bot_id}")],
        [InlineKeyboardButton("‹ Retour à la liste", callback_data="list_page_0")]
    ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    await callback.answer()


# ============================================================
# COMMANDE /BOTS (OWNER UNIQUEMENT - INFOS COMPLÈTES)
# ============================================================

@Bot.on_message(filters.command('bots') & filters.private & filters.user(OWNER_ID))
async def bots_command(client: Bot, message: Message):
    """
    Commande /bots - Vue d'ensemble complète de tous les bots
    Accessible uniquement par l'OWNER
    """
    all_stats = await db.get_all_bots_stats()
    
    if not all_stats:
        return await message.reply_text(
            "<b>Aucun bot cloné</b>\n\nAucun bot n'a encore été créé dans le système.",
            quote=True
        )
    
    # Calculer les totaux
    total_balance = sum(s['earnings']['balance'] for s in all_stats if s['earnings'])
    total_earned = sum(s['earnings']['total_earned'] for s in all_stats if s['earnings'])
    total_users = sum(s['stats']['total_users'] for s in all_stats)
    total_files = sum(s['stats']['total_files_sent'] for s in all_stats)
    total_ads = sum(s['stats']['total_ads_watched'] for s in all_stats)
    
    text = (
        f"<b>🤖 Vue d'ensemble des Bots Clonés</b>\n\n"
        f"<b>📊 Statistiques Globales:</b>\n"
        f"• Bots actifs: {len([s for s in all_stats if s['is_active']])}/{len(all_stats)}\n"
        f"• 👥 Utilisateurs totaux: {total_users}\n"
        f"• 📁 Fichiers envoyés: {total_files}\n"
        f"• 📺 Pubs regardées: {total_ads}\n\n"
        f"<b>💰 Finances:</b>\n"
        f"• 💵 Solde total: ${total_balance:.2f}\n"
        f"• 💰 Total gagné: ${total_earned:.2f}\n\n"
        f"<b>📋 Liste détaillée:</b>\n"
    )
    
    for stat in all_stats[:10]:  # Limiter à 10 pour la lisibilité
        earnings = stat['earnings'] or {}
        text += (
            f"\n🤖 @{stat['username']}\n"
            f"   👤 Maître: <code>{stat['master_id']}</code>\n"
            f"   💵 ${earnings.get('balance', 0):.2f} | 👥 {stat['stats']['total_users']}\n"
        )
    
    if len(all_stats) > 10:
        text += f"\n<i>... et {len(all_stats) - 10} autres bots</i>"
    
    buttons = [
        [InlineKeyboardButton("📋 Voir liste complète", callback_data="list_page_0")],
        [InlineKeyboardButton("💰 Créditer un bot", callback_data="admin_credit_select")]
    ]
    
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), quote=True)


# ============================================================
# CALLBACKS ADMIN (OWNER)
# ============================================================

@Bot.on_callback_query(filters.regex(r"^admin_credit_(\d+)$"))
async def admin_credit_callback(client: Bot, callback: CallbackQuery):
    """Créditer le solde d'un bot"""
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Accès refusé", show_alert=True)
    
    bot_id = int(callback.matches[0].group(1))
    bot_data = await db.get_cloned_bot(bot_id)
    
    if not bot_data:
        return await callback.answer("❌ Bot non trouvé", show_alert=True)
    
    earnings = await db.get_bot_earnings(bot_id)
    current_balance = earnings['balance'] if earnings else 0
    
    text = (
        f"<b>💰 Créditer un bot</b>\n\n"
        f"🤖 @{bot_data['bot_username']}\n"
        f"💵 Solde actuel: ${current_balance:.2f}\n\n"
        f"Envoyez le montant à ajouter (ex: 10.50)\n"
        f"Utilisez <code>+10.50</code> pour ajouter ou <code>-5.00</code> pour retirer\n"
        f"<code>/annuler</code> pour annuler"
    )
    
    await callback.message.edit_text(text)
    await callback.answer()


@Bot.on_callback_query(filters.regex(r"^admin_restart_(\d+)$"))
async def admin_restart_callback(client: Bot, callback: CallbackQuery):
    """Redémarrer un bot cloné"""
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Accès refusé", show_alert=True)
    
    bot_id = int(callback.matches[0].group(1))
    
    # Importer la fonction de démarrage
    from clone import restart_cloned_bot
    
    success = await restart_cloned_bot(bot_id)
    
    if success:
        await callback.answer("✅ Bot redémarré avec succès!", show_alert=True)
    else:
        await callback.answer("❌ Erreur lors du redémarrage", show_alert=True)


@Bot.on_callback_query(filters.regex(r"^admin_delete_(\d+)$"))
async def admin_delete_callback(client: Bot, callback: CallbackQuery):
    """Supprimer un bot cloné"""
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Accès refusé", show_alert=True)
    
    bot_id = int(callback.matches[0].group(1))
    bot_data = await db.get_cloned_bot(bot_id)
    
    if not bot_data:
        return await callback.answer("❌ Bot non trouvé", show_alert=True)
    
    text = (
        f"<b>🗑️ Supprimer un bot</b>\n\n"
        f"🤖 @{bot_data['bot_username']}\n\n"
        f"⚠️ <b>ATTENTION:</b> Cette action est irréversible!\n\n"
        f"Êtes-vous sûr de vouloir supprimer ce bot?"
    )
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Oui, supprimer", callback_data=f"admin_confirm_delete_{bot_id}"),
            InlineKeyboardButton("❌ Non, annuler", callback_data=f"list_details_{bot_id}")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)
    await callback.answer()


@Bot.on_callback_query(filters.regex(r"^admin_confirm_delete_(\d+)$"))
async def admin_confirm_delete_callback(client: Bot, callback: CallbackQuery):
    """Confirmation de suppression"""
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Accès refusé", show_alert=True)
    
    bot_id = int(callback.matches[0].group(1))
    
    # Arrêter le bot d'abord
    from clone import stop_cloned_bot
    await stop_cloned_bot(bot_id)
    
    # Supprimer de la DB
    success = await db.delete_cloned_bot(bot_id)
    
    if success:
        await callback.message.edit_text(
            "<b>✅ Bot supprimé avec succès!</b>\n\n"
            "Le bot a été arrêté et supprimé du système.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Retour à la liste", callback_data="list_page_0")]
            ])
        )
    else:
        await callback.answer("❌ Erreur lors de la suppression", show_alert=True)
