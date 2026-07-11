# ==========================================
# plugins/cloned/start.py
# HANDLER /start POUR BOTS CLONÉS
# ==========================================

import asyncio
import base64
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from database.database import db
try:
    from config import ADSGRAM_WEBAPP_URL
except ImportError:
    ADSGRAM_WEBAPP_URL = None
try:
    from config import MOTHER_BOT_LINK
except ImportError:
    MOTHER_BOT_LINK = "https://t.me/ZeeXFileStoreBot"

# Nom court de la Mini App "Direct Link" enregistrée via @BotFather (/newapp)
# sur le bot mère. C'est celui utilisé dans https://t.me/<bot>/<CE_NOM>
MOTHER_BOT_APP_SHORTNAME = "app"


# ============================================================
# HELPERS
# ============================================================

async def get_clone_settings(bot_id: int) -> dict:
    """Récupère les paramètres personnalisés du bot cloné"""
    bot_data = await db.get_cloned_bot(bot_id)
    if bot_data:
        return bot_data.get('settings', {})
    return {}


async def build_start_keyboard(bot_id: int, bot_username: str) -> InlineKeyboardMarkup:
    """Construit le clavier de démarrage avec les boutons personnalisés"""
    settings = await get_clone_settings(bot_id)
    custom_buttons = settings.get('custom_buttons', [])

    keyboard = []

    # Boutons personnalisés du maître
    for btn in custom_buttons:
        keyboard.append([InlineKeyboardButton(btn['text'], url=btn['url'])])

    # Bouton vérifier session
    keyboard.append([InlineKeyboardButton("Ma session", callback_data="check_session")])

    # Bouton obligatoire vers bot mère
    try:
        from config import MOTHER_BOT_USERNAME as TG_BOT_USERNAME
        mother_bot = TG_BOT_USERNAME
    except ImportError:
        mother_bot = "ZeeXFileStoreBot"
    keyboard.append([InlineKeyboardButton(
        "Créer mon propre bot",
        url=f"https://t.me/{mother_bot}?start=clone"
    )])

    return InlineKeyboardMarkup(keyboard)


async def get_start_message(bot_id: int, user) -> str:
    """Récupère le message de démarrage personnalisé ou par défaut"""
    settings = await get_clone_settings(bot_id)
    custom_msg = settings.get('start_message')

    if custom_msg:
        try:
            return custom_msg.format(
                first=user.first_name,
                last=user.last_name or '',
                username=user.username or '',
                mention=user.mention,
                id=user.id
            )
        except Exception:
            return custom_msg

    return (
        f"<b>👋 Bienvenue, {user.first_name} !</b>\n\n"
        f"Ce bot vous permet de récupérer des fichiers.\n\n"
        f"<b>📺 Comment ça marche ?</b>\n"
        f"1. Recevez un lien de fichier\n"
        f"2. Cliquez sur le lien\n"
        f"3. Regardez une pub pour débloquer l'accès\n\n"
        f"<i>Propulsé par <a href='https://t.me/itz_Kingcey'>Kingcey</a></i>"
    )


async def get_start_photo(bot_id: int):
    """Récupère la photo de démarrage personnalisée ou None"""
    settings = await get_clone_settings(bot_id)
    return settings.get('start_photo')


async def decode(base64_string: str) -> str:
    """Décode une chaîne base64"""
    base64_string = base64_string.strip("=")
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes)
    return string_bytes.decode("ascii")


async def get_messages(client, channel_id, message_ids):
    """Récupère plusieurs messages d'un canal"""
    messages = []
    total_messages = 0
    while total_messages != len(message_ids):
        temp_ids = message_ids[total_messages:total_messages + 200]
        try:
            msgs = await client.get_messages(chat_id=channel_id, message_ids=temp_ids)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            msgs = await client.get_messages(chat_id=channel_id, message_ids=temp_ids)
        except Exception as e:
            print(f"[CLONE] Error getting messages: {e}")
            break
        total_messages += len(temp_ids)
        messages.extend(msgs)
    return messages


# ============================================================
# HANDLER /start
# ============================================================

