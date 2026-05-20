# ==========================================
# plugins/cloned/admin.py
# COMMANDES ADMIN POUR BOTS CLONÉS
# /addchnl /delchnl /listchnl /fsub_mode
# /genlink /batch /broadcast /stats /users
# ==========================================

import asyncio
import base64
import logging
import re
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from pyrogram.enums import ParseMode, ChatMemberStatus, ChatType
from pyrogram.errors import FloodWait
from database.database import db

logger = logging.getLogger(__name__)


# ============================================================
# FILTRE ADMIN/MAÎTRE POUR BOTS CLONÉS
# ============================================================

def cloned_admin_filter():
    """
    Filtre qui autorise uniquement le MAÎTRE du bot cloné
    et les admins globaux définis dans la DB principale.
    """
    async def func(flt, client, message):
        if not message.from_user:
            return False
        user_id = message.from_user.id
        bot_id = client.me.id

        # Récupérer les données du bot cloné
        bot_data = await db.get_cloned_bot(bot_id)
        if not bot_data:
            return False

        # Le maître a toujours accès
        master_id = bot_data.get('master_id') or bot_data.get('owner_id')
        if master_id and user_id == master_id:
            return True

        # Vérifier le rôle dans la DB du bot cloné
        role = await db.get_user_bot_role(bot_id, user_id)
        if role in ['maitre', 'admin']:
            return True

        # Vérifier si c'est un admin global
        try:
            if await db.admin_exist(user_id):
                return True
        except Exception:
            pass

        return False

    return filters.create(func, name="ClonedAdminFilter")


cloned_admin = cloned_admin_filter()


# ============================================================
# HELPERS
# ============================================================

async def encode(string: str) -> str:
    """Encode une chaîne en base64 URL-safe"""
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    return base64_bytes.decode("ascii").rstrip("=")


async def get_clone_settings(bot_id: int) -> dict:
    """Récupère les paramètres du bot cloné"""
    bot_data = await db.get_cloned_bot(bot_id)
    if bot_data:
        return bot_data.get('settings', {})
    return {}


async def get_db_channel_id(bot_id: int):
    """Récupère l'ID du canal DB configuré pour ce bot cloné"""
    settings = await get_clone_settings(bot_id)
    return settings.get('channel_id')


async def extract_msg_id_from_link(channel_id: int, link: str) -> int:
    """
    Extrait l'ID du message depuis un lien Telegram t.me/c/ID/MSG
    et vérifie qu'il correspond bien au canal DB du bot cloné.
    Retourne 0 si invalide.
    """
    if not link:
        return 0

    pattern = r"https://t\.me/(?:c/)?([^/]+)/(\d+)"
    match = re.match(pattern, link.strip())
    if not match:
        return 0

    channel_part = match.group(1)
    msg_id = int(match.group(2))

    if channel_part.isdigit():
        expected_id = int(f"-100{channel_part}")
        if expected_id != channel_id:
            return 0
    # canal public : on fait confiance au maître
    return msg_id


# ============================================================
# /addchnl — Ajouter le canal DB du bot cloné
# ============================================================

