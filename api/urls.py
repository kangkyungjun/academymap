from django.urls import path
from .views import (
    AcademyListAPIView,
    AcademyDetailAPIView,
    AcademyNearbyAPIView,
    AcademySearchAPIView,
    PopularAcademiesAPIView,
    RecommendedAcademiesAPIView,
    AcademyListAPIViewLegacy,
    categories_view,
    regions_view,
    academy_stats_view,
    autocomplete_view,
    api_info_view
)

app_name = 'api'

urlpatterns = [
    # API 정보 및 헬스체크
    path('', api_info_view, name='api_info'),
    path('health/', api_info_view, name='api_health'),
    
    # 메인 API 엔드포인트들
    path('academies/', AcademyListAPIView.as_view(), name='academy_list'),
    path('academies/<int:pk>/', AcademyDetailAPIView.as_view(), name='academy_detail'),
    path('academies/nearby/', AcademyNearbyAPIView.as_view(), name='academy_nearby'),
    path('academies/search/', AcademySearchAPIView.as_view(), name='academy_search'),
    
    # 특화 학원 목록
    path('academies/popular/', PopularAcademiesAPIView.as_view(), name='academy_popular'),
    path('academies/recommended/', RecommendedAcademiesAPIView.as_view(), name='academy_recommended'),
    
    # 메타데이터 및 유틸리티 엔드포인트들
    path('categories/', categories_view, name='categories'),
    path('regions/', regions_view, name='regions'),
    path('stats/', academy_stats_view, name='academy_stats'),
    path('autocomplete/', autocomplete_view, name='autocomplete'),
    
    # 하위 호환성 (기존 API)
    path('legacy/academies/', AcademyListAPIViewLegacy.as_view(), name='academy_list_legacy'),
]
