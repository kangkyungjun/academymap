from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import recommendation_views

# Router 설정
router = DefaultRouter()
router.register(r'user-preferences', recommendation_views.UserPreferenceViewSet, basename='user-preferences')
router.register(r'recommendations', recommendation_views.RecommendationViewSet, basename='recommendations')
router.register(r'behavior-tracking', recommendation_views.BehaviorTrackingViewSet, basename='behavior-tracking')
router.register(r'recommendation-history', recommendation_views.RecommendationHistoryViewSet, basename='recommendation-history')
router.register(r'admin-recommendations', recommendation_views.AdminRecommendationViewSet, basename='admin-recommendations')

# URL 패턴
urlpatterns = router.urls