#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.

from pyrogram import Client 
from bot import Bot
from config import *
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.database import *

@Bot.on_callback_query(group=2)
async def cb_handler(client: Bot, query: CallbackQuery):
    data = query.data

    # Les callbacks help, about, start, close sont gérés dans start.py
    # On garde seulement les callbacks spécifiques au Force Sub ici

    if data.startswith("rfs_ch_"):
        cid = int(data.split("_")[2])
        try:
            chat = await client.get_chat(cid)
            mode = await db.get_channel_mode(cid)
            status = "🟢 Activé" if mode == "on" else "🔴 Désactivé"
            new_mode = "off" if mode == "on" else "on"
            buttons = [
                [InlineKeyboardButton(f"Mode Req {'DÉSACTIVER' if mode == 'on' else 'ACTIVER'}", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
                [InlineKeyboardButton("‹ Retour", callback_data="fsub_back")]
            ]
            await query.message.edit_text(
                f"Chaîne : {chat.title}\nMode Abonnement Obligatoire : {status}",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            await query.answer("Échec de la récupération des infos de la chaîne", show_alert=True)

    elif data.startswith("rfs_toggle_"):
        cid, action = data.split("_")[2:]
        cid = int(cid)
        mode = "on" if action == "on" else "off"

        await db.set_channel_mode(cid, mode)
        await query.answer(f"Abonnement obligatoire {'ACTIVÉ' if mode == 'on' else 'DÉSACTIVÉ'}")

        # Rafraîchir la vue du mode de la même chaîne
        chat = await client.get_chat(cid)
        status = "🟢 ACTIVÉ" if mode == "on" else "🔴 DÉSACTIVÉ"
        new_mode = "off" if mode == "on" else "on"
        buttons = [
            [InlineKeyboardButton(f"Mode Req {'DÉSACTIVER' if mode == 'on' else 'ACTIVER'}", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
            [InlineKeyboardButton("‹ Retour", callback_data="fsub_back")]
        ]
        await query.message.edit_text(
            f"Chaîne : {chat.title}\nMode Abonnement Obligatoire : {status}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == "fsub_back":
        channels = await db.show_channels()
        buttons = []
        for cid in channels:
            try:
                chat = await client.get_chat(cid)
                mode = await db.get_channel_mode(cid)
                status = "🟢" if mode == "on" else "🔴"
                buttons.append([InlineKeyboardButton(f"{status} {chat.title}", callback_data=f"rfs_ch_{cid}")])
            except:
                continue

        await query.message.edit_text(
            "Sélectionnez une chaîne pour modifier son mode d'abonnement obligatoire :",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
