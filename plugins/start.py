import asyncio
import os
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, WebAppInfo
)
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from bot import Bot
from config import (
    BAN_SUPPORT, ADSGRAM_WEBAPP_URL, CUSTOM_CAPTION,
    PROTECT_CONTENT, DISABLE_CHANNEL_BUTTON, FSUB_LINK_EXPIRY,
    START_MSG, START_PIC, FORCE_MSG, FORCE_PIC,
    MOTHER_BOT_USERNAME, MOTHER_BOT_LINK
)
from helper_func import decode, get_exp_time, is_subscribed, is_sub, check_admin
from database.database import db

WEBAPP_URL = ADSGRAM_WEBAPP_URL or "https://waramugi.vercel.app"

admin = filters.create(check_admin)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS — ID du bot courant et ID_PUBS
# ─────────────────────────────────────────────────────────────────────────────

async def get_bot_id(client: Client) -> int:
    try:
        me = await client.get_me()
        cloned = await db.get_cloned_bot(me.id)
        return me.id if cloned else 0
    except Exception as e:
        print(f"[get_bot_id] Erreur: {e}")
        return 0


async def get_id_pubs_for_client(client: Client) -> str | None:
    try:
        me = await client.get_me()
        cloned = await db.get_cloned_bot(me.id)
        if cloned:
            id_data = await db.get_id_codes(bot_id=me.id)
            if id_data:
                return id_data["id_pubs"]
            print(f"[get_id_pubs] Bot cloné {me.id} sans ID_CODES !")
            return None
        return "YUMEFLOWER"
    except Exception as e:
        print(f"[get_id_pubs] Erreur: {e}")
        return None


def format_time_left(seconds: int) -> str:
    if seconds <= 0:
        return "Expirée"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}h {m}min"
    if m:
        return f"{m}min {s}s"
    return f"{s}s"


# ─────────────────────────────────────────────────────────────────────────────
# VÉRIFICATION D'ACCÈS — retourne (has_access, status_msg)
# ─────────────────────────────────────────────────────────────────────────────

async def check_user_access(client: Client, user_id: int, message: Message) -> tuple:
    bot_id = await get_bot_id(client)

    has_session = await db.has_active_session(user_id, bot_id)

    if has_session:
        time_left = await db.get_session_time_left(user_id, bot_id)
        if time_left > 0:
            session = await db.get_user_session(user_id, bot_id)
            type_label = "Premium" if session.get("type") == "premium" else "Gratuite"
            return True, f"Session {type_label} — {format_time_left(time_left)} restant"
        else:
            await db.deactivate_session(user_id, bot_id)

    # Pas de session — construire les boutons pour débloquer
    id_pubs = await get_id_pubs_for_client(client)
    if not id_pubs:
        await message.reply_text(
            "<b>Erreur de configuration</b>\n\n"
            "Ce bot n'a pas d'identifiant publicitaire configuré. "
            "Contactez le support.",
            parse_mode=ParseMode.HTML
        )
        return False, None

    # URL de la page principale avec id_pubs
    index_url = f"{WEBAPP_URL}/?id_pubs={id_pubs}&clone_id={bot_id}"
    prime_url  = f"{WEBAPP_URL}/prime?id_pubs={id_pubs}&clone_id={bot_id}"

    # Récupérer le lien du fichier pour permettre un retour facile
    orig_link = None
    try:
        if message.text and " " in message.text:
            b64 = message.text.split(" ", 1)[1]
            orig_link = f"https://t.me/{client.username}?start={b64}"
    except Exception:
        pass

    dur_min = await db.get_free_session_duration() if hasattr(db, "get_free_session_duration") else 10

    text = (
        "<b>Accès requis</b>\n\n"
        "Vous n'avez pas de session active pour accéder à ce fichier.\n\n"
        f"<b>Option gratuite</b> — Regardez une publicité pour {dur_min} minutes d'accès.\n"
        "<b>Option Premium</b> — Accès illimité selon le plan choisi."
    )

    if orig_link:
        text += (
            f"\n\n<blockquote>Une fois l'accès obtenu, "
            f"<a href='{orig_link}'>cliquez ici</a> pour récupérer votre fichier.</blockquote>"
        )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "Regarder la publicité (Gratuit)",
            web_app=WebAppInfo(url=index_url)
        )],
        [InlineKeyboardButton(
            "Voir les plans Premium",
            web_app=WebAppInfo(url=prime_url)
        )],
    ])

    try:
        await message.delete()
    except Exception:
        pass

    await client.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )
    return False, None


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS MÉDIAS
# ─────────────────────────────────────────────────────────────────────────────

