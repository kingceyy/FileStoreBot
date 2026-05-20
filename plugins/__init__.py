# plugins/__init__.py
import sys
import os
from aiohttp import web
from .route import routes


# Ajouter la racine au path pour les imports
parent_dir = os.path.dirname(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Charger les commandes
from . import clone
from . import gestion
from . import list_bots
from . import stats

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app