"""
Enhanced Academy 관리를 위한 Django Admin 설정
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

try:
    from .academy_enhancements import (
        AcademyDetailInfo, AcademyGallery, AcademyStatistics,
        AcademyViewHistory, AcademyFAQ, AcademyNews, AcademyComparison
    )

    @admin.register(AcademyDetailInfo)
    class AcademyDetailInfoAdmin(admin.ModelAdmin):
        list_display = ['academy', 'total_classrooms', 'total_teachers', 'max_students_per_class', 'established_year']
        list_filter = ['established_year', 'has_scholarship']
        search_fields = ['academy__상호명', 'website_url']
        readonly_fields = ['created_at', 'updated_at']
        
        fieldsets = (
            ('기본 정보', {
                'fields': ('academy', 'facilities', 'total_classrooms', 'max_students_per_class')
            }),
            ('교육 정보', {
                'fields': ('total_teachers', 'teacher_student_ratio', 'programs', 'special_programs')
            }),
            ('설립 정보', {
                'fields': ('established_year', 'website_url', 'social_media')
            }),
            ('학사 정보', {
                'fields': ('class_schedule', 'registration_fee', 'material_fee', 'has_scholarship')
            }),
            ('기타 정보', {
                'fields': ('parking_info', 'transportation_info', 'notice')
            }),
            ('시스템 정보', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            })
        )

    @admin.register(AcademyGallery)
    class AcademyGalleryAdmin(admin.ModelAdmin):
        list_display = ['academy', 'title', 'category', 'order', 'uploaded_at']
        list_filter = ['category', 'uploaded_at']
        search_fields = ['academy__상호명', 'title', 'description']
        list_editable = ['order']
        ordering = ['academy', 'order']
        
        def image_preview(self, obj):
            if obj.image_url:
                return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover;"/>', obj.image_url)
            return "이미지 없음"
        image_preview.short_description = "미리보기"
        
        list_display = ['academy', 'title', 'category', 'image_preview', 'order', 'uploaded_at']

    @admin.register(AcademyStatistics)
    class AcademyStatisticsAdmin(admin.ModelAdmin):
        list_display = ['academy', 'view_count', 'monthly_views', 'bookmark_count', 'average_rating', 'popularity_score']
        list_filter = ['last_updated', 'average_rating']
        search_fields = ['academy__상호명']
        readonly_fields = ['last_updated']
        
        fieldsets = (
            ('조회 통계', {
                'fields': ('academy', 'view_count', 'monthly_views')
            }),
            ('참여 통계', {
                'fields': ('bookmark_count', 'share_count', 'review_count')
            }),
            ('평가 정보', {
                'fields': ('average_rating', 'popularity_score')
            }),
            ('순위 정보', {
                'fields': ('local_rank', 'category_rank')
            }),
            ('시스템 정보', {
                'fields': ('last_updated',),
                'classes': ('collapse',)
            })
        )

    @admin.register(AcademyFAQ)
    class AcademyFAQAdmin(admin.ModelAdmin):
        list_display = ['academy', 'question_preview', 'order']
        list_filter = ['academy']
        search_fields = ['academy__상호명', 'question', 'answer']
        list_editable = ['order']
        ordering = ['academy', 'order']
        
        def question_preview(self, obj):
            return obj.question[:50] + "..." if len(obj.question) > 50 else obj.question
        question_preview.short_description = "질문"

    @admin.register(AcademyNews)
    class AcademyNewsAdmin(admin.ModelAdmin):
        list_display = ['academy', 'title', 'news_type', 'is_important', 'is_pinned', 'publish_date', 'is_active']
        list_filter = ['news_type', 'is_important', 'is_pinned', 'publish_date']
        search_fields = ['academy__상호명', 'title', 'content']
        list_editable = ['is_important', 'is_pinned']
        date_hierarchy = 'publish_date'
        
        def is_active(self, obj):
            return obj.is_active()
        is_active.boolean = True
        is_active.short_description = "활성 상태"

    @admin.register(AcademyViewHistory)
    class AcademyViewHistoryAdmin(admin.ModelAdmin):
        list_display = ['academy', 'user', 'viewed_at', 'duration_display', 'referrer']
        list_filter = ['viewed_at', 'referrer']
        search_fields = ['academy__상호명', 'user__username']
        readonly_fields = ['viewed_at']
        date_hierarchy = 'viewed_at'
        
        def duration_display(self, obj):
            if obj.duration:
                if obj.duration >= 60:
                    minutes = obj.duration // 60
                    seconds = obj.duration % 60
                    return f"{minutes}분 {seconds}초"
                else:
                    return f"{obj.duration}초"
            return "기록없음"
        duration_display.short_description = "체류 시간"

    @admin.register(AcademyComparison)
    class AcademyComparisonAdmin(admin.ModelAdmin):
        list_display = ['academy', 'competitor_count', 'price_competitiveness', 'last_updated']
        list_filter = ['last_updated', 'price_competitiveness']
        search_fields = ['academy__상호명']
        readonly_fields = ['last_updated']
        
        fieldsets = (
            ('기본 정보', {
                'fields': ('academy', 'competitor_count', 'price_competitiveness')
            }),
            ('비교 데이터', {
                'fields': ('comparison_data', 'strengths', 'weaknesses')
            }),
            ('시스템 정보', {
                'fields': ('last_updated',),
                'classes': ('collapse',)
            })
        )

except ImportError:
    # 모델을 import할 수 없는 경우 (마이그레이션 중 등)
    pass