@Client.on_message(filters.command('addchnl') & filters.private & cloned_admin)
async def add_channel_command(client: Client, message: Message):
    """
    Ajoute le canal de stockage (DB) du bot cloné.
    Usage: /addchnl -100xxxxxxxxxx
    Le bot cloné DOIT être admin de ce canal.
    """
    bot_id = client.me.id
    temp = await message.reply("<b><i>Veuillez patienter...</i></b>", quote=True)

    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        return await temp.edit(
            "<b>❌ Usage :</b> <code>/addchnl -100xxxxxxxxxx</code>\n\n"
            "<i>Fournissez l'ID numérique du canal (commence par -100).</i>",
            parse_mode=ParseMode.HTML
        )

    try:
        chat_id = int(args[1])
    except ValueError:
        return await temp.edit(
            "<b>❌ ID de canal invalide !</b>\n"
            "L'ID doit être un nombre (ex: <code>-1001234567890</code>)",
            parse_mode=ParseMode.HTML
        )

    # Vérifier que c'est bien un canal/supergroupe et que le bot en est admin
    try:
        chat = await client.get_chat(chat_id)

        if chat.type not in [ChatType.CHANNEL, ChatType.SUPERGROUP]:
            return await temp.edit(
                "<b>❌ Seuls les canaux et supergroupes sont autorisés.</b>",
                parse_mode=ParseMode.HTML
            )

        bot_member = await client.get_chat_member(chat.id, "me")
        if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await temp.edit(
                "<b>❌ Ce bot doit être administrateur dans ce canal.</b>\n\n"
                "Ajoutez ce bot comme admin du canal, puis réessayez.",
                parse_mode=ParseMode.HTML
            )

        # Test d'envoi pour vérifier les droits
        test_msg = await client.send_message(chat_id=chat.id, text="🔄 Test de connexion...")
        await test_msg.delete()

    except Exception as e:
        return await temp.edit(
            f"<b>❌ Impossible d'accéder au canal :</b>\n<code>{chat_id}</code>\n\n"
            f"<i>{e}</i>\n\n"
            "<b>Vérifiez que :</b>\n"
            "• L'ID est correct\n"
            "• Ce bot est admin du canal\n"
            "• Le canal existe",
            parse_mode=ParseMode.HTML
        )

    # Sauvegarder dans les settings du bot cloné
    try:
        current_settings = await get_clone_settings(bot_id)
        current_settings['channel_id'] = chat.id
        current_settings['channel_username'] = chat.username or None
        current_settings['channel_title'] = chat.title

        await db.update_bot_settings(bot_id, {'settings': current_settings})

        try:
            link = await client.export_chat_invite_link(chat.id)
        except Exception:
            link = f"https://t.me/{chat.username}" if chat.username else f"https://t.me/c/{str(chat.id)[4:]}"

        await temp.edit(
            f"<b>✅ Canal DB configuré avec succès !</b>\n\n"
            f"<b>📢 Canal :</b> <a href='{link}'>{chat.title}</a>\n"
            f"<b>🆔 ID :</b> <code>{chat.id}</code>\n\n"
            "<i>Vous pouvez maintenant utiliser /genlink et /batch pour générer des liens.</i>",
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logger.error(f"[CLONE] Erreur sauvegarde canal DB: {e}")
        await temp.edit(
            f"<b>❌ Erreur lors de la sauvegarde :</b>\n<code>{e}</code>",
            parse_mode=ParseMode.HTML
        )


# ============================================================
# /delchnl — Supprimer le canal DB du bot cloné
# ============================================================

@Client.on_message(filters.command('delchnl') & filters.private & cloned_admin)
async def del_channel_command(client: Client, message: Message):
    """
    Supprime le canal de stockage (DB) du bot cloné.
    Usage: /delchnl
    """
    bot_id = client.me.id
    temp = await message.reply("<b><i>Veuillez patienter...</i></b>", quote=True)

    current_settings = await get_clone_settings(bot_id)
    channel_id = current_settings.get('channel_id')

    if not channel_id:
        return await temp.edit(
            "<b>❌ Aucun canal DB configuré.</b>\n\n"
            "Utilisez <code>/addchnl -100xxxxxxxxxx</code> pour en ajouter un.",
            parse_mode=ParseMode.HTML
        )

    # Afficher un bouton de confirmation
    channel_title = current_settings.get('channel_title', str(channel_id))

    await temp.edit(
        f"<b>⚠️ Confirmer la suppression ?</b>\n\n"
        f"Canal actuel : <b>{channel_title}</b> (<code>{channel_id}</code>)\n\n"
        "<i>Cette action supprime uniquement la configuration. Les fichiers dans le canal ne sont pas affectés.</i>",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirmer", callback_data="delchnl_confirm"),
                InlineKeyboardButton("❌ Annuler", callback_data="delchnl_cancel")
            ]
        ]),
        parse_mode=ParseMode.HTML
    )


