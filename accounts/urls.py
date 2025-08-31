from django.urls import path, include
from . import views

app_name = 'accounts'

urlpatterns = [
    # 인증 관련
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # 프로필 관리
    path('profile/', views.profile, name='profile'),
    path('preferences/', views.preferences, name='preferences'),
    path('change-password/', views.change_password, name='change_password'),
    path('delete-account/', views.delete_account, name='delete_account'),
    
    # 즐겨찾기 관련
    path('', include('accounts.bookmark_urls')),
    
    # 리뷰 관련
    path('', include('accounts.review_urls')),
    
    # 비교 관련
    path('', include('accounts.comparison_urls')),
    
    # 테마 관련
    path('', include('accounts.theme_urls')),
    
    # 소셜 미디어 공유 관련
    path('social/', include('accounts.social_urls')),
]