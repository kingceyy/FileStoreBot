import asyncio
from aiohttp import web
from aiohttp.web_middlewares import middleware
from database.database import db
from config import TG_BOT_TOKEN, FREE_SESSION_DURATION, ADMIN_PASSWORD, OWNER_ID
import json
import hashlib
import hmac
import logging
import secrets
import os
import traceback
from datetime import datetime, timedelta

# Configuration logging détaillé
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# ✅ AJOUT : CONSTANTES BOT MÈRE
# ============================================================

MOTHER_BOT_ID_PUBS = "YUMEFLOWER"
MOTHER_BOT_ID_CODE = "KINGCEY00"
MOTHER_BOT_ID      = 0  # bot_id=0 → bot mère dans la DB sessions

# ============================================================
# ✅ AJOUT : HELPERS — Résoudre ID_PUBS / ID_CODE → bot_id
# Ces fonctions gèrent le cas bot mère ET les clones
# ============================================================

async def resolve_bot_id_from_id_pubs(id_pubs: str):
    """
    Retourne (bot_id, bot_info_dict or None, error_str or None)
    Gère le cas bot mère (YUMEFLOWER) ET les clones.
    """
    id_pubs = id_pubs.strip().upper()
    if id_pubs == MOTHER_BOT_ID_PUBS:
        return MOTHER_BOT_ID, {"username": "YumeFlowerBot", "name": "YumeFlower (Bot Mère)", "is_mother": True}, None
    id_data = await db.get_id_codes(id_pubs=id_pubs)
    if not id_data:
        return None, None, "ID_PUBS invalide"
    bot_data = await db.get_cloned_bot(id_data["bot_id"])
    if not bot_data:
        return None, None, "Bot non trouvé"
    return id_data["bot_id"], bot_data, None


async def resolve_bot_id_from_id_code(id_code: str):
    """
    Retourne (bot_id, id_data_dict or None, error_str or None)
    Gère le cas bot mère (KINGCEY00) ET les clones.
    """
    id_code = id_code.strip().upper()
    if id_code == MOTHER_BOT_ID_CODE:
        return MOTHER_BOT_ID, {
            "bot_id":    MOTHER_BOT_ID,
            "id_pubs":   MOTHER_BOT_ID_PUBS,
            "id_code":   MOTHER_BOT_ID_CODE,
            "master_id": OWNER_ID,
            "is_mother": True
        }, None
    id_data = await db.get_id_codes(id_code=id_code)
    if not id_data:
        return None, None, "ID_CODE invalide"
    return id_data["bot_id"], id_data, None

# ============================================================
# AUTHENTIFICATION TELEGRAM WEB APP
# ============================================================

def verify_telegram_auth(auth_data: str) -> dict:
    """
    Vérifie l'authentification Telegram Web App
    """
    try:
        if not auth_data:
            logger.warning("Auth data vide")
            return None
        
        # Parser les données (format query string)
        data = {}
        if isinstance(auth_data, str):
            for pair in auth_data.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    data[key] = value
        elif isinstance(auth_data, dict):
            data = auth_data.copy()
        
        check_hash = data.pop('hash', None)
        
        if not check_hash:
            logger.warning("Pas de hash dans auth_data")
            return None
        
        # Créer la data check string (triée par clés)
        data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted(data.items()) if k != 'hash'])
        
        # Clé secrète = SHA256 du bot token
        secret_key = hashlib.sha256(TG_BOT_TOKEN.encode()).digest()
        
        # Calculer le hash
        hash_calc = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if hash_calc != check_hash:
            logger.warning(f"Hash invalide. Reçu: {check_hash}, Calculé: {hash_calc}")
            return None
        
        # Vérifier date (24h max)
        auth_date = int(data.get('auth_date', 0))
        if auth_date == 0:
            logger.warning("Pas de auth_date")
            return None
            
        if (datetime.now().timestamp() - auth_date) > 86400:
            logger.warning("Auth date trop vieux")
            return None
            
        logger.info(f"Auth OK pour user {data.get('id')}")
        return data
        
    except Exception as e:
        logger.error(f"Erreur verify_telegram_auth: {e}")
        logger.error(traceback.format_exc())
        return None

# ============================================================
# MIDDLEWARE CORS
# ============================================================

@middleware
async def cors_middleware(request, handler):
    """Autorise les requêtes CORS depuis n'importe quelle origine Telegram"""
    origin = request.headers.get('Origin', '')
    
    # Autoriser les origines Telegram et locales
    allowed_origins = [
        'https://web.telegram.org',
        'https://telegram.org',
        'http://localhost:3000',
        'http://localhost:8000',
        'http://localhost:8080',
        'https://localhost',
    ]
    
    # Autoriser aussi toutes les origines https (pour la production)
    is_allowed = (
        any(allowed in origin for allowed in allowed_origins) or 
        origin.startswith('https://') or
        'telegram' in origin.lower()
    )
    
    if request.method == "OPTIONS":
        # Preflight CORS : repondre immediatement 200 sans passer par les handlers
        response = web.Response(status=200)
        if is_allowed and origin:
            response.headers['Access-Control-Allow-Origin'] = origin
        else:
            response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Telegram-Init-Data, X-Requested-With'
        response.headers['Access-Control-Max-Age'] = '86400'
        return response

    try:
        response = await handler(request)
    except Exception as e:
        logger.error(f"ERREUR DANS HANDLER: {e}")
        logger.error(traceback.format_exc())
        response = web.json_response(
            {'error': 'Internal server error', 'detail': str(e)},
            status=500
        )

    if is_allowed and origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    else:
        response.headers['Access-Control-Allow-Origin'] = '*'

    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Telegram-Init-Data, X-Requested-With'
    response.headers['Access-Control-Max-Age'] = '86400'

    return response

# ============================================================
# ROUTES API
# ============================================================

routes = web.RouteTableDef()

