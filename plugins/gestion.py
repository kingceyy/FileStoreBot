# ==========================================
# SYSTÈME DE CLONAGE - COMMANDE /GESTION
# ==========================================
# Version complète et corrigée
# ==========================================

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, InputMediaPhoto, User
)
from pyrogram.errors import (
    FloodWait, MessageNotModified, MessageDeleteForbidden,
    UserNotParticipant, ChatAdminRequired
)
from pyrogram.enums import ParseMode

from bot import Bot
from config import OWNER_ID
from database.database import db

# Configuration du logging
logger = logging.getLogger(__name__)

# ============================================================
# SYSTÈME DE SESSIONS (FSM - Finite State Machine)
# ============================================================

# Stockage des sessions utilisateurs pour les conversations multi-étapes
user_sessions: Dict[int, Dict[str, Any]] = {}

def get_session(user_id: int) -> Dict[str, Any]:
    """Récupère ou crée une session utilisateur"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'state': None,
            'data': {},
            'last_activity': time.time(),
            'bot_id': None
        }
    else:
        user_sessions[user_id]['last_activity'] = time.time()
    return user_sessions[user_id]

def clear_session(user_id: int):
    """Efface la session d'un utilisateur"""
    if user_id in user_sessions:
        del user_sessions[user_id]

def set_state(user_id: int, state: str, bot_id: int = None, **data):
    """Définit l'état d'un utilisateur avec des données"""
    session = get_session(user_id)
    session['state'] = state
    if bot_id:
        session['bot_id'] = bot_id
    session['data'].update(data)

def get_state(user_id: int) -> Optional[str]:
    """Récupère l'état actuel d'un utilisateur"""
    session = get_session(user_id)
    return session.get('state')

def clear_state(user_id: int):
    """Efface uniquement l'état mais garde la session"""
    session = get_session(user_id)
    session['state'] = None
    session['data'] = {}

# Nettoyage automatique des sessions inactives (plus de 30 minutes)
async def cleanup_sessions():
    """Nettoie les sessions inactives"""
    while True:
        await asyncio.sleep(300)  # Toutes les 5 minutes
        current_time = time.time()
        expired = [
            user_id for user_id, session in user_sessions.items()
            if current_time - session.get('last_activity', 0) > 1800  # 30 min
        ]
        for user_id in expired:
            clear_session(user_id)
            logger.info(f"Session expirée nettoyée pour user {user_id}")

# ============================================================
# VÉRIFICATION DES RÔLES ET PERMISSIONS
# ============================================================

async def check_role(user_id: int, bot_id: int = None) -> Optional[str]:
    """
    Vérifie le rôle d'un utilisateur
    Retourne: 'owner', 'maitre', 'admin', ou None
    """
    if user_id == OWNER_ID:
        return 'owner'
    
    if bot_id:
        try:
            # Vérifier d'abord si master_id direct dans cloned_bots
            bot_data = await db.get_cloned_bot(bot_id)
            if bot_data and bot_data.get('master_id') == user_id:
                return 'maitre'
            role = await db.get_user_bot_role(bot_id, user_id)
            if role:
                return role
        except Exception as e:
            logger.error(f"Erreur check_role: {e}")

    return None

async def is_owner(user_id: int) -> bool:
    """Vérifie si l'utilisateur est le propriétaire"""
    return user_id == OWNER_ID

async def can_manage_bot(user_id: int, bot_id: int, required_role: str = 'admin') -> bool:
    """
    Vérifie si l'utilisateur peut gérer un bot avec le rôle requis minimum
    owner > maitre > admin
    """
    role = await check_role(user_id, bot_id)
    
    hierarchy = {
        'owner': 3,
        'maitre': 2,
        'admin': 1
    }
    
    user_level = hierarchy.get(role, 0)
    required_level = hierarchy.get(required_role, 0)
    
    return user_level >= required_level

# ============================================================
# COMMANDE PRINCIPALE /GESTION
# ============================================================

@Bot.on_message(filters.command('gestion') & filters.private)
async def gestion_command(client: Bot, message: Message):
    """
    Commande /gestion - Interface de gestion complète
    Permet de personnaliser le bot cloné (MAITRE, ADMIN et OWNER)
    """
    user_id = message.from_user.id
    
    # Vérifier si l'utilisateur est OWNER
    if await is_owner(user_id):
        return await gestion_owner_menu(message)
    
    # Récupérer tous les bots où l'utilisateur est MAITRE ou ADMIN
    user_bots = await get_user_managed_bots(user_id)
    
    if not user_bots:
        return await message.reply_text(
            "<b>Accès refusé</b>\n\n"
            "Vous n'êtes pas <b>MAITRE</b> ou <b>ADMIN</b> d'un bot cloné.\n"
            "Créez d'abord un bot avec <code>/clone</code>",
            quote=True,
            parse_mode=ParseMode.HTML
        )
    
    # Si un seul bot, ouvrir directement
    if len(user_bots) == 1:
        return await show_gestion_menu(message, user_bots[0].get('bot_id', user_bots[0]['_id']), user_id)
    
    # Sinon, afficher la liste des bots
    return await show_bot_selection(message, user_bots)

async def get_user_managed_bots(user_id: int) -> List[Dict]:
    """Récupère tous les bots gérés par un utilisateur"""
    try:
        all_bots = await db.get_all_cloned_bots()
        user_bots = []
        
        for bot in all_bots:
            real_bot_id = bot.get('bot_id')
            if real_bot_id is None:
                continue
            try:
                real_bot_id = int(real_bot_id)
            except (TypeError, ValueError):
                continue
            # Maître direct → toujours visible
            if bot.get('master_id') == user_id:
                bot['role'] = 'maitre'
                user_bots.append(bot)
                continue
            # Vérifier dans bot_admins
            role = await db.get_user_bot_role(real_bot_id, user_id)
            if role in ['maitre', 'admin']:
                bot['role'] = role
                user_bots.append(bot)
        
        return user_bots
    except Exception as e:
        logger.error(f"Erreur get_user_managed_bots: {e}")
        return []

async def gestion_owner_menu(message: Message):
    """Menu spécial pour l'OWNER avec tous les bots"""
    try:
        bots = await db.get_all_cloned_bots()
        
        if not bots:
            return await message.reply_text(
                "<b> Aucun bot cloné</b>\n\n"
                "Il n'y a pas encore de bots clonés dans le système.\n"
                "Utilisez <code>/clone</code> pour créer le premier bot.",
                quote=True,
                parse_mode=ParseMode.HTML
            )
        
        # Statistiques globales
        total_bots = len(bots)
        active_bots = sum(1 for b in bots if b.get('is_active', False))
        total_users = sum(b.get('stats', {}).get('total_users', 0) for b in bots)
        
        text = (
            f"<b>Panel Administrateur</b>\n\n"
            f"<b>Statistiques globales</b>\n"
            f"Bots clonés : {total_bots} ({active_bots} actifs)\n"
            f"Utilisateurs totaux : {total_users:,}\n\n"
            f"<i>Sélectionnez un bot :</i>"
        )
        
        buttons = []
        for bot in bots[:20]:  # Limiter à 20 pour éviter les messages trop longs
            status = "🟢" if bot.get('is_active') else "🔴"
            real_id = bot.get('bot_id', bot['_id'])
            buttons.append([InlineKeyboardButton(
                f"{status} @{bot['bot_username']}",
                callback_data=f"gestion_select_{real_id}"
            )])
        
        # Pagination si plus de 20 bots
        if len(bots) > 20:
            buttons.append([InlineKeyboardButton(
                "📄 Page suivante ➡️", callback_data="gestion_owner_page_1"
            )])
        
        buttons.append([InlineKeyboardButton("Fermer", callback_data="close")])
        
        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=True,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Erreur gestion_owner_menu: {e}")
        await message.reply_text(
            "<b> Erreur</b>\n"
            "Impossible de récupérer la liste des bots.",
            quote=True
        )

async def show_bot_selection(message: Message, bots: List[Dict]):
    """Affiche la sélection de bots pour un utilisateur normal"""
    text = (
        f"<b>Gestion des bots</b>\n\n"
        f"Vous gérez <b>{len(bots)}</b> bot(s).\n\n"
        f"<i>Cliquez sur un bot pour accéder à sa gestion :</i>"
    )
    
    buttons = []
    for bot in bots:
        emoji = "👑" if bot['role'] == 'maitre' else "👤"
        status = "🟢" if bot.get('is_active') else "🔴"
        real_id = bot.get('bot_id', bot['_id'])
        buttons.append([InlineKeyboardButton(
            f"{emoji} {status} @{bot['bot_username']}",
            callback_data=f"gestion_select_{real_id}"
        )])
    
    buttons.append([InlineKeyboardButton("Fermer", callback_data="close")])
    
    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True,
        parse_mode=ParseMode.HTML
    )

# ============================================================
# MENU PRINCIPAL DE GESTION
# ============================================================

