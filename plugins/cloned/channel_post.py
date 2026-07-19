# ==========================================
# plugins/cloned/channel_post.py
# AUTO-POST HANDLER POUR BOTS CLONÉS
# Quand le maître envoie un fichier en privé
# → le copie dans le canal DB → génère le lien
# ==========================================

import asyncio
import base64
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait


# ============================================================
# HELPERS
# ============================================================

async def encode(string: str) -> str:
    """Encode une chaîne en base64 URL-safe"""
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    return base64_bytes.decode("ascii").rstrip("=")


async def get_clone_settings(client, bot_id: int) -> dict:
    from database.database import db
    bot_data = await db.get_cloned_bot(bot_id)
    if bot_data:
        return bot_data.get('settings', {})
    return {}


def cloned_admin_filter():
    async def func(flt, client, message):
        if not message.from_user:
            return False
        from database.database import db
        user_id = message.from_user.id
        bot_id = client.me.id
        bot_data = await db.get_cloned_bot(bot_id)
        if not bot_data:
            return False
        master_id = bot_data.get('master_id') or bot_data.get('owner_id')
        if master_id and user_id == master_id:
            return True
        role = await db.get_user_bot_role(bot_id, user_id)
        if role in ['maitre', 'admin']:
            return True
        try:
            if await db.admin_exist(user_id):
                return True
        except Exception:
            pass
        return False
    return filters.create(func, name="ClonedAdminFilter")


cloned_admin = cloned_admin_filter()

# Commandes à exclure du handler auto-post
EXCLUDED_COMMANDS = [
    'start', 'genlink', 'batch', 'stats', 'users',
    'addchnl', 'delchnl', 'listchnl', 'fsub_mode',
    'addfsub', 'delfsub', 'broadcast', 'settings',
    'ban', 'unban', 'cancel', 'annuler',
    'add_admin', 'deladmin', 'admins', 'banlist',
    'dlt_time', 'check_dlt_time', 'pbroadcast',
    'dbroadcast', 'custom_batch'
]


# ============================================================
# HANDLER AUTO-POST
# ============================================================

@Client.on_message(
    filters.private & cloned_admin
    & ~filters.command(EXCLUDED_COMMANDS)
)
async def channel_post_handler(client: Client, message: Message):
    """
    Quand le maître envoie un fichier/message en privé au bot cloné,
    il est automatiquement copié dans le canal DB et un lien est généré.
    """
    bot_id = client.me.id
    settings = await get_clone_settings(client, bot_id)
    channel_id = settings.get('channel_id')

    if not channel_id:
        return await message.reply_text(
            "<b>⚠️ Canal DB non configuré !</b>\n\n"
            "Configurez d'abord le canal avec <code>/addchnl -100xxxxxxxxxx</code>",
            quote=True
        )

    reply_text = await message.reply_text("⏳ <b>Traitement...</b>", quote=True)

    try:
        post_message = await message.copy(
            chat_id=channel_id,
            disable_notification=True
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
        post_message = await message.copy(
            chat_id=channel_id,
            disable_notification=True
        )
    except Exception as e:
        return await reply_text.edit_text(
            f"<b>❌ Erreur lors de l'envoi au canal :</b>\n<code>{e}</code>"
        )

    # Générer le lien
    converted_id = post_message.id * abs(channel_id)
    string = f"get-{converted_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.me.username}?start={base64_string}"

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Partager le lien", url=f"https://telegram.me/share/url?url={link}")]
    ])

    await reply_text.edit(
        f"<b>✅ Lien généré !</b>\n\n"
        f"<code>{link}</code>",
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
