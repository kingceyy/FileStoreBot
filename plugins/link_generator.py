#(©)Codexbotz

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from pyrogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from asyncio import TimeoutError
from helper_func import encode, get_message_id, admin
import re

async def extract_msg_id_from_link(client, link: str) -> int:
    """
    Extrait l'ID du message depuis un lien Telegram
    Retourne 0 si le lien est invalide ou ne correspond pas au canal DB
    """
    if not link:
        return 0
    
    # Pattern pour les liens : t.me/c/ID/MSG ou t.me/username/MSG
    pattern = r"https://t.me/(?:c/)?([^/]+)/(\d+)"
    match = re.match(pattern, link.strip())
    
    if not match:
        return 0
    
    channel_part = match.group(1)
    msg_id = int(match.group(2))
    
    # Récupérer l'ID du canal DB
    db_channel_id = client.db_channel.id if hasattr(client.db_channel, 'id') else client.db_channel
    
    # Vérifier si c'est le bon canal
    if channel_part.isdigit():
        # Canal privé : format c/123456789
        expected_id = f"-100{channel_part}"
        if expected_id != str(db_channel_id):
            return 0
    else:
        # Canal public : format @username
        # Si on a le username du canal DB, on vérifie
        if hasattr(client.db_channel, 'username') and client.db_channel.username:
            if channel_part.lower() != client.db_channel.username.lower():
                return 0
    
    return msg_id


@Bot.on_message(filters.private & admin & filters.command('batch'))
async def batch(client: Client, message: Message):
    """Nouveau format: /batch https://t.me/channel/123 https://t.me/channel/145"""
    
    if len(message.command) < 3:
        return await message.reply_text(
            "<b>❌ Format incorrect</b>\n\n"
            "<b>Usage:</b> <code>/batch [lien début] [lien fin]</code>\n\n"
            "<b>Exemple:</b>\n"
            "<code>/batch https://t.me/zeexclub/123 https://t.me/zeexclub/145</code>",
            quote=True
        )
    
    first_link = message.command[1]
    second_link = message.command[2]
    
    # Extraction des IDs
    f_msg_id = await extract_msg_id_from_link(client, first_link)
    s_msg_id = await extract_msg_id_from_link(client, second_link)
    
    if not f_msg_id:
        return await message.reply_text(
            "❌ <b>Erreur premier lien</b>\n\n"
            "Le lien ne provient pas de la chaîne de base de données ou est invalide.",
            quote=True
        )
    
    if not s_msg_id:
        return await message.reply_text(
            "❌ <b>Erreur deuxième lien</b>\n\n"
            "Le lien ne provient pas de la chaîne de base de données ou est invalide.",
            quote=True
        )
    
    if f_msg_id > s_msg_id:
        return await message.reply_text(
            "❌ <b>Erreur</b>\n\n"
            "Le premier message doit avoir un ID inférieur au dernier message.",
            quote=True
        )
    
    try:
        # Génération du lien
        channel_id = client.db_channel.id if hasattr(client.db_channel, 'id') else client.db_channel
        
        string = f"get-{f_msg_id * abs(channel_id)}-{s_msg_id * abs(channel_id)}"
        base64_string = await encode(string)
        link = f"https://t.me/{client.username}?start={base64_string}"
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Partager le lien", url=f'https://telegram.me/share/url?url={link}')]
        ])
        
        await message.reply_text(
            f"<b>✅ Lien batch généré</b>\n\n"
            f"<b>Début:</b> Message {f_msg_id}\n"
            f"<b>Fin:</b> Message {s_msg_id}\n"
            f"<b>Total:</b> {s_msg_id - f_msg_id + 1} fichiers\n\n"
            f"<code>{link}</code>",
            quote=True,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Erreur lors de la génération: {str(e)}", quote=True)


@Bot.on_message(filters.private & admin & filters.command('genlink'))
async def link_generator(client: Client, message: Message):
    """Nouveau format: /genlink https://t.me/channel/123"""
    
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Format incorrect</b>\n\n"
            "<b>Usage:</b> <code>/genlink [lien du message]</code>\n\n"
            "<b>Exemple:</b>\n"
            "<code>/genlink https://t.me/zeexclub/229</code>",
            quote=True
        )
    
    channel_message = message.command[1]
    
    # Extraction de l'ID
    msg_id = await extract_msg_id_from_link(client, channel_message)
    
    if not msg_id:
        return await message.reply_text(
            "❌ <b>Erreur</b>\n\n"
            "Ce lien ne provient pas de la chaîne de base de données ou est invalide.\n\n"
            f"<i>Assurez-vous que le lien vient bien du canal configuré (ID: {client.db_channel.id if hasattr(client.db_channel, 'id') else client.db_channel})</i>",
            quote=True
        )
    
    try:
        # Génération du lien
        channel_id = client.db_channel.id if hasattr(client.db_channel, 'id') else client.db_channel
        
        base64_string = await encode(f"get-{msg_id * abs(channel_id)}")
        link = f"https://t.me/{client.username}?start={base64_string}"
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Partager le lien", url=f'https://telegram.me/share/url?url={link}')]
        ])
        
        await message.reply_text(
            f"<b>✅ Lien généré</b>\n\n"
            f"<b>Message ID:</b> {msg_id}\n\n"
            f"<code>{link}</code>",
            quote=True,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Erreur lors de la génération: {str(e)}", quote=True)


@Bot.on_message(filters.private & admin & filters.command("custom_batch"))
async def custom_batch(client: Client, message: Message):
    """Celle-ci garde le système de collection car elle envoie les messages au canal"""
    collected = []
    STOP_KEYBOARD = ReplyKeyboardMarkup([["ARRÊTER"]], resize_keyboard=True)

    await message.reply(
        "Envoie tous les messages que tu souhaites inclure dans le lot.\n\n"
        "Appuie sur ARRÊTER quand tu as terminé.", 
        reply_markup=STOP_KEYBOARD
    )

    while True:
        try:
            user_msg = await client.ask(
                chat_id=message.chat.id,
                text="En attente de fichiers/messages...\nAppuie sur ARRÊTER pour terminer.",
                timeout=60
            )
        except TimeoutError:
            break

        if user_msg.text and user_msg.text.strip().upper() == "ARRÊTER":
            break

        try:
            target_chat = client.db_channel.id if hasattr(client.db_channel, 'id') else client.db_channel
            sent = await user_msg.copy(target_chat, disable_notification=True)
            collected.append(sent.id)
        except Exception as e:
            await message.reply(f"❌ Échec du stockage d'un message :\n<code>{e}</code>")
            continue

    await message.reply("✅ Collecte du lot terminée.", reply_markup=ReplyKeyboardRemove())

    if not collected:
        await message.reply("❌ Aucun message n'a été ajouté au lot.")
        return

    try:
        channel_id = client.db_channel.id if hasattr(client.db_channel, 'id') else client.db_channel
        
        start_id = collected[0] * abs(channel_id)
        end_id = collected[-1] * abs(channel_id)
        string = f"get-{start_id}-{end_id}"
        base64_string = await encode(string)
        link = f"https://t.me/{client.username}?start={base64_string}"

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Partager le lien", url=f'https://telegram.me/share/url?url={link}')]
        ])
        
        await message.reply(
            f"<b>Voici le lien de votre lot personnalisé :</b>\n\n"
            f"<code>{link}</code>", 
            reply_markup=reply_markup
        )
        
    except Exception as e:
        await message.reply(f"❌ Erreur lors de la génération du lien: {e}")