async def determine_media_type(msg):
    if msg.video:    return ChatAction.UPLOAD_VIDEO
    if msg.document: return ChatAction.UPLOAD_DOCUMENT
    if msg.photo:    return ChatAction.UPLOAD_PHOTO
    if msg.audio:    return ChatAction.UPLOAD_AUDIO
    return ChatAction.TYPING


async def send_with_progress(client, message, msg):
    try:
        action = await determine_media_type(msg)
        await client.send_chat_action(message.chat.id, action)

        original_caption = msg.caption.html if msg.caption else ""
        caption = f"{original_caption}\n\n{CUSTOM_CAPTION}" if CUSTOM_CAPTION else original_caption

        sent_msg = await msg.copy(
            chat_id=message.from_user.id,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=msg.reply_markup if not DISABLE_CHANNEL_BUTTON else None,
            protect_content=PROTECT_CONTENT
        )
        await asyncio.sleep(0.9)
        return sent_msg
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await send_with_progress(client, message, msg)
    except Exception as e:
        print(f"[send_with_progress] Erreur: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# COMMANDE /start
# ─────────────────────────────────────────────────────────────────────────────

@Bot.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id

    # Vérification ban
    banned_users = await db.get_ban_users()
    if user_id in banned_users:
        return await message.reply_text(
            "<b>Accès banni</b>\n\n"
            "Votre compte a été banni de ce bot.\n"
            "Contactez le support si vous pensez qu'il s'agit d'une erreur.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Contacter le support", url=BAN_SUPPORT)]
            ])
        )

    # Vérification Force Sub
    if not await is_subscribed(client, user_id):
        return await not_joined(client, message)

    FILE_AUTO_DELETE = await db.get_del_timer()

    if not await db.present_user(user_id):
        try:
            await db.add_user(user_id)
        except Exception:
            pass

    text = message.text

    # Lien de fichier (base64)
    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
        except IndexError:
            return

        has_access, status_msg = await check_user_access(client, user_id, message)
        if not has_access:
            return

        string   = await decode(base64_string)
        argument = string.split("-")
        ids      = []

        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end   = int(int(argument[2]) / abs(client.db_channel.id))
                ids   = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))
            except Exception as e:
                print(f"[start] Erreur décodage IDs: {e}")
                return
        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            except Exception as e:
                print(f"[start] Erreur décodage ID: {e}")
                return

        temp_msg = await message.reply("<b>Préparation des fichiers...</b>")
        try:
            messages = await get_messages(client, ids)
        except Exception as e:
            await message.reply_text("<b>Erreur lors de la récupération des fichiers.</b>")
            print(f"[start] get_messages: {e}")
            return
        finally:
            await temp_msg.delete()

        sent_messages = []
        for msg in messages:
            sent_msg = await send_with_progress(client, message, msg)
            if sent_msg:
                sent_messages.append(sent_msg)

        # Auto-delete si configuré
        if FILE_AUTO_DELETE > 0 and sent_messages:
            notif = await message.reply(
                f"<b>Fichiers temporaires</b>\n\n"
                f"Ces fichiers seront supprimés dans <b>{get_exp_time(FILE_AUTO_DELETE)}</b>.\n"
                "Transférez-les dans vos sauvegardes avant la suppression."
            )
            await asyncio.sleep(FILE_AUTO_DELETE)

            for snt_msg in sent_messages:
                try:
                    await snt_msg.delete()
                except Exception:
                    pass

            try:
                reload_url = (
                    f"https://t.me/{client.username}?start={message.command[1]}"
                    if message.command and len(message.command) > 1 else None
                )
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Récupérer à nouveau", url=reload_url)]
                ]) if reload_url else None
                await notif.edit(
                    "<b>Fichiers supprimés</b>\n\n"
                    "Cliquez ci-dessous pour les récupérer à nouveau.",
                    reply_markup=keyboard
                )
            except Exception:
                pass

    # /start simple sans fichier
    else:
        id_pubs   = await get_id_pubs_for_client(client)
        index_url = f"{WEBAPP_URL}/?id_pubs={id_pubs}" if id_pubs else WEBAPP_URL
        prime_url = f"{WEBAPP_URL}/prime?id_pubs={id_pubs}" if id_pubs else f"{WEBAPP_URL}/prime"

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Obtenir un accès", web_app=WebAppInfo(url=index_url))],
            [InlineKeyboardButton("Plans Premium",    web_app=WebAppInfo(url=prime_url))],
            [
                InlineKeyboardButton("Ma session",       callback_data="check_session"),
                InlineKeyboardButton("Créer mon bot",    url=MOTHER_BOT_LINK),
            ],
            [
                InlineKeyboardButton("Aide",     callback_data="help"),
                InlineKeyboardButton("À propos", callback_data="about"),
            ],
        ])
        await message.reply_photo(
            photo=START_PIC,
            caption=START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name or "",
                username=f"@{message.from_user.username}" if message.from_user.username else "—",
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=reply_markup,
        )


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK — Aide et À propos
# ─────────────────────────────────────────────────────────────────────────────

