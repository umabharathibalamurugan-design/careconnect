from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/tracking/(?P<society_id>\d+)/$', consumers.SocietyTrackingConsumer.as_asgi()),
]