@routes.get("/")
async def health_check(request):
    """Vérification que le serveur est en ligne"""
    try:
        return web.json_response({
            "status": "online",
            "service": "YumeFlower2 Bot API",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return web.json_response({
            "status": "error",
            "error": str(e)
        }, status=500)

# ============================================================
# API POUR SYSTÈME DE CLONAGE - ID_PUBS
# ============================================================

@routes.post("/api/verify-id-pubs")
async def api_verify_id_pubs(request):
    try:
        data = await request.json()
        id_pubs = data.get('id_pubs', '').strip().upper()
        
        logger.info(f"[VERIFY] ID_PUBS reçu: '{id_pubs}'")
        
        if not id_pubs:
            return web.json_response({
                'success': False,
                'error': 'ID_PUBS manquant'
            }, status=400)
        
        # ✅ CORRIGÉ : Supporte maintenant YUMEFLOWER (bot mère) ET les clones
        bot_id, bot_info, error = await resolve_bot_id_from_id_pubs(id_pubs)
        logger.info(f"[VERIFY] Résultat: bot_id={bot_id}, error={error}")
        
        if error:
            logger.warning(f"[VERIFY] ID_PUBS non trouvé: '{id_pubs}'")
            return web.json_response({
                'success': False,
                'error': error
            })

        # Cas bot mère : retourner un objet bot synthétique
        if bot_info.get("is_mother"):
            return web.json_response({
                'success': True,
                'bot': {
                    'id': MOTHER_BOT_ID,
                    'username': 'YumeFlowerBot',
                    'name': 'YumeFlower (Bot Mère)'
                },
                'id_pubs': id_pubs
            })
        
        # Cas clone : retourner les vraies données
        bot_data = bot_info
        logger.info(f"[VERIFY] Bot trouvé: {bot_data}")
        
        return web.json_response({
            'success': True,
            'bot': {
                'id': bot_data['_id'],
                'username': bot_data['bot_username'],
                'name': bot_data.get('bot_username', 'Bot')
            },
            'id_pubs': id_pubs
        })
        
    except Exception as e:
        logger.error(f"[VERIFY] Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)



@routes.post("/api/watch-ad-clone")
async def api_watch_ad_clone(request):
    """
    Active une session gratuite après visionnage de pub pour un bot cloné
    Nécessite l'ID_PUBS pour identifier le bot
    """
    try:
        data = await request.json()
        user_id = data.get('user_id')
        id_pubs = data.get('id_pubs', '').strip().upper()
        auth = data.get('auth')
        
        logger.info(f"Watch ad clone - User: {user_id}, ID_PUBS: {id_pubs}")
        
        if not user_id or not id_pubs:
            return web.json_response({
                'success': False,
                'error': 'Paramètres manquants'
            }, status=400)
        
        # ✅ CORRIGÉ : Supporte maintenant YUMEFLOWER (bot mère) ET les clones
        bot_id, bot_info, error = await resolve_bot_id_from_id_pubs(id_pubs)
        
        if error:
            logger.error(f"ID_PUBS invalide: {id_pubs}")
            return web.json_response({
                'success': False,
                'error': error
            })
        
        logger.info(f"ID_PUBS {id_pubs} correspond au bot_id: {bot_id}")
        
        # Pour les clones, vérifier que le bot existe bien dans cloned_bots
        if not bot_info.get("is_mother"):
            bot_data = bot_info
            if not bot_data:
                logger.error(f"Bot non trouvé pour bot_id: {bot_id}")
                return web.json_response({
                    'success': False,
                    'error': 'Bot non trouvé'
                })
        
        # Vérifier auth Telegram (optionnel mais recommandé)
        if auth:
            user_data = verify_telegram_auth(auth)
            if user_data and int(user_data.get('id', 0)) != int(user_id):
                logger.warning(f"Mismatch user_id: {user_id} vs {user_data.get('id')}")
        
        # Vérifier si déjà session active pour CE bot
        existing_session = await db.has_active_session(user_id, bot_id)
        if existing_session:
            logger.info(f"Session déjà active pour user {user_id} sur bot {bot_id}")
            return web.json_response({
                'success': False,
                'message': 'Session déjà active pour ce bot'
            })
        
        # Creer session gratuite pour CE bot specifique
        # Priorite : session_duration du bot > config globale
        duration = await db.get_bot_session_duration(bot_id)
        session  = await db.create_free_session(user_id, duration, bot_id)
        
        # Incrémenter les stats
        await db.increment_bot_stat(bot_id, 'total_ads_watched')
        
        # AJOUTER DES GAINS AU BOT ($0.002 par impression = $2 CPM)
        earning_per_ad = 0.002
        await db.add_earning(bot_id, earning_per_ad, 'ad_impression')
        
        bot_username = "YumeFlowerBot" if bot_info.get("is_mother") else bot_info.get('bot_username', 'Bot')
        
        logger.info(f"✅ Session créée pour user {user_id} sur bot {bot_id} (ID_PUBS: {id_pubs})")
        logger.info(f"Gains ajoutés au bot {bot_id}: ${earning_per_ad}")
        
        return web.json_response({
            'success': True,
            'duration': duration,
            'expires_at': session.get('expires_at'),
            'bot_username': bot_username,
            'message': 'Session activée avec succès'
        })
        
    except Exception as e:
        logger.error(f"Error in watch-ad-clone: {e}")
        logger.error(traceback.format_exc())
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


@routes.post("/api/check-session-clone")
async def api_check_session_clone(request):
    """Vérifie si l'utilisateur a une session active pour un bot spécifique"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        id_pubs = data.get('id_pubs', '').strip().upper()
        
        logger.info(f"Check session clone - User: {user_id}, ID_PUBS: {id_pubs}")
        
        if not user_id or not id_pubs:
            return web.json_response({
                'success': False,
                'error': 'Paramètres manquants'
            }, status=400)
        
        # ✅ CORRIGÉ : Supporte maintenant YUMEFLOWER (bot mère) ET les clones
        bot_id, bot_info, error = await resolve_bot_id_from_id_pubs(id_pubs)
        
        if error:
            logger.warning(f"ID_PUBS invalide: {id_pubs}")
            return web.json_response({
                'success': False,
                'error': error
            })
        
        logger.info(f"Check session - ID_PUBS {id_pubs} -> bot_id {bot_id}")
        
        # Vérifier session pour CE bot
        has_session = await db.has_active_session(user_id, bot_id)
        time_left = await db.get_session_time_left(user_id, bot_id) if has_session else 0
        session = await db.get_user_session(user_id, bot_id) if has_session else None
        
        logger.info(f"Check session result - has_session: {has_session}, time_left: {time_left}")
        
        return web.json_response({
            'success': True,
            'has_access': has_session and time_left > 0,
            'time_left': time_left,
            'expires_at': session.get('expires_at') if session else None,
            'type': session.get('type') if session else None,
            'bot_id': bot_id
        })
        
    except Exception as e:
        logger.error(f"Error in check-session-clone: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

# ============================================================
# API PAGE MAÎTRE (ID_CODE)
# ============================================================

@routes.post("/api/master/login")
async def api_master_login(request):
    """Connexion à la page Maître avec ID_CODE"""
    try:
        data = await request.json()
        id_code = data.get('id_code', '').strip().upper()
        auth = data.get('auth')
        
        logger.info(f"Tentative connexion maître avec ID_CODE")
        
        if not id_code:
            return web.json_response({
                'success': False,
                'error': 'ID_CODE manquant'
            }, status=400)
        
        # ✅ CORRIGÉ : Supporte maintenant KINGCEY00 (bot mère) ET les clones
        bot_id, id_data, error = await resolve_bot_id_from_id_code(id_code)
        
        if error:
            return web.json_response({
                'success': False,
                'error': error
            })
        
        # Vérifier auth Telegram si fourni
        if auth:
            user_data = verify_telegram_auth(auth)
            if user_data:
                # Vérifier que l'utilisateur est bien le maître
                master_id = id_data.get('master_id', OWNER_ID)
                if int(user_data.get('id', 0)) != master_id:
                    logger.warning(f"Tentative accès maître non autorisée: {user_data.get('id')} vs {master_id}")
                    return web.json_response({
                        'success': False,
                        'error': 'Non autorisé'
                    }, status=403)
        
        # ── CAS BOT MÈRE ──────────────────────────────────────
        if id_data.get("is_mother"):
            earnings = await db.get_bot_earnings(MOTHER_BOT_ID) or {
                "balance": 0, "total_earned": 0, "total_withdrawn": 0
            }
            return web.json_response({
                'success': True,
                'bot': {
                    'id': MOTHER_BOT_ID,
                    'username': 'YumeFlowerBot',
                    'created_at': '2025-01-01T00:00:00'
                },
                'id_pubs': MOTHER_BOT_ID_PUBS,
                'stats': {
                    'total_users': 0,
                    'total_ads_watched': earnings.get('total_ads_watched', 0),
                    'total_files_sent': 0
                },
                'earnings': {
                    'balance':         earnings.get('balance', 0),
                    'total_earned':    earnings.get('total_earned', 0),
                    'total_withdrawn': earnings.get('total_withdrawn', 0)
                }
            })
        
        # ── CAS CLONE ─────────────────────────────────────────
        bot_data = await db.get_cloned_bot(bot_id)
        earnings = await db.get_bot_earnings(bot_id)
        stats = bot_data.get('stats', {}) if bot_data else {}
        
        return web.json_response({
            'success': True,
            'bot': {
                'id': bot_data['_id'],
                'username': bot_data['bot_username'],
                'created_at': bot_data['created_at']
            },
            'id_pubs': id_data['id_pubs'],
            'stats': {
                'total_users': stats.get('total_users', 0),
                'total_ads_watched': stats.get('total_ads_watched', 0),
                'total_files_sent': stats.get('total_files_sent', 0)
            },
            'earnings': {
                'balance': earnings['balance'] if earnings else 0,
                'total_earned': earnings['total_earned'] if earnings else 0,
                'total_withdrawn': earnings['total_withdrawn'] if earnings else 0
            }
        })
        
    except Exception as e:
        logger.error(f"Error in master login: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


@routes.post("/api/master/withdraw")
async def api_master_withdraw(request):
    """Demande de retrait pour un maître (manuel - envoie notification à l'OWNER)"""
    try:
        data = await request.json()
        id_code = data.get('id_code', '').strip().upper()
        amount = float(data.get('amount', 0))
        method = data.get('method', 'crypto')  # crypto, moov, orange, ecobank
        account_info = data.get('account_info', '')  # numéro de téléphone/compte
        
        if not id_code or amount <= 0:
            return web.json_response({
                'success': False,
                'error': 'Paramètres invalides'
            }, status=400)
        
        # Vérifier ID_CODE
        id_data = await db.get_id_codes(id_code=id_code)
        if not id_data:
            return web.json_response({
                'success': False,
                'error': 'ID_CODE invalide'
            })
        
        bot_id = id_data['bot_id']
        bot_data = await db.get_cloned_bot(bot_id)
        
        # Vérifier solde suffisant (minimum $7)
        earnings = await db.get_bot_earnings(bot_id)
        if not earnings or earnings['balance'] < 7.0:
            return web.json_response({
                'success': False,
                'error': 'Solde insuffisant (minimum $7)'
            })
        
        if earnings['balance'] < amount:
            return web.json_response({
                'success': False,
                'error': 'Montant supérieur au solde'
            })
        
        # Créer la demande de retrait (statut: pending)
        result = await db.request_withdrawal(bot_id, amount, method)
        
        if result['success']:
            # Envoyer notification à l'OWNER (manuel)
            try:
                from bot import Bot
                bot = Bot()
                
                method_names = {
                    'crypto': 'Crypto (BTC/USDT)',
                    'moov': 'Moov Money',
                    'orange': 'Orange Money',
                    'ecobank': 'Ecobank Xpress'
                }
                
                await bot.send_message(
                    OWNER_ID,
                    f"💸 <b>Nouvelle demande de retrait!</b>\n\n"
                    f"🤖 Bot: @{bot_data['bot_username']}\n"
                    f"👤 Maître ID: <code>{id_data['master_id']}</code>\n"
                    f"💵 Montant: ${amount:.2f}\n"
                    f"💳 Méthode: {method_names.get(method, method)}\n"
                    f"📱 Compte: <code>{account_info}</code>\n\n"
                    f"🆔 ID_PUBS: <code>{id_data['id_pubs']}</code>\n\n"
                    f"Utilisez /withdrawals pour voir toutes les demandes.",
                    parse_mode='HTML'
                )
            except Exception as notify_error:
                logger.error(f"Erreur notification owner: {notify_error}")
            
            logger.info(f"Retrait demandé pour bot {bot_id}: ${amount} via {method}")
        
        return web.json_response(result)
        
    except Exception as e:
        logger.error(f"Error in master withdraw: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


@routes.post("/api/master/regenerate-code")
async def api_master_regenerate_code(request):
    """Régénère l'ID_CODE et ID_PUBS"""
    try:
        data = await request.json()
        id_code = data.get('id_code', '').strip().upper()
        auth = data.get('auth')
        
        if not id_code:
            return web.json_response({
                'success': False,
                'error': 'ID_CODE manquant'
            }, status=400)
        
        # Vérifier ID_CODE et auth
        id_data = await db.get_id_codes(id_code=id_code)
        if not id_data:
            return web.json_response({
                'success': False,
                'error': 'ID_CODE invalide'
            })
        
        # Vérifier auth
        if auth:
            user_data = verify_telegram_auth(auth)
            if user_data:
                if int(user_data.get('id', 0)) != id_data['master_id']:
                    return web.json_response({
                        'success': False,
                        'error': 'Non autorisé'
                    }, status=403)
        
        # Régénérer
        new_codes = await db.regenerate_id_code(id_data['bot_id'], id_data['master_id'])
        
        if new_codes:
            logger.info(f"ID_CODE régénéré pour bot {id_data['bot_id']}")
            return web.json_response({
                'success': True,
                'id_pubs': new_codes['id_pubs'],
                'id_code': new_codes['id_code']
            })
        else:
            return web.json_response({
                'success': False,
                'error': 'Erreur lors de la régénération'
            })
            
    except Exception as e:
        logger.error(f"Error in regenerate code: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

# ============================================================
# API EXISTANTES (BOT MÈRE)
# ============================================================

@routes.post("/api/check-session")
async def api_check_session(request):
    """Vérifie si l'utilisateur a une session active (bot mère)"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        auth = data.get('auth')
        
        logger.info(f"Check session (bot mère) - User: {user_id}")
        
        if not user_id:
            return web.json_response({'error': 'Missing user_id'}, status=400)
        
        # Vérifier session pour bot mère (bot_id=0)
        try:
            has_session = await db.has_active_session(user_id, 0)  # bot_id=0 pour bot mère
            time_left = await db.get_session_time_left(user_id, 0) if has_session else 0
            session = await db.get_user_session(user_id, 0) if has_session else None
            
            return web.json_response({
                'has_access': has_session and time_left > 0,
                'time_left': time_left,
                'expires_at': session.get('expires_at') if session else None,
                'type': session.get('type') if session else None,
                'duration': await db.get_free_session_duration(),
                'can_watch_ad': await db.can_watch_ad(user_id)
            })
        except Exception as db_error:
            logger.error(f"Erreur DB check-session: {db_error}")
            return web.json_response({
                'has_access': False,
                'error': 'Database error',
                'detail': str(db_error)
            }, status=500)
        
    except Exception as e:
        logger.error(f"Error in check-session: {e}")
        logger.error(traceback.format_exc())
        return web.json_response({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@routes.post("/api/watch-ad")
async def api_watch_ad(request):
    """
    Active une session gratuite apres visionnage de pub.
    Supporte le bot mere (bot_id=0) ET les bots clones via id_pubs.
    Si id_pubs est fourni on redirige vers la logique clone.
    """
    try:
        data    = await request.json()
        user_id = data.get('user_id')
        id_pubs = data.get('id_pubs', '').strip().upper()
        auth    = data.get('auth')

        if not user_id:
            return web.json_response({'error': 'Missing user_id'}, status=400)

        # Si id_pubs fourni → logique clone (meme traitement que watch-ad-clone)
        if id_pubs:
            logger.info(f"Watch ad (via id_pubs={id_pubs}) - User: {user_id}")
            bot_id, bot_info, error = await resolve_bot_id_from_id_pubs(id_pubs)
            if error:
                return web.json_response({'success': False, 'error': error}, status=400)
        else:
            logger.info(f"Watch ad (bot mere) - User: {user_id}")
            bot_id   = MOTHER_BOT_ID
            bot_info = {"is_mother": True}

        # Verifier auth Telegram (optionnel)
        if auth:
            user_data = verify_telegram_auth(auth)
            if not user_data:
                logger.warning(f"Auth echouee pour user {user_id}")

        # Verifier si session deja active pour ce bot
        try:
            if await db.has_active_session(user_id, bot_id):
                logger.info(f"User {user_id} a deja une session active sur bot {bot_id}")
                return web.json_response({'success': False, 'message': 'Session already active'})
        except Exception as e:
            logger.error(f"Erreur DB has_active_session: {e}")
            return web.json_response({'error': f'DB Error: {str(e)}'}, status=500)

        # Determiner la duree via la methode unifiee get_bot_session_duration
        try:
            duration = await db.get_bot_session_duration(bot_id)

            logger.info(f"Creation session - Duration: {duration}min - User: {user_id} - Bot: {bot_id}")
            session = await db.create_free_session(user_id, duration, bot_id)
            logger.info(f"Session creee avec succes: {session}")

            # Crediter les gains
            try:
                await db.add_earning(bot_id, 0.002, 'ad_impression')
                await db.increment_bot_stat(bot_id, 'total_ads_watched')
            except Exception as eg:
                logger.warning(f"Gains non credites pour bot {bot_id}: {eg}")

            return web.json_response({
                'success':    True,
                'duration':   duration,
                'expires_at': session.get('expires_at'),
                'message':    'Session activated successfully'
            })
        except Exception as e:
            logger.error(f"Erreur creation session: {e}")
            logger.error(traceback.format_exc())
            return web.json_response({
                'error':  f'Failed to create session: {str(e)}',
                'detail': traceback.format_exc()
            }, status=500)
        
    except Exception as e:
        logger.error(f"Error in watch-ad: {e}")
        logger.error(traceback.format_exc())
        return web.json_response({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@routes.post("/api/payment")
async def api_payment(request):
    """Créer une session premium après paiement"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        auth = data.get('auth')
        plan = data.get('plan', 'monthly')
        id_pubs = data.get('id_pubs', '').strip().upper()
        
        if not user_id or not auth:
            return web.json_response({'error': 'Missing parameters'}, status=400)
        
        # Vérifier auth Telegram
        user_data = verify_telegram_auth(auth)
        if not user_data or int(user_data.get('id', 0)) != int(user_id):
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        # Déterminer le bot_id
        bot_id = 0  # Par défaut bot mère
        if id_pubs:
            id_data = await db.get_id_codes(id_pubs=id_pubs)
            if id_data:
                bot_id = id_data['bot_id']
        
        # Déterminer la durée selon le plan
        duration_days = 7 if plan == 'weekly' else 30 if plan == 'monthly' else 365
        duration_minutes = duration_days * 24 * 60
        
        session = await db.create_premium_session(user_id, duration_minutes, None, bot_id)
        
        logger.info(f"Premium session created for user {user_id}, bot {bot_id}, plan: {plan}")
        
        return web.json_response({
            'success': True,
            'duration': duration_days,
            'expires_at': session['expires_at'],
            'plan': plan
        })
        
    except Exception as e:
        logger.error(f"Error in payment: {e}")
        return web.json_response({'error': str(e)}, status=500)

# ============================================================
# API ADMIN (OWNER)
# ============================================================

@routes.post("/api/admin/login")
async def api_admin_login(request):
    """Login admin"""
    try:
        data = await request.json()
        password = data.get('password')
        
        if not password:
            return web.json_response({
                'success': False,
                'error': 'Password required'
            }, status=400)
        
        if password == ADMIN_PASSWORD:
            token = secrets.token_urlsafe(32)
            logger.info("✅ Admin login successful")
            
            return web.json_response({
                'success': True,
                'token': token
            })
        else:
            logger.warning("❌ Admin login failed")
            return web.json_response({
                'success': False,
                'error': 'Invalid password'
            }, status=401)
        
    except Exception as e:
        logger.error(f"Error in admin login: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


@routes.get("/api/admin/stats")
async def api_admin_stats(request):
    """Statistiques admin"""
    try:
        all_users = await db.full_userbase()
        all_bots = await db.get_all_cloned_bots()
        
        # Calculer sessions actives
        active_sessions = 0
        premium_users = 0
        free_users = 0
        
        # Stats des bots clonés
        total_cloned_balance = 0
        total_ads_watched = 0
        
        for bot in all_bots:
            earnings = await db.get_bot_earnings(bot['_id'])
            if earnings:
                total_cloned_balance += earnings['balance']
                total_ads_watched += bot.get('stats', {}).get('total_ads_watched', 0)
        
        return web.json_response({
            'success': True,
            'total_users': len(all_users),
            'cloned_bots': len(all_bots),
            'cloned_bots_balance': total_cloned_balance,
            'total_ads_watched': total_ads_watched,
            'config': {
                'free_session_duration': await db.get_free_session_duration()
            }
        })
        
    except Exception as e:
        logger.error(f"Error in admin stats: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


@routes.post("/api/admin/credit-bot")
async def api_admin_credit_bot(request):
    """Crédite le solde d'un bot (owner only)"""
    try:
        data = await request.json()
        bot_id = data.get('bot_id')
        amount = float(data.get('amount', 0))
        
        if not bot_id:
            return web.json_response({
                'success': False,
                'error': 'bot_id manquant'
            }, status=400)
        
        success = await db.admin_credit_balance(bot_id, amount)
        
        if success:
            logger.info(f"Bot {bot_id} crédité de ${amount}")
            return web.json_response({
                'success': True,
                'message': f'Bot crédité de ${amount}'
            })
        else:
            return web.json_response({
                'success': False,
                'error': 'Erreur lors du crédit'
            })
            
    except Exception as e:
        logger.error(f"Error in admin credit bot: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


@routes.post("/api/admin/config")
async def api_admin_config(request):
    """Modifie la configuration"""
    try:
        data = await request.json()
        
        if 'free_duration' in data:
            await db.set_free_session_duration(int(data['free_duration']))
            logger.info(f"Free duration updated to {data['free_duration']} minutes")
        
        return web.json_response({
            'success': True,
            'free_session_duration': await db.get_free_session_duration()
        })
        
    except Exception as e:
        logger.error(f"Error in admin config: {e}")
        return web.json_response({'error': str(e)}, status=500)


@routes.get("/api/admin/withdrawals")
async def api_admin_withdrawals(request):
    """Liste toutes les demandes de retrait en attente (OWNER)"""
    try:
        pending = await db.get_pending_withdrawals()
        
        return web.json_response({
            'success': True,
            'withdrawals': pending
        })
        
    except Exception as e:
        logger.error(f"Error in admin withdrawals: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


@routes.post("/api/admin/approve-withdrawal")
async def api_admin_approve_withdrawal(request):
    """Approuve un retrait (OWNER)"""
    try:
        data = await request.json()
        bot_id = data.get('bot_id')
        tx_timestamp = data.get('timestamp')
        
        if not bot_id or not tx_timestamp:
            return web.json_response({
                'success': False,
                'error': 'Paramètres manquants'
            }, status=400)
        
        success = await db.approve_withdrawal(bot_id, tx_timestamp)
        
        if success:
            # Notifier le maître
            try:
                from bot import Bot
                bot = Bot()
                bot_data = await db.get_cloned_bot(bot_id)
                id_data = await db.get_id_codes(bot_id=bot_id)
                
                if bot_data and id_data:
                    await bot.send_message(
                        id_data['master_id'],
                        f"✅ <b>Retrait approuvé!</b>\n\n"
                        f"Votre demande de retrait a été traitée.\n"
                        f"Le montant sera envoyé sous peu.",
                        parse_mode='HTML'
                    )
            except Exception as e:
                logger.error(f"Erreur notification maître: {e}")
        
        return web.json_response({
            'success': success
        })
        
    except Exception as e:
        logger.error(f"Error in approve withdrawal: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

# ============================================================
# CREATION APP
# ============================================================

async def web_server():
    """Crée et retourne l'application web aiohttp"""
    web_app = web.Application(middlewares=[cors_middleware])
    web_app.add_routes(routes)
    
    logger.info("✅ Web server initialized")
    logger.info(f"🔐 Admin password: {'Yes' if ADMIN_PASSWORD else 'No'}")
    logger.info(f"🤖 Bot token: {'Yes' if TG_BOT_TOKEN else 'No'}")
    logger.info(f"👑 Owner ID: {OWNER_ID}")
    
    return web_app


# =============================================================================
# SYSTÈME KGC-SPHÈRES — Profil utilisateur, Tâches, Retraits
# =============================================================================

@routes.get("/api/user/profile")
async def api_user_profile(request):
    """Retourne le profil et solde KGC d'un utilisateur"""
    try:
        user_id = request.query.get("user_id")
        if not user_id:
            return web.json_response({"error": "user_id manquant"}, status=400)
        user_id = int(user_id)

        profile = await db.db["user_profiles"].find_one({"user_id": user_id})
        if not profile:
            profile = {
                "user_id": user_id, "first_name": "", "username": None,
                "balance_kgc": 0, "total_earned_kgc": 0, "tasks_completed": 0,
                "created_at": datetime.now().isoformat(),
            }
            await db.db["user_profiles"].insert_one(profile)

        withdrawals = await db.db["user_withdrawals"].find(
            {"user_id": user_id}
        ).sort("requested_at", -1).limit(10).to_list(length=10)
        for w in withdrawals:
            w["id"] = str(w.pop("_id", ""))

        return web.json_response({
            "success": True,
            "profile": {
                "user_id": profile["user_id"],
                "first_name": profile.get("first_name", ""),
                "username": profile.get("username"),
                "balance_kgc": profile.get("balance_kgc", 0),
                "total_earned_kgc": profile.get("total_earned_kgc", 0),
                "tasks_completed": profile.get("tasks_completed", 0),
                "withdrawals": withdrawals,
            }
        })
    except Exception as e:
        logger.error(f"user/profile: {e}")
        return web.json_response({"error": str(e)}, status=500)


@routes.get("/api/tasks")
async def api_get_tasks(request):
    """Liste des tâches disponibles pour un utilisateur"""
    try:
        user_id = request.query.get("user_id")
        if not user_id:
            return web.json_response({"error": "user_id manquant"}, status=400)
        user_id = int(user_id)

        base_tasks = [
            {
                "id": "adsgram_daily",
                "title": "Tâche AdsGram",
                "description": "Complétez une tâche native AdsGram pour gagner des KGC-Sphères.",
                "reward_kgc": 50, "type": "adsgram", "url": None,
            },
            {
                "id": "monetag_daily",
                "title": "Publicité Monetag",
                "description": "Regardez une publicité Monetag interstitielle pour gagner des KGC-Sphères.",
                "reward_kgc": 30, "type": "monetag", "url": None,
            },
        ]

        manual_tasks = await db.db["manual_tasks"].find({"active": True}).to_list(length=50)
        for t in manual_tasks:
            t["id"] = str(t.pop("_id", ""))
            t["type"] = "manual"

        all_tasks = base_tasks + manual_tasks

        # Comparaison string ISO fiable : stocker et comparer en format YYYY-MM-DD
        today_str = datetime.now().strftime("%Y-%m-%d")
        completed_docs = await db.db["task_claims"].find(
            {"user_id": user_id, "claimed_at": {"$gte": today_str}},
            {"task_id": 1}
        ).to_list(length=200)
        completed_today = {doc["task_id"] for doc in completed_docs}

        for t in all_tasks:
            t["completed"] = t["id"] in completed_today

        return web.json_response({"success": True, "tasks": all_tasks})
    except Exception as e:
        logger.error(f"tasks: {e}")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/api/tasks/claim")
async def api_claim_task(request):
    """Valider une tâche et créditer les KGC"""
    try:
        data    = await request.json()
        user_id = data.get("user_id")
        task_id = data.get("task_id")
        if not user_id or not task_id:
            return web.json_response({"error": "user_id et task_id requis"}, status=400)
        user_id = int(user_id)

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        existing = await db.db["task_claims"].find_one({
            "user_id": user_id, "task_id": task_id,
            "claimed_at": {"$gte": today_start.isoformat()}
        })
        if existing:
            return web.json_response({"success": False, "error": "Tâche déjà complétée aujourd'hui"}, status=400)

        reward_map = {"adsgram_daily": 50, "monetag_daily": 30}
        reward_kgc = reward_map.get(task_id)

        if reward_kgc is None:
            try:
                from bson import ObjectId
                manual = await db.db["manual_tasks"].find_one({"_id": ObjectId(task_id)})
                reward_kgc = manual.get("reward_kgc", 0) if manual else 0
            except Exception:
                reward_kgc = 0

        if reward_kgc <= 0:
            return web.json_response({"success": False, "error": "Tâche introuvable"}, status=404)

        await db.db["task_claims"].insert_one({
            "user_id": user_id, "task_id": task_id,
            "reward_kgc": reward_kgc, "claimed_at": datetime.now().isoformat(),
        })
        await db.db["user_profiles"].update_one(
            {"user_id": user_id},
            {"$inc": {"balance_kgc": reward_kgc, "total_earned_kgc": reward_kgc, "tasks_completed": 1},
             "$setOnInsert": {"created_at": datetime.now().isoformat()}},
            upsert=True
        )
        return web.json_response({"success": True, "reward_kgc": reward_kgc})
    except Exception as e:
        logger.error(f"tasks/claim: {e}")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/api/user/withdraw")
async def api_user_withdraw(request):
    """Demande de retrait KGC utilisateur"""
    try:
        data    = await request.json()
        user_id = data.get("user_id")
        amount  = float(data.get("amount", 0))
        method  = data.get("method", "")
        address = data.get("address", "").strip()

        if not user_id or not method or not address:
            return web.json_response({"success": False, "error": "Paramètres manquants"}, status=400)
        user_id = int(user_id)

        MIN_USDT = 3.0
        if amount < MIN_USDT:
            return web.json_response({"success": False, "error": f"Minimum {MIN_USDT} USDT"}, status=400)

        KGC_TO_USDT = 0.001
        profile = await db.db["user_profiles"].find_one({"user_id": user_id})
        if not profile:
            return web.json_response({"success": False, "error": "Profil introuvable"}, status=404)

        balance_usdt = profile.get("balance_kgc", 0) * KGC_TO_USDT
        if balance_usdt < amount:
            return web.json_response({"success": False, "error": "Solde insuffisant"}, status=400)

        pending = await db.db["user_withdrawals"].find_one({"user_id": user_id, "status": "pending"})
        if pending:
            return web.json_response({"success": False, "error": "Un retrait est déjà en attente"}, status=400)

        kgc_to_deduct = int(amount / KGC_TO_USDT)
        await db.db["user_profiles"].update_one(
            {"user_id": user_id}, {"$inc": {"balance_kgc": -kgc_to_deduct}}
        )
        await db.db["user_withdrawals"].insert_one({
            "user_id": user_id,
            "first_name": profile.get("first_name", ""),
            "username":   profile.get("username"),
            "amount_usdt": amount, "method": method, "address": address,
            "status": "pending", "requested_at": datetime.now().isoformat(),
        })
        return web.json_response({"success": True})
    except Exception as e:
        logger.error(f"user/withdraw: {e}")
        return web.json_response({"error": str(e)}, status=500)


@routes.get("/api/admin/users")
async def api_admin_users(request):
    try:
        profiles = await db.db["user_profiles"].find({}).sort("balance_kgc", -1).limit(100).to_list(length=100)
        users = [{
            "user_id": p.get("user_id"), "first_name": p.get("first_name", ""),
            "username": p.get("username"), "balance_kgc": p.get("balance_kgc", 0),
            "total_earned_kgc": p.get("total_earned_kgc", 0),
            "tasks_completed": p.get("tasks_completed", 0),
        } for p in profiles]
        return web.json_response({"success": True, "users": users})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.get("/api/admin/user-withdrawals")
async def api_admin_user_withdrawals(request):
    try:
        withdrawals = await db.db["user_withdrawals"].find({}).sort("requested_at", -1).limit(100).to_list(length=100)
        result = []
        for w in withdrawals:
            w["id"] = str(w.pop("_id", ""))
            result.append(w)
        return web.json_response({"success": True, "withdrawals": result})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/api/admin/approve-user-withdrawal")
async def api_approve_user_withdrawal(request):
    try:
        data = await request.json()
        withdrawal_id = data.get("withdrawal_id")
        if not withdrawal_id:
            return web.json_response({"success": False, "error": "withdrawal_id manquant"}, status=400)
        from bson import ObjectId
        result = await db.db["user_withdrawals"].update_one(
            {"_id": ObjectId(withdrawal_id), "status": "pending"},
            {"$set": {"status": "approved", "processed_at": datetime.now().isoformat()}}
        )
        if result.modified_count == 0:
            return web.json_response({"success": False, "error": "Retrait introuvable ou déjà traité"}, status=404)
        # Notifier l'utilisateur
        w = await db.db["user_withdrawals"].find_one({"_id": ObjectId(withdrawal_id)})
        if w:
            try:
                from aiogram import Bot as AioBot
                from aiogram.client.default import DefaultBotProperties
                from aiogram.enums import ParseMode as PM
                from config import TG_BOT_TOKEN as MOTHER_TOKEN
                bot = AioBot(token=MOTHER_TOKEN, default=DefaultBotProperties(parse_mode=PM.HTML))
                method_label = "Mobile Money (JessiKaPay)" if w.get("method") == "mobile_money" else "USDT TRC-20"
                await bot.send_message(
                    w["user_id"],
                    f"<b>Retrait approuvé</b>\n\n"
                    f"Montant : <b>{w['amount_usdt']:.3f} USDT</b>\n"
                    f"Méthode : {method_label}\n\n"
                    f"<i>Votre paiement a été traité.</i>"
                )
                await bot.session.close()
            except Exception as notify_err:
                logger.warning(f"Notification user échouée : {notify_err}")
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/api/admin/reject-user-withdrawal")
async def api_reject_user_withdrawal(request):
    try:
        data = await request.json()
        withdrawal_id = data.get("withdrawal_id")
        reason = data.get("reason", "Refusé par l'administrateur")
        if not withdrawal_id:
            return web.json_response({"success": False, "error": "withdrawal_id manquant"}, status=400)
        from bson import ObjectId
        w = await db.db["user_withdrawals"].find_one({"_id": ObjectId(withdrawal_id)})
        if not w or w.get("status") != "pending":
            return web.json_response({"success": False, "error": "Retrait introuvable ou déjà traité"}, status=404)
        await db.db["user_withdrawals"].update_one(
            {"_id": ObjectId(withdrawal_id)},
            {"$set": {"status": "rejected", "reject_reason": reason, "processed_at": datetime.now().isoformat()}}
        )
        KGC_TO_USDT = 0.001
        kgc_to_refund = int(w.get("amount_usdt", 0) / KGC_TO_USDT)
        await db.db["user_profiles"].update_one(
            {"user_id": w["user_id"]}, {"$inc": {"balance_kgc": kgc_to_refund}}
        )
        try:
            from aiogram import Bot as AioBot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode as PM
            from config import TG_BOT_TOKEN as MOTHER_TOKEN
            bot = AioBot(token=MOTHER_TOKEN, default=DefaultBotProperties(parse_mode=PM.HTML))
            await bot.send_message(
                w["user_id"],
                f"<b>Retrait refusé</b>\n\nMontant : {w['amount_usdt']:.3f} USDT\nRaison : {reason}\n\n"
                "<i>Vos KGC-Sphères ont été remboursés.</i>"
            )
            await bot.session.close()
        except Exception as notify_err:
            logger.warning(f"Notification rejet échouée : {notify_err}")
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/api/admin/tasks/add")
async def api_admin_task_add(request):
    try:
        data = await request.json()
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        reward_kgc = int(data.get("reward_kgc", 0))
        url = data.get("url", "").strip()
        if not title or reward_kgc <= 0:
            return web.json_response({"success": False, "error": "Titre et récompense requis"}, status=400)
        result = await db.db["manual_tasks"].insert_one({
            "title": title, "description": description,
            "reward_kgc": reward_kgc, "url": url or None,
            "active": True, "created_at": datetime.now().isoformat(),
        })
        return web.json_response({"success": True, "task_id": str(result.inserted_id)})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/api/admin/tasks/delete")
async def api_admin_task_delete(request):
    try:
        data = await request.json()
        task_id = data.get("task_id")
        if not task_id:
            return web.json_response({"success": False, "error": "task_id manquant"}, status=400)
        from bson import ObjectId
        await db.db["manual_tasks"].update_one(
            {"_id": ObjectId(task_id)}, {"$set": {"active": False}}
        )
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# =============================================================================
# ALIAS ET ENDPOINTS MANQUANTS — Pour aligner avec le frontend
# =============================================================================

@routes.get("/api/admin/clones")
async def api_admin_clones(request):
    """Liste tous les bots clonés pour le dashboard admin"""
    try:
        all_bots = await db.get_all_cloned_bots()
        result = []
        for bot in all_bots:
            bot_id = bot.get("bot_id", bot.get("_id"))
            earnings = await db.get_bot_earnings(bot_id) or {}
            result.append({
                "id":          str(bot_id),
                "username":    bot.get("bot_username", "—"),
                "id_pubs":     bot.get("id_pubs", ""),
                "id_code":     bot.get("id_code", ""),
                "active":      bot.get("is_active", False),
                "balance":     earnings.get("balance", 0),
                "impressions": bot.get("stats", {}).get("total_ads_watched", 0),
            })
        return web.json_response({"success": True, "clones": result})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/api/admin/credit")
async def api_admin_credit(request):
    """Alias de /api/admin/credit-bot"""
    try:
        data    = await request.json()
        clone_id = data.get("clone_id")
        amount   = float(data.get("amount", 0))
        if not clone_id:
            return web.json_response({"success": False, "error": "clone_id manquant"}, status=400)
        success = await db.admin_credit_balance(int(clone_id), amount)
        return web.json_response({"success": success})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/api/admin/reject-withdrawal")
async def api_admin_reject_withdrawal(request):
    """Rejette un retrait maître"""
    try:
        data          = await request.json()
        withdrawal_id = data.get("withdrawal_id")
        reason        = data.get("reason", "Rejeté par l'administrateur")
        if not withdrawal_id:
            return web.json_response({"success": False, "error": "withdrawal_id manquant"}, status=400)
        try:
            from bson import ObjectId
            result = await db.db["withdrawals"].update_one(
                {"_id": ObjectId(withdrawal_id), "status": "pending"},
                {"$set": {"status": "rejected", "reject_reason": reason,
                          "processed_at": datetime.now().isoformat()}}
            )
            return web.json_response({"success": result.modified_count > 0})
        except Exception:
            # Fallback si la collection s'appelle autrement
            success = await db.reject_withdrawal(withdrawal_id, reason)
            return web.json_response({"success": success})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/api/master-config")
async def api_master_config_alias(request):
    """Configure les paramètres d'un bot cloné via ID_CODE"""
    try:
        data     = await request.json()
        id_code  = data.get("id_code", "").strip().upper()
        if not id_code:
            return web.json_response({"success": False, "error": "id_code manquant"}, status=400)

        bot_id, id_data, error = await resolve_bot_id_from_id_code(id_code)
        if error:
            return web.json_response({"success": False, "error": error})

        updates = {}
        if "ads_enabled" in data:
            updates["ads_enabled"] = bool(data["ads_enabled"])
        if "session_duration" in data:
            updates["session_duration"] = int(data["session_duration"])

        if updates:
            await db.db["cloned_bots"].update_one(
                {"bot_id": bot_id}, {"$set": updates}
            )
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/api/master-broadcast")
async def api_master_broadcast_alias(request):
    """Broadcast à tous les users d'un bot via ID_CODE"""
    try:
        data    = await request.json()
        id_code = data.get("id_code", "").strip().upper()
        message = data.get("message", "").strip()

        if not id_code or not message:
            return web.json_response({"success": False, "error": "id_code et message requis"}, status=400)

        bot_id, id_data, error = await resolve_bot_id_from_id_code(id_code)
        if error:
            return web.json_response({"success": False, "error": error})

        # Récupérer les users du bot et broadcaster en arrière-plan
        asyncio.create_task(_do_broadcast(bot_id, message))
        return web.json_response({"success": True, "message": "Broadcast mis en file d'attente"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def _do_broadcast(bot_id: int, message: str):
    """Tâche asynchrone de broadcast"""
    try:
        from plugins.clone import cloned_bots
        if bot_id in cloned_bots:
            bot_client = cloned_bots[bot_id]
            users = await db.get_bot_users(bot_id)
            sent = 0
            for uid in users:
                try:
                    await bot_client.send_message(uid, message, parse_mode="HTML")
                    sent += 1
                    await asyncio.sleep(0.05)
                except Exception:
                    pass
            logger.info(f"[BROADCAST] Bot {bot_id}: {sent}/{len(users)} messages envoyés")
    except Exception as e:
        logger.error(f"[BROADCAST] Erreur: {e}")


@routes.post("/api/regenerate-ids")
async def api_regenerate_ids_alias(request):
    """Alias de /api/master/regenerate-code"""
    try:
        data    = await request.json()
        id_code = data.get("id_code", "").strip().upper()
        if not id_code:
            return web.json_response({"success": False, "error": "id_code manquant"}, status=400)
        bot_id, id_data, error = await resolve_bot_id_from_id_code(id_code)
        if error:
            return web.json_response({"success": False, "error": error})
        new_codes = await db.regenerate_id_code(bot_id, id_data.get("master_id", OWNER_ID))
        if new_codes:
            return web.json_response({
                "success":   True,
                "new_id_pubs": new_codes["id_pubs"],
                "new_id_code": new_codes["id_code"],
            })
        return web.json_response({"success": False, "error": "Erreur lors de la régénération"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/api/verify-code")
async def api_verify_code_alias(request):
    """Alias de /api/master/login pour la compatibilité frontend"""
    try:
        data    = await request.json()
        id_code = data.get("id_code", "").strip().upper()
        if not id_code:
            return web.json_response({"success": False, "error": "id_code manquant"}, status=400)
        bot_id, id_data, error = await resolve_bot_id_from_id_code(id_code)
        if error:
            return web.json_response({"success": False, "valid": False, "error": error})
        return web.json_response({"success": True, "valid": True, "bot_id": bot_id})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/api/verify-pubs")
async def api_verify_pubs_alias(request):
    """Alias de /api/verify-id-pubs pour la compatibilité frontend"""
    try:
        data   = await request.json()
        id_pubs = data.get("id_pubs", "").strip().upper()
        if not id_pubs:
            return web.json_response({"success": False, "error": "id_pubs manquant"}, status=400)
        bot_id, bot_info, error = await resolve_bot_id_from_id_pubs(id_pubs)
        if error:
            return web.json_response({"success": False, "error": error})
        return web.json_response({"success": True, "valid": True, "bot_id": bot_id})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.get("/api/master-stats")
async def api_master_stats_alias(request):
    """Stats d'un bot via ID_CODE (GET)"""
    try:
        id_code = request.query.get("id_code", "").strip().upper()
        if not id_code:
            return web.json_response({"success": False, "error": "id_code manquant"}, status=400)
        bot_id, id_data, error = await resolve_bot_id_from_id_code(id_code)
        if error:
            return web.json_response({"success": False, "error": error})
        bot_data = await db.get_cloned_bot(bot_id)
        earnings = await db.get_bot_earnings(bot_id) or {}
        stats    = bot_data.get("stats", {}) if bot_data else {}
        # Récupérer retraits récents
        try:
            pending = await db.get_pending_withdrawals()
            bot_withdrawals = [w for w in pending if w.get("bot_id") == bot_id]
        except Exception:
            bot_withdrawals = []
        return web.json_response({
            "success":      True,
            "bot_username": bot_data.get("bot_username", "—") if bot_data else "—",
            "id_pubs":      id_data.get("id_pubs", ""),
            "balance":      earnings.get("balance", 0),
            "cpm_rate":     2.0,
            "min_withdrawal": 7,
            "ads_enabled":  bot_data.get("ads_enabled", True) if bot_data else True,
            "session_duration": bot_data.get("session_duration", 30) if bot_data else 30,
            "stats": {
                "total_impressions": stats.get("total_ads_watched", 0),
                "active_sessions":   stats.get("total_users", 0),
            },
            "recent_withdrawals":  bot_withdrawals,
            "daily_impressions":   [0] * 7,
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
