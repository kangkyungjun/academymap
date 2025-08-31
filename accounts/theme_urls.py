from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import theme_views

# Router 설정
router = DefaultRouter()
router.register(r'theme-config', theme_views.ThemeConfigurationViewSet, basename='theme-config')
router.register(r'preset-themes', theme_views.PresetThemeViewSet, basename='preset-themes')
router.register(r'theme-history', theme_views.ThemeHistoryViewSet, basename='theme-history')
router.register(r'theme-utils', theme_views.ThemeUtilityViewSet, basename='theme-utils')
router.register(r'admin-themes', theme_views.AdminThemeViewSet, basename='admin-themes')

# URL 패턴
urlpatterns = router.urls