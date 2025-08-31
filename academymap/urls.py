from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.urls import path, include
import main.views
from main.enhanced_views import enhanced_academy_detail
from main.operator_views import (
    operator_dashboard, academy_analytics, inquiry_management, 
    promotion_management, academy_info_edit, respond_to_inquiry,
    create_promotion, api_academy_stats
)
from main.language_views import (
    language_selector, set_language, get_language_info, 
    detect_language, localized_content, language_stats
)
from main.performance_views import (
    performance_dashboard, performance_metrics_api, cache_management_api,
    database_optimization_api, system_health_api, production_readiness_api,
    performance_alert_api, performance_report_api
)
from rest_framework.routers import DefaultRouter
from main.enhanced_api_views import (
    EnhancedAcademyViewSet, AcademyAnalyticsViewSet
)

# Enhanced API Router
enhanced_router = DefaultRouter()
enhanced_router.register(r'academies', EnhancedAcademyViewSet, basename='enhanced-academy')
enhanced_router.register(r'analytics', AcademyAnalyticsViewSet, basename='academy-analytics')

# API 및 언어 독립적인 URL 패턴 (i18n 적용 안함)
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API 엔드포인트들 (언어 독립적)
    path('api/filtered_academies', main.views.filtered_academies, name='filtered_academies'),
    path('get_regions', main.views.get_regions, name='get_regions'),
    path('auth/', include('accounts.urls')),
    path('api/v1/', include('api.urls')),
    path('api/enhanced/', include(enhanced_router.urls)),
    path('chat/', include('chat.urls')),
    path('payment/', include('payment.urls')),
    path('ai-recommendation/', include('ai_recommendation.urls')),
    path('map_api/', include('map_api.urls')),
    path('data_update', main.views.data_update, name='data_update'),
    
    # 운영자 API
    path('operator/', include([
        path('api/inquiry/<int:inquiry_id>/respond/', respond_to_inquiry, name='respond_to_inquiry'),
        path('api/academy/<int:academy_id>/promotion/create/', create_promotion, name='create_promotion'),
        path('api/academy/<int:academy_id>/stats/', api_academy_stats, name='api_academy_stats'),
    ])),
    
    # 언어 선택 URL
    path('i18n/', include('django.conf.urls.i18n')),
    path('language-selector/', language_selector, name='language_selector'),
    path('set-language/', set_language, name='set_language'),
    path('api/language-info/', get_language_info, name='language_info'),
    path('api/detect-language/', detect_language, name='detect_language'),
    path('api/localized-content/<str:content_type>/', localized_content, name='localized_content'),
    path('api/language-stats/', language_stats, name='language_stats'),
    
    # 성능 모니터링 API (언어 독립적)
    path('performance/metrics/', performance_metrics_api, name='performance_metrics_api'),
    path('performance/cache/', cache_management_api, name='cache_management_api'),
    path('performance/database/', database_optimization_api, name='database_optimization_api'),
    path('performance/health/', system_health_api, name='system_health_api'),
    path('performance/production-readiness/', production_readiness_api, name='production_readiness_api'),
    path('performance/alert/', performance_alert_api, name='performance_alert_api'),
    path('performance/report/', performance_report_api, name='performance_report_api'),
]

# 다국어 지원이 필요한 사용자 인터페이스 URL 패턴
urlpatterns += i18n_patterns(
    path('main', main.views.main, name='main'),
    path('academy/<int:pk>', main.views.academy, name='academy'),
    path('enhanced-academy/<int:pk>/', enhanced_academy_detail, name='enhanced_academy_detail'),
    path('search', main.views.search, name='search'),
    path('', main.views.map, name='map'),
    path('map2/', main.views.map2, name='map2'),

    # 학원 관리 페이지
    path('manage/', main.views.manage, name='manage'),
    path('manage/add/', main.views.add_academy, name='add_academy'),
    path('manage/modify/<int:pk>/', main.views.modify_academy, name='modify_academy'),
    path('manage/delete/<int:pk>/', main.views.delete_academy, name='delete_academy'),
    
    # 운영자 대시보드 (사용자 인터페이스)
    path('operator/dashboard/', operator_dashboard, name='operator_dashboard'),
    path('operator/academy/<int:academy_id>/analytics/', academy_analytics, name='academy_analytics'),
    path('operator/academy/<int:academy_id>/inquiries/', inquiry_management, name='inquiry_management'),
    path('operator/academy/<int:academy_id>/promotions/', promotion_management, name='promotion_management'),
    path('operator/academy/<int:academy_id>/edit/', academy_info_edit, name='academy_info_edit'),
    
    # 데이터 분석 및 리포팅
    path('analytics/', include('main.analytics_urls')),
    
    # SEO 최적화
    path('seo/', include('main.seo_urls')),
    
    # 성능 모니터링 대시보드
    path('performance/', performance_dashboard, name='performance_dashboard'),
    
    prefix_default_language=False,  # 한국어를 기본으로 URL 앞에 /ko/ 없이 사용
)

# SEO 관련 직접 URL (include 없이)
try:
    from main.seo_views import sitemap_xml, robots_txt
    urlpatterns.extend([
        path('sitemap.xml', sitemap_xml, name='sitemap_xml'),
        path('robots.txt', robots_txt, name='robots_txt'),
    ])
except ImportError:
    pass

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)