async def show_gestion_menu(
    target: Message or CallbackQuery, 
    bot_id: int, 
    user_id: int,
    edit: bool = True
):
    """
    Affiche le menu de gestion complet d'un bot
    
    Args:
        target: Message ou CallbackQuery à éditer/répondre
        bot_id: ID du bot à gérer
        user_id: ID de l'utilisateur qui gère
        edit: True pour éditer, False pour répondre
    """
    try:
        bot_data = await db.get_cloned_bot(bot_id)
        if not bot_data:
            text = "<b> Bot non trouvé</b>\n\nCe bot n'existe plus ou a été supprimé."
            if isinstance(target, CallbackQuery) and edit:
                return await target.message.edit_text(text)
            return await target.reply_text(text, quote=True)
        
        role = await check_role(user_id, bot_id)
        if not role:
            text = "<b>Accès refusé</b>\n\nVous n'avez pas les permissions pour gérer ce bot."
            if isinstance(target, CallbackQuery) and edit:
                return await target.message.edit_text(text)
            return await target.reply_text(text, quote=True)
        
        # Récupérer les informations
        id_codes = await db.get_id_codes(bot_id=bot_id)
        settings = bot_data.get('settings', {})
        stats = bot_data.get('stats', {})
        
        # Formatage du rôle
        role_display = {
            'owner': '👑 Propriétaire',
            'maitre': '👑 Maître',
            'admin': '👤 Administrateur'
        }.get(role, '❓ Inconnu')
        
        # Calcul des statuts
        has_photo = '✅' if settings.get('start_photo') else '❌'
        has_message = '✅' if settings.get('start_message') else '❌ (défaut)'
        has_channel = '✅' if settings.get('channel_id') else '❌'
        fsub_count = len(settings.get('force_sub_channels', []))
        btn_count = len(settings.get('custom_buttons', []))
        admin_count = len(bot_data.get('admins', []))
        
        # Construction du texte
        text = (
            f"<b>Gestion — @{bot_data['bot_username']}</b>\n\n"
            f"<b>Rôle :</b> {role_display}\n"
            f"<b>ID :</b> <code>{bot_id}</code>\n\n"
            f"<b>Identifiants</b>\n"
            f"ID_PUBS : <code>{id_codes.get('id_pubs', 'N/A') if id_codes else 'N/A'}</code>\n"
            f"ID_CODE : <code>{id_codes.get('id_code', 'N/A') if id_codes else 'N/A'}</code>\n\n"
            f"<b>Statistiques</b>\n"
            f"Utilisateurs : {stats.get('total_users', 0):,}\n"
            f"Fichiers envoyés : {stats.get('total_files_sent', 0):,}\n"
            f"Publicités visionnées : {stats.get('total_ads_watched', 0):,}\n\n"
            f"<b>Configuration</b>\n"
            f"Photo de démarrage : {has_photo}\n"
            f"Message de démarrage : {has_message}\n"
            f"Boutons personnalisés : {btn_count}\n"
            f"Canal DB : {has_channel}\n"
            f"Force Sub : {fsub_count} canal(aux)\n"
            f"Administrateurs : {admin_count}\n\n"
            f"Créé le : {bot_data.get('created_at', 'N/A')[:10]} — {'Actif' if bot_data.get('is_active') else 'Inactif'}"
        )
        
        # Construction des boutons — groupes logiques
        buttons = []

        # ── Groupe 1 : Apparence (Photo + Message) ──────────────────────────
        buttons.append([
            InlineKeyboardButton("Photo démarrage",    callback_data=f"gestion_photo_{bot_id}"),
            InlineKeyboardButton("Message démarrage",  callback_data=f"gestion_msg_{bot_id}"),
        ])

        # ── Groupe 2 : Interactivite (Boutons + Canal DB) ───────────────────
        buttons.append([
            InlineKeyboardButton("Boutons",   callback_data=f"gestion_buttons_{bot_id}"),
            InlineKeyboardButton("Canal DB",  callback_data=f"gestion_channel_{bot_id}"),
        ])

        # ── Groupe 3 : Acces & Securite (Force Sub + Admins) ────────────────
        buttons.append([
            InlineKeyboardButton("Force Sub",       callback_data=f"gestion_fsub_{bot_id}"),
            InlineKeyboardButton("Administrateurs", callback_data=f"gestion_admins_{bot_id}"),
        ])

        # ── Groupe 4 : Monetisation — Maitre/Owner uniquement ───────────────
        if role in ['owner', 'maitre']:
            buttons.append([
                InlineKeyboardButton("Gains",        callback_data=f"gestion_earnings_{bot_id}"),
                InlineKeyboardButton("Statistiques", callback_data=f"gestion_stats_{bot_id}"),
            ])

        # ── Groupe 5 : Configuration — Maitre/Owner uniquement ──────────────
        if role in ['owner', 'maitre']:
            # Session duration : valeur actuelle affichee dans le label
            cur_duration = bot_data.get('session_duration') or settings.get('session_duration') or 0
            dur_label = f"Session : {cur_duration}min" if cur_duration else "Duree session"
            buttons.append([
                InlineKeyboardButton(dur_label,          callback_data=f"gestion_session_dur_{bot_id}"),
                InlineKeyboardButton("Parametres",       callback_data=f"gestion_settings_{bot_id}"),
            ])
            buttons.append([
                InlineKeyboardButton("Regenerer les IDs", callback_data=f"gestion_regen_{bot_id}"),
            ])

        # ── Groupe 6 : Actions rapides — Maitre/Owner uniquement ────────────
        if role in ['owner', 'maitre']:
            status_action = "Desactiver" if bot_data.get('is_active') else "Activer"
            buttons.append([
                InlineKeyboardButton(status_action,   callback_data=f"gestion_toggle_{bot_id}"),
                InlineKeyboardButton("Supprimer",     callback_data=f"gestion_delete_{bot_id}"),
            ])

        # ── Navigation ───────────────────────────────────────────────────────
        if role == 'owner':
            buttons.append([InlineKeyboardButton("Liste des bots", callback_data="gestion_owner_back")])

        buttons.append([InlineKeyboardButton("Fermer", callback_data="close")])
        
        # Envoi/Édition du message
        markup = InlineKeyboardMarkup(buttons)
        
        if isinstance(target, CallbackQuery) and edit:
            try:
                await target.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
            except MessageNotModified:
                await target.answer("✅ Menu à jour!")
        else:
            await target.reply_text(text, reply_markup=markup, quote=True, parse_mode=ParseMode.HTML)
            
    except Exception as e:
        logger.error(f"Erreur show_gestion_menu: {e}")
        text = "<b> Erreur</b>\n\nImpossible d'afficher le menu de gestion."
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text)
        else:
            await target.reply_text(text, quote=True)

# ============================================================
# CALLBACKS - SÉLECTION ET NAVIGATION
# ============================================================

