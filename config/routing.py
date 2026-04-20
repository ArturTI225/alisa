"""
Top-level WebSocket URL routes.
Keep per-app route lists in each app's routing module and compose them here.
"""

from chat.routing import websocket_urlpatterns as chat_ws
from accounts.routing import websocket_urlpatterns as accounts_ws

websocket_urlpatterns = chat_ws + accounts_ws