@Bot.on_callback_query(filters.regex("^help$"))
async def help_callback(client: Client, callback_query: CallbackQuery):
    from config import HELP_TXT
    await callback_query.message.edit_text(
        HELP_TXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Retour", callback_data="start")]
        ])
    )
    await callback_query.answer()


@Bot.on_callback_query(filters.regex("^about$"))
async def about_callback(client: Client, callback_query: CallbackQuery):
    from config import ABOUT_TXT
    await callback_query.message.edit_text(
        ABOUT_TXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Retour",         callback_data="start")],
            [InlineKeyboardButton("Créer mon bot",  url=MOTHER_BOT_LINK)],
        ])
    )
    await callback_query.answer()


@Bot.on_callback_query(filters.regex("^start$"))
async def start_callback(client: Client, callback_query: CallbackQuery):
    from config import START_MSG, START_PIC
    user = callback_query.from_user
    id_pubs   = await get_id_pubs_for_client(client)
    index_url = f"{WEBAPP_URL}/?id_pubs={id_pubs}" if id_pubs else WEBAPP_URL
    prime_url = f"{WEBAPP_URL}/prime?id_pubs={id_pubs}" if id_pubs else f"{WEBAPP_URL}/prime"

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Obtenir un accès", web_app=WebAppInfo(url=index_url))],
        [InlineKeyboardButton("Plans Premium",    web_app=WebAppInfo(url=prime_url))],
        [
            InlineKeyboardButton("Ma session",    callback_data="check_session"),
            InlineKeyboardButton("Créer mon bot", url=MOTHER_BOT_LINK),
        ],
        [
            InlineKeyboardButton("Aide",     callback_data="help"),
            InlineKeyboardButton("À propos", callback_data="about"),
        ],
    ])
    try:
        await callback_query.message.edit_caption(
            caption=START_MSG.format(
                first=user.first_name,
                last=user.last_name or "",
                username=f"@{user.username}" if user.username else "—",
                mention=user.mention,
                id=user.id
            ),
            reply_markup=reply_markup
        )
    except Exception:
        pass
    await callback_query.answer()


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK — Ma session
# ─────────────────────────────────────────────────────────────────────────────