@Bot.on_callback_query(filters.regex(r"^gestion_select_(\d+)$"))
async def gestion_select_callback(client: Bot, callback: CallbackQuery):
    """Sélection d'un bot à gérer"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        # Vérifier les permissions
        role = await check_role(user_id, bot_id)
        if not role:
            return await callback.answer("⛔ Vous n'avez pas accès à ce bot", show_alert=True)
        
        await show_gestion_menu(callback, bot_id, user_id)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_select_callback: {e}")
        await callback.answer("❌ Erreur lors de la sélection", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_owner_page_(\d+)$"))
async def gestion_owner_page_callback(client: Bot, callback: CallbackQuery):
    """Pagination pour l'owner"""
    try:
        page = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await is_owner(user_id):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        bots = await db.get_all_cloned_bots()
        per_page = 20
        start = page * per_page
        end = start + per_page
        page_bots = bots[start:end]
        
        if not page_bots:
            return await callback.answer("📄 Plus de bots", show_alert=True)
        
        buttons = []
        for bot in page_bots:
            status = "🟢" if bot.get('is_active') else "🔴"
            real_id = bot.get('bot_id', bot['_id'])
            buttons.append([InlineKeyboardButton(
                f"{status} @{bot['bot_username']}",
                callback_data=f"gestion_select_{real_id}"
            )])
        
        # Pagination
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Précédent", callback_data=f"gestion_owner_page_{page-1}"))
        if end < len(bots):
            nav_buttons.append(InlineKeyboardButton("Suivant ➡️", callback_data=f"gestion_owner_page_{page+1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        buttons.append([InlineKeyboardButton("Retour", callback_data="gestion_owner_back")])
        buttons.append([InlineKeyboardButton("Fermer", callback_data="close")])
        
        await callback.message.edit_text(
            f"<b> Panel Administrateur</b> (Page {page+1})\n\n"
            f"Total: {len(bots)} bots",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_owner_page: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_owner_back$"))
async def gestion_owner_back_callback(client: Bot, callback: CallbackQuery):
    """Retour au menu owner"""
    if not await is_owner(callback.from_user.id):
        return await callback.answer("⛔ Accès refusé", show_alert=True)
    
    await gestion_owner_menu(callback.message)
    await callback.answer()

# ============================================================
# CALLBACKS - GESTION PHOTO
# ============================================================

@Bot.on_callback_query(filters.regex(r"^gestion_photo_(\d+)$"))
async def gestion_photo_callback(client: Bot, callback: CallbackQuery):
    """Menu de gestion de la photo"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        has_photo = bot_data.get('settings', {}).get('start_photo')
        
        text = (
            f"<b>📸 Photo de démarrage</b>\n\n"
            f"Statut actuel: {'✅ Configurée' if has_photo else '❌ Non configurée'}\n\n"
            f"<b>Options disponibles:</b>\n"
            f"• 📤 <b>Envoyer une photo</b> - Définir nouvelle photo\n"
            f"• 🗑️ <b>Supprimer</b> - Retirer la photo actuelle\n"
            f"• 👁️ <b>Voir</b> - Aperçu de la photo actuelle\n\n"
            f"<i>La photo sera affichée avec le message de démarrage</i>"
        )
        
        buttons = []
        if has_photo:
            buttons.append([
                InlineKeyboardButton("👁️ Voir", callback_data=f"gestion_photo_view_{bot_id}"),
                InlineKeyboardButton("🗑️ Supprimer", callback_data=f"gestion_photo_del_{bot_id}")
            ])
        
        buttons.append([InlineKeyboardButton("📤 Envoyer une photo", callback_data=f"gestion_photo_set_{bot_id}")])
        buttons.append([InlineKeyboardButton("‹ Retour", callback_data=f"gestion_select_{bot_id}")])
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_photo: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_photo_view_(\d+)$"))
async def gestion_photo_view_callback(client: Bot, callback: CallbackQuery):
    """Voir la photo actuelle"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        photo = bot_data.get('settings', {}).get('start_photo')
        
        if not photo:
            return await callback.answer("❌ Aucune photo configurée", show_alert=True)
        
        # Envoyer la photo dans un nouveau message pour pouvoir la voir
        await callback.message.reply_photo(
            photo=photo,
            caption=f"<b>📸 Photo actuelle de @{bot_data['bot_username']}</b>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("‹ Retour à la gestion", callback_data=f"gestion_photo_{bot_id}")
            ]]),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_photo_view: {e}")
        await callback.answer("❌ Impossible d'afficher la photo", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_photo_del_(\d+)$"))
async def gestion_photo_del_callback(client: Bot, callback: CallbackQuery):
    """Supprimer la photo"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        # Demander confirmation
        text = (
            f"<b>🗑️ Supprimer la photo?</b>\n\n"
            f"Êtes-vous sûr de vouloir supprimer la photo de démarrage?\n"
            f"Cette action est immédiate."
        )
        
        buttons = [
            [
                InlineKeyboardButton("Confirmer la suppression", callback_data=f"gestion_photo_del_confirm_{bot_id}"),
                InlineKeyboardButton("❌ Non, annuler", callback_data=f"gestion_photo_{bot_id}")
            ]
        ]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_photo_del: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_photo_del_confirm_(\d+)$"))
async def gestion_photo_del_confirm_callback(client: Bot, callback: CallbackQuery):
    """Confirmer suppression photo"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        # Supprimer la photo
        await db.update_bot_settings(bot_id, {'start_photo': None})
        
        await callback.answer("✅ Photo supprimée!", show_alert=True)
        await gestion_photo_callback(client, callback)
        
    except Exception as e:
        logger.error(f"Erreur gestion_photo_del_confirm: {e}")
        await callback.answer("❌ Erreur lors de la suppression", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_photo_set_(\d+)$"))
async def gestion_photo_set_callback(client: Bot, callback: CallbackQuery):
    """Définir nouvelle photo - active le mode attente"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        # Définir l'état pour attendre une photo
        set_state(user_id, 'waiting_photo', bot_id)
        
        text = (
            f"<b>📤 Envoyer une nouvelle photo</b>\n\n"
            f"Veuillez envoyer la photo que vous souhaitez définir.\n\n"
            f"<b>Options:</b>\n"
            f"• Envoyez une <b>photo</b> (compressée ou non)\n"
            f"• Envoyez <code>/annuler</code> pour annuler\n\n"
            f"<i>La photo sera automatiquement redimensionnée si nécessaire</i>"
        )
        
        buttons = [[InlineKeyboardButton("Annuler", callback_data=f"gestion_photo_{bot_id}")]]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer("📤 Envoyez une photo maintenant", show_alert=True)
        
    except Exception as e:
        logger.error(f"Erreur gestion_photo_set: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

# ============================================================
# CALLBACKS - GESTION MESSAGE
# ============================================================

@Bot.on_callback_query(filters.regex(r"^gestion_msg_(\d+)$"))
async def gestion_msg_callback(client: Bot, callback: CallbackQuery):
    """Menu de gestion du message"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        current_msg = bot_data.get('settings', {}).get('start_message')
        
        if current_msg:
            display_msg = current_msg[:500] + "..." if len(current_msg) > 500 else current_msg
            msg_status = f"✅ Configuré:\n{display_msg}"
        else:
            msg_status = "❌ Non configuré (utilise le message par défaut du système)"
        
        text = (
            f"<b>💬 Message de démarrage</b>\n\n"
            f"<b>Actuel:</b>\n{msg_status}\n\n"
            f"<b>📝 Variables disponibles:</b>\n"
            f"• <code>{{first}}</code> - Prénom de l'utilisateur\n"
            f"• <code>{{last}}</code> - Nom de famille\n"
            f"• <code>{{username}}</code> - Nom d'utilisateur (@username)\n"
            f"• <code>{{mention}}</code> - Mention cliquable\n"
            f"• <code>{{id}}</code> - ID Telegram\n"
            f"• <code>{{bot}}</code> - Nom du bot\n\n"
            f"<b>HTML supporté:</b> <code>&lt;b&gt;</code>, <code>&lt;i&gt;</code>, <code>&lt;u&gt;</code>, <code>&lt;a&gt;</code>, etc."
        )
        
        buttons = [
            [InlineKeyboardButton("✏️ Modifier", callback_data=f"gestion_msg_set_{bot_id}")],
            [InlineKeyboardButton("🔄 Réinitialiser", callback_data=f"gestion_msg_reset_{bot_id}")],
            [InlineKeyboardButton("‹ Retour", callback_data=f"gestion_select_{bot_id}")]
        ]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_msg: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_msg_set_(\d+)$"))
async def gestion_msg_set_callback(client: Bot, callback: CallbackQuery):
    """Activer le mode édition de message"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        set_state(user_id, 'waiting_message', bot_id)
        
        text = (
            f"<b>✏️ Nouveau message de démarrage</b>\n\n"
            f"Envoyez le nouveau message.\n\n"
            f"<b>Exemple:</b>\n"
            f"<code>Bienvenue {{first}} sur {{bot}}! 🎉\n\n"
            f"Ton ID: <code>{{id}}</code></code>\n\n"
            f"Envoyez <code>/annuler</code> pour annuler."
        )
        
        buttons = [[InlineKeyboardButton("Annuler", callback_data=f"gestion_msg_{bot_id}")]]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer("✏️ Envoyez le nouveau message", show_alert=True)
        
    except Exception as e:
        logger.error(f"Erreur gestion_msg_set: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_msg_reset_(\d+)$"))
async def gestion_msg_reset_callback(client: Bot, callback: CallbackQuery):
    """Réinitialiser le message"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        text = (
            f"<b> Réinitialiser le message?</b>\n\n"
            f"Le message reviendra à celui par défaut du système.\n"
            f"Confirmer?"
        )
        
        buttons = [
            [
                InlineKeyboardButton("✅ Oui", callback_data=f"gestion_msg_reset_confirm_{bot_id}"),
                InlineKeyboardButton("❌ Non", callback_data=f"gestion_msg_{bot_id}")
            ]
        ]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_msg_reset: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_msg_reset_confirm_(\d+)$"))
async def gestion_msg_reset_confirm_callback(client: Bot, callback: CallbackQuery):
    """Confirmer réinitialisation"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        await db.update_bot_settings(bot_id, {'start_message': None})
        
        await callback.answer("✅ Message réinitialisé!", show_alert=True)
        await gestion_msg_callback(client, callback)
        
    except Exception as e:
        logger.error(f"Erreur gestion_msg_reset_confirm: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

# ============================================================
# CALLBACKS - GESTION BOUTONS
# ============================================================

@Bot.on_callback_query(filters.regex(r"^gestion_buttons_(\d+)$"))
async def gestion_buttons_callback(client: Bot, callback: CallbackQuery):
    """Menu de gestion des boutons"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        buttons_list = bot_data.get('settings', {}).get('custom_buttons', [])
        
        text = f"<b>🔘 Boutons personnalisés</b>\n\n"
        text += f"<b>Total:</b> {len(buttons_list)}/10 boutons\n\n"
        
        if buttons_list:
            text += "<b>Boutons actuels:</b>\n"
            for i, btn in enumerate(buttons_list, 1):
                text += f"{i}. {btn.get('text', 'Sans titre')} → {btn.get('url', 'N/A')}\n"
        else:
            text += "<i>Aucun bouton personnalisé configuré</i>\n"
        
        text += (
            f"\n<b>ℹ️ Info:</b> Le bouton '🤖 Créer Votre Propre Bot' est toujours présent par défaut.\n\n"
            f"<b>Format pour ajouter:</b>\n"
            f"<code>Titre du bouton - https://lien.com</code>"
        )
        
        buttons = []
        if len(buttons_list) < 10:
            buttons.append([InlineKeyboardButton("➕ Ajouter un bouton", callback_data=f"gestion_addbtn_{bot_id}")])
        
        if buttons_list:
            buttons.append([InlineKeyboardButton("🗑️ Supprimer un bouton", callback_data=f"gestion_delbtn_menu_{bot_id}")])
            buttons.append([InlineKeyboardButton("🔄 Réorganiser", callback_data=f"gestion_reorderbtn_{bot_id}")])
        
        buttons.append([InlineKeyboardButton("‹ Retour", callback_data=f"gestion_select_{bot_id}")])
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_buttons: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_addbtn_(\d+)$"))
async def gestion_addbtn_callback(client: Bot, callback: CallbackQuery):
    """Ajouter un bouton - mode attente"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        # Vérifier limite
        bot_data = await db.get_cloned_bot(bot_id)
        current = bot_data.get('settings', {}).get('custom_buttons', [])
        if len(current) >= 10:
            return await callback.answer("❌ Maximum 10 boutons atteint", show_alert=True)
        
        set_state(user_id, 'waiting_button', bot_id)
        
        text = (
            f"<b>➕ Ajouter un bouton</b>\n\n"
            f"Envoyez le bouton au format:\n"
            f"<code>Titre - https://votre-lien.com</code>\n\n"
            f"<b>Exemples:</b>\n"
            f"<code>📢 Canal Officiel - https://t.me/moncanal</code>\n"
            f"<code>💬 Support - https://t.me/monsupport</code>\n"
            f"<code>🌐 Site Web - https://monsite.com</code>\n\n"
            f"Envoyez <code>/annuler</code> pour annuler."
        )
        
        buttons = [[InlineKeyboardButton("Annuler", callback_data=f"gestion_buttons_{bot_id}")]]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer("➕ Envoyez le nouveau bouton", show_alert=True)
        
    except Exception as e:
        logger.error(f"Erreur gestion_addbtn: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_delbtn_menu_(\d+)$"))
async def gestion_delbtn_menu_callback(client: Bot, callback: CallbackQuery):
    """Menu de suppression de boutons"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        buttons_list = bot_data.get('settings', {}).get('custom_buttons', [])
        
        if not buttons_list:
            return await callback.answer("Aucun bouton à supprimer", show_alert=True)
        
        text = "<b>🗑️ Supprimer un bouton</b>\n\nCliquez sur le bouton à supprimer:"
        
        btns = []
        for i, btn in enumerate(buttons_list):
            btns.append([InlineKeyboardButton(
                f"🗑️ {i+1}. {btn.get('text', 'Sans titre')[:20]}...",
                callback_data=f"gestion_delbtn_{bot_id}_{i}"
            )])
        
        btns.append([InlineKeyboardButton("‹ Retour", callback_data=f"gestion_buttons_{bot_id}")])
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_delbtn_menu: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_delbtn_(\d+)_(\d+)$"))
async def gestion_delbtn_callback(client: Bot, callback: CallbackQuery):
    """Supprimer un bouton spécifique"""
    try:
        bot_id = int(callback.matches[0].group(1))
        btn_index = int(callback.matches[0].group(2))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        buttons_list = bot_data.get('settings', {}).get('custom_buttons', [])
        
        if 0 <= btn_index < len(buttons_list):
            removed = buttons_list.pop(btn_index)
            await db.update_bot_settings(bot_id, {'custom_buttons': buttons_list})
            await callback.answer(f"🗑️ Bouton '{removed.get('text', 'Sans titre')}' supprimé!", show_alert=True)
        else:
            await callback.answer("❌ Bouton introuvable", show_alert=True)
        
        await gestion_buttons_callback(client, callback)
        
    except Exception as e:
        logger.error(f"Erreur gestion_delbtn: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

# ============================================================
# CALLBACKS - GESTION CANAL DB
# ============================================================

@Bot.on_callback_query(filters.regex(r"^gestion_channel_(\d+)$"))
async def gestion_channel_callback(client: Bot, callback: CallbackQuery):
    """Gestion du canal de stockage"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        channel_id = bot_data.get('settings', {}).get('channel_id')
        
        text = (
            f"<b> Canal de Base de Données (DB)</b>\n\n"
            f"<b>Actuel:</b> <code>{channel_id if channel_id else 'Non configuré'}</code>\n\n"
            f"<b> Instructions:</b>\n"
            f"1. Créez un canal privé sur Telegram\n"
            f"2. Ajoutez votre bot @{bot_data['bot_username']} comme <b>administrateur</b>\n"
            f"3. Donnez les permissions: <b>Supprimer messages</b> et <b>Inviter via lien</b>\n"
            f"4. Envoyez ici l'ID du canal (ex: <code>-1001234567890</code>)\n\n"
            f"<b> Important:</b>\n"
            f"• Le bot DOIT être admin du canal\n"
            f"• Le canal sert à stocker les fichiers\n"
            f"• Sans canal, le bot ne peut pas fonctionner"
        )
        
        buttons = []
        if channel_id:
            buttons.append([InlineKeyboardButton("🔄 Modifier", callback_data=f"gestion_setchannel_{bot_id}")])
            buttons.append([InlineKeyboardButton("🗑️ Supprimer", callback_data=f"gestion_delchannel_{bot_id}")])
        else:
            buttons.append([InlineKeyboardButton("➕ Configurer", callback_data=f"gestion_setchannel_{bot_id}")])
        
        buttons.append([InlineKeyboardButton("‹ Retour", callback_data=f"gestion_select_{bot_id}")])
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_channel: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_setchannel_(\d+)$"))
async def gestion_setchannel_callback(client: Bot, callback: CallbackQuery):
    """Configurer le canal"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        set_state(user_id, 'waiting_channel', bot_id)
        
        text = (
            f"<b> Configuration du canal</b>\n\n"
            f"Envoyez l'ID du canal (format: <code>-1001234567890</code>)\n\n"
            f"<b>Comment obtenir l'ID:</b>\n"
            f"1. Ajoutez @userinfobot dans votre canal\n"
            f"2. Envoyez un message dans le canal\n"
            f"3. Le bot répondra avec l'ID\n\n"
            f"Envoyez <code>/annuler</code> pour annuler.\n"
            f"Ou utilsé simplement <code>/addchnl ID_CANAL</code>"
        )
        
        buttons = [[InlineKeyboardButton("Annuler", callback_data=f"gestion_channel_{bot_id}")]]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer("📢 Envoyez l'ID du canal", show_alert=True)
        
    except Exception as e:
        logger.error(f"Erreur gestion_setchannel: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_delchannel_(\d+)$"))
async def gestion_delchannel_callback(client: Bot, callback: CallbackQuery):
    """Supprimer le canal"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):  # Seul maitre peut supprimer
            return await callback.answer("⛔ Seul le MAITRE peut supprimer le canal", show_alert=True)
        
        text = (
            f"<b>🗑️ Supprimer le canal?</b>\n\n"
            f"⚠️ <b>Attention:</b> Sans canal de stockage, le bot ne pourra plus envoyer de fichiers!\n\n"
            f"Confirmer la suppression?"
        )
        
        buttons = [
            [
                InlineKeyboardButton("Confirmer la suppression", callback_data=f"gestion_delchannel_confirm_{bot_id}"),
                InlineKeyboardButton("❌ Non", callback_data=f"gestion_channel_{bot_id}")
            ]
        ]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_delchannel: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_delchannel_confirm_(\d+)$"))
async def gestion_delchannel_confirm_callback(client: Bot, callback: CallbackQuery):
    """Confirmer suppression canal"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        await db.update_bot_settings(bot_id, {'channel_id': None})
        
        await callback.answer("✅ Canal supprimé!", show_alert=True)
        await gestion_channel_callback(client, callback)
        
    except Exception as e:
        logger.error(f"Erreur gestion_delchannel_confirm: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

# ============================================================
# CALLBACKS - FORCE SUB
# ============================================================

@Bot.on_callback_query(filters.regex(r"^gestion_fsub_(\d+)$"))
async def gestion_fsub_callback(client: Bot, callback: CallbackQuery):
    """Gestion des abonnements forcés"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        fsub_channels = bot_data.get('settings', {}).get('force_sub_channels', [])
        
        text = (
            f"<b>📌 Force Subscription</b>\n\n"
            f"<b>Canaux configurés ({len(fsub_channels)}/5):</b>\n"
        )
        
        if fsub_channels:
            for i, ch in enumerate(fsub_channels, 1):
                text += f"{i}. {ch}\n"
        else:
            text += "<i>Aucun canal configuré</i>\n"
        
        text += (
            f"\n<b>ℹ️ Fonctionnement:</b>\n"
            f"Les utilisateurs doivent rejoindre ces canaux avant d'utiliser le bot.\n\n"
            f"<b>Format:</b> <code>@username</code> ou <code>-100ID</code>"
        )
        
        buttons = []
        if len(fsub_channels) < 5:
            buttons.append([InlineKeyboardButton("➕ Ajouter un canal", callback_data=f"gestion_fsub_add_{bot_id}")])
        if fsub_channels:
            buttons.append([InlineKeyboardButton("🗑️ Supprimer", callback_data=f"gestion_fsub_del_menu_{bot_id}")])
        
        buttons.append([InlineKeyboardButton("‹ Retour", callback_data=f"gestion_select_{bot_id}")])
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_fsub: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_fsub_add_(\d+)$"))
async def gestion_fsub_add_callback(client: Bot, callback: CallbackQuery):
    """Ajouter un canal fsub"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        set_state(user_id, 'waiting_fsub', bot_id)
        
        text = (
            f"<b>📌 Ajouter un canal Force Sub</b>\n\n"
            f"Envoyez le username du canal (ex: <code>@moncanal</code>)\n"
            f"ou l'ID (ex: <code>-1001234567890</code>)\n\n"
            f"<b> Important:</b>\n"
            f"• Le bot doit être admin du canal\n"
            f"• Le canal doit être public ou le bot doit en être membre\n\n"
            f"Envoyez <code>/annuler</code> pour annuler."
        )
        
        buttons = [[InlineKeyboardButton("Annuler", callback_data=f"gestion_fsub_{bot_id}")]]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer("📌 Envoyez le canal", show_alert=True)
        
    except Exception as e:
        logger.error(f"Erreur gestion_fsub_add: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

# ============================================================
# CALLBACKS - GESTION ADMINS
# ============================================================

@Bot.on_callback_query(filters.regex(r"^gestion_admins_(\d+)$"))
async def gestion_admins_callback(client: Bot, callback: CallbackQuery):
    """Gestion des administrateurs du bot"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        # Seul le maitre peut gérer les admins
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            return await callback.answer("⛔ Seul le MAITRE peut gérer les admins", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        admins_list = await db.get_bot_admins(bot_id)
        admins = [a['user_id'] for a in admins_list if a.get('role') == 'admin']
        
        text = (
            f"<b>👥 Gestion des Administrateurs</b>\n\n"
            f"<b>Liste actuelle ({len(admins)}):</b>\n"
        )
        
        if admins:
            for i, admin_id in enumerate(admins, 1):
                try:
                    user = await client.get_users(admin_id)
                    name = user.first_name or "Inconnu"
                    username = f"@{user.username}" if user.username else f"ID:{admin_id}"
                    text += f"{i}. {name} ({username})\n"
                except:
                    text += f"{i}. ID:{admin_id} (inaccessible)\n"
        else:
            text += "<i>Aucun admin configuré</i>\n"
        
        text += (
            f"\n<b>ℹ️ Info:</b>\n"
            f"• Les admins peuvent gérer le contenu\n"
            f"• Seul le MAITRE peut ajouter/supprimer des admins\n"
            f"• Le MAITRE a tous les droits"
        )
        
        buttons = [
            [InlineKeyboardButton("➕ Ajouter un admin", callback_data=f"gestion_admin_add_{bot_id}")],
            [InlineKeyboardButton("🗑️ Retirer un admin", callback_data=f"gestion_admin_del_menu_{bot_id}")]
        ]
        
        buttons.append([InlineKeyboardButton("‹ Retour", callback_data=f"gestion_select_{bot_id}")])
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_admins: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_admin_add_(\d+)$"))
async def gestion_admin_add_callback(client: Bot, callback: CallbackQuery):
    """Ajouter un admin"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        set_state(user_id, 'waiting_admin', bot_id)
        
        text = (
            f"<b>➕ Ajouter un administrateur</b>\n\n"
            f"Envoyez l'ID Telegram de l'utilisateur à promouvoir admin.\n\n"
            f"<b>Comment obtenir l'ID:</b>\n"
            f"1. Demandez à l'utilisateur d'envoyer <code>/id</code> à @userinfobot\n"
            f"2. Ou transférez un message de l'utilisateur ici\n\n"
            f"<b> Attention:</b> L'admin aura accès à la gestion du bot!\n\n"
            f"Envoyez <code>/annuler</code> pour annuler."
        )
        
        buttons = [[InlineKeyboardButton("Annuler", callback_data=f"gestion_admins_{bot_id}")]]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer("➕ Envoyez l'ID de l'utilisateur", show_alert=True)
        
    except Exception as e:
        logger.error(f"Erreur gestion_admin_add: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_admin_del_menu_(\d+)$"))
async def gestion_admin_del_menu_callback(client: Bot, callback: CallbackQuery):
    """Menu de suppression d'admin"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        admins_list = await db.get_bot_admins(bot_id)
        admins = [a['user_id'] for a in admins_list if a.get('role') == 'admin']
        
        if not admins:
            return await callback.answer("❌ Aucun admin à retirer", show_alert=True)
        
        text = "<b>🗑️ Retirer un admin</b>\n\nCliquez sur l'admin à retirer:"
        
        buttons = []
        for admin_id in admins:
            try:
                user = await client.get_users(admin_id)
                name = user.first_name or f"ID:{admin_id}"
            except:
                name = f"ID:{admin_id}"
            
            buttons.append([InlineKeyboardButton(
                f"🗑️ {name}",
                callback_data=f"gestion_admin_del_{bot_id}_{admin_id}"
            )])
        
        buttons.append([InlineKeyboardButton("‹ Retour", callback_data=f"gestion_admins_{bot_id}")])
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_admin_del_menu: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_admin_del_(\d+)_(\d+)$"))
async def gestion_admin_del_callback(client: Bot, callback: CallbackQuery):
    """Retirer un admin spécifique"""
    try:
        bot_id = int(callback.matches[0].group(1))
        admin_id = int(callback.matches[0].group(2))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        existing_role = await db.get_user_bot_role(bot_id, admin_id)
        
        if existing_role:
            await db.remove_bot_admin(bot_id, admin_id)
            
            try:
                user = await client.get_users(admin_id)
                name = user.first_name
            except:
                name = f"ID:{admin_id}"
            
            await callback.answer(f"✅ {name} retiré des admins!", show_alert=True)
        else:
            await callback.answer("❌ Admin introuvable", show_alert=True)
        
        await gestion_admins_callback(client, callback)
        
    except Exception as e:
        logger.error(f"Erreur gestion_admin_del: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

# ============================================================
# CALLBACKS - GAINS ET MONÉTISATION
# ============================================================

@Bot.on_callback_query(filters.regex(r"^gestion_earnings_(\d+)$"))
async def gestion_earnings_callback(client: Bot, callback: CallbackQuery):
    """Affiche les gains et statistiques de monétisation"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            return await callback.answer("⛔ Seul le MAITRE peut voir les gains", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        earnings = await db.get_bot_earnings(bot_id)
        
        if not earnings:
            earnings = {
                'balance': 0.0,
                'total_earned': 0.0,
                'total_withdrawn': 0.0,
                'cpm': 2.0,  # $2 par 1000 vues
                'today_views': 0,
                'week_views': 0,
                'month_views': 0
            }
        
        text = (
            f"<b> Gains du Bot</b>\n\n"
            f"🤖 @{bot_data['bot_username']}\n\n"
            f"<b>💵 Solde actuel:</b> <code>${earnings['balance']:.2f}</code>\n"
            f"<b> Total gagné:</b> <code>${earnings['total_earned']:.2f}</code>\n"
            f"<b>💸 Total retiré:</b> <code>${earnings['total_withdrawn']:.2f}</code>\n\n"
            f"<b> Statistiques vues:</b>\n"
            f"• Aujourd'hui: {earnings.get('today_views', 0):,}\n"
            f"• Cette semaine: {earnings.get('week_views', 0):,}\n"
            f"• Ce mois: {earnings.get('month_views', 0):,}\n\n"
            f"<b>💵 CPM:</b> ${earnings.get('cpm', 2.0):.2f} (Pour CPM)\n\n"
        )
        
        # Seuil de retrait
        threshold = 7.0
        if earnings['balance'] >= threshold:
            text += f"✅ <b>Seuil de retrait atteint!</b> (min: ${threshold})\n"
            can_withdraw = True
        else:
            missing = threshold - earnings['balance']
            text += f"❌ Encore ${missing:.2f} pour atteindre le seuil de ${threshold}\n"
            can_withdraw = False
        
        buttons = []
        if can_withdraw:
            buttons.append([InlineKeyboardButton("💸 Demander un retrait", callback_data=f"gestion_withdraw_{bot_id}")])
        
        buttons.append([InlineKeyboardButton("📊 Historique détaillé", callback_data=f"gestion_earnings_history_{bot_id}")])
        buttons.append([InlineKeyboardButton("‹ Retour", callback_data=f"gestion_select_{bot_id}")])
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_earnings: {e}")
        await callback.answer("❌ Erreur lors du chargement des gains", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_withdraw_(\d+)$"))
async def gestion_withdraw_callback(client: Bot, callback: CallbackQuery):
    """Demande de retrait"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        earnings = await db.get_bot_earnings(bot_id)
        if not earnings or earnings['balance'] < 7.0:
            return await callback.answer("❌ Solde insuffisant", show_alert=True)
        
        set_state(user_id, 'waiting_withdraw', bot_id)
        
        text = (
            f"<b>💸 Demande de Retrait</b>\n\n"
            f"<b>Solde disponible:</b> <code>${earnings['balance']:.2f}</code>\n\n"
            f"Envoyez vos informations de paiement:\n\n"
            f"<b>Formats acceptés:</b>\n"
            f"• <b>PayPal:</b> <code>paypal:email@example.com</code>\n"
            f"• <b>Crypto:</b> <code>btc:1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa</code>\n"
            f"• <b>Payeer:</b> <code>payeer:P123456789</code>\n"
            f"• <b>Perfect Money:</b> <code>pm:U12345678</code>\n\n"
            f"Envoyez <code>/annuler</code> pour annuler."
        )
        
        buttons = [[InlineKeyboardButton("Annuler", callback_data=f"gestion_earnings_{bot_id}")]]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer("💸 Envoyez vos infos de paiement", show_alert=True)
        
    except Exception as e:
        logger.error(f"Erreur gestion_withdraw: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

# ============================================================
# CALLBACKS - STATISTIQUES AVANCÉES
# ============================================================

@Bot.on_callback_query(filters.regex(r"^gestion_stats_(\d+)$"))
async def gestion_stats_callback(client: Bot, callback: CallbackQuery):
    """Statistiques avancées du bot"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        stats = bot_data.get('stats', {})
        
        # Calculer les tendances
        total_users = stats.get('total_users', 0)
        total_files = stats.get('total_files_sent', 0)
        total_ads = stats.get('total_ads_watched', 0)
        
        # Éviter division par zéro
        avg_files = total_files / total_users if total_users > 0 else 0
        avg_ads = total_ads / total_users if total_users > 0 else 0
        
        text = (
            f"<b> Statistiques Avancées</b>\n\n"
            f"🤖 @{bot_data['bot_username']}\n\n"
            f"<b>👥 Utilisateurs:</b>\n"
            f"• Total: {total_users:,}\n"
            f"• Actifs aujourd'hui: {stats.get('active_today', 0):,}\n"
            f"• Actifs cette semaine: {stats.get('active_week', 0):,}\n\n"
            f"<b>📁 Fichiers:</b>\n"
            f"• Total envoyés: {total_files:,}\n"
            f"• Moyenne/utilisateur: {avg_files:.2f}\n\n"
            f"<b>📺 Publicités:</b>\n"
            f"• Total vues: {total_ads:,}\n"
            f"• Moyenne/utilisateur: {avg_ads:.2f}\n"
            f"• Taux de conversion: {(total_ads/total_files*100) if total_files > 0 else 0:.1f}%\n\n"
            f"<b>📅 Créé le:</b> {bot_data.get('created_at', 'N/A')[:10]}\n"
            f"<b>⏱️ Dernière activité:</b> {stats.get('last_activity', 'Jamais')[:10]}\n\n"
            f"{'🟢 Bot actif' if bot_data.get('is_active') else '🔴 Bot inactif'}"
        )
        
        buttons = [
            [InlineKeyboardButton("📈 Graphiques", callback_data=f"gestion_stats_graph_{bot_id}")],
            [InlineKeyboardButton("📥 Exporter données", callback_data=f"gestion_stats_export_{bot_id}")],
            [InlineKeyboardButton("‹ Retour", callback_data=f"gestion_select_{bot_id}")]
        ]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_stats: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

# ============================================================
# CALLBACKS - RÉGÉNÉRATION ID_CODE
# ============================================================

@Bot.on_callback_query(filters.regex(r"^gestion_regen_(\d+)$"))
async def gestion_regen_callback(client: Bot, callback: CallbackQuery):
    """Régénérer les codes ID"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            return await callback.answer("⛔ Seul le MAITRE peut régénérer les codes", show_alert=True)
        
        text = (
            f"<b> Régénérer les codes?</b>\n\n"
            f"⚠️ <b>Attention!</b>\n"
            f"• Le ID_CODE actuel sera invalidé\n"
            f"• Les anciens liens de parrainage ne fonctionneront plus\n"
            f"• Les statistiques de parrainage seront conservées\n\n"
            f"Confirmer la régénération?"
        )
        
        buttons = [
            [
                InlineKeyboardButton("✅ Oui, régénérer", callback_data=f"gestion_regen_confirm_{bot_id}"),
                InlineKeyboardButton("❌ Non, annuler", callback_data=f"gestion_select_{bot_id}")
            ]
        ]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_regen: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^gestion_regen_confirm_(\d+)$"))
async def gestion_regen_confirm_callback(client: Bot, callback: CallbackQuery):
    """Confirmer régénération"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        # Régénérer les codes
        new_codes = await db.regenerate_id_code(bot_id, user_id)
        
        if new_codes:
            await callback.answer("✅ Codes régénérés!", show_alert=True)
            
            # Afficher les nouveaux codes
            text = (
                f"<b> Codes régénérés avec succès!</b>\n\n"
                f"<b>Nouveaux identifiants:</b>\n"
                f"🆔 <b>ID_PUBS:</b> <code>{new_codes['id_pubs']}</code>\n"
                f"🔑 <b>ID_CODE:</b> <code>{new_codes['id_code']}</code>\n\n"
                f"⚠️ <b>Note:</b> Les anciens liens ne fonctionnent plus!"
            )
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⚙️ Retour à la gestion", callback_data=f"gestion_select_{bot_id}")
                ]]),
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.answer("❌ Erreur lors de la régénération", show_alert=True)
            
    except Exception as e:
        logger.error(f"Erreur gestion_regen_confirm: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

# ============================================================
# CALLBACKS - ACTIVATION/DÉSACTIVATION
# ============================================================

@Bot.on_callback_query(filters.regex(r"^gestion_toggle_(\d+)$"))
async def gestion_toggle_callback(client: Bot, callback: CallbackQuery):
    """Activer/désactiver le bot"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            return await callback.answer("⛔ Seul le MAITRE peut activer/désactiver", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        current_status = bot_data.get('is_active', False)
        new_status = not current_status
        
        await db.update_cloned_bot(bot_id, {'is_active': new_status})
        
        status_text = "activé" if new_status else "désactivé"
        emoji = "🟢" if new_status else "🔴"
        
        await callback.answer(f"{emoji} Bot {status_text}!", show_alert=True)
        await show_gestion_menu(callback, bot_id, user_id)
        
    except Exception as e:
        logger.error(f"Erreur gestion_toggle: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

# ============================================================
# CALLBACKS - SUPPRESSION DU BOT
# ============================================================

@Bot.on_callback_query(filters.regex(r"^gestion_delete_(\d+)$"))
async def gestion_delete_callback(client: Bot, callback: CallbackQuery):
    """Demande de suppression du bot"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            return await callback.answer("⛔ Seul le MAITRE peut supprimer le bot", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        
        text = (
            f"<b>🗑️ Supprimer le bot?</b>\n\n"
            f"⚠️ <b>Action irréversible!</b>\n\n"
            f"Vous allez supprimer définitivement:\n"
            f"🤖 @{bot_data['bot_username']}\n\n"
            f"<b>Cela supprimera:</b>\n"
            f"• Toutes les configurations\n"
            f"• Les statistiques (conservées 30j)\n"
            f"• Les liens de parrainage\n\n"
            f"<b>Cela ne supprimera PAS:</b>\n"
            f"• Les fichiers dans le canal DB\n"
            f"• Le bot Telegram lui-même\n\n"
            f"Pour confirmer, envoyez le username du bot:\n"
            f"<code>@{bot_data['bot_username']}</code>"
        )
        
        set_state(user_id, 'waiting_delete_confirm', bot_id, confirm_username=bot_data['bot_username'])
        
        buttons = [[InlineKeyboardButton("Annuler", callback_data=f"gestion_select_{bot_id}")]]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer("🗑️ Confirmation requise", show_alert=True)
        
    except Exception as e:
        logger.error(f"Erreur gestion_delete: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

# ============================================================
# HANDLERS DE MESSAGES - CORRIGÉS ET FONCTIONNELS
# ============================================================

# Handler pour recevoir la photo - CORRIGÉ
@Bot.on_message(filters.photo & filters.private, group=2)
async def handle_photo_upload(client: Bot, message: Message):
    """Gère l'upload de photo pour la configuration"""
    user_id = message.from_user.id
    state = get_state(user_id)
    
    if state != 'waiting_photo':
        return

    temp_path = None
    try:
        bot_id = get_session(user_id).get('bot_id')
        if not bot_id:
            clear_state(user_id)
            return await message.reply_text("❌ Session invalide. Recommencez avec /gestion")
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            clear_state(user_id)
            return await message.reply_text("⛔ Vous n'avez plus les permissions pour ce bot")
        
        if not message.photo:
            return await message.reply_text("❌ Aucune photo détectée. Envoyez une image.")

        # Télécharger la photo localement depuis la bot mère
        import os
        tmp_dir = "/tmp/yume_photos"
        os.makedirs(tmp_dir, exist_ok=True)
        temp_path = await client.download_media(message.photo, file_name=f"{tmp_dir}/start_photo_{bot_id}.jpg")

        # Récupérer le client du bot cloné pour obtenir son propre file_id
        from plugins.clone import cloned_clients
        cloned_client = cloned_clients.get(bot_id)

        if cloned_client:
            # Uploader via le bot cloné → obtenir un file_id valide pour LUI
            sent = await cloned_client.send_photo(
                chat_id=user_id,
                photo=temp_path,
                caption="<b> Photo de démarrage configurée !</b>",
                parse_mode=ParseMode.HTML
            )
            file_id = sent.photo.file_id
            # Supprimer le message de preview envoyé par le cloné
            try:
                await sent.delete()
            except Exception:
                pass
        else:
            # Bot cloné pas en mémoire → on utilise le file_id de la bot mère
            # (fonctionnera uniquement si les deux bots partagent le même API_ID)
            file_id = message.photo.file_id
            logger.warning(f"[GESTION] Bot cloné {bot_id} non trouvé en mémoire, file_id mère utilisé")

        # Sauvegarder dans la DB
        await db.update_bot_settings(bot_id, {'start_photo': file_id})
        clear_state(user_id)

        # Supprimer le fichier temp
        if temp_path:
            import os
            try:
                os.remove(temp_path)
            except Exception:
                pass

        # Confirmation avec aperçu via la bot mère
        await message.reply_photo(
            photo=message.photo.file_id,
            caption=(
                "<b> Photo mise à jour !</b>\n\n"
                "La nouvelle photo de démarrage a été configurée.\n"
                "Les utilisateurs la verront au /start."
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⚙️ Retour à la gestion", callback_data=f"gestion_select_{bot_id}")
            ]]),
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Erreur handle_photo_upload: {e}")
        clear_state(user_id)
        # Supprimer le fichier temp en cas d'erreur
        if temp_path:
            import os
            try:
                os.remove(temp_path)
            except Exception:
                pass
        await message.reply_text(f"❌ Erreur lors de la sauvegarde de la photo: {str(e)}")


# Handler principal pour dispatcher les messages texte - CORRIGÉ
@Bot.on_message(filters.text & filters.private, group=2)
async def handle_text_messages(client: Bot, message: Message):
    """Dispatcher vers le bon handler selon l'état"""
    user_id = message.from_user.id
    
    # Ignorer les commandes
    if message.text.startswith('/'):
        return
    
    state = get_state(user_id)
    
    if not state:
        return  # Pas d'état actif, ignorer
    
    # Dispatcher vers le bon handler selon l'état
    if state == 'waiting_message':
        await process_message_set(client, message)
    elif state == 'waiting_button':
        await process_button_add(client, message)
    elif state == 'waiting_channel':
        await process_channel_set(client, message)
    elif state == 'waiting_fsub':
        await process_fsub_add(client, message)
    elif state == 'waiting_admin':
        await process_admin_add(client, message)
    elif state == 'waiting_withdraw':
        await process_withdraw_request(client, message)
    elif state == 'waiting_delete_confirm':
        await process_delete_confirm(client, message)


async def process_message_set(client: Bot, message: Message):
    """Traite la configuration du message"""
    user_id = message.from_user.id
    
    try:
        bot_id = get_session(user_id).get('bot_id')
        if not bot_id:
            clear_state(user_id)
            return await message.reply_text("❌ Session invalide")
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            clear_state(user_id)
            return await message.reply_text("⛔ Permissions insuffisantes")
        
        new_message = message.text
        
        # Validation de base
        if len(new_message) > 4096:
            return await message.reply_text(
                "❌ Message trop long! Maximum 4096 caractères.\n"
                "Envoyez un message plus court ou /annuler"
            )
        
        # Sauvegarder
        await db.update_bot_settings(bot_id, {'start_message': new_message})
        clear_state(user_id)
        
        # Aperçu
        preview = new_message.replace('{first}', message.from_user.first_name or 'Utilisateur')
        preview = preview.replace('{last}', message.from_user.last_name or '')
        preview = preview.replace('{username}', message.from_user.username or 'Aucun')
        preview = preview.replace('{mention}', message.from_user.mention)
        preview = preview.replace('{id}', str(message.from_user.id))
        preview = preview.replace('{bot}', '@VotreBot')
        
        await message.reply_text(
            f"<b> Message enregistré!</b>\n\n"
            f"<b>Aperçu:</b>\n{preview}\n\n"
            f"Ce message sera affiché aux nouveaux utilisateurs.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⚙️ Retour à la gestion", callback_data=f"gestion_select_{bot_id}")
            ]]),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Erreur process_message_set: {e}")
        clear_state(user_id)
        await message.reply_text("❌ Erreur lors de l'enregistrement")


