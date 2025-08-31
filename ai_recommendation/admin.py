from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Avg
from .models import (
    UserPreference, UserBehavior, AcademyVector, RecommendationModel,
    Recommendation, RecommendationLog, AcademySimilarity
)


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user_display', 'preference_type', 'preference_display', 'weight', 'updated_at']
    list_filter = ['preference_type', 'created_at', 'updated_at']
    search_fields = ['user__username', 'user__email', 'preference_value']
    ordering = ['-updated_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'preference_type', 'weight')
        }),
        ('선호도 데이터', {
            'fields': ('preference_value',),
            'classes': ('wide',)
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def user_display(self, obj):
        return f"{obj.user.get_full_name() or obj.user.username}"
    user_display.short_description = '사용자'
    
    def preference_display(self, obj):
        data = obj.get_preference_data()
        if isinstance(data, dict):
            items = [f"{k}: {v}" for k, v in list(data.items())[:3]]
            display = ", ".join(items)
            if len(data) > 3:
                display += f" ... (+{len(data)-3}개)"
            return display
        return str(data)[:50]
    preference_display.short_description = '선호도 내용'


@admin.register(UserBehavior)
class UserBehaviorAdmin(admin.ModelAdmin):
    list_display = ['user_display', 'academy_display', 'action_display', 'duration_display', 'timestamp']
    list_filter = ['action', 'timestamp', 'user']
    search_fields = ['user__username', 'academy__상호명', 'search_query', 'session_id']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'academy', 'action', 'duration')
        }),
        ('행동 상세', {
            'fields': ('search_query', 'filter_criteria', 'session_id')
        }),
        ('컨텍스트', {
            'fields': ('page_url', 'referrer', 'user_agent', 'ip_address'),
            'classes': ('collapse',)
        }),
        ('시간 정보', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['timestamp']
    
    def user_display(self, obj):
        if obj.user:
            return f"{obj.user.get_full_name() or obj.user.username}"
        return "익명 사용자"
    user_display.short_description = '사용자'
    
    def academy_display(self, obj):
        return obj.academy.상호명 if obj.academy else '-'
    academy_display.short_description = '학원'
    
    def action_display(self, obj):
        colors = {
            'view': '#17a2b8',
            'search': '#6c757d',
            'filter': '#ffc107',
            'contact': '#28a745',
            'bookmark': '#dc3545',
            'click': '#007bff',
            'share': '#6f42c1',
            'review': '#fd7e14'
        }
        color = colors.get(obj.action, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_action_display()
        )
    action_display.short_description = '행동'
    
    def duration_display(self, obj):
        if obj.duration > 0:
            minutes, seconds = divmod(obj.duration, 60)
            if minutes > 0:
                return f"{minutes}분 {seconds}초"
            return f"{seconds}초"
        return "-"
    duration_display.short_description = '체류시간'


@admin.register(AcademyVector)
class AcademyVectorAdmin(admin.ModelAdmin):
    list_display = ['academy_display', 'popularity_score', 'rating_score', 'engagement_score', 'last_updated']
    list_filter = ['vector_version', 'last_updated']
    search_fields = ['academy__상호명']
    ordering = ['-popularity_score']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('academy', 'vector_version')
        }),
        ('특성 벡터', {
            'fields': ('subject_vector', 'location_vector', 'price_vector', 'facility_vector'),
            'classes': ('wide',)
        }),
        ('점수', {
            'fields': ('popularity_score', 'rating_score', 'engagement_score')
        }),
        ('임베딩', {
            'fields': ('description_embedding', 'keyword_embedding'),
            'classes': ('collapse',)
        }),
        ('메타데이터', {
            'fields': ('last_updated',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['last_updated']
    
    def academy_display(self, obj):
        return obj.academy.상호명
    academy_display.short_description = '학원'


@admin.register(RecommendationModel)
class RecommendationModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'model_type', 'version', 'is_active_display', 'performance_display', 'trained_at']
    list_filter = ['model_type', 'is_active', 'is_trained', 'created_at']
    search_fields = ['name', 'version']
    ordering = ['-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'model_type', 'version')
        }),
        ('설정', {
            'fields': ('parameters', 'hyperparameters'),
            'classes': ('wide',)
        }),
        ('성능 지표', {
            'fields': ('accuracy', 'precision', 'recall', 'f1_score')
        }),
        ('상태', {
            'fields': ('is_active', 'is_trained')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'trained_at', 'last_used_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: #28a745; font-weight: bold;">활성</span>')
        return format_html('<span style="color: #6c757d;">비활성</span>')
    is_active_display.short_description = '상태'
    
    def performance_display(self, obj):
        if obj.f1_score:
            return f"F1: {obj.f1_score:.3f}"
        elif obj.accuracy:
            return f"정확도: {obj.accuracy:.3f}"
        return "-"
    performance_display.short_description = '성능'


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = [
        'user_display', 'academy_display', 'final_score_display',
        'reason_type', 'is_clicked_display', 'feedback_display', 'recommended_at'
    ]
    list_filter = ['reason_type', 'is_clicked', 'is_contacted', 'model', 'recommended_at']
    search_fields = ['user__username', 'academy__상호명', 'session_id']
    ordering = ['-recommended_at']
    date_hierarchy = 'recommended_at'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'academy', 'model', 'session_id')
        }),
        ('점수', {
            'fields': ('confidence_score', 'relevance_score', 'final_score')
        }),
        ('추천 이유', {
            'fields': ('reason_type', 'reason_details', 'explanation'),
            'classes': ('wide',)
        }),
        ('사용자 반응', {
            'fields': ('is_clicked', 'is_contacted', 'feedback_score')
        }),
        ('컨텍스트', {
            'fields': ('context',),
            'classes': ('collapse',)
        }),
        ('시간 정보', {
            'fields': ('recommended_at', 'clicked_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['recommended_at', 'clicked_at']
    
    def user_display(self, obj):
        return f"{obj.user.get_full_name() or obj.user.username}"
    user_display.short_description = '사용자'
    
    def academy_display(self, obj):
        return obj.academy.상호명
    academy_display.short_description = '학원'
    
    def final_score_display(self, obj):
        score = obj.final_score
        if score >= 0.8:
            color = '#28a745'
        elif score >= 0.6:
            color = '#ffc107'
        elif score >= 0.4:
            color = '#fd7e14'
        else:
            color = '#dc3545'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.3f}</span>',
            color, score
        )
    final_score_display.short_description = '최종점수'
    
    def is_clicked_display(self, obj):
        if obj.is_clicked:
            return format_html('<span style="color: #28a745;">✓</span>')
        return format_html('<span style="color: #dc3545;">✗</span>')
    is_clicked_display.short_description = '클릭'
    
    def feedback_display(self, obj):
        if obj.feedback_score:
            return f"⭐ {obj.feedback_score}/5"
        return "-"
    feedback_display.short_description = '피드백'


@admin.register(RecommendationLog)
class RecommendationLogAdmin(admin.ModelAdmin):
    list_display = ['user_display', 'log_type_display', 'message_short', 'processing_time_display', 'timestamp']
    list_filter = ['log_type', 'timestamp']
    search_fields = ['user__username', 'message', 'session_id']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'log_type', 'session_id')
        }),
        ('로그 내용', {
            'fields': ('message', 'data'),
            'classes': ('wide',)
        }),
        ('성능 정보', {
            'fields': ('processing_time', 'recommendation_count')
        }),
        ('컨텍스트', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('시간 정보', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['timestamp']
    
    def user_display(self, obj):
        if obj.user:
            return f"{obj.user.get_full_name() or obj.user.username}"
        return "시스템"
    user_display.short_description = '사용자'
    
    def log_type_display(self, obj):
        colors = {
            'request': '#17a2b8',
            'generation': '#28a745',
            'serving': '#007bff',
            'feedback': '#ffc107',
            'error': '#dc3545'
        }
        color = colors.get(obj.log_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_log_type_display()
        )
    log_type_display.short_description = '로그 타입'
    
    def message_short(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_short.short_description = '메시지'
    
    def processing_time_display(self, obj):
        if obj.processing_time:
            return f"{obj.processing_time:.3f}초"
        return "-"
    processing_time_display.short_description = '처리시간'


@admin.register(AcademySimilarity)
class AcademySimilarityAdmin(admin.ModelAdmin):
    list_display = [
        'academy_pair_display', 'overall_similarity_display',
        'content_similarity', 'location_similarity', 'user_similarity', 'calculated_at'
    ]
    list_filter = ['calculation_method', 'calculated_at']
    search_fields = ['academy1__상호명', 'academy2__상호명']
    ordering = ['-overall_similarity']
    
    fieldsets = (
        ('학원 정보', {
            'fields': ('academy1', 'academy2')
        }),
        ('유사도 점수', {
            'fields': ('content_similarity', 'location_similarity', 'user_similarity', 'overall_similarity')
        }),
        ('계산 정보', {
            'fields': ('calculation_method', 'calculated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['calculated_at']
    
    def academy_pair_display(self, obj):
        return f"{obj.academy1.상호명} ↔ {obj.academy2.상호명}"
    academy_pair_display.short_description = '학원 쌍'
    
    def overall_similarity_display(self, obj):
        score = obj.overall_similarity
        if score >= 0.8:
            color = '#28a745'
        elif score >= 0.6:
            color = '#ffc107'
        elif score >= 0.4:
            color = '#fd7e14'
        else:
            color = '#dc3545'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.3f}</span>',
            color, score
        )
    overall_similarity_display.short_description = '전체 유사도'


# 사용자 정의 액션
@admin.action(description='선택된 추천에 대한 통계 보기')
def show_recommendation_stats(modeladmin, request, queryset):
    total_count = queryset.count()
    clicked_count = queryset.filter(is_clicked=True).count()
    contacted_count = queryset.filter(is_contacted=True).count()
    avg_score = queryset.aggregate(avg=Avg('final_score'))['avg']
    
    message = f"""
    추천 통계:
    - 총 추천 수: {total_count}
    - 클릭된 추천: {clicked_count} ({clicked_count/total_count*100:.1f}%)
    - 문의된 추천: {contacted_count} ({contacted_count/total_count*100:.1f}%)
    - 평균 점수: {avg_score:.3f}
    """
    
    modeladmin.message_user(request, message)

RecommendationAdmin.actions = [show_recommendation_stats]


@admin.action(description='선택된 벡터 인기도 점수 업데이트')
def update_popularity_scores(modeladmin, request, queryset):
    updated_count = 0
    for vector in queryset:
        vector.update_popularity_score()
        updated_count += 1
    
    modeladmin.message_user(request, f'{updated_count}개 벡터의 인기도 점수가 업데이트되었습니다.')

AcademyVectorAdmin.actions = [update_popularity_scores]