@Client.on_callback_query(filters.regex("^delchnl_confirm$"))
async def delchnl_confirm_callback(client: Client, callback: CallbackQuery):
    """Confirme la suppression du canal DB"""
    bot_id = client.me.id
    user_id = callback.from_user.id

    # Vérifier les droits
    bot_data = await db.get_cloned_bot(bot_id)
    if not bot_data:
        return await callback.answer("❌ Bot introuvable", show_alert=True)

    master_id = bot_data.get('master_id') or bot_data.get('owner_id')
    role = await db.get_user_bot_role(bot_id, user_id)
    if user_id != master_id and role not in ['maitre', 'admin']:
        return await callback.answer("⛔ Accès refusé", show_alert=True)

    try:
        current_settings = await get_clone_settings(bot_id)
        current_settings.pop('channel_id', None)
        current_settings.pop('channel_username', None)
        current_settings.pop('channel_title', None)

        await db.update_bot_settings(bot_id, {'settings': current_settings})

        await callback.message.edit_text(
            "<b>✅ Canal DB supprimé avec succès !</b>\n\n"
            "Utilisez <code>/addchnl</code> pour en configurer un nouveau.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await callback.message.edit_text(
            f"<b>❌ Erreur :</b> <code>{e}</code>",
            parse_mode=ParseMode.HTML
        )

    await callback.answer()


@Client.on_callback_query(filters.regex("^delchnl_cancel$"))
async def delchnl_cancel_callback(client: Client, callback: CallbackQuery):
    """Annule la suppression du canal DB"""
    await callback.message.edit_text(
        "<b>❌ Suppression annulée.</b>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer("Annulé")


# ============================================================
# /listchnl — Lister le canal DB configuré
# ============================================================

@Client.on_message(filters.command('listchnl') & filters.private & cloned_admin)
async def list_channel_command(client: Client, message: Message):
    """Affiche le canal DB actuellement configuré"""
    bot_id = client.me.id
    temp = await message.reply("<b><i>Veuillez patienter...</i></b>", quote=True)

    settings = await get_clone_settings(bot_id)
    channel_id = settings.get('channel_id')

    if not channel_id:
        return await temp.edit(
            "<b>❌ Aucun canal DB configuré.</b>\n\n"
            "Utilisez <code>/addchnl -100xxxxxxxxxx</code> pour en ajouter un.",
            parse_mode=ParseMode.HTML
        )

    try:
        chat = await client.get_chat(channel_id)
        try:
            link = await client.export_chat_invite_link(chat.id)
        except Exception:
            link = f"https://t.me/{chat.username}" if chat.username else f"https://t.me/c/{str(chat.id)[4:]}"

        await temp.edit(
            f"<b>📢 Canal DB configuré :</b>\n\n"
            f"• <a href='{link}'>{chat.title}</a> [<code>{channel_id}</code>]",
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Fermer ✖️", callback_data="close")]
            ])
        )
    except Exception as e:
        await temp.edit(
            f"<b>⚠️ Canal configuré :</b> <code>{channel_id}</code>\n"
            f"<i>Impossible de récupérer les infos : {e}</i>",
            parse_mode=ParseMode.HTML
        )


# ============================================================
# /fsub_mode — Gérer les canaux force-sub du bot cloné
# ============================================================

