from django.urls import path
from . import bookmark_views

urlpatterns = [
    # 즐겨찾기 관리
    path('bookmarks/', bookmark_views.bookmark_list_create, name='bookmark-list-create'),
    path('bookmarks/<int:pk>/', bookmark_views.bookmark_detail, name='bookmark-detail'),
    path('bookmarks/bulk-action/', bookmark_views.bookmark_bulk_action, name='bookmark-bulk-action'),
    path('bookmarks/stats/', bookmark_views.bookmark_stats, name='bookmark-stats'),
    
    # 즐겨찾기 폴더 관리
    path('bookmark-folders/', bookmark_views.bookmark_folder_list_create, name='bookmark-folder-list-create'),
    path('bookmark-folders/<int:pk>/', bookmark_views.bookmark_folder_detail, name='bookmark-folder-detail'),
    path('bookmark-folders/create-default/', bookmark_views.create_default_folder, name='create-default-folder'),
]