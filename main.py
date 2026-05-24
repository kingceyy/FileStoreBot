import os
import sys
import asyncio
import logging

# Configuration logging avant tout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from aiohttp import web
import pyrogram.utils

# Configuration Pyrogram (évite les erreurs d'ID de canal)
pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

# Import web_server APRÈS la config de base
from plugins.web_server import web_server

async def main():
    # Démarrage du serveur web (Mini App + API)
    print("🌐 Démarrage du serveur web...")
    app = await web_server()
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Port Render (10000 par défaut, ou 8000/8080 en local)
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Serveur web actif sur le port {port}")
    print(f"🌍 URL: http://localhost:{port} (local) ou votre URL Render")

    # Démarrage du bot Telegram
    print("🤖 Démarrage du bot Telegram...")
    
    # Import ICI, juste avant de créer l'instance
    from bot import Bot
    
    # CRÉER L'INSTANCE BOT
    bot = Bot()
    
    # ============================================================
    # IMPORT DES PLUGINS - ORDRE CRITIQUE
    # start.py doit être chargé en PREMIER car il définit admin = filters.create(check_admin)
    # Les autres plugins utilisent admin depuis helper_func.py
    # ============================================================
    print("📦 Chargement des plugins...")
    try:
        # 1. Plugins core (ordre important)
        import plugins.start           # /start - DÉFINIT admin = filters.create(check_admin)
        import plugins.cbb             # Callbacks (help, about, close, etc.)
        
        # 2. Plugins qui utilisent admin depuis helper_func
        import plugins.link_generator  # /batch, /genlink, /custom_batch
        import plugins.channel_post    # Post dans le canal DB
        import plugins.admin           # Commandes admin (/add_admin, /deladmin, etc.)
        import plugins.useless         # /stats, /users, /dlt_time, /check_dlt_time
        
        # 3. Plugins système
        import plugins.clone           # /clone
        import plugins.gestion         # /gestion
        import plugins.list_bots       # /list, /bots
        import plugins.stats           # /stats
        print("✅ Tous les plugins chargés avec succès!")
    except Exception as e:
        print(f"❌ Erreur chargement plugins: {e}")
        import traceback
        traceback.print_exc()
    # ============================================================
    
    # DÉMARRER LE BOT (charge les plugins et démarre les handlers)
    await bot.start()
    
    print("✅ Bot démarré avec succès!")
    print("⏳ Le bot est en ligne et écoute les messages...")

    # Lancement de la tâche de nettoyage des sessions en arrière-plan
    try:
        from plugins.gestion import cleanup_sessions
        asyncio.create_task(cleanup_sessions())
        print("🧹 Tâche de nettoyage des sessions lancée en arrière-plan")
    except Exception as e:
        print(f"⚠️ Impossible de lancer cleanup_sessions : {e}")

    # ============================================================
    # DÉMARRAGE DES BOTS CLONÉS — AVEC TIMEOUT ET PROTECTION
    # ============================================================
    try:
        print("🔄 Initialisation des bots clonés...")
        from plugins.clone import init_cloned_bots
        
        # Timeout de 60 secondes max pour ne pas bloquer le bot mère
        await asyncio.wait_for(init_cloned_bots(), timeout=60.0)
        print("✅ Bots clonés initialisés!")
    except asyncio.TimeoutError:
        print("⚠️ Timeout: démarrage des clones trop long — bot mère continue normalement")
    except Exception as e:
        print(f"⚠️ Erreur lors du démarrage des bots clonés: {e}")
        import traceback
        traceback.print_exc()
    # ============================================================

    # Garder le programme en vie indéfiniment
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
