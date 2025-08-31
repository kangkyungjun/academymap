from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'ai_recommendation'

# API 라우터 설정
router = DefaultRouter()
router.register(r'preferences', views.UserPreferenceViewSet, basename='user-preference')
router.register(r'behaviors', views.UserBehaviorViewSet, basename='user-behavior')
router.register(r'recommendations', views.RecommendationViewSet, basename='recommendation')

urlpatterns = [
    # API 엔드포인트
    path('api/', include(router.urls)),
    
    # 행동 추적 (비인증 사용자도 가능)
    path('api/track/', views.BehaviorTrackingView.as_view(), name='behavior-tracking'),
    
    # 추천 시스템 분석
    path('api/analytics/', views.RecommendationAnalyticsView.as_view(), name='analytics'),
    
    # 유지보수 API
    path('api/maintenance/', views.RecommendationMaintenanceView.as_view(), name='maintenance'),
]