async def process_button_add(client: Bot, message: Message):
    """Traite l'ajout d'un bouton"""
    user_id = message.from_user.id
    
    try:
        bot_id = get_session(user_id).get('bot_id')
        if not bot_id:
            clear_state(user_id)
            return await message.reply_text("❌ Session invalide")
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            clear_state(user_id)
            return await message.reply_text("⛔ Permissions insuffisantes")
        
        # Parser le format "Titre - URL"
        text = message.text
        if ' - ' not in text:
            return await message.reply_text(
                "❌ Format invalide!\n\n"
                "Utilisez: <code>Titre - https://lien.com</code>\n"
                "Ou envoyez /annuler"
            )
        
        parts = text.split(' - ', 1)
        btn_text = parts[0].strip()
        btn_url = parts[1].strip()
        
        # Validation
        if len(btn_text) > 64:
            return await message.reply_text("❌ Titre trop long (max 64 caractères)")
        
        if not btn_url.startswith(('http://', 'https://', 'tg://')):
            return await message.reply_text("❌ URL invalide. Doit commencer par http://, https:// ou tg://")
        
        # Ajouter à la liste
        bot_data = await db.get_cloned_bot(bot_id)
        buttons_list = bot_data.get('settings', {}).get('custom_buttons', [])
        
        if len(buttons_list) >= 10:
            clear_state(user_id)
            return await message.reply_text("❌ Maximum 10 boutons atteint")
        
        buttons_list.append({'text': btn_text, 'url': btn_url})
        await db.update_bot_settings(bot_id, {'custom_buttons': buttons_list})
        
        clear_state(user_id)
        
        await message.reply_text(
            f"<b> Bouton ajouté!</b>\n\n"
            f"<b>Titre:</b> {btn_text}\n"
            f"<b>URL:</b> {btn_url}\n\n"
            f"Total: {len(buttons_list)}/10 boutons",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔘 Retour aux boutons", callback_data=f"gestion_buttons_{bot_id}")
            ]]),
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Erreur process_button_add: {e}")
        clear_state(user_id)
        await message.reply_text("❌ Erreur lors de l'ajout du bouton")