@Bot.on_callback_query(filters.regex("^check_session$"))
async def check_session_callback(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    try:
        me     = await client.get_me()
        cloned = await db.get_cloned_bot(me.id)
        bot_id = me.id if cloned else 0
    except Exception:
        bot_id = 0

    id_pubs   = await get_id_pubs_for_client(client)
    index_url = f"{WEBAPP_URL}/?id_pubs={id_pubs}" if id_pubs else WEBAPP_URL
    prime_url = f"{WEBAPP_URL}/prime?id_pubs={id_pubs}" if id_pubs else f"{WEBAPP_URL}/prime"

    has_session = await db.has_active_session(user_id, bot_id)

    if has_session:
        time_left = await db.get_session_time_left(user_id, bot_id)
        session   = await db.get_user_session(user_id, bot_id)
        type_label = "Premium" if session.get("type") == "premium" else "Gratuite"

        text = (
            f"<b>Session {type_label} active</b>\n\n"
            f"<b>Temps restant :</b> <code>{format_time_left(time_left)}</code>\n"
            f"<b>Expire le :</b> <code>{session['expires_at'][:19].replace('T', ' ')}</code>\n\n"
            "<i>Vous pouvez télécharger des fichiers librement durant cette période.</i>"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Actualiser",  callback_data="check_session")],
            [InlineKeyboardButton("Fermer",      callback_data="close")],
        ])
    else:
        dur_min = await db.get_free_session_duration() if hasattr(db, "get_free_session_duration") else 10
        text = (
            "<b>Aucune session active</b>\n\n"
            "Vous n'avez pas d'accès actif aux fichiers.\n\n"
            f"<b>Option gratuite</b> — Regardez une publicité pour {dur_min} minutes d'accès.\n"
            "<b>Option Premium</b> — Accès illimité selon le plan choisi."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Regarder la publicité", web_app=WebAppInfo(url=index_url))],
            [InlineKeyboardButton("Voir les plans Premium", web_app=WebAppInfo(url=prime_url))],
            [InlineKeyboardButton("Fermer", callback_data="close")],
        ])

    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Bot.on_callback_query(filters.regex("^close$"))
async def close_callback(client: Client, callback_query: CallbackQuery):
    try:
        await callback_query.message.delete()
    except Exception:
        pass
    await callback_query.answer()


# ─────────────────────────────────────────────────────────────────────────────
# COMMANDE /prime — donner session premium
# ─────────────────────────────────────────────────────────────────────────────