@Client.on_message(filters.command('start') & filters.private)
async def cloned_start_handler(client: Client, message: Message):
    """Handler /start pour bots clonés"""
    bot_id = client.me.id
    bot_username = client.me.username
    user_id = message.from_user.id

    print(f"[CLONE DEBUG] ===== cloned_start_handler =====")
    print(f"[CLONE DEBUG] Bot ID: {bot_id}")
    print(f"[CLONE DEBUG] Bot Username: {bot_username}")
    print(f"[CLONE DEBUG] User ID: {user_id}")
    print(f"[CLONE DEBUG] Message text: {message.text}")

    # Enregistrer l'utilisateur dans la DB du bot cloné
    try:
        await db.add_bot_user(bot_id, user_id)
        print(f"[CLONE DEBUG] User {user_id} added to bot {bot_id}")
    except Exception as e:
        print(f"[CLONE DEBUG] Error adding user: {e}")

    # Vérifier si c'est un lien de fichier (argument après /start)
    args = message.text.split(" ", 1)
    if len(args) > 1 and args[1].strip():
        print(f"[CLONE DEBUG] Handling file link: {args[1].strip()}")
        await handle_file_link(client, message, args[1].strip())
        return

    # Message de démarrage normal
    print(f"[CLONE DEBUG] Sending normal start message")
    start_msg = await get_start_message(bot_id, message.from_user)
    start_photo = await get_start_photo(bot_id)
    keyboard = await build_start_keyboard(bot_id, bot_username)

    try:
        if start_photo:
            await message.reply_photo(
                photo=start_photo,
                caption=start_msg,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        else:
            await message.reply_text(
                start_msg,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
    except Exception as e:
        print(f"[CLONE {bot_id}] Error in start: {e}")
        await message.reply_text(
            "<b>👋 Bienvenue !</b>\n\nUtilisez les boutons ci-dessous.",
            reply_markup=keyboard
        )


# ============================================================
# GESTION DES LIENS DE FICHIERS
# ============================================================

async def handle_file_link(client: Client, message: Message, base64_string: str):
    """Gère les liens de fichiers pour les bots clonés"""
    bot_id = client.me.id
    user_id = message.from_user.id

    print(f"[CLONE DEBUG] ===== handle_file_link =====")
    print(f"[CLONE DEBUG] Bot ID: {bot_id}")
    print(f"[CLONE DEBUG] User ID: {user_id}")
    print(f"[CLONE DEBUG] Base64: {base64_string}")

    # Vérifier si l'utilisateur a une session active pour CE bot
    has_access = await db.has_active_session(user_id, bot_id)
    print(f"[CLONE DEBUG] has_active_session({user_id}, {bot_id}) = {has_access}")

    if not has_access:
        # Récupérer l'ID_PUBS du bot
        id_codes = await db.get_id_codes(bot_id=bot_id)
        id_pubs = id_codes['id_pubs'] if id_codes else None
        
        print(f"[CLONE DEBUG] ID_PUBS for bot {bot_id}: {id_pubs}")

        if not id_pubs:
            await message.reply_text(
                "❌ <b>Erreur de configuration</b>\n\n"
                "Ce bot n'a pas d'ID_PUBS configuré. Contactez le maître du bot.",
                parse_mode=ParseMode.HTML
            )
            return

        web_app_url = ADSGRAM_WEBAPP_URL or f"https://{client.me.username}.onrender.com"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "Regarder la publicité (Gratuit)",
                url=f"{MOTHER_BOT_LINK}/{MOTHER_BOT_APP_SHORTNAME}?startapp=adw_{bot_id}"
            )],
            [InlineKeyboardButton(
                "Voir les plans Premium",
                web_app=WebAppInfo(url=f"{web_app_url}/prime?id_pubs={id_pubs}&clone_id={bot_id}")
            )]
        ])

        try:
            free_duration = await db.get_free_session_duration()
        except Exception:
            free_duration = 30

        await message.reply_text(
            f"<b>Accès requis</b>\n\n"
            f"Vous n'avez pas de session active pour ce bot.\n\n"
            f"<b>Option gratuite</b> — Regardez une publicité pour {free_duration} minutes d'accès.\n"
            f"<b>Option Premium</b> — Accès illimité selon le plan choisi.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return

    # L'utilisateur a accès → récupérer le fichier
    try:
        string = await decode(base64_string)
        argument = string.split("-")

        # Récupérer le canal DB du bot cloné
        settings = await get_clone_settings(bot_id)
        channel_id = settings.get('channel_id')

        print(f"[CLONE DEBUG] Channel ID from settings: {channel_id}")

        if not channel_id:
            await message.reply_text(
                "<b>❌ Erreur:</b> Canal DB non configuré.\n"
                "Le maître du bot doit configurer un canal DB via /addchnl",
                parse_mode=ParseMode.HTML
            )
            return

        ids = []
        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(channel_id))
                end = int(int(argument[2]) / abs(channel_id))
                ids = list(range(start, end + 1)) if start <= end else list(range(start, end - 1, -1))
            except Exception as e:
                print(f"[CLONE] Error decoding IDs: {e}")
                return
        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(channel_id))]
            except Exception as e:
                print(f"[CLONE] Error decoding ID: {e}")
                return

        print(f"[CLONE DEBUG] Message IDs to fetch: {ids}")

        # Récupérer et envoyer les messages
        messages = await get_messages(client, channel_id, ids)
        print(f"[CLONE DEBUG] Retrieved {len(messages)} messages")

        for msg in messages:
            try:
                await msg.copy(chat_id=user_id)
                await db.increment_bot_stat(bot_id, 'total_files_sent')
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await msg.copy(chat_id=user_id)
            except Exception as e:
                print(f"[CLONE] Error sending message: {e}")

        # Afficher le temps restant + stats
        try:
            time_left = await db.get_session_time_left(user_id, bot_id)
            print(f"[CLONE DEBUG] Time left: {time_left}s")
            if time_left > 0:
                minutes = time_left // 60
                seconds = time_left % 60
                await message.reply_text(
                    f"<b>Fichiers envoyés</b>\n\n"
                    f"<b>Temps restant :</b> {minutes}m {seconds}s",
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            print(f"[CLONE DEBUG] Error showing time left: {e}")

        # Incrémenter stat fichiers
        try:
            await db.increment_bot_stat(bot_id, 'total_files_sent', len(messages))
        except Exception as e:
            print(f"[CLONE DEBUG] Error incrementing stats: {e}")

    except Exception as e:
        print(f"[CLONE] Error handling file link: {e}")
        import traceback
        traceback.print_exc()
        await message.reply_text(
            "<b>❌ Erreur lors de la récupération des fichiers.</b>",
            parse_mode=ParseMode.HTML
        )


# ============================================================
# CALLBACK - VÉRIFICATION SESSION
# ============================================================

@Client.on_callback_query(filters.regex("^check_session$"))
async def check_session_callback(client: Client, callback_query):
    """Vérifie la session de l'utilisateur"""
    bot_id = client.me.id
    user_id = callback_query.from_user.id

    print(f"[CLONE DEBUG] check_session_callback - Bot: {bot_id}, User: {user_id}")

    has_session = await db.has_active_session(user_id, bot_id)

    if has_session:
        time_left = await db.get_session_time_left(user_id, bot_id)
        minutes = time_left // 60
        seconds = time_left % 60

        await callback_query.message.edit_text(
            f"<b>Session active</b>\n\n"
            f"<b>Temps restant :</b> {minutes}m {seconds}s\n\n"
            "<i>Vous pouvez télécharger des fichiers librement.</i>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Actualiser", callback_data="check_session")],
                [InlineKeyboardButton("Fermer", callback_data="close")]
            ]),
            parse_mode=ParseMode.HTML
        )
    else:
        id_codes = await db.get_id_codes(bot_id=bot_id)
        id_pubs = id_codes['id_pubs'] if id_codes else 'N/A'
        web_app_url = ADSGRAM_WEBAPP_URL or f"https://{client.me.username}.onrender.com"

        await callback_query.message.edit_text(
            "<b>Aucune session active</b>\n\n"
            "Regardez une publicité pour obtenir un accès gratuit, ou choisissez un plan Premium.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "Regarder la publicité",
                    url=f"{MOTHER_BOT_LINK}/{MOTHER_BOT_APP_SHORTNAME}?startapp=adw_{bot_id}"
                )],
                [InlineKeyboardButton("Fermer", callback_data="close")]
            ]),
            parse_mode=ParseMode.HTML
        )

    await callback_query.answer()


# ============================================================
# CALLBACK - FERMER
# ============================================================

@Client.on_callback_query(filters.regex("^close$"))
async def close_callback(client: Client, callback_query):
    """Ferme le message"""
    try:
        await callback_query.message.delete()
    except Exception:
        pass
    await callback_query.answer()
