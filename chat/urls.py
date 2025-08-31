from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API Router
router = DefaultRouter()
router.register(r'rooms', views.ChatRoomViewSet, basename='chatroom')
router.register(r'messages', views.ChatMessageViewSet, basename='chatmessage')

app_name = 'chat'

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    path('api/notifications/', views.chat_notifications, name='chat_notifications'),
    path('api/notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('api/unread-count/', views.unread_message_count, name='unread_message_count'),
    path('api/rooms/<str:room_id>/online-users/', views.online_users, name='online_users'),
    
    # Template URLs
    path('', views.chat_room_list, name='room_list'),
    path('room/<str:room_id>/', views.chat_room_detail, name='room_detail'),
    path('create/<int:academy_id>/', views.create_chat_room, name='create_room'),
]