@Client.on_message(filters.command('fsub_mode') & filters.private & cloned_admin)
async def fsub_mode_command(client: Client, message: Message):
    """
    Gère le mode force-sub des canaux du bot cloné.
    Affiche la liste des canaux fsub avec leur statut ON/OFF.
    """
    bot_id = client.me.id
    temp = await message.reply("<b><i>Veuillez patienter...</i></b>", quote=True)

    # Récupérer les canaux fsub de ce bot cloné
    try:
        channels = await db.get_bot_fsub_channels(bot_id)
    except Exception:
        channels = []

    if not channels:
        return await temp.edit(
            "<b>❌ Aucun canal force-sub configuré pour ce bot.</b>\n\n"
            "Ajoutez des canaux force-sub via /addfsub <code>-100xxxxxxxxxx</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Fermer ✖️", callback_data="close")]
            ])
        )

    buttons = []
    for ch_id in channels:
        try:
            chat = await client.get_chat(ch_id)
            mode = await db.get_bot_channel_mode(bot_id, ch_id)
            status = "🟢" if mode == "on" else "🔴"
            title = f"{status} {chat.title}"
        except Exception:
            mode = await db.get_bot_channel_mode(bot_id, ch_id)
            status = "🟢" if mode == "on" else "🔴"
            title = f"{status} ⚠️ {ch_id} (Indisponible)"

        buttons.append([InlineKeyboardButton(title, callback_data=f"cloned_rfs_ch_{bot_id}_{ch_id}")])

    buttons.append([InlineKeyboardButton("Fermer ✖️", callback_data="close")])

    await temp.edit(
        "<b>⚡ Canaux Force-Sub de votre bot :</b>\n\n"
        "<i>Cliquez sur un canal pour basculer son mode.</i>",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )


# ============================================================
# /addfsub — Ajouter un canal force-sub
# ============================================================

