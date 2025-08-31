"""
SEO 최적화 URL 설정
"""

from django.urls import path

try:
    from . import seo_views

    app_name = 'seo'

    urlpatterns = [
        # 공개 SEO 엔드포인트
        path('sitemap.xml', seo_views.sitemap_xml, name='sitemap_xml'),
        path('robots.txt', seo_views.robots_txt, name='robots_txt'),
        
        # SEO API
        path('api/meta/', seo_views.seo_meta_api, name='meta_api'),
        path('api/track-search/', seo_views.track_search_api, name='track_search'),
        path('api/track-click/', seo_views.track_click_api, name='track_click'),
        
        # SEO 관리 (관리자용)
        path('dashboard/', seo_views.seo_dashboard, name='dashboard'),
        path('academies/', seo_views.academy_seo_list, name='academy_list'),
        path('academies/<int:academy_id>/', seo_views.academy_seo_detail, name='academy_detail'),
        path('keywords/', seo_views.keyword_analytics, name='keyword_analytics'),
        path('sitemap/', seo_views.sitemap_management, name='sitemap_management'),
        
        # SEO 작업 API
        path('api/regenerate-sitemap/', seo_views.regenerate_sitemap, name='regenerate_sitemap'),
        path('api/optimize-bulk/', seo_views.optimize_academy_seo_bulk, name='optimize_bulk'),
    ]

except ImportError:
    # 마이그레이션 중이거나 모델이 아직 생성되지 않은 경우
    app_name = 'seo'
    urlpatterns = []