async def process_channel_set(client: Bot, message: Message):
    """Traite la configuration du canal"""
    user_id = message.from_user.id
    
    try:
        bot_id = get_session(user_id).get('bot_id')
        if not bot_id:
            clear_state(user_id)
            return await message.reply_text("❌ Session invalide")
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            clear_state(user_id)
            return await message.reply_text("⛔ Permissions insuffisantes")
        
        channel_id_str = message.text.strip()
        
        # Validation du format
        if not re.match(r'^-100\d{10,}$', channel_id_str):
            return await message.reply_text(
                "❌ Format invalide!\n\n"
                "L'ID doit commencer par <code>-100</code> suivi de 10+ chiffres.\n"
                "Exemple: <code>-1001234567890</code>\n\n"
                "Réessayez ou envoyez /annuler"
            )
        
        channel_id = int(channel_id_str)
        
        # Récupérer le client du bot CLONÉ (c'est lui qui doit être admin du canal,
        # pas le bot mère : le bot mère n'a jamais accès à ce chat -> CHANNEL_INVALID)
        from plugins.clone import cloned_clients
        cloned_client = cloned_clients.get(bot_id)

        if not cloned_client:
            return await message.reply_text(
                "❌ <b>Le bot cloné n'est pas en ligne (pas en mémoire).</b>\n\n"
                "Le bot cloné doit être démarré pour pouvoir vérifier son accès au canal.\n"
                "Redémarrez-le puis réessayez, ou envoyez /annuler",
                parse_mode=ParseMode.HTML
            )

        # Vérifier que le bot CLONÉ est admin du canal (test via get_chat)
        try:
            chat = await cloned_client.get_chat(channel_id)
            # Si on arrive ici, le bot cloné a accès au canal
            await db.update_bot_settings(bot_id, {'channel_id': channel_id})
            clear_state(user_id)
            
            await message.reply_text(
                f"<b> Canal configuré!</b>\n\n"
                f"📢 <b>Nom:</b> {chat.title}\n"
                f"🆔 <b>ID:</b> <code>{channel_id}</code>\n\n"
                f"Le bot peut maintenant stocker les fichiers dans ce canal.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⚙️ Retour à la gestion", callback_data=f"gestion_select_{bot_id}")
                ]]),
                parse_mode=ParseMode.HTML
            )
            
        except ChatAdminRequired:
            await message.reply_text(
                "❌ <b>Le bot n'est pas administrateur du canal!</b>\n\n"
                "1. Allez dans les paramètres du canal\n"
                "2. Ajoutez le bot comme admin\n"
                "3. Réessayez ou envoyez /annuler"
            )
        except Exception as e:
            await message.reply_text(
                f"❌ <b>Impossible d'accéder au canal</b>\n\n"
                f"Erreur: {str(e)}\n\n"
                f"Vérifiez que:\n"
                f"• Le bot est admin du canal\n"
                f"• L'ID est correct\n"
                f"• Le canal existe"
            )
        
    except Exception as e:
        logger.error(f"Erreur process_channel_set: {e}")
        clear_state(user_id)
        await message.reply_text("❌ Erreur lors de la configuration")