@Bot.on_message(filters.command("prime") & filters.private & admin)
async def give_premium_session(client: Client, message: Message):
    # Correspondance noms de plans → durée en secondes
    PLAN_DURATIONS = {
        "bronze":     7   * 86400,
        "argent":     30  * 86400,
        "or":         60  * 86400,
        "platine":    90  * 86400,
        "diamant":    180 * 86400,
        "adamantide": 365 * 86400,
        "1h":   3600,
        "1j":   86400,
        "7j":   7  * 86400,
        "30j":  30 * 86400,
    }
    args = message.command
    if len(args) < 2:
        return await message.reply_text(
            "<b>Utilisation</b>\n\n"
            "<code>/prime user_id plan [bot_id]</code>\n\n"
            "<b>Plans disponibles :</b>\n"
            "• <code>Bronze</code> — 7 jours\n"
            "• <code>Argent</code> — 30 jours\n"
            "• <code>Or</code> — 2 mois\n"
            "• <code>Platine</code> — 3 mois\n"
            "• <code>Diamant</code> — 6 mois\n"
            "• <code>Adamantide</code> — 1 an\n\n"
            "<b>Ou en secondes :</b> <code>/prime 123456 86400</code>",
            quote=True
        )
    try:
        user_id = int(args[1])
        # Résoudre la durée : nom de plan OU secondes (Bronze par défaut)
        if len(args) >= 3:
            raw = args[2].lower()
            if raw in PLAN_DURATIONS:
                duration  = PLAN_DURATIONS[raw]
                plan_name = raw.capitalize()
            else:
                duration  = int(raw)
                plan_name = None
        else:
            duration  = PLAN_DURATIONS["bronze"]
            plan_name = "Bronze"
        bot_id = int(args[3]) if len(args) >= 4 else 0

        await db.create_premium_session(user_id, duration, message.from_user.id, bot_id)

        expiry = datetime.now() + timedelta(seconds=duration)
        d = duration // 86400
        h = (duration % 86400) // 3600
        m = (duration % 3600) // 60
        bot_info = f" (Bot cloné ID: {bot_id})" if bot_id else " (Bot principal)"

        plan_line = f"<b>Plan :</b> {plan_name}\n" if plan_name else ""
        await message.reply_text(
            f"<b>Session Premium accordée</b>{bot_info}\n\n"
            f"<b>Utilisateur :</b> <code>{user_id}</code>\n"
            + plan_line +
            f"<b>Durée :</b> {d}j {h}h {m}m\n"
            f"<b>Expire le :</b> <code>{expiry.strftime('%d/%m/%Y %H:%M')}</code>",
            quote=True
        )
        try:
            await client.send_message(
                user_id,
                f"<b>Accès Premium accordé</b>\n\n"
                f"Vous avez reçu un accès Premium de la part d'un administrateur.\n\n"
                + plan_line +
                f"<b>Durée :</b> {d}j {h}h {m}m\n"
                f"<b>Expire le :</b> <code>{expiry.strftime('%d/%m/%Y %H:%M')}</code>\n\n"
                "Profitez de l'accès illimité sans publicités."
            )
        except Exception as e:
            await message.reply_text(f"Note : impossible de notifier l'utilisateur ({e})", quote=True)
    except ValueError:
        await message.reply_text("L'identifiant et la durée doivent être des nombres entiers.", quote=True)
    except Exception as e:
        await message.reply_text(f"Erreur : <code>{e}</code>", quote=True)


@Bot.on_message(filters.command("delprime") & filters.private & admin)
async def delete_premium_session(client: Client, message: Message):
    args = message.command
    if len(args) < 2:
        return await message.reply_text(
            "<b>Utilisation :</b> <code>/delprime user_id [bot_id]</code>",
            quote=True
        )
    try:
        user_id = int(args[1])
        bot_id  = int(args[2]) if len(args) >= 3 else 0

        session = await db.get_user_session(user_id, bot_id)
        if not session:
            return await message.reply_text(
                f"Aucune session trouvée pour l'utilisateur <code>{user_id}</code>.",
                quote=True
            )

        await db.remove_session(user_id, bot_id)
        await message.reply_text(
            f"<b>Session supprimée</b>\n\n"
            f"<b>Utilisateur :</b> <code>{user_id}</code>\n"
            f"<b>Type :</b> {session.get('type', '—').upper()}",
            quote=True
        )
        try:
            await client.send_message(
                user_id,
                "<b>Session révoquée</b>\n\n"
                "Votre accès a été révoqué par un administrateur.\n"
                "Regardez une publicité ou souscrivez à un plan Premium pour continuer."
            )
        except Exception:
            pass
    except ValueError:
        await message.reply_text("L'identifiant doit être un nombre entier.", quote=True)
    except Exception as e:
        await message.reply_text(f"Erreur : <code>{e}</code>", quote=True)


# ─────────────────────────────────────────────────────────────────────────────
# COMMANDE /broadcast
# ─────────────────────────────────────────────────────────────────────────────

