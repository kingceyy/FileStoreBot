# ==========================================
# plugins/cloned/fsub_events.py
# ÉVÉNEMENTS FORCE-SUB (mode "on" / join-request) POUR BOTS CLONÉS
#
# Ces handlers sont nécessaires pour que le mode "on" (canaux où
# les membres ne sont acceptés que sur demande) fonctionne : ils
# suivent les demandes d'adhésion et les retirent une fois traitées.
# Sans ça, is_sub_clone() ne peut jamais confirmer qu'un utilisateur
# a bien demandé à rejoindre un canal en mode "on".
# ==========================================

from pyrogram import Client
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import ChatMemberUpdated
from database.database import db


@Client.on_chat_member_updated()
async def clone_handle_chat_members(client: Client, chat_member_updated: ChatMemberUpdated):
    chat_id = chat_member_updated.chat.id
    bot_id = client.me.id

    fsub_channels = await db.get_bot_fsub_channels(bot_id)
    if chat_id not in fsub_channels:
        return

    old_member = chat_member_updated.old_chat_member
    if not old_member:
        return

    if old_member.status == ChatMemberStatus.MEMBER:
        user_id = old_member.user.id
        if await db.req_user_exist(chat_id, user_id):
            await db.del_req_user(chat_id, user_id)


@Client.on_chat_join_request()
async def clone_handle_join_request(client: Client, chat_join_request):
    chat_id = chat_join_request.chat.id
    user_id = chat_join_request.from_user.id
    bot_id = client.me.id

    fsub_channels = await db.get_bot_fsub_channels(bot_id)
    if chat_id not in fsub_channels:
        return

    if not await db.req_user_exist(chat_id, user_id):
        await db.req_user(chat_id, user_id)