async def process_fsub_add(client: Bot, message: Message):
    """Traite l'ajout d'un canal fsub"""
    user_id = message.from_user.id
    
    try:
        bot_id = get_session(user_id).get('bot_id')
        if not bot_id:
            clear_state(user_id)
            return await message.reply_text("❌ Session invalide")
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            clear_state(user_id)
            return await message.reply_text("⛔ Permissions insuffisantes")
        
        channel = message.text.strip()
        
        # Validation basique
        if not (channel.startswith('@') or channel.startswith('-100')):
            return await message.reply_text(
                "❌ Format invalide!\n"
                "Utilisez @username ou -100ID"
            )
        
        # Ajouter à la liste
        bot_data = await db.get_cloned_bot(bot_id)
        fsub_list = bot_data.get('settings', {}).get('force_sub_channels', [])
        
        if len(fsub_list) >= 5:
            clear_state(user_id)
            return await message.reply_text("❌ Maximum 5 canaux atteint")
        
        if channel in fsub_list:
            return await message.reply_text("❌ Ce canal est déjà dans la liste!")
        
        fsub_list.append(channel)
        await db.update_bot_settings(bot_id, {'force_sub_channels': fsub_list})
        clear_state(user_id)
        
        await message.reply_text(
            f"<b> Canal ajouté!</b>\n\n"
            f"📌 {channel}\n\n"
            f"Les utilisateurs devront rejoindre ce canal pour utiliser le bot.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📌 Retour aux Force Sub", callback_data=f"gestion_fsub_{bot_id}")
            ]]),
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Erreur process_fsub_add: {e}")
        clear_state(user_id)
        await message.reply_text("❌ Erreur lors de l'ajout")


