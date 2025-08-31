"""
데이터 분석 및 리포팅 Admin 설정
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count

try:
    from .analytics_models import (
        AnalyticsReport, UserAnalytics, AcademyAnalytics,
        RegionalAnalytics, MarketTrend, ConversionFunnel, CustomDashboard
    )

    @admin.register(AnalyticsReport)
    class AnalyticsReportAdmin(admin.ModelAdmin):
        list_display = [
            'title', 'report_type', 'category', 'date_range', 
            'generated_by', 'generated_at', 'is_public'
        ]
        list_filter = [
            'report_type', 'category', 'is_public', 
            'generated_at', 'generated_by'
        ]
        search_fields = ['title', 'summary', 'generated_by__username']
        readonly_fields = ['generated_at', 'generated_by']
        date_hierarchy = 'generated_at'
        list_per_page = 50
        
        fieldsets = (
            ('기본 정보', {
                'fields': ('title', 'report_type', 'category', 'is_public')
            }),
            ('기간 설정', {
                'fields': ('start_date', 'end_date')
            }),
            ('리포트 내용', {
                'fields': ('summary', 'data', 'insights', 'recommendations')
            }),
            ('메타 정보', {
                'fields': ('generated_at', 'generated_by'),
                'classes': ('collapse',)
            })
        )
        
        def date_range(self, obj):
            """날짜 범위 표시"""
            return f"{obj.start_date} ~ {obj.end_date}"
        date_range.short_description = "분석 기간"
        
        def save_model(self, request, obj, form, change):
            """리포트 저장 시 생성자 설정"""
            if not change:  # 새로운 객체인 경우
                obj.generated_by = request.user
            super().save_model(request, obj, form, change)
        
        actions = ['make_public', 'make_private']
        
        def make_public(self, request, queryset):
            """리포트 공개"""
            updated = queryset.update(is_public=True)
            self.message_user(request, f'{updated}개 리포트가 공개되었습니다.')
        make_public.short_description = '선택된 리포트 공개'
        
        def make_private(self, request, queryset):
            """리포트 비공개"""
            updated = queryset.update(is_public=False)
            self.message_user(request, f'{updated}개 리포트가 비공개되었습니다.')
        make_private.short_description = '선택된 리포트 비공개'

    @admin.register(UserAnalytics)
    class UserAnalyticsAdmin(admin.ModelAdmin):
        list_display = [
            'date', 'total_users', 'new_users', 'returning_users',
            'total_sessions', 'bounce_rate_display', 'updated_at'
        ]
        list_filter = ['date', 'created_at']
        search_fields = ['date']
        readonly_fields = ['created_at', 'updated_at']
        date_hierarchy = 'date'
        ordering = ['-date']
        
        def bounce_rate_display(self, obj):
            """이탈률 표시 (색상 포함)"""
            rate = obj.bounce_rate
            if rate > 70:
                color = 'red'
            elif rate > 50:
                color = 'orange'
            else:
                color = 'green'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color, rate
            )
        bounce_rate_display.short_description = "이탈률"
        
        fieldsets = (
            ('기본 정보', {
                'fields': ('date',)
            }),
            ('사용자 통계', {
                'fields': ('total_users', 'new_users', 'returning_users')
            }),
            ('세션 통계', {
                'fields': ('total_sessions', 'avg_session_duration', 'bounce_rate')
            }),
            ('페이지 뷰', {
                'fields': ('total_pageviews', 'unique_pageviews', 'avg_pages_per_session')
            }),
            ('트래픽 소스', {
                'fields': ('organic_traffic', 'direct_traffic', 'referral_traffic', 'social_traffic')
            }),
            ('디바이스 정보', {
                'fields': ('desktop_users', 'mobile_users', 'tablet_users')
            }),
            ('시스템 정보', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            })
        )

    @admin.register(AcademyAnalytics)
    class AcademyAnalyticsAdmin(admin.ModelAdmin):
        list_display = [
            'academy', 'date', 'views', 'unique_views', 
            'bookmarks', 'inquiries', 'conversion_rate_display'
        ]
        list_filter = [
            'date', 'academy__시도명', 'academy__시군구명',
            'created_at'
        ]
        search_fields = ['academy__상호명', 'academy__도로명주소']
        readonly_fields = ['created_at', 'updated_at']
        date_hierarchy = 'date'
        ordering = ['-date', '-views']
        
        def conversion_rate_display(self, obj):
            """전환율 표시 (색상 포함)"""
            rate = obj.conversion_rate
            if rate > 5:
                color = 'green'
            elif rate > 2:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="color: {};">{:.2f}%</span>',
                color, rate
            )
        conversion_rate_display.short_description = "전환율"
        
        fieldsets = (
            ('기본 정보', {
                'fields': ('academy', 'date')
            }),
            ('조회 통계', {
                'fields': ('views', 'unique_views', 'avg_view_duration')
            }),
            ('참여 통계', {
                'fields': ('bookmarks', 'shares', 'inquiries')
            }),
            ('전환 통계', {
                'fields': ('conversion_rate', 'inquiry_conversion')
            }),
            ('검색 및 순위', {
                'fields': ('top_keywords', 'recommendation_score', 'popularity_rank')
            }),
            ('시스템 정보', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            })
        )

    @admin.register(RegionalAnalytics)
    class RegionalAnalyticsAdmin(admin.ModelAdmin):
        list_display = [
            'region_display', 'date', 'total_academies', 
            'total_views', 'avg_rating_display', 'competition_index_display'
        ]
        list_filter = ['region_sido', 'date', 'created_at']
        search_fields = ['region_sido', 'region_sigungu']
        readonly_fields = ['created_at', 'updated_at']
        date_hierarchy = 'date'
        ordering = ['-date', 'region_sido', 'region_sigungu']
        
        def region_display(self, obj):
            """지역 표시"""
            return f"{obj.region_sido} {obj.region_sigungu}"
        region_display.short_description = "지역"
        
        def avg_rating_display(self, obj):
            """평균 평점 표시 (별점)"""
            rating = obj.avg_rating
            stars = '★' * int(rating) + '☆' * (5 - int(rating))
            return format_html(
                '<span title="{:.2f}">{}</span>',
                rating, stars
            )
        avg_rating_display.short_description = "평균 평점"
        
        def competition_index_display(self, obj):
            """경쟁 지수 표시"""
            index = obj.competition_index
            if index > 0.7:
                color = 'red'
                level = '높음'
            elif index > 0.4:
                color = 'orange'  
                level = '보통'
            else:
                color = 'green'
                level = '낮음'
            return format_html(
                '<span style="color: {};">{:.2f} ({})</span>',
                color, index, level
            )
        competition_index_display.short_description = "경쟁 지수"
        
        fieldsets = (
            ('지역 정보', {
                'fields': ('region_sido', 'region_sigungu', 'date')
            }),
            ('학원 통계', {
                'fields': ('total_academies', 'active_academies')
            }),
            ('사용자 관심도', {
                'fields': ('total_views', 'unique_visitors', 'avg_rating')
            }),
            ('수강료 통계', {
                'fields': ('avg_tuition', 'tuition_range_min', 'tuition_range_max')
            }),
            ('시장 분석', {
                'fields': ('subject_distribution', 'competition_index', 'market_saturation')
            }),
            ('시스템 정보', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            })
        )

    @admin.register(MarketTrend)
    class MarketTrendAdmin(admin.ModelAdmin):
        list_display = [
            'trend_type', 'date', 'trend_score_display', 
            'change_rate_display', 'change_direction', 'confidence_level_display'
        ]
        list_filter = ['trend_type', 'change_direction', 'date', 'created_at']
        search_fields = ['description']
        readonly_fields = ['created_at', 'updated_at']
        date_hierarchy = 'date'
        ordering = ['-date', 'trend_type']
        
        def trend_score_display(self, obj):
            """트렌드 점수 표시"""
            score = obj.trend_score
            if score > 0.7:
                color = 'green'
            elif score > 0.4:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="color: {};">{:.2f}</span>',
                color, score
            )
        trend_score_display.short_description = "트렌드 점수"
        
        def change_rate_display(self, obj):
            """변화율 표시"""
            rate = obj.change_rate
            if rate > 0:
                color = 'green'
                icon = '↗'
            elif rate < 0:
                color = 'red'
                icon = '↘'
            else:
                color = 'gray'
                icon = '→'
            return format_html(
                '<span style="color: {};">{} {:.1f}%</span>',
                color, icon, rate
            )
        change_rate_display.short_description = "변화율"
        
        def confidence_level_display(self, obj):
            """신뢰도 표시"""
            level = obj.confidence_level
            if level > 0.8:
                color = 'green'
                text = '높음'
            elif level > 0.6:
                color = 'orange'
                text = '보통'
            else:
                color = 'red'
                text = '낮음'
            return format_html(
                '<span style="color: {};">{:.0f}% ({})</span>',
                color, level * 100, text
            )
        confidence_level_display.short_description = "신뢰도"

    @admin.register(ConversionFunnel)
    class ConversionFunnelAdmin(admin.ModelAdmin):
        list_display = [
            'date', 'stage_1_visitors', 'stage_5_inquiry',
            'overall_conversion_display', 'updated_at'
        ]
        list_filter = ['date', 'created_at']
        readonly_fields = ['created_at', 'updated_at']
        date_hierarchy = 'date'
        ordering = ['-date']
        
        def overall_conversion_display(self, obj):
            """전체 전환율 표시"""
            rate = obj.overall_conversion
            if rate > 5:
                color = 'green'
            elif rate > 2:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="color: {};">{:.2f}%</span>',
                color, rate
            )
        overall_conversion_display.short_description = "전체 전환율"
        
        fieldsets = (
            ('기본 정보', {
                'fields': ('date',)
            }),
            ('퍼널 단계', {
                'fields': (
                    'stage_1_visitors', 'stage_2_search', 'stage_3_view',
                    'stage_4_detail', 'stage_5_inquiry'
                )
            }),
            ('전환율', {
                'fields': (
                    'search_conversion', 'view_conversion', 'detail_conversion',
                    'inquiry_conversion', 'overall_conversion'
                )
            }),
            ('이탈률', {
                'fields': (
                    'stage_1_drop', 'stage_2_drop', 'stage_3_drop', 'stage_4_drop'
                )
            }),
            ('시스템 정보', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            })
        )

    @admin.register(CustomDashboard)
    class CustomDashboardAdmin(admin.ModelAdmin):
        list_display = [
            'name', 'user', 'is_default', 'is_shared', 
            'shared_count', 'created_at'
        ]
        list_filter = ['is_default', 'is_shared', 'created_at', 'user']
        search_fields = ['name', 'description', 'user__username']
        readonly_fields = ['created_at', 'updated_at']
        filter_horizontal = ['shared_with']
        
        def shared_count(self, obj):
            """공유 대상 수"""
            count = obj.shared_with.count()
            return f"{count}명" if count > 0 else "-"
        shared_count.short_description = "공유 대상"
        
        fieldsets = (
            ('기본 정보', {
                'fields': ('user', 'name', 'description')
            }),
            ('대시보드 설정', {
                'fields': ('layout_config', 'widget_config', 'filter_config')
            }),
            ('공유 설정', {
                'fields': ('is_shared', 'shared_with', 'is_default')
            }),
            ('시스템 정보', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            })
        )
        
        actions = ['make_default', 'make_shared']
        
        def make_default(self, request, queryset):
            """기본 대시보드 설정"""
            for dashboard in queryset:
                # 기존 기본 대시보드 해제
                CustomDashboard.objects.filter(
                    user=dashboard.user, is_default=True
                ).update(is_default=False)
                # 새 기본 대시보드 설정
                dashboard.is_default = True
                dashboard.save()
            self.message_user(request, f'{queryset.count()}개 대시보드가 기본으로 설정되었습니다.')
        make_default.short_description = '기본 대시보드로 설정'
        
        def make_shared(self, request, queryset):
            """대시보드 공유 설정"""
            updated = queryset.update(is_shared=True)
            self.message_user(request, f'{updated}개 대시보드가 공유되었습니다.')
        make_shared.short_description = '선택된 대시보드 공유'

except ImportError:
    # 모델들이 아직 마이그레이션되지 않은 경우
    pass