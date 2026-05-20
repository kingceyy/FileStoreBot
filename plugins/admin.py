import asyncio
import os
import random
import sys
import time
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction, ChatMemberStatus, ChatType
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, ChatMemberUpdated, ChatPermissions
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, InviteHashEmpty, ChatAdminRequired, PeerIdInvalid, UserIsBlocked, InputUserDeactivated
from bot import Bot
from config import *
from helper_func import *
from database.database import *



# Commandes pour ajouter des administrateurs par le propriétaire
@Bot.on_message(filters.command('add_admin') & filters.private & filters.user(OWNER_ID))
async def add_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>Veuillez patienter..</i></b>", quote=True)
    check = 0
    admin_ids = await db.get_all_admins()
    admins = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Fermer", callback_data="close")]])

    if not admins:
        return await pro.edit(
            "<b>Vous devez fournir des ID utilisateur à ajouter comme administrateur.</b>\n\n"
            "<b>Utilisation :</b>\n"
            "<code>/add_admin [id_utilisateur]</code> — Ajouter un ou plusieurs ID utilisateur\n\n"
            "<b>Exemple :</b>\n"
            "<code>/add_admin 1234567890 9876543210</code>",
            reply_markup=reply_markup
        )

    admin_list = ""
    valid_ids = []
    for id in admins:
        try:
            id_int = int(id)
        except:
            admin_list += f"<blockquote><b>ID invalide : <code>{id}</code></b></blockquote>\n"
            continue

        if id_int in admin_ids:
            admin_list += f"<blockquote><b>L'ID <code>{id}</code> existe déjà.</b></blockquote>\n"
            continue

        valid_ids.append(id_int)
        admin_list += f"<b><blockquote>(ID : <code>{id}</code>) ajouté.</blockquote></b>\n"
        check += 1

    if check == len(valid_ids):
        for id in valid_ids:
            await db.add_admin(id)
        await pro.edit(f"<b>✅ Administrateur(s) ajouté(s) avec succès :</b>\n\n{admin_list}", reply_markup=reply_markup)
    else:
        await pro.edit(
            f"<b>⚠️ Certains ID n'ont pas été ajoutés :</b>\n\n{admin_list.strip()}\n\n"
            "<b><i>Vérifiez la saisie et réessayez.</i></b>",
            reply_markup=reply_markup
        )


@Bot.on_message(filters.command('deladmin') & filters.private & filters.user(OWNER_ID))
async def delete_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>Veuillez patienter..</i></b>", quote=True)
    admin_ids = await db.get_all_admins()
    admins = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Fermer", callback_data="close")]])

    if not admins:
        return await pro.edit(
            "<b>Veuillez fournir des ID administrateur valides à supprimer.</b>\n\n"
            "<b>Utilisation :</b>\n"
            "<code>/deladmin [id_utilisateur]</code> — Supprimer des ID spécifiques\n"
            "<code>/deladmin all</code> — Supprimer tous les administrateurs",
            reply_markup=reply_markup
        )

    if len(admins) == 1 and admins[0].lower() == "all":
        if admin_ids:
            for id in admin_ids:
                await db.del_admin(id)
            ids = "\n".join(f"<blockquote><code>{admin}</code> ✅</blockquote>" for admin in admin_ids)
            return await pro.edit(f"<b>⛔️ Tous les ID administrateur ont été supprimés :</b>\n{ids}", reply_markup=reply_markup)
        else:
            return await pro.edit("<b><blockquote>Aucun ID administrateur à supprimer.</blockquote></b>", reply_markup=reply_markup)

    if admin_ids:
        passed = ''
        for admin_id in admins:
            try:
                id = int(admin_id)
            except:
                passed += f"<blockquote><b>ID invalide : <code>{admin_id}</code></b></blockquote>\n"
                continue

            if id in admin_ids:
                await db.del_admin(id)
                passed += f"<blockquote><code>{id}</code> ✅ Supprimé</blockquote>\n"
            else:
                passed += f"<blockquote><b>L'ID <code>{id}</code> n'a pas été trouvé dans la liste des administrateurs.</b></blockquote>\n"

        await pro.edit(f"<b>⛔️ Résultat de la suppression d'administrateur :</b>\n\n{passed}", reply_markup=reply_markup)
    else:
        await pro.edit("<b><blockquote>Aucun ID administrateur disponible à supprimer.</blockquote></b>", reply_markup=reply_markup)


@Bot.on_message(filters.command('admins') & filters.private & admin)
async def get_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>Veuillez patienter..</i></b>", quote=True)
    admin_ids = await db.get_all_admins()

    if not admin_ids:
        admin_list = "<b><blockquote>❌ Aucun administrateur trouvé.</blockquote></b>"
    else:
        admin_list = "\n".join(f"<b><blockquote>ID : <code>{id}</code></blockquote></b>" for id in admin_ids)

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Fermer", callback_data="close")]])
    await pro.edit(f"<b>⚡ Liste des administrateurs actuels :</b>\n\n{admin_list}", reply_markup=reply_markup)

# ─────────────────────────────────────────────────────────────────────────────
# COMMANDE /users — nombre total d'utilisateurs du bot
# ─────────────────────────────────────────────────────────────────────────────

@Bot.on_message(filters.command('users') & filters.private & admin)
async def users_command(client: Client, message: Message):
    pro = await message.reply("<b><i>Récupération en cours...</i></b>", quote=True)
    try:
        all_users = await db.full_userbase()
        total     = len(all_users)
        banned    = await db.get_ban_users()
        nb_banned = len(banned)

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Fermer", callback_data="close")]
        ])

        await pro.edit(
            f"<b>👥 Utilisateurs du bot</b>\n\n"
            f"<b>Total inscrits :</b> <code>{total:,}</code>\n"
            f"<b>Bannis :</b> <code>{nb_banned:,}</code>\n"
            f"<b>Actifs :</b> <code>{total - nb_banned:,}</code>",
            reply_markup=reply_markup
        )
    except Exception as e:
        await pro.edit(f"<b>Erreur :</b> <code>{e}</code>")