async def process_admin_add(client: Bot, message: Message):
    """Traite l'ajout d'un admin"""
    user_id = message.from_user.id
    
    try:
        bot_id = get_session(user_id).get('bot_id')
        if not bot_id:
            clear_state(user_id)
            return await message.reply_text("❌ Session invalide")
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            clear_state(user_id)
            return await message.reply_text("⛔ Permissions insuffisantes")
        
        # Essayer de parser l'ID
        try:
            new_admin_id = int(message.text.strip())
        except ValueError:
            return await message.reply_text("❌ ID invalide! Envoyez uniquement le nombre.")
        
        if new_admin_id == user_id:
            return await message.reply_text("❌ Vous êtes déjà le MAITRE!")
        
        # Vérifier que l'utilisateur existe
        try:
            target_user = await client.get_users(new_admin_id)
        except Exception:
            return await message.reply_text(
                "❌ Utilisateur introuvable!\n"
                "L'utilisateur doit avoir démarré le bot au moins une fois."
            )
        
        # Ajouter dans le vrai systeme de permissions (collection bot_admins)
        existing_role = await db.get_user_bot_role(bot_id, new_admin_id)
        
        if existing_role:
            clear_state(user_id)
            return await message.reply_text("❌ Cet utilisateur est déjà admin!")
        
        await db.add_bot_admin(bot_id, new_admin_id, "admin", user_id)
        clear_state(user_id)
        
        await message.reply_text(
            f"<b> Administrateur ajouté!</b>\n\n"
            f"👤 <b>Nom:</b> {target_user.first_name}\n"
            f"🆔 <b>ID:</b> <code>{new_admin_id}</code>\n"
            f"📛 <b>Username:</b> @{target_user.username or 'Aucun'}\n\n"
            f"Cet utilisateur peut maintenant gérer le bot avec /gestion",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("👥 Retour aux admins", callback_data=f"gestion_admins_{bot_id}")
            ]]),
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Erreur process_admin_add: {e}")
        clear_state(user_id)
        await message.reply_text("❌ Erreur lors de l'ajout")


async def process_withdraw_request(client: Bot, message: Message):
    """Traite la demande de retrait"""
    user_id = message.from_user.id
    
    try:
        bot_id = get_session(user_id).get('bot_id')
        if not bot_id:
            clear_state(user_id)
            return await message.reply_text("❌ Session invalide")
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            clear_state(user_id)
            return await message.reply_text("⛔ Permissions insuffisantes")
        
        payment_info = message.text.strip()
        
        # Validation basique
        valid_prefixes = ['paypal:', 'btc:', 'eth:', 'ltc:', 'payeer:', 'pm:']
        if not any(payment_info.lower().startswith(p) for p in valid_prefixes):
            return await message.reply_text(
                "❌ Format invalide!\n\n"
                "Utilisez un des formats:\n"
                "• paypal:email@example.com\n"
                "• btc:adresse_bitcoin\n"
                "• payeer:P123456789\n\n"
                "Réessayez ou /annuler"
            )
        
        # Créer la demande
        earnings = await db.get_bot_earnings(bot_id)
        amount = earnings['balance']
        
        withdraw_data = {
            'bot_id': bot_id,
            'user_id': user_id,
            'amount': amount,
            'payment_info': payment_info,
            'status': 'pending',
            'requested_at': datetime.now().isoformat()
        }
        
        await db.create_withdrawal_request(withdraw_data)
        
        # Mettre à jour le solde (mettre à 0 ou en attente)
        await db.update_earnings(bot_id, {
            'balance': 0.0,
            'pending_withdrawal': amount
        })
        
        clear_state(user_id)
        
        # Notifier l'owner
        try:
            await client.send_message(
                OWNER_ID,
                f"<b>💸 Nouvelle demande de retrait!</b>\n\n"
                f"🤖 Bot ID: {bot_id}\n"
                f"💵 Montant: ${amount:.2f}\n"
                f"💳 Paiement: <code>{payment_info}</code>\n\n"
                f"Utilisez /withdrawals pour gérer.",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Impossible de notifier l'owner: {e}")
        
        await message.reply_text(
            f"<b> Demande envoyée!</b>\n\n"
            f"💵 Montant: ${amount:.2f}\n"
            f"💳 Méthode: {payment_info.split(':')[0].upper()}\n\n"
            f"Votre demande sera traitée sous 24-48h.\n"
            f"Vous recevrez une notification une fois traitée.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💰 Retour aux gains", callback_data=f"gestion_earnings_{bot_id}")
            ]]),
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Erreur process_withdraw_request: {e}")
        clear_state(user_id)
        await message.reply_text("❌ Erreur lors de la création de la demande")


async def process_delete_confirm(client: Bot, message: Message):
    """Traite la confirmation de suppression"""
    user_id = message.from_user.id
    session = get_session(user_id)
    
    try:
        bot_id = session.get('bot_id')
        confirm_username = session.get('data', {}).get('confirm_username')
        
        if not bot_id or not confirm_username:
            clear_session(user_id)
            return await message.reply_text("❌ Session invalide")
        
        if message.text.strip() != f"@{confirm_username}":
            return await message.reply_text(
                "❌ Confirmation incorrecte!\n\n"
                f"Envoyez exactement: <code>@{confirm_username}</code>\n"
                "Ou /annuler pour annuler."
            )
        
        # Supprimer le bot
        await db.delete_cloned_bot(bot_id)
        clear_session(user_id)
        
        await message.reply_text(
            f"<b>🗑️ Bot supprimé!</b>\n\n"
            f"@{confirm_username} a été supprimé du système.\n\n"
            f"Les fichiers dans le canal DB ne sont pas affectés.\n"
            f"Pour recréer un bot, utilisez /clone",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🤖 Créer un nouveau bot", callback_data="start_clone")
            ]]),
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Erreur process_delete_confirm: {e}")
        clear_session(user_id)
        await message.reply_text("❌ Erreur lors de la suppression")

# ============================================================
# COMMANDE /ANNULER (CANCEL)
# ============================================================

@Bot.on_message(filters.command(['annuler', 'cancel']) & filters.private)
async def cancel_command(client: Bot, message: Message):
    """Annule l'opération en cours"""
    user_id = message.from_user.id
    
    if user_id in user_sessions and user_sessions[user_id].get('state'):
        clear_session(user_id)
        await message.reply_text(
            "✅ <b>Opération annulée</b>\n\n"
            "Retournez à la gestion avec /gestion",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.reply_text("ℹ️ Aucune opération en cours à annuler.")

# ============================================================
# CALLBACK FERMETURE (CLOSE)
# ============================================================

@Bot.on_callback_query(filters.regex(r"^close$"))
async def close_callback(client: Bot, callback: CallbackQuery):
    """Ferme le menu"""
    try:
        await callback.message.delete()
        await callback.answer("✅ Menu fermé")
    except Exception as e:
        await callback.answer("❌ Impossible de fermer", show_alert=True)

# ============================================================
# CALLBACKS - PARAMÈTRES ET AUTRES
# ============================================================

@Bot.on_callback_query(filters.regex(r"^gestion_session_dur_(\d+)$"))
async def gestion_session_dur_callback(client: Bot, callback: CallbackQuery):
    """Configurer la duree de session pour ce bot uniquement"""
    try:
        bot_id  = int(callback.matches[0].group(1))
        user_id = callback.from_user.id

        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            return await callback.answer("Acces refuse", show_alert=True)

        bot_data = await db.get_cloned_bot(bot_id)
        current  = bot_data.get('session_duration', 0) if bot_data else 0
        global_d = await db.get_free_session_duration()

        text = (
            f"<b>Duree de session</b>\n\n"
            f"Configurez la duree de session gratuite accordee a vos utilisateurs "
            f"apres visionnage de publicite.\n\n"
            f"<b>Valeur actuelle :</b> "
            f"{'<code>' + str(current) + ' min</code> (specifique a ce bot)' if current else f'<code>{global_d} min</code> (valeur globale)'}\n\n"
            f"Repondez avec le nombre de minutes voulu (ex: <code>30</code>).\n"
            f"Envoyez <code>0</code> pour utiliser la valeur globale ({global_d} min)."
        )

        buttons = [[InlineKeyboardButton("Annuler", callback_data=f"gestion_select_{bot_id}")]]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()

        # Stocker l'attente de reponse
        from database.database import db as _db
        await _db.db["pending_inputs"].update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id":  user_id,
                "action":   "set_session_duration",
                "bot_id":   bot_id,
                "expires":  (datetime.now() + timedelta(minutes=5)).isoformat(),
            }},
            upsert=True
        )

    except Exception as e:
        logger.error(f"Erreur gestion_session_dur: {e}")
        await callback.answer("Erreur", show_alert=True)


