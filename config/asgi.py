import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# django_asgi_app must be created before importing anything that touches models
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from config.ws_auth import JWTAuthMiddleware
import tracking.routing
import notifications.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        URLRouter(tracking.routing.websocket_urlpatterns + notifications.routing.websocket_urlpatterns)
    ),
})
