from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/dashboard/(?P<barber_id>\w+)/$', consumers.BarberDashboardConsumer.as_asgi()),
]