@Bot.on_message(filters.private & filters.text)
async def handle_pending_input(client: Bot, message: Message):
    """Intercepte les reponses aux actions en attente (ex: duree session)"""
    try:
        # Ne jamais intercepter une commande (ex: /clone, /add_admin, /start...)
        # sinon ce handler "attrape-tout" peut avaler le message avant que
        # le vrai handler de la commande ne soit essayé.
        if message.text and message.text.startswith('/'):
            return

        user_id = message.from_user.id
        pending = await db.db["pending_inputs"].find_one({"user_id": user_id})
        if not pending:
            return  # Pas d'action en attente, laisser les autres handlers traiter

        action  = pending.get("action")
        bot_id  = pending.get("bot_id")
        expires = pending.get("expires", "")

        # Verifier expiration
        try:
            if datetime.fromisoformat(expires) < datetime.now():
                await db.db["pending_inputs"].delete_one({"user_id": user_id})
                return
        except Exception:
            pass

        # Supprimer immediatement pour eviter les doublons
        await db.db["pending_inputs"].delete_one({"user_id": user_id})

        if action == "set_session_duration":
            text = message.text.strip()
            try:
                minutes = int(text)
                if minutes < 0:
                    raise ValueError("Negatif")
            except ValueError:
                return await message.reply_text(
                    "Valeur invalide. Envoyez un nombre entier (ex: 30).", quote=True
                )

            # Sauvegarder dans cloned_bots
            if minutes == 0:
                await db.db["cloned_bots"].update_one(
                    {"bot_id": bot_id},
                    {"$unset": {"session_duration": ""}}
                )
                await message.reply_text(
                    f"Duree de session remise a la valeur globale.", quote=True
                )
            else:
                await db.db["cloned_bots"].update_one(
                    {"bot_id": bot_id},
                    {"$set": {"session_duration": minutes}}
                )
                await message.reply_text(
                    f"Duree de session mise a jour : <b>{minutes} minutes</b> pour ce bot.", quote=True,
                    parse_mode=ParseMode.HTML
                )

    except Exception as e:
        logger.error(f"Erreur handle_pending_input: {e}")


@Bot.on_callback_query(filters.regex(r"^gestion_settings_(\d+)$"))
async def gestion_settings_callback(client: Bot, callback: CallbackQuery):
    """Paramètres du bot"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        await _render_gestion_settings(callback, bot_id)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_settings: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


async def _render_gestion_settings(callback: CallbackQuery, bot_id: int):
    """Construit et affiche l'écran Paramètres (réutilisé par le toggle ads)"""
    bot_data = await db.get_cloned_bot(bot_id)
    ads_disabled = bot_data.get('settings', {}).get('ads_disabled', False) if bot_data else False
    ads_status = "🔴 Désactivées" if ads_disabled else "🟢 Activées"
    toggle_label = "🟢 Réactiver les pubs" if ads_disabled else "🔴 Désactiver les pubs"

    text = (
        f"<b>⚙️ Paramètres du Bot</b>\n\n"
        f"<b>Publicités :</b> {ads_status}\n\n"
        f"<i>Si désactivées, les utilisateurs reçoivent leurs fichiers directement, "
        f"sans regarder de pub ni ouvrir de session — mais aucun gain n'est généré "
        f"sur ce bot. Le Force-Sub, si configuré, reste appliqué.</i>\n\n"
        f"<i>À venir : langue du bot, restrictions d'accès.</i>"
    )

    buttons = [
        [InlineKeyboardButton(toggle_label, callback_data=f"gestion_toggle_ads_{bot_id}")],
        [InlineKeyboardButton("‹ Retour", callback_data=f"gestion_select_{bot_id}")]
    ]

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)


@Bot.on_callback_query(filters.regex(r"^gestion_toggle_ads_(\d+)$"))
async def gestion_toggle_ads_callback(client: Bot, callback: CallbackQuery):
    """Active/désactive les publicités (et donc les sessions/gains) pour ce bot"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        current = bot_data.get('settings', {}).get('ads_disabled', False) if bot_data else False
        new_value = not current
        
        await db.update_bot_settings(bot_id, {'ads_disabled': new_value})
        
        await callback.answer(
            "🔴 Publicités désactivées — plus aucun gain sur ce bot" if new_value
            else "🟢 Publicités réactivées",
            show_alert=True
        )
        
        await _render_gestion_settings(callback, bot_id)
        
    except Exception as e:
        logger.error(f"Erreur gestion_toggle_ads: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@Bot.on_callback_query(filters.regex(r"^gestion_earnings_history_(\d+)$"))
async def gestion_earnings_history_callback(client: Bot, callback: CallbackQuery):
    """Historique des gains"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'maitre'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        text = (
            f"<b> Historique des Gains</b>\n\n"
            f"<i>Fonctionnalité en développement...</i>\n\n"
            f"L'historique détaillé sera disponible prochainement."
        )
        
        buttons = [[InlineKeyboardButton("‹ Retour", callback_data=f"gestion_earnings_{bot_id}")]]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_earnings_history: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@Bot.on_callback_query(filters.regex(r"^gestion_stats_graph_(\d+)$"))
async def gestion_stats_graph_callback(client: Bot, callback: CallbackQuery):
    """Graphiques des stats"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        text = (
            f"<b>📈 Graphiques</b>\n\n"
            f"<i>Fonctionnalité en développement...</i>\n\n"
            f"Les graphiques seront disponibles prochainement."
        )
        
        buttons = [[InlineKeyboardButton("‹ Retour", callback_data=f"gestion_stats_{bot_id}")]]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_stats_graph: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@Bot.on_callback_query(filters.regex(r"^gestion_stats_export_(\d+)$"))
async def gestion_stats_export_callback(client: Bot, callback: CallbackQuery):
    """Exporter les données"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        text = (
            f"<b>📥 Exporter les Données</b>\n\n"
            f"<i>Fonctionnalité en développement...</i>\n\n"
            f"L'exportation sera disponible prochainement."
        )
        
        buttons = [[InlineKeyboardButton("‹ Retour", callback_data=f"gestion_stats_{bot_id}")]]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_stats_export: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@Bot.on_callback_query(filters.regex(r"^gestion_reorderbtn_(\d+)$"))
async def gestion_reorderbtn_callback(client: Bot, callback: CallbackQuery):
    """Réorganiser les boutons"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        text = (
            f"<b> Réorganiser les Boutons</b>\n\n"
            f"<i>Fonctionnalité en développement...</i>\n\n"
            f"La réorganisation sera disponible prochainement."
        )
        
        buttons = [[InlineKeyboardButton("‹ Retour", callback_data=f"gestion_buttons_{bot_id}")]]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_reorderbtn: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@Bot.on_callback_query(filters.regex(r"^gestion_fsub_del_menu_(\d+)$"))
async def gestion_fsub_del_menu_callback(client: Bot, callback: CallbackQuery):
    """Menu suppression fsub"""
    try:
        bot_id = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        fsub_channels = bot_data.get('settings', {}).get('force_sub_channels', [])
        
        if not fsub_channels:
            return await callback.answer("❌ Aucun canal à supprimer", show_alert=True)
        
        text = "<b>🗑️ Supprimer un canal Force Sub</b>\n\nCliquez sur le canal à supprimer:"
        
        buttons = []
        for i, ch in enumerate(fsub_channels):
            buttons.append([InlineKeyboardButton(
                f"🗑️ {ch[:30]}...",
                callback_data=f"gestion_fsub_del_{bot_id}_{i}"
            )])
        
        buttons.append([InlineKeyboardButton("‹ Retour", callback_data=f"gestion_fsub_{bot_id}")])
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Erreur gestion_fsub_del_menu: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@Bot.on_callback_query(filters.regex(r"^gestion_fsub_del_(\d+)_(\d+)$"))
async def gestion_fsub_del_callback(client: Bot, callback: CallbackQuery):
    """Supprimer un canal fsub"""
    try:
        bot_id = int(callback.matches[0].group(1))
        idx = int(callback.matches[0].group(2))
        user_id = callback.from_user.id
        
        if not await can_manage_bot(user_id, bot_id, 'admin'):
            return await callback.answer("⛔ Accès refusé", show_alert=True)
        
        bot_data = await db.get_cloned_bot(bot_id)
        fsub_channels = bot_data.get('settings', {}).get('force_sub_channels', [])
        
        if 0 <= idx < len(fsub_channels):
            removed = fsub_channels.pop(idx)
            await db.update_bot_settings(bot_id, {'force_sub_channels': fsub_channels})
            await callback.answer(f"🗑️ {removed} supprimé!", show_alert=True)
        else:
            await callback.answer("❌ Canal introuvable", show_alert=True)
        
        await gestion_fsub_callback(client, callback)
        
    except Exception as e:
        logger.error(f"Erreur gestion_fsub_del: {e}")
        await callback.answer("❌ Erreur", show_alert=True)

# ============================================================
# GESTION DES ERREURS GLOBALES
# ============================================================

@Bot.on_callback_query(filters.regex(r"^gestion_"), group=1)
async def gestion_error_handler(client: Bot, callback: CallbackQuery):
    """Gestionnaire d'erreurs générique pour les callbacks gestion"""
    try:
        # Si on arrive ici, c'est que le callback n'a pas été traité par les handlers ci-dessus
        await callback.answer("⚠️ Fonctionnalité en développement", show_alert=True)
    except Exception as e:
        logger.error(f"Erreur dans gestion_error_handler: {e}")

# ============================================================
# INITIALISATION
# ============================================================

logger.info("Module gestion.py chargé avec succès - Système de gestion des bots clonés actif")