@Client.on_message(filters.command('addfsub') & filters.private & cloned_admin)
async def add_fsub_command(client: Client, message: Message):
    """
    Ajoute un canal force-sub au bot cloné.
    Usage: /addfsub -100xxxxxxxxxx
    """
    bot_id = client.me.id
    temp = await message.reply("<b><i>Veuillez patienter...</i></b>", quote=True)

    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        return await temp.edit(
            "<b>❌ Usage :</b> <code>/addfsub -100xxxxxxxxxx</code>",
            parse_mode=ParseMode.HTML
        )

    try:
        chat_id = int(args[1])
    except ValueError:
        return await temp.edit("<b>❌ ID de canal invalide !</b>", parse_mode=ParseMode.HTML)

    # Vérifier si déjà ajouté
    try:
        existing = await db.get_bot_fsub_channels(bot_id)
        if chat_id in (existing or []):
            return await temp.edit(
                f"<b>⚠️ Ce canal est déjà en force-sub :</b> <code>{chat_id}</code>",
                parse_mode=ParseMode.HTML
            )
    except Exception:
        pass

    try:
        chat = await client.get_chat(chat_id)

        if chat.type not in [ChatType.CHANNEL, ChatType.SUPERGROUP]:
            return await temp.edit(
                "<b>❌ Seuls les canaux et supergroupes sont autorisés.</b>",
                parse_mode=ParseMode.HTML
            )

        bot_member = await client.get_chat_member(chat.id, "me")
        if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await temp.edit(
                "<b>❌ Ce bot doit être administrateur dans ce canal.</b>",
                parse_mode=ParseMode.HTML
            )

        try:
            link = await client.export_chat_invite_link(chat.id)
        except Exception:
            link = f"https://t.me/{chat.username}" if chat.username else f"https://t.me/c/{str(chat.id)[4:]}"

        await db.add_bot_fsub_channel(bot_id, chat_id)

        await temp.edit(
            f"<b>✅ Canal force-sub ajouté !</b>\n\n"
            f"<b>Nom :</b> <a href='{link}'>{chat.title}</a>\n"
            f"<b>ID :</b> <code>{chat_id}</code>",
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        await temp.edit(
            f"<b>❌ Échec :</b> <code>{chat_id}</code>\n\n<i>{e}</i>",
            parse_mode=ParseMode.HTML
        )


# ============================================================
# /delfsub — Supprimer un canal force-sub
# ============================================================

@Client.on_message(filters.command('delfsub') & filters.private & cloned_admin)
async def del_fsub_command(client: Client, message: Message):
    """
    Supprime un canal force-sub du bot cloné.
    Usage: /delfsub -100xxxxxxxxxx | /delfsub all
    """
    bot_id = client.me.id
    temp = await message.reply("<b><i>Veuillez patienter...</i></b>", quote=True)

    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        return await temp.edit(
            "<b>❌ Usage :</b>\n"
            "<code>/delfsub -100xxxxxxxxxx</code>\n"
            "<code>/delfsub all</code>",
            parse_mode=ParseMode.HTML
        )

    try:
        all_channels = await db.get_bot_fsub_channels(bot_id) or []
    except Exception:
        all_channels = []

    if args[1].lower() == "all":
        if not all_channels:
            return await temp.edit("<b>❌ Aucun canal force-sub à supprimer.</b>", parse_mode=ParseMode.HTML)
        for ch_id in all_channels:
            try:
                await db.del_bot_fsub_channel(bot_id, ch_id)
            except Exception:
                pass
        return await temp.edit("<b>✅ Tous les canaux force-sub ont été supprimés.</b>", parse_mode=ParseMode.HTML)

    try:
        ch_id = int(args[1])
    except ValueError:
        return await temp.edit("<b>❌ ID invalide.</b>", parse_mode=ParseMode.HTML)

    if ch_id in all_channels:
        await db.del_bot_fsub_channel(bot_id, ch_id)
        return await temp.edit(
            f"<b>✅ Canal supprimé :</b> <code>{ch_id}</code>",
            parse_mode=ParseMode.HTML
        )
    else:
        return await temp.edit(
            f"<b>❌ Canal introuvable dans la liste force-sub :</b> <code>{ch_id}</code>",
            parse_mode=ParseMode.HTML
        )


# ============================================================
# CALLBACKS — fsub_mode (rfs) pour bots clonés
# ============================================================

@Client.on_callback_query(filters.regex(r"^cloned_rfs_ch_(\d+)_(-?\d+)$"))
async def cloned_rfs_ch_callback(client: Client, callback: CallbackQuery):
    """Affiche le détail d'un canal force-sub pour le bot cloné"""
    bot_id = int(callback.matches[0].group(1))
    ch_id = int(callback.matches[0].group(2))

    try:
        chat = await client.get_chat(ch_id)
        mode = await db.get_bot_channel_mode(bot_id, ch_id)
        status = "🟢 Activé" if mode == "on" else "🔴 Désactivé"
        new_mode = "off" if mode == "on" else "on"

        buttons = [
            [InlineKeyboardButton(
                f"Mode Req {'DÉSACTIVER' if mode == 'on' else 'ACTIVER'}",
                callback_data=f"cloned_rfs_toggle_{bot_id}_{ch_id}_{new_mode}"
            )],
            [InlineKeyboardButton("‹ Retour", callback_data=f"cloned_fsub_back_{bot_id}")]
        ]

        await callback.message.edit_text(
            f"<b>Canal :</b> {chat.title}\n"
            f"<b>Mode Force-Sub :</b> {status}",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )
    except Exception:
        await callback.answer("❌ Impossible de récupérer les infos du canal", show_alert=True)


@Client.on_callback_query(filters.regex(r"^cloned_rfs_toggle_(\d+)_(-?\d+)_(on|off)$"))
async def cloned_rfs_toggle_callback(client: Client, callback: CallbackQuery):
    """Bascule le mode force-sub d'un canal pour le bot cloné"""
    bot_id = int(callback.matches[0].group(1))
    ch_id = int(callback.matches[0].group(2))
    new_mode = callback.matches[0].group(3)

    await db.set_bot_channel_mode(bot_id, ch_id, new_mode)
    await callback.answer(
        f"Force-Sub {'ACTIVÉ' if new_mode == 'on' else 'DÉSACTIVÉ'} ✅"
    )

    try:
        chat = await client.get_chat(ch_id)
        status = "🟢 ACTIVÉ" if new_mode == "on" else "🔴 DÉSACTIVÉ"
        toggle_mode = "off" if new_mode == "on" else "on"

        buttons = [
            [InlineKeyboardButton(
                f"Mode Req {'DÉSACTIVER' if new_mode == 'on' else 'ACTIVER'}",
                callback_data=f"cloned_rfs_toggle_{bot_id}_{ch_id}_{toggle_mode}"
            )],
            [InlineKeyboardButton("‹ Retour", callback_data=f"cloned_fsub_back_{bot_id}")]
        ]

        await callback.message.edit_text(
            f"<b>Canal :</b> {chat.title}\n"
            f"<b>Mode Force-Sub :</b> {status}",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^cloned_fsub_back_(\d+)$"))
async def cloned_fsub_back_callback(client: Client, callback: CallbackQuery):
    """Retour à la liste des canaux fsub"""
    bot_id = int(callback.matches[0].group(1))

    try:
        channels = await db.get_bot_fsub_channels(bot_id) or []
    except Exception:
        channels = []

    if not channels:
        return await callback.message.edit_text(
            "<b>❌ Aucun canal force-sub configuré.</b>",
            parse_mode=ParseMode.HTML
        )

    buttons = []
    for ch_id in channels:
        try:
            chat = await client.get_chat(ch_id)
            mode = await db.get_bot_channel_mode(bot_id, ch_id)
            status = "🟢" if mode == "on" else "🔴"
            buttons.append([InlineKeyboardButton(
                f"{status} {chat.title}",
                callback_data=f"cloned_rfs_ch_{bot_id}_{ch_id}"
            )])
        except Exception:
            buttons.append([InlineKeyboardButton(
                f"⚠️ {ch_id}",
                callback_data=f"cloned_rfs_ch_{bot_id}_{ch_id}"
            )])

    buttons.append([InlineKeyboardButton("Fermer ✖️", callback_data="close")])

    await callback.message.edit_text(
        "<b>⚡ Canaux Force-Sub de votre bot :</b>",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


# ============================================================
# /genlink — Générer un lien depuis un message du canal DB
# ============================================================

@Client.on_message(filters.command('genlink') & filters.private & cloned_admin)
async def genlink_command(client: Client, message: Message):
    """
    Génère un lien de partage pour un fichier du canal DB.
    Usage: /genlink https://t.me/c/CHANNEL_ID/MSG_ID
    """
    bot_id = client.me.id

    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Format incorrect</b>\n\n"
            "<b>Usage :</b> <code>/genlink https://t.me/c/CHANNEL_ID/MSG_ID</code>\n\n"
            "<b>Exemple :</b>\n"
            "<code>/genlink https://t.me/c/1234567890/229</code>",
            quote=True,
            parse_mode=ParseMode.HTML
        )

    channel_id = await get_db_channel_id(bot_id)
    if not channel_id:
        return await message.reply_text(
            "<b>❌ Canal DB non configuré !</b>\n\n"
            "Configurez d'abord le canal avec <code>/addchnl -100xxxxxxxxxx</code>",
            quote=True,
            parse_mode=ParseMode.HTML
        )

    link_input = message.command[1]
    msg_id = await extract_msg_id_from_link(channel_id, link_input)

    if not msg_id:
        return await message.reply_text(
            "<b>❌ Lien invalide</b>\n\n"
            "Ce lien ne provient pas du canal DB configuré, ou le format est incorrect.\n\n"
            f"<i>Canal DB actuel : <code>{channel_id}</code></i>",
            quote=True,
            parse_mode=ParseMode.HTML
        )

    try:
        base64_string = await encode(f"get-{msg_id * abs(channel_id)}")
        share_link = f"https://t.me/{client.me.username}?start={base64_string}"

        await message.reply_text(
            f"<b>✅ Lien généré</b>\n\n"
            f"<b>Message ID :</b> {msg_id}\n\n"
            f"<code>{share_link}</code>",
            quote=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Partager le lien", url=f"https://telegram.me/share/url?url={share_link}")]
            ]),
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logger.error(f"[CLONE genlink] Erreur: {e}")
        await message.reply_text(
            f"<b>❌ Erreur lors de la génération :</b>\n<code>{e}</code>",
            quote=True,
            parse_mode=ParseMode.HTML
        )


# ============================================================
# /batch — Générer un lien batch (début → fin)
# ============================================================

@Client.on_message(filters.command('batch') & filters.private & cloned_admin)
async def batch_command(client: Client, message: Message):
    """
    Génère un lien batch pour une plage de messages du canal DB.
    Usage: /batch https://t.me/c/CHANNEL/START https://t.me/c/CHANNEL/END
    """
    bot_id = client.me.id

    if len(message.command) < 3:
        return await message.reply_text(
            "<b>❌ Format incorrect</b>\n\n"
            "<b>Usage :</b> <code>/batch [lien début] [lien fin]</code>\n\n"
            "<b>Exemple :</b>\n"
            "<code>/batch https://t.me/c/1234567890/123 https://t.me/c/1234567890/145</code>",
            quote=True,
            parse_mode=ParseMode.HTML
        )

    channel_id = await get_db_channel_id(bot_id)
    if not channel_id:
        return await message.reply_text(
            "<b>❌ Canal DB non configuré !</b>\n\n"
            "Configurez d'abord le canal avec <code>/addchnl -100xxxxxxxxxx</code>",
            quote=True,
            parse_mode=ParseMode.HTML
        )

    first_link = message.command[1]
    second_link = message.command[2]

    f_msg_id = await extract_msg_id_from_link(channel_id, first_link)
    s_msg_id = await extract_msg_id_from_link(channel_id, second_link)

    if not f_msg_id:
        return await message.reply_text(
            "<b>❌ Erreur premier lien</b>\n\n"
            "Le lien ne provient pas du canal DB ou est invalide.",
            quote=True,
            parse_mode=ParseMode.HTML
        )

    if not s_msg_id:
        return await message.reply_text(
            "<b>❌ Erreur deuxième lien</b>\n\n"
            "Le lien ne provient pas du canal DB ou est invalide.",
            quote=True,
            parse_mode=ParseMode.HTML
        )

    if f_msg_id > s_msg_id:
        return await message.reply_text(
            "<b>❌ Erreur</b>\n\n"
            "Le premier message doit avoir un ID inférieur au dernier.",
            quote=True,
            parse_mode=ParseMode.HTML
        )

    try:
        string = f"get-{f_msg_id * abs(channel_id)}-{s_msg_id * abs(channel_id)}"
        base64_string = await encode(string)
        share_link = f"https://t.me/{client.me.username}?start={base64_string}"

        await message.reply_text(
            f"<b>✅ Lien batch généré</b>\n\n"
            f"<b>Début :</b> Message {f_msg_id}\n"
            f"<b>Fin :</b> Message {s_msg_id}\n"
            f"<b>Total :</b> {s_msg_id - f_msg_id + 1} fichiers\n\n"
            f"<code>{share_link}</code>",
            quote=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Partager le lien", url=f"https://telegram.me/share/url?url={share_link}")]
            ]),
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logger.error(f"[CLONE batch] Erreur: {e}")
        await message.reply_text(
            f"<b>❌ Erreur lors de la génération :</b>\n<code>{e}</code>",
            quote=True,
            parse_mode=ParseMode.HTML
        )


