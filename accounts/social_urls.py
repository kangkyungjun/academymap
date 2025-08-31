from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import social_views

# Router 설정
router = DefaultRouter()
router.register(r'platforms', social_views.SocialPlatformViewSet, basename='social-platforms')
router.register(r'shares', social_views.SocialShareViewSet, basename='social-shares')
router.register(r'popular', social_views.PopularContentViewSet, basename='popular-content')
router.register(r'analytics', social_views.ShareAnalyticsViewSet, basename='share-analytics')
router.register(r'admin', social_views.AdminSocialViewSet, basename='admin-social')
router.register(r'cache', social_views.SocialCacheViewSet, basename='social-cache')

# URL 패턴
urlpatterns = router.urls