@Bot.on_message(filters.command("broadcast") & filters.private & admin)
async def broadcast_message(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text(
            "<b>Utilisation incorrecte</b>\n\n"
            "Répondez à un message avec <code>/broadcast</code> pour le diffuser.",
            quote=True
        )

    target_msg  = message.reply_to_message
    all_users   = await db.full_userbase()
    total_users = len(all_users)

    if total_users == 0:
        return await message.reply_text("Aucun utilisateur dans la base de données.", quote=True)

    confirm_msg = await message.reply_text(
        f"<b>Diffusion en cours...</b>\n\n"
        f"<b>Destinataires :</b> {total_users}\n"
        f"<i>Envoi en cours...</i>",
        quote=True
    )

    sent = failed = blocked = 0

    for user_id in all_users:
        try:
            await target_msg.copy(user_id)
            sent += 1
            await asyncio.sleep(0.1)
        except UserIsBlocked:
            blocked += 1
        except InputUserDeactivated:
            blocked += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            try:
                await target_msg.copy(user_id)
                sent += 1
            except Exception:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"[broadcast] Erreur user {user_id}: {e}")

    await confirm_msg.edit_text(
        f"<b>Diffusion terminée</b>\n\n"
        f"<b>Envoyés :</b> {sent}\n"
        f"<b>Échoués :</b> {failed}\n"
        f"<b>Bloqués / Désactivés :</b> {blocked}\n"
        f"<b>Total :</b> {total_users}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# COMMANDE /commands
# ─────────────────────────────────────────────────────────────────────────────

@Bot.on_message(filters.command("commands") & filters.private & admin)
async def show_commands(client: Client, message: Message):
    from config import CMD_TXT
    await message.reply(
        CMD_TXT,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Fermer", callback_data="close")]]),
        quote=True
    )


# ─────────────────────────────────────────────────────────────────────────────
# FORCE SUB
# ─────────────────────────────────────────────────────────────────────────────

chat_data_cache = {}


async def not_joined(client: Client, message: Message):
    temp    = await message.reply("<b>Vérification en cours...</b>")
    user_id = message.from_user.id
    buttons = []

    try:
        all_channels = await db.show_channels()
        for chat_id in all_channels:
            mode = await db.get_channel_mode(chat_id)
            if not await is_sub(client, user_id, chat_id):
                try:
                    if chat_id in chat_data_cache:
                        data = chat_data_cache[chat_id]
                    else:
                        data = await client.get_chat(chat_id)
                        chat_data_cache[chat_id] = data

                    if mode == "on" and not data.username:
                        invite = await client.create_chat_invite_link(
                            chat_id=chat_id,
                            creates_join_request=True,
                            expire_date=(
                                datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY)
                                if FSUB_LINK_EXPIRY else None
                            )
                        )
                        link = invite.invite_link
                    else:
                        if data.username:
                            link = f"https://t.me/{data.username}"
                        else:
                            invite = await client.create_chat_invite_link(
                                chat_id=chat_id,
                                expire_date=(
                                    datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY)
                                    if FSUB_LINK_EXPIRY else None
                                )
                            )
                            link = invite.invite_link

                    buttons.append([InlineKeyboardButton(text=data.title, url=link)])
                except Exception as e:
                    print(f"[not_joined] Erreur canal {chat_id}: {e}")
                    return await temp.edit(
                        f"<b>Erreur technique</b>\n<code>{e}</code>"
                    )

        try:
            buttons.append([
                InlineKeyboardButton(
                    text="Vérifier à nouveau",
                    url=f"https://t.me/{client.username}?start={message.command[1]}"
                )
            ])
        except IndexError:
            pass

        await temp.delete()
        await message.reply_photo(
            photo=FORCE_PIC,
            caption=FORCE_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name or "",
                username=f"@{message.from_user.username}" if message.from_user.username else "—",
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception as e:
        print(f"[not_joined] Erreur finale: {e}")
        await temp.edit(f"<b>Erreur critique</b>\n<code>{e}</code>")
