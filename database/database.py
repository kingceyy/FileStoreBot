# Database module - MongoDB (Production / Render / VPS compatible)
# Original: MongoDB version by Codeflix_Botz/rohit_1888
# Modified + Extended: Full MongoDB version avec support bots clonés complet

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import logging
import secrets
import string
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

logging.basicConfig(level=logging.INFO)

# ==========================================
# CONFIGURATION MONGODB
# ==========================================

MONGO_URI = os.environ.get("DATABASE_URL", "mongodb+srv://elisabethboko45_db_user:kmrLKNKnfe8lK1df@cluster0.isv90ao.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = os.environ.get("DATABASE_NAME", "Cluster0")

class Rohit:
    def __init__(self):
        self.client = None
        self.db = None
        self._initialized = False

    async def init(self):
        """Initialize MongoDB connection"""
        if self._initialized:
            return

        try:
            self.client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.db = self.client[DB_NAME]

            # Test connection
            await self.client.admin.command('ping')

            # Create indexes (drop + recreate pour éviter conflits)
            await self._create_indexes()

            # Seed bot mère avec codes fixes
            await self._seed_mother_bot()

            self._initialized = True
            logging.info("[DB] MongoDB connected successfully")
        except Exception as e:
            logging.error(f"[DB] Error connecting to MongoDB: {e}")
            raise

    async def _seed_mother_bot(self):
        """Crée les codes fixes de la bot mère si absents"""
        try:
            existing = await self.db.id_codes.find_one({"bot_id": 0})
            if not existing:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                await self.db.id_codes.update_one(
                    {"bot_id": 0},
                    {"$set": {
                        "bot_id": 0,
                        "id_pubs": "YUMEFLOWER",
                        "id_code": "KINGCEY00",
                        "master_id": 0,
                        "is_mother_bot": True,
                        "created_at": now,
                        "updated_at": now
                    }},
                    upsert=True
                )
                logging.info("[DB] Bot mère seedée: ID_PUBS=YUMEFLOWER, ID_CODE=KINGCEY00")
        except Exception as e:
            logging.warning(f"[DB] Seed bot mère ignoré: {e}")

    async def _create_indexes(self):
        """
        Create indexes — drop les anciens d'abord pour éviter les conflits de nom.
        Nécessaire quand sparse=True a été ajouté après coup.
        """
        # ── STEP 1 : Supprimer les anciens index qui pourraient être en conflit ──
        _drops = [
            ("users",             "user_id_1"),
            ("cloned_bots",       "bot_id_1"),
            ("cloned_bots",       "bot_token_1"),
            ("bot_admins",        "bot_id_user_id_1"),
            ("id_codes",          "bot_id_1"),
            ("id_codes",          "id_pubs_1"),
            ("id_codes",          "id_code_1"),
            ("bot_users",         "bot_id_user_id_1"),
            ("bot_fsub_channels", "bot_id_channel_id_1"),
            ("sessions",          "session_id_1"),
            ("bot_earnings",      "bot_id_1"),
            ("bot_banned_users",  "bot_id_user_id_1"),
        ]
        for col_name, idx_name in _drops:
            try:
                await self.db[col_name].drop_index(idx_name)
                logging.info(f"[DB] Index dropped: {col_name}.{idx_name}")
            except Exception:
                pass  # n'existait pas ou déjà supprimé

        # ── STEP 2 : Recréer tous les index proprement ──
        try:
            # Users
            await self.db.users.create_index("user_id", unique=True, sparse=True)

            # Cloned bots
            await self.db.cloned_bots.create_index("bot_id", unique=True, sparse=True)
            await self.db.cloned_bots.create_index("master_id", sparse=True)
            await self.db.cloned_bots.create_index("bot_token", sparse=True)

            # Bot admins
            await self.db.bot_admins.create_index([("bot_id", ASCENDING), ("user_id", ASCENDING)], unique=True, sparse=True)
            await self.db.bot_admins.create_index("bot_id", sparse=True)

            # ID codes
            await self.db.id_codes.create_index("bot_id", unique=True, sparse=True)
            await self.db.id_codes.create_index("id_pubs", unique=True, sparse=True)
            await self.db.id_codes.create_index("id_code", unique=True, sparse=True)

            # Bot users
            await self.db.bot_users.create_index([("bot_id", ASCENDING), ("user_id", ASCENDING)], unique=True, sparse=True)

            # Bot fsub channels
            await self.db.bot_fsub_channels.create_index([("bot_id", ASCENDING), ("channel_id", ASCENDING)], unique=True, sparse=True)

            # Sessions
            await self.db.sessions.create_index("session_id", unique=True, sparse=True)
            await self.db.sessions.create_index([("user_id", ASCENDING), ("bot_id", ASCENDING)], sparse=True)
            await self.db.sessions.create_index("expires_at", sparse=True)

            # Bot earnings
            await self.db.bot_earnings.create_index("bot_id", unique=True, sparse=True)

            # Banned users per bot
            await self.db.bot_banned_users.create_index([("bot_id", ASCENDING), ("user_id", ASCENDING)], unique=True, sparse=True)

            logging.info("[DB] Tous les index créés avec succès")

        except Exception as e:
            logging.warning(f"[DB] Erreur création index (non bloquant): {e}")

    # ==========================================
    # USER DATA (bot mère)
    # ==========================================

    async def present_user(self, user_id: int) -> bool:
        if not self._initialized:
            await self.init()
        user = await self.db.users.find_one({"user_id": user_id})
        return user is not None

    async def add_user(self, user_id: int) -> None:
        if not self._initialized:
            await self.init()
        if not await self.present_user(user_id):
            await self.db.users.insert_one({
                "user_id": user_id,
                "joined_at": datetime.now(timezone.utc)
            })

    async def full_userbase(self) -> List[int]:
        if not self._initialized:
            await self.init()
        cursor = self.db.users.find({"user_id": {"$exists": True}}, {"user_id": 1})
        return [doc["user_id"] async for doc in cursor if "user_id" in doc]

    async def del_user(self, user_id: int) -> None:
        if not self._initialized:
            await self.init()
        await self.db.users.delete_one({"user_id": user_id})

    # ==========================================
    # ADMIN DATA
    # ==========================================

    async def admin_exist(self, admin_id: int) -> bool:
        if not self._initialized:
            await self.init()
        admin = await self.db.admins.find_one({"admin_id": admin_id})
        return admin is not None

    async def add_admin(self, admin_id: int) -> None:
        if not self._initialized:
            await self.init()
        if not await self.admin_exist(admin_id):
            await self.db.admins.insert_one({
                "admin_id": admin_id,
                "added_at": datetime.now(timezone.utc)
            })

    async def del_admin(self, admin_id: int) -> None:
        if not self._initialized:
            await self.init()
        await self.db.admins.delete_one({"admin_id": admin_id})

    async def get_all_admins(self) -> List[int]:
        if not self._initialized:
            await self.init()
        cursor = self.db.admins.find({}, {"admin_id": 1})
        return [doc["admin_id"] async for doc in cursor]

    # ==========================================
    # BAN USER DATA (Global)
    # ==========================================

    async def ban_user_exist(self, user_id: int) -> bool:
        if not self._initialized:
            await self.init()
        banned = await self.db.banned_users.find_one({"user_id": user_id})
        return banned is not None

    async def add_ban_user(self, user_id: int) -> None:
        if not self._initialized:
            await self.init()
        if not await self.ban_user_exist(user_id):
            await self.db.banned_users.insert_one({
                "user_id": user_id,
                "banned_at": datetime.now(timezone.utc)
            })

    async def del_ban_user(self, user_id: int) -> None:
        if not self._initialized:
            await self.init()
        await self.db.banned_users.delete_one({"user_id": user_id})

    async def get_ban_users(self) -> List[int]:
        if not self._initialized:
            await self.init()
        cursor = self.db.banned_users.find({"user_id": {"$exists": True}}, {"user_id": 1})
        return [doc["user_id"] async for doc in cursor if "user_id" in doc]

    # ==========================================
    # BAN USER DATA (Per Bot)
    # ==========================================

    async def ban_user_from_bot(self, bot_id: int, user_id: int, reason: str = "") -> bool:
        """Ban a user from a specific cloned bot"""
        if not self._initialized:
            await self.init()
        try:
            await self.db.bot_banned_users.update_one(
                {"bot_id": bot_id, "user_id": user_id},
                {
                    "$set": {
                        "bot_id": bot_id,
                        "user_id": user_id,
                        "reason": reason,
                        "banned_at": datetime.now(timezone.utc).isoformat()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logging.error(f"[DB] Error banning user: {e}")
            return False

    async def unban_user_from_bot(self, bot_id: int, user_id: int) -> bool:
        """Unban a user from a specific cloned bot"""
        if not self._initialized:
            await self.init()
        try:
            result = await self.db.bot_banned_users.delete_one({
                "bot_id": bot_id,
                "user_id": user_id
            })
            return result.deleted_count > 0
        except Exception as e:
            logging.error(f"[DB] Error unbanning user: {e}")
            return False

    async def is_user_banned_from_bot(self, bot_id: int, user_id: int) -> bool:
        """Check if a user is banned from a specific bot"""
        if not self._initialized:
            await self.init()
        banned = await self.db.bot_banned_users.find_one({
            "bot_id": bot_id,
            "user_id": user_id
        })
        return banned is not None

    async def get_banned_users(self, bot_id: int) -> List[Dict]:
        """Get list of banned users for a bot"""
        if not self._initialized:
            await self.init()
        cursor = self.db.bot_banned_users.find({"bot_id": bot_id})
        return [{
            "user_id": doc["user_id"],
            "reason": doc.get("reason", ""),
            "banned_at": doc.get("banned_at", "")
        } async for doc in cursor]

    # ==========================================
    # AUTO DELETE TIMER SETTINGS
    # ==========================================

    async def set_del_timer(self, value: int) -> None:
        if not self._initialized:
            await self.init()
        await self.db.config.update_one(
            {"id": "del_timer"},
            {"$set": {"value": value}},
            upsert=True
        )

    async def get_del_timer(self) -> int:
        if not self._initialized:
            await self.init()
        doc = await self.db.config.find_one({"id": "del_timer"})
        return doc.get("value", 0) if doc else 0

    # ==========================================
    # CHANNEL MANAGEMENT (bot mère - force sub global)
    # ==========================================

    async def channel_exist(self, channel_id: int) -> bool:
        if not self._initialized:
            await self.init()
        channel = await self.db.channels.find_one({"channel_id": channel_id})
        return channel is not None

    async def add_channel(self, channel_id: int, mode: str = "off") -> None:
        if not self._initialized:
            await self.init()
        if not await self.channel_exist(channel_id):
            await self.db.channels.insert_one({
                "channel_id": channel_id,
                "mode": mode,
                "added_at": datetime.now(timezone.utc)
            })

    async def rem_channel(self, channel_id: int) -> None:
        if not self._initialized:
            await self.init()
        await self.db.channels.delete_one({"channel_id": channel_id})

    async def del_channel(self, channel_id: int) -> None:
        """Alias de rem_channel pour compatibilité"""
        await self.rem_channel(channel_id)

    async def show_channels(self) -> List[int]:
        if not self._initialized:
            await self.init()
        cursor = self.db.channels.find({}, {"channel_id": 1})
        return [doc["channel_id"] async for doc in cursor]

    async def get_channel_mode(self, channel_id: int) -> str:
        if not self._initialized:
            await self.init()
        channel = await self.db.channels.find_one({"channel_id": channel_id})
        return channel.get("mode", "off") if channel else "off"

    async def set_channel_mode(self, channel_id: int, mode: str) -> None:
        if not self._initialized:
            await self.init()
        await self.db.channels.update_one(
            {"channel_id": channel_id},
            {"$set": {"mode": mode}},
            upsert=True
        )

    # ==========================================
    # REQUEST FORCE-SUB MANAGEMENT
    # ==========================================

    async def req_user(self, channel_id: int, user_id: int) -> None:
        if not self._initialized:
            await self.init()
        await self.db.request_fsub.update_one(
            {"channel_id": channel_id},
            {"$addToSet": {"user_ids": user_id}},
            upsert=True
        )

    async def del_req_user(self, channel_id: int, user_id: int) -> None:
        if not self._initialized:
            await self.init()
        await self.db.request_fsub.update_one(
            {"channel_id": channel_id},
            {"$pull": {"user_ids": user_id}}
        )

    async def req_user_exist(self, channel_id: int, user_id: int) -> bool:
        if not self._initialized:
            await self.init()
        doc = await self.db.request_fsub.find_one({
            "channel_id": channel_id,
            "user_ids": {"$in": [user_id]}
        })
        return doc is not None

    async def reqChannel_exist(self, channel_id: int) -> bool:
        return await self.channel_exist(channel_id)

    # ==========================================
    # SESSIONS MANAGEMENT
    # ==========================================

    async def get_user_session(self, user_id: int, bot_id: int = None) -> Optional[Dict]:
        """
        Récupère la session d'un utilisateur POUR UN BOT SPÉCIFIQUE.
        session_id = "{user_id}_{bot_id}" — une session par bot par utilisateur.
        bot_id=0 = bot mère YUMEFLOWER.
        """
        if not self._initialized:
            await self.init()
        bot_id = bot_id if bot_id is not None else 0
        session_id = f"{user_id}_{bot_id}"
        
        logging.info(f"[DB DEBUG] get_user_session - Looking for session_id: {session_id}")
        
        session = await self.db.sessions.find_one({"session_id": session_id})
        if session:
            session["_id"] = str(session["_id"])
            logging.info(f"[DB DEBUG] Session found: {session}")
        else:
            logging.info(f"[DB DEBUG] No session found for {session_id}")
        return session

    async def create_free_session(self, user_id: int, duration_minutes: int = 10, bot_id: int = None) -> Dict:
        """
        Crée une session gratuite pour ce bot spécifique.
        session_id = "{user_id}_{bot_id}" — une session par bot par utilisateur.
        bot_id=0 = bot mère YUMEFLOWER.
        """
        if not self._initialized:
            await self.init()
        bot_id = bot_id if bot_id is not None else 0
        now = datetime.now(timezone.utc)
        expiry_time = now + timedelta(minutes=duration_minutes)
        session_id = f"{user_id}_{bot_id}"

        session_doc = {
            "session_id": session_id,
            "user_id": user_id,
            "bot_id": bot_id,  # conservé pour tracking gains
            "type": "free",
            "is_active": True,
            "created_at": now,
            "expires_at": expiry_time,
            "last_ad_watch": now
        }

        await self.db.sessions.update_one(
            {"session_id": session_id},
            {"$set": session_doc},
            upsert=True
        )

        logging.info(f"[DB] Session créée: {session_id} pour bot {bot_id}, expire à {expiry_time}")
        return {
            "_id": session_id,
            "user_id": user_id,
            "bot_id": bot_id,
            "type": "free",
            "is_active": True,
            "created_at": now.isoformat(),
            "expires_at": expiry_time.isoformat()
        }

    async def create_premium_session(self, user_id: int, duration_seconds: int, admin_id: int = None, bot_id: int = None) -> Dict:
        if not self._initialized:
            await self.init()
        now = datetime.now(timezone.utc)
        expiry_time = now + timedelta(seconds=duration_seconds)
        bot_id = bot_id if bot_id is not None else 0
        session_id = f"{user_id}_{bot_id}"  # session par bot

        session_doc = {
            "session_id": session_id,
            "user_id": user_id,
            "bot_id": bot_id,
            "type": "premium",
            "is_active": True,
            "created_at": now,
            "expires_at": expiry_time,
            "granted_by": admin_id,
            "payment_method": "manual" if admin_id else "crypto"
        }

        await self.db.sessions.update_one(
            {"session_id": session_id},
            {"$set": session_doc},
            upsert=True
        )

        logging.info(f"[DB] Session premium créée: {session_id} pour bot {bot_id}")
        return {
            "_id": session_id,
            "user_id": user_id,
            "bot_id": bot_id,
            "type": "premium",
            "is_active": True,
            "created_at": now.isoformat(),
            "expires_at": expiry_time.isoformat()
        }

    async def set_free_session(self, user_id: int, duration_hours: int = 20) -> None:
        await self.create_free_session(user_id, duration_hours * 60)

    async def has_active_session(self, user_id: int, bot_id: int = None) -> bool:
        if not self._initialized:
            await self.init()
        bot_id = bot_id if bot_id is not None else 0
        session_id = f"{user_id}_{bot_id}"
        
        logging.info(f"[DB DEBUG] has_active_session - Checking {session_id}")
        
        session = await self.get_user_session(user_id, bot_id)
        if not session or not session.get("is_active"):
            logging.info(f"[DB DEBUG] No active session for {session_id}")
            return False

        try:
            expiry = session.get("expires_at")
            if isinstance(expiry, str):
                expiry = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
            
            # ✅ FIX : forcer UTC si MongoDB retourne un datetime sans timezone
            if expiry is not None and expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            
            if now > expiry:
                logging.info(f"[DB DEBUG] Session expired for {session_id}")
                await self.deactivate_session(user_id, bot_id)
                return False
            
            logging.info(f"[DB DEBUG] Session active for {session_id}")
            return True
        except Exception as e:
            logging.error(f"[DB DEBUG] Error checking session {session_id}: {e}")
            return False

    async def deactivate_session(self, user_id: int, bot_id: int = None) -> None:
        if not self._initialized:
            await self.init()
        bot_id = bot_id if bot_id is not None else 0
        session_id = f"{user_id}_{bot_id}"
        await self.db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"is_active": False}}
        )
        logging.info(f"[DB] Session deactivated: {session_id}")

    async def remove_session(self, user_id: int, bot_id: int = None) -> None:
        if not self._initialized:
            await self.init()
        bot_id = bot_id if bot_id is not None else 0
        session_id = f"{user_id}_{bot_id}"
        await self.db.sessions.delete_one({"session_id": session_id})
        logging.info(f"[DB] Session removed: {session_id}")

    async def get_session_time_left(self, user_id: int, bot_id: int = None) -> int:
        if not self._initialized:
            await self.init()
        session = await self.get_user_session(user_id, bot_id)  # par bot
        if not session or not session.get("is_active"):
            return 0

        try:
            expiry = session.get("expires_at")
            if isinstance(expiry, str):
                expiry = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
            
            # ✅ FIX : forcer UTC si MongoDB retourne un datetime sans timezone
            if expiry is not None and expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            remaining = (expiry - now).total_seconds()
            return max(0, int(remaining))
        except Exception as e:
            logging.error(f"[ERROR] Erreur calcul temps restant: {e}")
            return 0

    async def can_watch_ad(self, user_id: int) -> bool:
        return True

    async def force_reset_ad_timer(self, user_id: int) -> None:
        if not self._initialized:
            await self.init()
        session_id = str(user_id)
        await self.db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"last_ad_watch": None}}
        )

    # ==========================================
    # ADMIN CONFIGURATION
    # ==========================================

    async def set_free_session_duration(self, minutes: int) -> None:
        if not self._initialized:
            await self.init()
        await self.db.config.update_one(
            {"id": "settings"},
            {"$set": {"free_session_duration": minutes}},
            upsert=True
        )

    async def get_free_session_duration(self) -> int:
        if not self._initialized:
            await self.init()
        doc = await self.db.config.find_one({"id": "settings"})
        return doc.get("free_session_duration", 10) if doc else 10

    async def get_bot_session_duration(self, bot_id: int) -> int:
        """
        Retourne la duree de session pour un bot specifique.
        Priorite : session_duration dans cloned_bots > config globale.
        Pour le bot mere (bot_id=0), retourne la config globale.
        """
        if bot_id == 0:
            return await self.get_free_session_duration()
        if not self._initialized:
            await self.init()
        bot = await self.db.cloned_bots.find_one({"bot_id": bot_id}, {"session_duration": 1})
        if bot and bot.get("session_duration"):
            return int(bot["session_duration"])
        return await self.get_free_session_duration()

    # ==========================================
    # SYSTÈME DE CLONAGE - BOTS CLONÉS
    # ==========================================

    def generate_unique_id(self, length: int = 10) -> str:
        alphabet = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    async def count_user_cloned_bots(self, master_id: int) -> int:
        """Compte le nombre de bots clonés par un utilisateur"""
        if not self._initialized:
            await self.init()
        return await self.db.cloned_bots.count_documents({"master_id": master_id})

    async def create_cloned_bot(self, bot_token: str, master_id: int, bot_username: str,
                                bot_id: int, api_id: int = None, api_hash: str = None) -> Dict:
        if not self._initialized:
            await self.init()
        
        # ✅ Pas de limite de clones

        now = datetime.now(timezone.utc)

        id_pubs = self.generate_unique_id(12)
        id_code = self.generate_unique_id(16)

        bot_data = {
            "bot_id": bot_id,
            "bot_token": bot_token,
            "bot_username": bot_username,
            "master_id": master_id,
            "created_at": now,
            "is_active": True,
            "settings": {
                "start_message": None,
                "start_photo": None,
                "custom_buttons": [],
                "channel_id": None,
                "force_sub_channels": []
            },
            "stats": {
                "total_users": 0,
                "total_files_sent": 0,
                "total_ads_watched": 0
            }
        }

        # ✅ FIX duplicate key : upsert au lieu de insert pour éviter E11000
        await self.db.cloned_bots.update_one(
            {"bot_id": bot_id},
            {"$set": bot_data},
            upsert=True
        )

        await self.db.id_codes.update_one(
            {"bot_id": bot_id},
            {"$setOnInsert": {
                "bot_id": bot_id,
                "id_pubs": id_pubs,
                "id_code": id_code,
                "master_id": master_id,
                "created_at": now,
                "updated_at": now
            }},
            upsert=True
        )

        await self.db.bot_earnings.update_one(
            {"bot_id": bot_id},
            {"$setOnInsert": {
                "bot_id": bot_id,
                "balance": 0.0,
                "total_earned": 0.0,
                "total_withdrawn": 0.0,
                "transactions": [],
                "master_id": master_id
            }},
            upsert=True
        )

        await self.add_bot_admin(bot_id, master_id, "maitre", master_id)

        return {
            "bot_data": bot_data,
            "id_pubs": id_pubs,
            "id_code": id_code
        }

    async def get_cloned_bot(self, bot_id: int) -> Optional[Dict]:
        if not self._initialized:
            await self.init()
        bot = await self.db.cloned_bots.find_one({"bot_id": bot_id})
        if bot:
            bot["_id"] = str(bot["_id"])
            # Convert datetime objects to ISO format strings for compatibility
            if isinstance(bot.get("created_at"), datetime):
                bot["created_at"] = bot["created_at"].isoformat()
        return bot

    async def get_cloned_bot_by_token(self, bot_token: str) -> Optional[Dict]:
        if not self._initialized:
            await self.init()
        bot = await self.db.cloned_bots.find_one({"bot_token": bot_token})
        if bot:
            bot["_id"] = str(bot["_id"])
            if isinstance(bot.get("created_at"), datetime):
                bot["created_at"] = bot["created_at"].isoformat()
        return bot

    async def get_all_cloned_bots(self, master_id: int = None) -> List[Dict]:
        if not self._initialized:
            await self.init()
        
        query = {}
        if master_id:
            query["master_id"] = master_id
        
        cursor = self.db.cloned_bots.find(query)
        bots = []
        async for bot in cursor:
            bot["_id"] = str(bot["_id"])
            if isinstance(bot.get("created_at"), datetime):
                bot["created_at"] = bot["created_at"].isoformat()
            bots.append(bot)
        return bots

    async def update_bot_settings(self, bot_id: int, updates: Dict) -> bool:
        """
        Met à jour les settings d'un bot cloné en FUSIONNANT avec l'existant.
        """
        if not self._initialized:
            await self.init()

        set_fields = {}
        
        # Colonne racine is_active
        if "is_active" in updates:
            set_fields["is_active"] = updates["is_active"]

        # Remplacement complet du JSON settings
        if "settings" in updates:
            set_fields["settings"] = updates["settings"]

        # Toutes les autres clés → fusion dans le JSON settings
        settings_keys = {k: v for k, v in updates.items() if k not in ("is_active", "settings")}
        if settings_keys:
            # Use $set with dot notation for nested fields
            for key, value in settings_keys.items():
                set_fields[f"settings.{key}"] = value

        if set_fields:
            await self.db.cloned_bots.update_one(
                {"bot_id": bot_id},
                {"$set": set_fields}
            )
        
        return True

    async def update_cloned_bot(self, bot_id: int, updates: Dict) -> bool:
        """Alias de update_bot_settings pour compatibilité"""
        return await self.update_bot_settings(bot_id, updates)

    async def delete_cloned_bot(self, bot_id: int) -> bool:
        if not self._initialized:
            await self.init()
        
        await self.db.cloned_bots.delete_one({"bot_id": bot_id})
        await self.db.id_codes.delete_one({"bot_id": bot_id})
        await self.db.bot_earnings.delete_one({"bot_id": bot_id})
        await self.db.bot_admins.delete_many({"bot_id": bot_id})
        await self.db.bot_users.delete_many({"bot_id": bot_id})
        await self.db.bot_fsub_channels.delete_many({"bot_id": bot_id})
        await self.db.bot_banned_users.delete_many({"bot_id": bot_id})
        
        return True

    async def regenerate_id_code(self, bot_id: int, master_id: int) -> Optional[Dict]:
        if not self._initialized:
            await self.init()
        
        bot = await self.get_cloned_bot(bot_id)
        if not bot or bot["master_id"] != master_id:
            return None

        new_id_pubs = self.generate_unique_id(12)
        new_id_code = self.generate_unique_id(16)

        await self.db.id_codes.update_one(
            {"bot_id": bot_id},
            {"$set": {
                "id_pubs": new_id_pubs,
                "id_code": new_id_code,
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        return {
            "id_pubs": new_id_pubs,
            "id_code": new_id_code
        }

    # ==========================================
    # SYSTÈME DE CLONAGE - ADMINS DE BOT
    # ==========================================

    async def add_bot_admin(self, bot_id: int, user_id: int, role: str, added_by: int) -> bool:
        if role not in ["maitre", "admin"]:
            return False
        
        if not self._initialized:
            await self.init()

        await self.db.bot_admins.update_one(
            {"bot_id": bot_id, "user_id": user_id},
            {"$set": {
                "role": role,
                "added_by": added_by,
                "added_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        return True

    async def remove_bot_admin(self, bot_id: int, user_id: int) -> bool:
        if not self._initialized:
            await self.init()
        result = await self.db.bot_admins.delete_one({"bot_id": bot_id, "user_id": user_id})
        return result.deleted_count > 0

    async def get_bot_admins(self, bot_id: int) -> List[Dict]:
        if not self._initialized:
            await self.init()
        cursor = self.db.bot_admins.find({"bot_id": bot_id})
        return [{
            "bot_id": doc["bot_id"],
            "user_id": doc["user_id"],
            "role": doc["role"],
            "added_by": doc.get("added_by"),
            "added_at": doc.get("added_at")
        } async for doc in cursor]

    async def get_user_bot_role(self, bot_id: int, user_id: int) -> Optional[str]:
        if not self._initialized:
            await self.init()
        admin = await self.db.bot_admins.find_one({"bot_id": bot_id, "user_id": user_id})
        return admin.get("role") if admin else None

    async def is_bot_admin(self, bot_id: int, user_id: int) -> bool:
        if not self._initialized:
            await self.init()
        admin = await self.db.bot_admins.find_one({"bot_id": bot_id, "user_id": user_id})
        return admin is not None

    async def is_bot_master(self, bot_id: int, user_id: int) -> bool:
        bot = await self.get_cloned_bot(bot_id)
        if bot and bot.get("master_id") == user_id:
            return True
        
        role = await self.get_user_bot_role(bot_id, user_id)
        return role == "maitre"

    # ==========================================
    # SYSTÈME DE CLONAGE - ID CODES
    # ==========================================

    async def get_id_codes(self, bot_id: int = None, id_pubs: str = None, id_code: str = None) -> Optional[Dict]:
        if not self._initialized:
            await self.init()
        
        query = {}
        if bot_id is not None:
            query["bot_id"] = bot_id
        if id_pubs:
            query["id_pubs"] = id_pubs.upper()
        if id_code:
            query["id_code"] = id_code.upper()
        
        logging.info(f"[DB DEBUG] get_id_codes - Query: {query}")
        
        codes = await self.db.id_codes.find_one(query)
        if codes:
            codes["_id"] = str(codes["_id"])
            if isinstance(codes.get("created_at"), datetime):
                codes["created_at"] = codes["created_at"].isoformat()
            if isinstance(codes.get("updated_at"), datetime):
                codes["updated_at"] = codes["updated_at"].isoformat()
            logging.info(f"[DB DEBUG] get_id_codes - Found: {codes}")
        else:
            logging.info(f"[DB DEBUG] get_id_codes - Not found for query: {query}")
        return codes

    async def get_bot_by_id_pubs(self, id_pubs: str) -> Optional[Dict]:
        if not self._initialized:
            await self.init()
        id_data = await self.get_id_codes(id_pubs=id_pubs)
        if id_data:
            return await self.get_cloned_bot(id_data["bot_id"])
        return None

    # ==========================================
    # UTILISATEURS PAR BOT CLONÉ
    # ==========================================

    async def add_bot_user(self, bot_id: int, user_id: int) -> None:
        """Enregistre un utilisateur pour un bot cloné spécifique"""
        if not self._initialized:
            await self.init()
        
        await self.db.bot_users.update_one(
            {"bot_id": bot_id, "user_id": user_id},
            {"$set": {
                "joined_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        
        # Incrémenter le compteur total_users dans les stats du bot
        await self.increment_bot_stat(bot_id, "total_users")

    async def get_bot_users(self, bot_id: int) -> List[Dict]:
        """Récupère tous les utilisateurs d'un bot cloné"""
        if not self._initialized:
            await self.init()
        cursor = self.db.bot_users.find({"bot_id": bot_id})
        return [{
            "user_id": doc["user_id"],
            "joined_at": doc.get("joined_at")
        } async for doc in cursor]

    async def bot_user_exists(self, bot_id: int, user_id: int) -> bool:
        """Vérifie si un utilisateur est déjà enregistré pour un bot cloné"""
        if not self._initialized:
            await self.init()
        user = await self.db.bot_users.find_one({"bot_id": bot_id, "user_id": user_id})
        return user is not None

    async def count_bot_users(self, bot_id: int) -> int:
        """Compte le nombre d'utilisateurs d'un bot cloné"""
        if not self._initialized:
            await self.init()
        return await self.db.bot_users.count_documents({"bot_id": bot_id})

    # ==========================================
    # CANAUX FORCE-SUB PAR BOT CLONÉ
    # ==========================================

    async def add_bot_fsub_channel(self, bot_id: int, channel_id: int, mode: str = "off") -> bool:
        """Ajoute un canal force-sub à un bot cloné"""
        if not self._initialized:
            await self.init()
        
        try:
            await self.db.bot_fsub_channels.update_one(
                {"bot_id": bot_id, "channel_id": channel_id},
                {"$set": {
                    "mode": mode,
                    "added_at": datetime.now(timezone.utc)
                }},
                upsert=True
            )
            return True
        except Exception as e:
            logging.error(f"[DB] add_bot_fsub_channel error: {e}")
            return False

    async def del_bot_fsub_channel(self, bot_id: int, channel_id: int) -> bool:
        """Supprime un canal force-sub d'un bot cloné"""
        if not self._initialized:
            await self.init()
        
        try:
            result = await self.db.bot_fsub_channels.delete_one({
                "bot_id": bot_id,
                "channel_id": channel_id
            })
            return result.deleted_count > 0
        except Exception as e:
            logging.error(f"[DB] del_bot_fsub_channel error: {e}")
            return False

    async def get_bot_fsub_channels(self, bot_id: int) -> List[int]:
        """Récupère la liste des IDs des canaux force-sub d'un bot cloné"""
        if not self._initialized:
            await self.init()
        cursor = self.db.bot_fsub_channels.find({"bot_id": bot_id})
        return [doc["channel_id"] async for doc in cursor]

    async def get_bot_channel_mode(self, bot_id: int, channel_id: int) -> str:
        """Récupère le mode force-sub (on/off) d'un canal pour un bot cloné"""
        if not self._initialized:
            await self.init()
        channel = await self.db.bot_fsub_channels.find_one({
            "bot_id": bot_id,
            "channel_id": channel_id
        })
        return channel.get("mode", "off") if channel else "off"

    async def set_bot_channel_mode(self, bot_id: int, channel_id: int, mode: str) -> bool:
        """Définit le mode force-sub (on/off) d'un canal pour un bot cloné"""
        if not self._initialized:
            await self.init()
        
        try:
            await self.db.bot_fsub_channels.update_one(
                {"bot_id": bot_id, "channel_id": channel_id},
                {"$set": {"mode": mode}},
                upsert=True
            )
            return True
        except Exception as e:
            logging.error(f"[DB] set_bot_channel_mode error: {e}")
            return False

    async def bot_fsub_channel_exists(self, bot_id: int, channel_id: int) -> bool:
        """Vérifie si un canal force-sub est configuré pour un bot cloné"""
        if not self._initialized:
            await self.init()
        channel = await self.db.bot_fsub_channels.find_one({
            "bot_id": bot_id,
            "channel_id": channel_id
        })
        return channel is not None

    # ==========================================
    # SYSTÈME DE CLONAGE - GAINS ET RETRAITS
    # ==========================================

    async def add_earning(self, bot_id: int, amount: float, source: str = "ad_impression") -> bool:
        if not self._initialized:
            await self.init()
        
        transaction = {
            "type": "earning",
            "amount": amount,
            "source": source,
            "timestamp": datetime.now(timezone.utc)
        }

        await self.db.bot_earnings.update_one(
            {"bot_id": bot_id},
            {
                "$inc": {
                    "balance": amount,
                    "total_earned": amount
                },
                "$push": {
                    "transactions": transaction
                }
            },
            upsert=True
        )
        return True

    async def request_withdrawal(self, bot_id: int, amount: float, method: str = "crypto") -> Dict:
        if not self._initialized:
            await self.init()
        
        earnings = await self.get_bot_earnings(bot_id)
        if not earnings:
            return {"success": False, "error": "Bot not found"}
        
        balance = earnings.get("balance", 0)

        if balance < 7.0:
            return {"success": False, "error": "Minimum withdrawal is $7"}

        if balance < amount:
            return {"success": False, "error": "Insufficient balance"}

        transaction = {
            "type": "withdrawal",
            "amount": amount,
            "method": method,
            "status": "pending",
            "timestamp": datetime.now(timezone.utc)
        }

        await self.db.bot_earnings.update_one(
            {"bot_id": bot_id},
            {
                "$inc": {"balance": -amount},
                "$push": {"transactions": transaction}
            }
        )

        return {
            "success": True,
            "transaction": transaction,
            "remaining_balance": balance - amount
        }

    async def get_bot_earnings(self, bot_id: int) -> Optional[Dict]:
        if not self._initialized:
            await self.init()
        earnings = await self.db.bot_earnings.find_one({"bot_id": bot_id})
        if earnings:
            earnings["_id"] = str(earnings["_id"])
        return earnings

    async def admin_credit_balance(self, bot_id: int, amount: float) -> bool:
        if not self._initialized:
            await self.init()
        
        transaction = {
            "type": "credit",
            "amount": amount,
            "source": "admin",
            "timestamp": datetime.now(timezone.utc)
        }

        await self.db.bot_earnings.update_one(
            {"bot_id": bot_id},
            {
                "$inc": {
                    "balance": amount,
                    "total_earned": amount
                },
                "$push": {
                    "transactions": transaction
                }
            },
            upsert=True
        )
        return True

    # ==========================================
    # SYSTÈME DE CLONAGE - STATISTIQUES
    # ==========================================

    async def increment_bot_stat(self, bot_id: int, stat_name: str, increment: int = 1) -> bool:
        valid_stats = ["total_users", "total_files_sent", "total_ads_watched"]
        if stat_name not in valid_stats:
            return False
        
        if not self._initialized:
            await self.init()

        await self.db.cloned_bots.update_one(
            {"bot_id": bot_id},
            {"$inc": {f"stats.{stat_name}": increment}}
        )
        return True

    async def get_bot_stats(self, bot_id: int) -> Optional[Dict]:
        bot = await self.get_cloned_bot(bot_id)
        if bot:
            return bot.get("stats", {})
        return None

    async def get_all_bots_stats(self) -> List[Dict]:
        bots = await self.get_all_cloned_bots()
        stats = []
        for bot in bots:
            earnings = await self.get_bot_earnings(bot["_id"])
            id_codes = await self.get_id_codes(bot_id=bot["_id"])
            stats.append({
                "bot_id": bot["_id"],
                "username": bot["bot_username"],
                "master_id": bot["master_id"],
                "created_at": bot.get("created_at"),
                "is_active": bot.get("is_active"),
                "stats": bot.get("stats", {}),
                "earnings": earnings,
                "id_pubs": id_codes.get("id_pubs") if id_codes else None
            })
        return stats

    # ==========================================
    # SYSTÈME DE RETRAITS - ADMIN
    # ==========================================

    async def get_pending_withdrawals(self) -> List[Dict]:
        """Récupère toutes les demandes de retrait en attente"""
        if not self._initialized:
            await self.init()
        
        cursor = self.db.bot_earnings.find({
            "transactions": {
                "$elemMatch": {
                    "type": "withdrawal",
                    "status": "pending"
                }
            }
        })
        
        pending = []
        async for doc in cursor:
            for tx in doc.get("transactions", []):
                if tx.get("type") == "withdrawal" and tx.get("status") == "pending":
                    pending.append({
                        "bot_id": doc["bot_id"],
                        "master_id": doc.get("master_id"),
                        "transaction": tx
                    })
        return pending

    async def approve_withdrawal(self, bot_id: int, tx_timestamp: str) -> bool:
        """Approuve une demande de retrait"""
        if not self._initialized:
            await self.init()
        
        # Find the specific transaction and update it
        result = await self.db.bot_earnings.update_one(
            {
                "bot_id": bot_id,
                "transactions": {
                    "$elemMatch": {
                        "type": "withdrawal",
                        "timestamp": tx_timestamp,
                        "status": "pending"
                    }
                }
            },
            {
                "$set": {
                    "transactions.$.status": "approved",
                    "transactions.$.processed_at": datetime.now(timezone.utc)
                },
                "$inc": {
                    "total_withdrawn": self.db.bot_earnings.find_one(
                        {"bot_id": bot_id}
                    )["transactions"][0]["amount"]
                }
            }
        )
        return result.modified_count > 0

    async def reject_withdrawal(self, bot_id: int, tx_timestamp: str, reason: str = "") -> bool:
        """Rejette une demande de retrait et rembourse"""
        if not self._initialized:
            await self.init()
        
        # Get the transaction amount first
        earnings = await self.db.bot_earnings.find_one({"bot_id": bot_id})
        if not earnings:
            return False
        
        amount = None
        for tx in earnings.get("transactions", []):
            if (tx.get("timestamp") == tx_timestamp and 
                tx.get("type") == "withdrawal" and 
                tx.get("status") == "pending"):
                amount = tx.get("amount")
                break
        
        if amount is None:
            return False

        # Update transaction and refund
        result = await self.db.bot_earnings.update_one(
            {
                "bot_id": bot_id,
                "transactions": {
                    "$elemMatch": {
                        "type": "withdrawal",
                        "timestamp": tx_timestamp,
                        "status": "pending"
                    }
                }
            },
            {
                "$set": {
                    "transactions.$.status": "rejected",
                    "transactions.$.reason": reason,
                    "transactions.$.processed_at": datetime.now(timezone.utc)
                },
                "$inc": {"balance": amount}
            }
        )
        return result.modified_count > 0

    # ==========================================
    # WITHDRAWAL REQUESTS (NEW COLLECTION)
    # ==========================================

    async def create_withdrawal_request(self, data: Dict) -> bool:
        """Create a new withdrawal request"""
        if not self._initialized:
            await self.init()
        
        try:
            await self.db.withdrawal_requests.insert_one({
                **data,
                "created_at": datetime.now(timezone.utc),
                "status": "pending"
            })
            return True
        except Exception as e:
            logging.error(f"[DB] Error creating withdrawal request: {e}")
            return False

    async def get_withdrawal_requests(self, bot_id: int = None, status: str = None) -> List[Dict]:
        """Get withdrawal requests with optional filters"""
        if not self._initialized:
            await self.init()
        
        query = {}
        if bot_id:
            query["bot_id"] = bot_id
        if status:
            query["status"] = status
        
        cursor = self.db.withdrawal_requests.find(query).sort("created_at", DESCENDING)
        requests = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            requests.append(doc)
        return requests

    async def update_withdrawal_status(self, request_id: str, status: str, processed_by: int = None) -> bool:
        """Update withdrawal request status"""
        if not self._initialized:
            await self.init()
        
        try:
            from bson.objectid import ObjectId
            update = {
                "$set": {
                    "status": status,
                    "processed_at": datetime.now(timezone.utc)
                }
            }
            if processed_by:
                update["$set"]["processed_by"] = processed_by
            
            result = await self.db.withdrawal_requests.update_one(
                {"_id": ObjectId(request_id)},
                update
            )
            return result.modified_count > 0
        except Exception as e:
            logging.error(f"[DB] Error updating withdrawal status: {e}")
            return False

    # ==========================================
    # BOT SETTINGS - DELETE TIMER
    # ==========================================

    async def set_bot_delete_timer(self, bot_id: int, minutes: int) -> bool:
        """Set auto-delete timer for a specific bot"""
        if not self._initialized:
            await self.init()
        
        await self.db.cloned_bots.update_one(
            {"bot_id": bot_id},
            {"$set": {"settings.delete_timer": minutes}}
        )
        return True

    async def get_bot_delete_timer(self, bot_id: int) -> int:
        """Get auto-delete timer for a specific bot"""
        if not self._initialized:
            await self.init()
        
        bot = await self.db.cloned_bots.find_one(
            {"bot_id": bot_id},
            {"settings.delete_timer": 1}
        )
        if bot and bot.get("settings"):
            return bot["settings"].get("delete_timer", 0)
        return 0

    # ==========================================
    # ADDITIONAL METHODS FOR COMPATIBILITY
    # ==========================================

    async def update_earnings(self, bot_id: int, updates: Dict) -> bool:
        """Update earnings data for a bot"""
        if not self._initialized:
            await self.init()
        
        set_fields = {}
        for key, value in updates.items():
            if key != "_id":
                set_fields[key] = value
        
        if set_fields:
            await self.db.bot_earnings.update_one(
                {"bot_id": bot_id},
                {"$set": set_fields},
                upsert=True
            )
        return True


# Initialisation de la base de données
db = Rohit()