# ============================================================
# /broadcast — Diffuser un message aux utilisateurs du bot cloné
# ============================================================

@Client.on_message(filters.command('broadcast') & filters.private & cloned_admin)
async def broadcast_command(client: Client, message: Message):
    """
    Diffuse un message à tous les utilisateurs du bot cloné.
    Répondez à un message et tapez /broadcast.
    """
    bot_id = client.me.id

    if not message.reply_to_message:
        return await message.reply_text(
            "<b>❌ Répondez à un message à diffuser.</b>\n\n"
            "<i>Exemple : répondez à une photo avec /broadcast</i>",
            quote=True,
            parse_mode=ParseMode.HTML
        )

    try:
        users = await db.get_bot_users(bot_id)
    except Exception:
        users = []

    if not users:
        return await message.reply_text(
            "<b>❌ Aucun utilisateur enregistré pour ce bot.</b>",
            quote=True,
            parse_mode=ParseMode.HTML
        )

    total = len(users)
    sent = 0
    failed = 0

    status_msg = await message.reply_text(
        f"<b>📤 Diffusion en cours...</b>\n\n"
        f"0/{total} messages envoyés",
        quote=True,
        parse_mode=ParseMode.HTML
    )

    for user in users:
        try:
            user_id = user['user_id'] if isinstance(user, dict) else user
            await message.reply_to_message.copy(user_id)
            sent += 1
        except Exception:
            failed += 1

        if (sent + failed) % 50 == 0:
            try:
                await status_msg.edit_text(
                    f"<b>📤 Diffusion en cours...</b>\n\n"
                    f"{sent + failed}/{total}\n"
                    f"✅ Envoyés : {sent}\n"
                    f"❌ Échoués : {failed}",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass

        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        f"<b>✅ Diffusion terminée !</b>\n\n"
        f"📊 <b>Total :</b> {total}\n"
        f"✅ <b>Envoyés :</b> {sent}\n"
        f"❌ <b>Échoués :</b> {failed}",
        parse_mode=ParseMode.HTML
    )


