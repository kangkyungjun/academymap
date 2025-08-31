"""
데이터 분석 및 리포팅 URL 설정
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

try:
    from . import analytics_views
    from .analytics_api import (
        AnalyticsReportViewSet, UserAnalyticsViewSet, AcademyAnalyticsViewSet,
        RegionalAnalyticsViewSet, MarketTrendViewSet, ConversionFunnelViewSet,
        CustomDashboardViewSet, AnalyticsDataViewSet
    )
    
    # REST API 라우터 설정
    router = DefaultRouter()
    router.register(r'reports', AnalyticsReportViewSet, basename='analytics-reports')
    router.register(r'user-analytics', UserAnalyticsViewSet, basename='user-analytics')
    router.register(r'academy-analytics', AcademyAnalyticsViewSet, basename='academy-analytics')
    router.register(r'regional-analytics', RegionalAnalyticsViewSet, basename='regional-analytics')
    router.register(r'market-trends', MarketTrendViewSet, basename='market-trends')
    router.register(r'conversion-funnel', ConversionFunnelViewSet, basename='conversion-funnel')
    router.register(r'dashboards', CustomDashboardViewSet, basename='custom-dashboards')
    router.register(r'data', AnalyticsDataViewSet, basename='analytics-data')

    app_name = 'analytics'

    urlpatterns = [
        # 웹 인터페이스 URL
        path('', analytics_views.analytics_dashboard, name='dashboard'),
        path('reports/', analytics_views.analytics_reports, name='reports'),
        path('reports/<int:report_id>/', analytics_views.analytics_report_detail, name='report_detail'),
        path('reports/create/', analytics_views.analytics_report_create, name='report_create'),
        
        path('academy/<int:academy_id>/', analytics_views.academy_analytics, name='academy_analytics'),
        path('regional/', analytics_views.regional_analytics, name='regional_analytics'),
        path('trends/', analytics_views.market_trends, name='market_trends'),
        path('funnel/', analytics_views.conversion_funnel, name='conversion_funnel'),
        
        path('dashboard/<int:dashboard_id>/', analytics_views.custom_dashboard, name='custom_dashboard'),
        path('dashboard/', analytics_views.custom_dashboard, name='default_dashboard'),
        
        path('export/', analytics_views.export_analytics_data, name='export_data'),
        
        # REST API URL
        path('api/', include(router.urls)),
    ]

except ImportError:
    # 마이그레이션 중이거나 모델이 아직 생성되지 않은 경우
    app_name = 'analytics'
    urlpatterns = []