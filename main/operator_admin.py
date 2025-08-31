"""
학원 운영자용 대시보드 Admin 설정
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count

try:
    from .operator_models import (
        AcademyOwner, OperatorDashboardSettings, AcademyInquiry,
        AcademyPromotion, RevenueTracking, CompetitorAnalysis
    )

    @admin.register(AcademyOwner)
    class AcademyOwnerAdmin(admin.ModelAdmin):
        list_display = ['user', 'academy', 'role', 'is_verified', 'created_at']
        list_filter = ['role', 'is_verified', 'created_at', 'can_edit_info']
        search_fields = ['user__username', 'academy__상호명', 'user__email']
        readonly_fields = ['created_at']
        list_editable = ['is_verified']
        
        fieldsets = (
            ('기본 정보', {
                'fields': ('user', 'academy', 'role', 'is_verified')
            }),
            ('권한 설정', {
                'fields': ('can_edit_info', 'can_view_analytics', 'can_manage_content', 'can_respond_reviews')
            }),
            ('인증 정보', {
                'fields': ('verification_documents', 'created_at'),
                'classes': ('collapse',)
            })
        )
        
        actions = ['verify_owners', 'unverify_owners']
        
        def verify_owners(self, request, queryset):
            updated = queryset.update(is_verified=True)
            self.message_user(request, f'{updated}명의 운영자가 승인되었습니다.')
        verify_owners.short_description = '선택된 운영자 승인'
        
        def unverify_owners(self, request, queryset):
            updated = queryset.update(is_verified=False)
            self.message_user(request, f'{updated}명의 운영자 승인이 취소되었습니다.')
        unverify_owners.short_description = '선택된 운영자 승인 취소'

    @admin.register(OperatorDashboardSettings)
    class OperatorDashboardSettingsAdmin(admin.ModelAdmin):
        list_display = ['owner', 'email_notifications', 'review_alerts', 'weekly_report', 'updated_at']
        list_filter = ['email_notifications', 'sms_notifications', 'weekly_report', 'monthly_report']
        search_fields = ['owner__user__username', 'owner__academy__상호명']
        readonly_fields = ['updated_at']
        
        fieldsets = (
            ('알림 설정', {
                'fields': ('owner', 'email_notifications', 'sms_notifications', 'review_alerts', 'inquiry_alerts')
            }),
            ('대시보드 표시', {
                'fields': ('show_visitor_stats', 'show_ranking_info', 'show_competitor_analysis', 'show_revenue_tracking')
            }),
            ('보고서 설정', {
                'fields': ('weekly_report', 'monthly_report', 'updated_at')
            })
        )

    @admin.register(AcademyInquiry)
    class AcademyInquiryAdmin(admin.ModelAdmin):
        list_display = ['academy', 'inquirer_name', 'inquiry_type', 'subject_short', 'status', 'priority', 'created_at']
        list_filter = ['status', 'inquiry_type', 'priority', 'created_at']
        search_fields = ['academy__상호명', 'inquirer_name', 'subject', 'content']
        readonly_fields = ['created_at', 'responded_at']
        list_editable = ['status', 'priority']
        date_hierarchy = 'created_at'
        ordering = ['-created_at']
        
        def subject_short(self, obj):
            return obj.subject[:30] + "..." if len(obj.subject) > 30 else obj.subject
        subject_short.short_description = "제목"
        
        fieldsets = (
            ('문의 기본 정보', {
                'fields': ('academy', 'inquiry_type', 'subject', 'content')
            }),
            ('문의자 정보', {
                'fields': ('inquirer_name', 'inquirer_phone', 'inquirer_email')
            }),
            ('처리 정보', {
                'fields': ('status', 'priority', 'response', 'responded_by', 'responded_at')
            }),
            ('시스템 정보', {
                'fields': ('created_at',),
                'classes': ('collapse',)
            })
        )
        
        actions = ['mark_answered', 'mark_closed', 'increase_priority']
        
        def mark_answered(self, request, queryset):
            updated = queryset.update(status='answered')
            self.message_user(request, f'{updated}개 문의가 답변완료로 변경되었습니다.')
        mark_answered.short_description = '답변완료로 변경'
        
        def mark_closed(self, request, queryset):
            updated = queryset.update(status='closed')
            self.message_user(request, f'{updated}개 문의가 완료로 변경되었습니다.')
        mark_closed.short_description = '완료로 변경'
        
        def increase_priority(self, request, queryset):
            for inquiry in queryset:
                if inquiry.priority < 5:
                    inquiry.priority += 1
                    inquiry.save()
            self.message_user(request, '선택된 문의의 우선순위가 증가되었습니다.')
        increase_priority.short_description = '우선순위 증가'

    @admin.register(AcademyPromotion)
    class AcademyPromotionAdmin(admin.ModelAdmin):
        list_display = ['academy', 'title', 'promotion_type', 'is_active', 'is_featured', 'start_date', 'end_date', 'participants_status']
        list_filter = ['promotion_type', 'is_active', 'is_featured', 'start_date', 'created_by']
        search_fields = ['academy__상호명', 'title', 'description']
        readonly_fields = ['created_at', 'created_by']
        list_editable = ['is_active', 'is_featured']
        date_hierarchy = 'start_date'
        
        def participants_status(self, obj):
            if obj.max_participants:
                percentage = (obj.current_participants / obj.max_participants) * 100
                color = 'red' if percentage > 80 else 'orange' if percentage > 60 else 'green'
                return format_html(
                    '<span style="color: {};">{}/{}</span>',
                    color,
                    obj.current_participants,
                    obj.max_participants
                )
            return f"{obj.current_participants}/제한없음"
        participants_status.short_description = "참여자 현황"
        
        fieldsets = (
            ('프로모션 기본 정보', {
                'fields': ('academy', 'title', 'description', 'promotion_type')
            }),
            ('할인 정보', {
                'fields': ('discount_rate', 'discount_amount')
            }),
            ('기간 및 조건', {
                'fields': ('start_date', 'end_date', 'min_months', 'max_participants', 'current_participants')
            }),
            ('상태', {
                'fields': ('is_active', 'is_featured')
            }),
            ('시스템 정보', {
                'fields': ('created_at', 'created_by'),
                'classes': ('collapse',)
            })
        )
        
        actions = ['activate_promotions', 'deactivate_promotions', 'feature_promotions']
        
        def activate_promotions(self, request, queryset):
            updated = queryset.update(is_active=True)
            self.message_user(request, f'{updated}개 프로모션이 활성화되었습니다.')
        activate_promotions.short_description = '선택된 프로모션 활성화'
        
        def deactivate_promotions(self, request, queryset):
            updated = queryset.update(is_active=False)
            self.message_user(request, f'{updated}개 프로모션이 비활성화되었습니다.')
        deactivate_promotions.short_description = '선택된 프로모션 비활성화'
        
        def feature_promotions(self, request, queryset):
            updated = queryset.update(is_featured=True)
            self.message_user(request, f'{updated}개 프로모션이 추천 프로모션으로 설정되었습니다.')
        feature_promotions.short_description = '추천 프로모션으로 설정'
        
        def save_model(self, request, obj, form, change):
            if not change:  # 새로운 객체인 경우
                obj.created_by = request.user
            super().save_model(request, obj, form, change)

    @admin.register(RevenueTracking)
    class RevenueTrackingAdmin(admin.ModelAdmin):
        list_display = ['academy', 'year', 'month', 'student_count', 'total_revenue', 'net_profit', 'profit_margin']
        list_filter = ['year', 'month', 'academy']
        search_fields = ['academy__상호명']
        readonly_fields = ['created_at', 'updated_at', 'net_profit', 'average_tuition']
        ordering = ['-year', '-month']
        
        def profit_margin(self, obj):
            if obj.total_revenue > 0:
                margin = (obj.net_profit / obj.total_revenue) * 100
                color = 'green' if margin > 20 else 'orange' if margin > 10 else 'red'
                return format_html(
                    '<span style="color: {};">{:.1f}%</span>',
                    color,
                    margin
                )
            return "0%"
        profit_margin.short_description = "수익률"
        
        fieldsets = (
            ('기간 정보', {
                'fields': ('academy', 'year', 'month')
            }),
            ('매출 정보', {
                'fields': ('student_count', 'total_revenue', 'average_tuition')
            }),
            ('비용 정보', {
                'fields': ('operating_costs', 'marketing_costs')
            }),
            ('수익 정보', {
                'fields': ('net_profit',)
            }),
            ('시스템 정보', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            })
        )

    @admin.register(CompetitorAnalysis)
    class CompetitorAnalysisAdmin(admin.ModelAdmin):
        list_display = ['academy', 'competitor', 'distance_km', 'price_comparison', 'rating_difference', 'last_analyzed']
        list_filter = ['price_comparison', 'last_analyzed']
        search_fields = ['academy__상호명', 'competitor__상호명']
        readonly_fields = ['last_analyzed']
        
        fieldsets = (
            ('기본 정보', {
                'fields': ('academy', 'competitor', 'distance_km')
            }),
            ('비교 분석', {
                'fields': ('price_comparison', 'rating_difference')
            }),
            ('SWOT 분석', {
                'fields': ('strengths', 'weaknesses', 'opportunities')
            }),
            ('시스템 정보', {
                'fields': ('last_analyzed',),
                'classes': ('collapse',)
            })
        )

except ImportError:
    # 모델들이 아직 마이그레이션되지 않은 경우
    pass