# ============================================================
# /stats — Statistiques du bot cloné
# ============================================================

@Client.on_message(filters.command('stats') & filters.private & cloned_admin)
async def stats_command(client: Client, message: Message):
    """Affiche les statistiques du bot cloné"""
    bot_id = client.me.id

    try:
        bot_data = await db.get_cloned_bot(bot_id)
        stats = bot_data.get('stats', {}) if bot_data else {}
        settings = bot_data.get('settings', {}) if bot_data else {}

        total_users = stats.get('total_users', 0)
        total_files = stats.get('total_files_sent', 0)
        channel_id = settings.get('channel_id', 'Non configuré')
        channel_title = settings.get('channel_title', str(channel_id))

        await message.reply_text(
            f"<b>📊 Statistiques de @{client.me.username}</b>\n\n"
            f"👥 <b>Utilisateurs :</b> {total_users}\n"
            f"📁 <b>Fichiers envoyés :</b> {total_files}\n"
            f"📢 <b>Canal DB :</b> {channel_title}\n",
            quote=True,
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        await message.reply_text(
            f"<b>❌ Erreur :</b> <code>{e}</code>",
            quote=True,
            parse_mode=ParseMode.HTML
        )


# ============================================================
# /users — Nombre d'utilisateurs du bot cloné
# ============================================================

@Client.on_message(filters.command('users') & filters.private & cloned_admin)
async def users_command(client: Client, message: Message):
    """Affiche le nombre d'utilisateurs du bot cloné"""
    bot_id = client.me.id

    try:
        users = await db.get_bot_users(bot_id) or []
        await message.reply_text(
            f"<b>👥 Utilisateurs de @{client.me.username} :</b>\n\n"
            f"<b>{len(users)}</b> utilisateur(s)",
            quote=True,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.reply_text(
            f"<b>❌ Erreur :</b> <code>{e}</code>",
            quote=True,
            parse_mode=ParseMode.HTML
        )
