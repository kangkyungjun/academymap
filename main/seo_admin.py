"""
SEO 최적화 Admin 설정
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg

try:
    from .seo_models import (
        SEOMetadata, AcademySEO, SearchKeyword, 
        SitemapEntry, RobotsRule, SEOAudit
    )
    from .seo_services import AcademySEOService, SitemapService

    @admin.register(SEOMetadata)
    class SEOMetadataAdmin(admin.ModelAdmin):
        list_display = [
            'path', 'page_type', 'title_truncated', 'description_truncated',
            'priority', 'is_active', 'updated_at'
        ]
        list_filter = ['page_type', 'is_active', 'changefreq', 'created_at']
        search_fields = ['path', 'title', 'description', 'keywords']
        readonly_fields = ['created_at', 'updated_at']
        list_editable = ['is_active', 'priority']
        
        fieldsets = (
            ('기본 정보', {
                'fields': ('page_type', 'path', 'is_active')
            }),
            ('SEO 메타데이터', {
                'fields': ('title', 'description', 'keywords')
            }),
            ('Open Graph', {
                'fields': ('og_title', 'og_description', 'og_image'),
                'classes': ('collapse',)
            }),
            ('Twitter Card', {
                'fields': ('twitter_title', 'twitter_description', 'twitter_image'),
                'classes': ('collapse',)
            }),
            ('사이트맵 설정', {
                'fields': ('priority', 'changefreq')
            }),
            ('구조화된 데이터', {
                'fields': ('schema_type', 'schema_data'),
                'classes': ('collapse',)
            }),
            ('시스템 정보', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            })
        )
        
        def title_truncated(self, obj):
            """제목 축약 표시"""
            if len(obj.title) > 50:
                return f"{obj.title[:47]}..."
            return obj.title
        title_truncated.short_description = "제목"
        
        def description_truncated(self, obj):
            """설명 축약 표시"""
            if len(obj.description) > 60:
                return f"{obj.description[:57]}..."
            return obj.description
        description_truncated.short_description = "설명"

    @admin.register(AcademySEO)
    class AcademySEOAdmin(admin.ModelAdmin):
        list_display = [
            'academy', 'seo_title_truncated', 'seo_score_display', 
            'review_count', 'average_rating', 'last_optimized'
        ]
        list_filter = [
            'last_optimized', 'academy__시도명', 'academy__시군구명'
        ]
        search_fields = [
            'academy__상호명', 'seo_title', 'seo_keywords', 'slug'
        ]
        readonly_fields = ['created_at', 'last_optimized', 'seo_score']
        list_per_page = 50
        
        fieldsets = (
            ('학원 정보', {
                'fields': ('academy', 'slug')
            }),
            ('SEO 최적화', {
                'fields': ('seo_title', 'seo_description', 'seo_keywords', 'seo_score')
            }),
            ('지역 SEO', {
                'fields': ('local_keywords', 'business_hours')
            }),
            ('리뷰 정보', {
                'fields': ('review_count', 'average_rating')
            }),
            ('소셜 미디어', {
                'fields': ('facebook_url', 'instagram_url', 'blog_url'),
                'classes': ('collapse',)
            }),
            ('시스템 정보', {
                'fields': ('created_at', 'last_optimized'),
                'classes': ('collapse',)
            })
        )
        
        def seo_title_truncated(self, obj):
            """SEO 제목 축약 표시"""
            if len(obj.seo_title) > 40:
                return f"{obj.seo_title[:37]}..."
            return obj.seo_title
        seo_title_truncated.short_description = "SEO 제목"
        
        def seo_score_display(self, obj):
            """SEO 점수 색상 표시"""
            score = obj.seo_score
            if score >= 80:
                color = 'green'
            elif score >= 60:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, score
            )
        seo_score_display.short_description = "SEO 점수"
        
        actions = ['optimize_seo', 'recalculate_score']
        
        def optimize_seo(self, request, queryset):
            """SEO 최적화 실행"""
            optimized_count = 0
            for academy_seo in queryset:
                if AcademySEOService.optimize_academy_seo(academy_seo.academy):
                    optimized_count += 1
            
            self.message_user(request, f'{optimized_count}개 학원 SEO가 최적화되었습니다.')
        optimize_seo.short_description = '선택된 학원 SEO 최적화'
        
        def recalculate_score(self, request, queryset):
            """SEO 점수 재계산"""
            for academy_seo in queryset:
                academy_seo.seo_score = AcademySEOService.calculate_seo_score(
                    academy_seo.academy, academy_seo
                )
                academy_seo.save(update_fields=['seo_score'])
            
            self.message_user(request, f'{queryset.count()}개 학원의 SEO 점수가 재계산되었습니다.')
        recalculate_score.short_description = 'SEO 점수 재계산'

    @admin.register(SearchKeyword)
    class SearchKeywordAdmin(admin.ModelAdmin):
        list_display = [
            'keyword', 'category', 'search_count', 'click_count', 
            'ctr_display', 'region_display', 'date'
        ]
        list_filter = [
            'category', 'date', 'region_sido', 'is_trending'
        ]
        search_fields = ['keyword', 'region_sido', 'region_sigungu']
        readonly_fields = ['created_at', 'updated_at', 'ctr']
        date_hierarchy = 'date'
        ordering = ['-date', '-search_count']
        
        fieldsets = (
            ('키워드 정보', {
                'fields': ('keyword', 'category', 'date')
            }),
            ('지역 정보', {
                'fields': ('region_sido', 'region_sigungu')
            }),
            ('통계 정보', {
                'fields': (
                    'search_count', 'click_count', 'impression_count', 'ctr'
                )
            }),
            ('트렌드 정보', {
                'fields': ('trend_score', 'is_trending')
            }),
            ('시스템 정보', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            })
        )
        
        def ctr_display(self, obj):
            """클릭률 표시"""
            if obj.ctr > 5:
                color = 'green'
            elif obj.ctr > 2:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="color: {};">{:.2f}%</span>',
                color, obj.ctr
            )
        ctr_display.short_description = "CTR"
        
        def region_display(self, obj):
            """지역 표시"""
            if obj.region_sido and obj.region_sigungu:
                return f"{obj.region_sido} {obj.region_sigungu}"
            elif obj.region_sido:
                return obj.region_sido
            return "-"
        region_display.short_description = "지역"

    @admin.register(SitemapEntry)
    class SitemapEntryAdmin(admin.ModelAdmin):
        list_display = [
            'url_truncated', 'page_type', 'priority', 'changefreq', 
            'is_active', 'lastmod'
        ]
        list_filter = ['page_type', 'changefreq', 'is_active', 'created_at']
        search_fields = ['url']
        readonly_fields = ['created_at']
        list_editable = ['is_active', 'priority', 'changefreq']
        ordering = ['-priority', 'page_type']
        
        fieldsets = (
            ('URL 정보', {
                'fields': ('url', 'page_type', 'is_active')
            }),
            ('사이트맵 설정', {
                'fields': ('priority', 'changefreq', 'lastmod')
            }),
            ('시스템 정보', {
                'fields': ('created_at',),
                'classes': ('collapse',)
            })
        )
        
        def url_truncated(self, obj):
            """URL 축약 표시"""
            if len(obj.url) > 50:
                return f"{obj.url[:47]}..."
            return obj.url
        url_truncated.short_description = "URL"
        
        actions = ['regenerate_sitemap']
        
        def regenerate_sitemap(self, request, queryset):
            """사이트맵 재생성"""
            entries_count = SitemapService.generate_sitemap_entries()
            self.message_user(request, f'사이트맵이 재생성되었습니다. ({entries_count}개 엔트리)')
        regenerate_sitemap.short_description = '사이트맵 재생성'

    @admin.register(RobotsRule)
    class RobotsRuleAdmin(admin.ModelAdmin):
        list_display = [
            'user_agent', 'rule_type', 'path', 'is_active', 'order'
        ]
        list_filter = ['rule_type', 'is_active', 'user_agent']
        search_fields = ['user_agent', 'path']
        readonly_fields = ['created_at']
        list_editable = ['is_active', 'order']
        ordering = ['order', 'user_agent']
        
        fieldsets = (
            ('규칙 정보', {
                'fields': ('user_agent', 'rule_type', 'path')
            }),
            ('설정', {
                'fields': ('is_active', 'order')
            }),
            ('시스템 정보', {
                'fields': ('created_at',),
                'classes': ('collapse',)
            })
        )

    @admin.register(SEOAudit)
    class SEOAuditAdmin(admin.ModelAdmin):
        list_display = [
            'url_truncated', 'overall_score_display', 'audit_date',
            'load_time', 'page_size_kb'
        ]
        list_filter = ['audit_date', 'overall_score']
        search_fields = ['url']
        readonly_fields = ['audit_date']
        ordering = ['-audit_date', '-overall_score']
        
        fieldsets = (
            ('감사 정보', {
                'fields': ('url', 'audit_date', 'overall_score')
            }),
            ('세부 점수', {
                'fields': (
                    'title_score', 'description_score', 'keywords_score',
                    'content_score', 'performance_score'
                )
            }),
            ('성능 정보', {
                'fields': ('load_time', 'page_size')
            }),
            ('이슈 및 권장사항', {
                'fields': ('issues', 'recommendations'),
                'classes': ('collapse',)
            })
        )
        
        def url_truncated(self, obj):
            """URL 축약 표시"""
            if len(obj.url) > 40:
                return f"{obj.url[:37]}..."
            return obj.url
        url_truncated.short_description = "URL"
        
        def overall_score_display(self, obj):
            """전체 점수 색상 표시"""
            score = obj.overall_score
            if score >= 80:
                color = 'green'
            elif score >= 60:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, score
            )
        overall_score_display.short_description = "전체 점수"
        
        def page_size_kb(self, obj):
            """페이지 크기 (KB)"""
            return f"{obj.page_size} KB" if obj.page_size else "-"
        page_size_kb.short_description = "페이지 크기"

except ImportError:
    # 모델들이 아직 마이그레이션되지 않은 경우
    pass