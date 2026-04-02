from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Путь, по которому фронтенд будет подключаться к сокету
    re_path(r'ws/editor/$', consumers.EditorConsumer.as_asgi()),
]