"""
ASGI config for academymap project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academymap.settings')

# Django ASGI 애플리케이션을 먼저 초기화
django_asgi_app = get_asgi_application()

# WebSocket 라우팅 임포트
from chat.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    # HTTP 요청 처리
    'http': django_asgi_app,
    
    # WebSocket 요청 처리
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
