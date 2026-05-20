# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport
#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.
#

import asyncio
import os
import random
import sys
import time
from datetime import datetime, timedelta
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, ChatInviteLink, ChatPrivileges
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant
from bot import Bot
from config import *
from helper_func import *
from database.database import *



#SYSTÈME DE BANISSEMENT D'UTILISATEUR
@Bot.on_message(filters.private & filters.command('ban') & admin)
async def add_banuser(client: Client, message: Message):        
    pro = await message.reply("⏳ <i>Traitement de la requête...</i>", quote=True)
    banuser_ids = await db.get_ban_users()
    banusers = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Fermer", callback_data="close")]])

    if not banusers:
        return await pro.edit(
            "<b>❗ Vous devez fournir des ID utilisateur à bannir.</b>\n\n"
            "<b>📌 Utilisation :</b>\n"
            "<code>/ban [id_utilisateur]</code> — Bannir un ou plusieurs utilisateurs par ID.",
            reply_markup=reply_markup
        )

    report, success_count = "", 0
    for uid in banusers:
        try:
            uid_int = int(uid)
        except:
            report += f"⚠️ ID invalide : <code>{uid}</code>\n"
            continue

        if uid_int in await db.get_all_admins() or uid_int == OWNER_ID:
            report += f"⛔ ID admin/propriétaire ignoré : <code>{uid_int}</code>\n"
            continue

        if uid_int in banuser_ids:
            report += f"⚠️ Déjà banni : <code>{uid_int}</code>\n"
            continue

        if len(str(uid_int)) == 10:
            await db.add_ban_user(uid_int)
            report += f"✅ Banni : <code>{uid_int}</code>\n"
            success_count += 1
        else:
            report += f"⚠️ Longueur d'ID Telegram invalide : <code>{uid_int}</code>\n"

    if success_count:
        await pro.edit(f"<b>✅ Utilisateurs bannis mis à jour :</b>\n\n{report}", reply_markup=reply_markup)
    else:
        await pro.edit(f"<b>❌ Aucun utilisateur n'a été banni.</b>\n\n{report}", reply_markup=reply_markup)

@Bot.on_message(filters.private & filters.command('unban') & admin)
async def delete_banuser(client: Client, message: Message):        
    pro = await message.reply("⏳ <i>Traitement de la requête...</i>", quote=True)
    banuser_ids = await db.get_ban_users()
    banusers = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Fermer", callback_data="close")]])

    if not banusers:
        return await pro.edit(
            "<b>❗ Veuillez fournir des ID utilisateur à débannir.</b>\n\n"
            "<b>📌 Utilisation :</b>\n"
            "<code>/unban [id_utilisateur]</code> — Débannir des utilisateurs spécifiques\n"
            "<code>/unban all</code> — Supprimer tous les utilisateurs bannis",
            reply_markup=reply_markup
        )

    if banusers[0].lower() == "all":
        if not banuser_ids:
            return await pro.edit("<b>✅ Aucun utilisateur dans la liste des bannis.</b>", reply_markup=reply_markup)
        for uid in banuser_ids:
            await db.del_ban_user(uid)
        listed = "\n".join([f"✅ Débanni : <code>{uid}</code>" for uid in banuser_ids])
        return await pro.edit(f"<b>🚫 Liste des bannis vidée :</b>\n\n{listed}", reply_markup=reply_markup)

    report = ""
    for uid in banusers:
        try:
            uid_int = int(uid)
        except:
            report += f"⚠️ ID invalide : <code>{uid}</code>\n"
            continue

        if uid_int in banuser_ids:
            await db.del_ban_user(uid_int)
            report += f"✅ Débanni : <code>{uid_int}</code>\n"
        else:
            report += f"⚠️ Non présent dans la liste des bannis : <code>{uid_int}</code>\n"

    await pro.edit(f"<b>🚫 Rapport de débannissement :</b>\n\n{report}", reply_markup=reply_markup)

@Bot.on_message(filters.private & filters.command('banlist') & admin)
async def get_banuser_list(client: Client, message: Message):        
    pro = await message.reply("⏳ <i>Récupération de la liste des bannis...</i>", quote=True)
    banuser_ids = await db.get_ban_users()

    if not banuser_ids:
        return await pro.edit("<b>✅ Aucun utilisateur dans la liste des bannis.</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Fermer", callback_data="close")]]))

    result = "<b>🚫 Utilisateurs bannis :</b>\n\n"
    for uid in banuser_ids:
        await message.reply_chat_action(ChatAction.TYPING)
        try:
            user = await client.get_users(uid)
            user_link = f'<a href="tg://user?id={uid}">{user.first_name}</a>'
            result += f"• {user_link} — <code>{uid}</code>\n"
        except:
            result += f"• <code>{uid}</code> — <i>Impossible de récupérer le nom</i>\n"

    await pro.edit(result, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Fermer", callback_data="close")]]))