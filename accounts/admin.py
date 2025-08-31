from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserPreference, Bookmark, BookmarkFolder
from .review_models import Review, ReviewImage, ReviewHelpful, ReviewReport
from .comparison_models import AcademyComparison, ComparisonTemplate, ComparisonHistory
try:
    from .theme_models import (
        ThemeConfiguration, PresetTheme, ThemeUsageStatistics, UserThemeHistory
    )
    THEME_MODELS_AVAILABLE = True
except ImportError:
    THEME_MODELS_AVAILABLE = False


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """커스텀 사용자 관리자"""
    fieldsets = UserAdmin.fieldsets + (
        ('추가 정보', {
            'fields': (
                'nickname', 'phone', 'birth_date', 'preferred_areas',
                'interested_subjects', 'child_ages', 'social_provider', 'social_id'
            )
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('추가 정보', {
            'fields': (
                'email', 'nickname', 'phone', 'birth_date'
            )
        }),
    )
    list_display = ('email', 'username', 'nickname', 'is_active', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'social_provider', 'date_joined')
    search_fields = ('email', 'username', 'nickname')
    ordering = ('-date_joined',)


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    """사용자 설정 관리자"""
    list_display = ('user', 'theme', 'email_notifications', 'push_notifications')
    list_filter = ('theme', 'email_notifications', 'push_notifications')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    """즐겨찾기 관리자"""
    list_display = ('user', 'academy', 'priority', 'created_at')
    list_filter = ('priority', 'created_at')
    search_fields = ('user__email', 'user__username', 'academy__상호명')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'academy')
    ordering = ('-created_at',)


@admin.register(BookmarkFolder)
class BookmarkFolderAdmin(admin.ModelAdmin):
    """즐겨찾기 폴더 관리자"""
    list_display = ('user', 'name', 'is_default', 'order', 'bookmark_count')
    list_filter = ('is_default', 'color', 'icon', 'created_at')
    search_fields = ('user__email', 'user__username', 'name')
    readonly_fields = ('created_at', 'updated_at', 'bookmark_count')
    raw_id_fields = ('user',)
    filter_horizontal = ('bookmarks',)
    ordering = ('user', 'order', 'name')
    
    def bookmark_count(self, obj):
        return obj.bookmarks.count()
    bookmark_count.short_description = '즐겨찾기 수'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """리뷰 관리자"""
    list_display = ('academy', 'get_author_name', 'overall_rating', 'is_verified', 'is_hidden', 'created_at')
    list_filter = ('overall_rating', 'is_verified', 'is_hidden', 'would_recommend', 'created_at')
    search_fields = ('academy__상호명', 'user__username', 'user__email', 'title', 'content')
    readonly_fields = ('created_at', 'updated_at', 'helpful_count', 'not_helpful_count')
    raw_id_fields = ('user', 'academy')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'academy', 'title', 'content')
        }),
        ('평점', {
            'fields': ('overall_rating', 'teaching_rating', 'facility_rating', 'management_rating', 'cost_rating')
        }),
        ('상세 정보', {
            'fields': ('attendance_period', 'grade_when_attended', 'subjects_taken', 'pros', 'cons', 'would_recommend')
        }),
        ('설정', {
            'fields': ('is_anonymous', 'is_verified', 'is_hidden')
        }),
        ('통계', {
            'fields': ('helpful_count', 'not_helpful_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_author_name(self, obj):
        if obj.is_anonymous:
            return "익명"
        return obj.user.nickname or obj.user.username
    get_author_name.short_description = '작성자'


class ReviewImageInline(admin.TabularInline):
    """리뷰 이미지 인라인"""
    model = ReviewImage
    extra = 1
    fields = ('image', 'caption', 'order')


@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    """리뷰 이미지 관리자"""
    list_display = ('review', 'caption', 'order', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('review__academy__상호명', 'caption')
    raw_id_fields = ('review',)
    ordering = ('review', 'order', 'created_at')


@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
    """리뷰 유용성 평가 관리자"""
    list_display = ('review', 'user', 'is_helpful', 'created_at')
    list_filter = ('is_helpful', 'created_at')
    search_fields = ('review__academy__상호명', 'user__username', 'user__email')
    raw_id_fields = ('user', 'review')
    ordering = ('-created_at',)


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    """리뷰 신고 관리자"""
    list_display = ('review', 'user', 'reason', 'status', 'created_at')
    list_filter = ('reason', 'status', 'created_at')
    search_fields = ('review__academy__상호명', 'user__username', 'user__email', 'description')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user', 'review')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('신고 정보', {
            'fields': ('user', 'review', 'reason', 'description')
        }),
        ('처리 상태', {
            'fields': ('status', 'admin_notes', 'resolved_at')
        }),
        ('시간', {
            'fields': ('created_at',)
        }),
    )


@admin.register(AcademyComparison)
class AcademyComparisonAdmin(admin.ModelAdmin):
    """학원 비교 관리자"""
    list_display = ('name', 'user', 'academy_count', 'is_public', 'created_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('name', 'user__username', 'user__email', 'description')
    readonly_fields = ('created_at', 'updated_at', 'academy_count')
    raw_id_fields = ('user',)
    filter_horizontal = ('academies',)
    ordering = ('-created_at',)
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'name', 'description', 'academies')
        }),
        ('비교 기준', {
            'fields': ('compare_tuition', 'compare_rating', 'compare_distance', 
                      'compare_subjects', 'compare_facilities')
        }),
        ('가중치', {
            'fields': ('tuition_weight', 'rating_weight', 'distance_weight', 'quality_weight')
        }),
        ('기준 위치', {
            'fields': ('base_latitude', 'base_longitude', 'base_address'),
            'classes': ('collapse',)
        }),
        ('설정', {
            'fields': ('is_public',)
        }),
        ('시간', {
            'fields': ('academy_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def academy_count(self, obj):
        return obj.academies.count()
    academy_count.short_description = '비교 학원 수'


@admin.register(ComparisonTemplate)
class ComparisonTemplateAdmin(admin.ModelAdmin):
    """비교 템플릿 관리자"""
    list_display = ('name', 'user', 'is_default', 'created_at')
    list_filter = ('is_default', 'created_at')
    search_fields = ('name', 'user__username', 'user__email', 'description')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user',)
    ordering = ('-is_default', 'name')
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'name', 'description', 'is_default')
        }),
        ('비교 기준', {
            'fields': ('compare_tuition', 'compare_rating', 'compare_distance', 
                      'compare_subjects', 'compare_facilities')
        }),
        ('가중치', {
            'fields': ('tuition_weight', 'rating_weight', 'distance_weight', 'quality_weight')
        }),
        ('시간', {
            'fields': ('created_at',)
        }),
    )


@admin.register(ComparisonHistory)
class ComparisonHistoryAdmin(admin.ModelAdmin):
    """비교 기록 관리자"""
    list_display = ('comparison', 'user', 'action', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('comparison__name', 'user__username', 'user__email')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user', 'comparison')
    ordering = ('-created_at',)


# 소셜 미디어 공유 관련 관리자 (조건부 등록)
try:
    from .social_models import (
        SocialPlatform, ShareableContent, SocialShare,
        AcademyShare, ShareAnalytics, PopularContent
    )
    SOCIAL_MODELS_AVAILABLE = True
except ImportError:
    SOCIAL_MODELS_AVAILABLE = False

if SOCIAL_MODELS_AVAILABLE:
    @admin.register(SocialPlatform)
    class SocialPlatformAdmin(admin.ModelAdmin):
        """소셜 플랫폼 관리자"""
        list_display = ('display_name', 'name', 'is_active', 'order', 'created_at')
        list_filter = ('is_active', 'created_at')
        search_fields = ('name', 'display_name')
        ordering = ('order', 'name')
        readonly_fields = ('created_at', 'updated_at')
        
        fieldsets = (
            ('기본 정보', {
                'fields': ('name', 'display_name', 'icon', 'color')
            }),
            ('설정', {
                'fields': ('share_url_template', 'is_active', 'order')
            }),
            ('시간', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            })
        )
    
    @admin.register(ShareableContent)
    class ShareableContentAdmin(admin.ModelAdmin):
        """공유 콘텐츠 관리자"""
        list_display = ('title', 'content_type', 'created_by', 'created_at')
        list_filter = ('content_type', 'created_at')
        search_fields = ('title', 'description', 'hashtags')
        readonly_fields = ('created_at', 'updated_at')
        raw_id_fields = ('created_by',)
        
        fieldsets = (
            ('기본 정보', {
                'fields': ('content_type', 'title', 'description', 'url')
            }),
            ('메타데이터', {
                'fields': ('image_url', 'metadata', 'hashtags')
            }),
            ('OG 태그', {
                'fields': ('og_title', 'og_description', 'og_image')
            }),
            ('생성 정보', {
                'fields': ('created_by', 'created_at', 'updated_at'),
                'classes': ('collapse',)
            })
        )
    
    @admin.register(SocialShare)
    class SocialShareAdmin(admin.ModelAdmin):
        """소셜 공유 관리자"""
        list_display = ('user', 'platform', 'content_title', 'clicks', 'engagement_score', 'shared_at')
        list_filter = ('platform', 'shared_at', 'engagement_score')
        search_fields = ('user__username', 'content__title', 'custom_message')
        readonly_fields = ('shared_at',)
        raw_id_fields = ('user', 'content')
        
        def content_title(self, obj):
            return obj.content.title[:50]
        content_title.short_description = '콘텐츠 제목'
    
    @admin.register(AcademyShare)
    class AcademyShareAdmin(admin.ModelAdmin):
        """학원 공유 관리자"""
        list_display = ('user', 'academy_name', 'platform', 'include_rating', 'shared_at')
        list_filter = ('platform', 'include_rating', 'include_price', 'include_location', 'shared_at')
        search_fields = ('user__username', 'academy__상호명', 'custom_title', 'recommendation_reason')
        readonly_fields = ('shared_at',)
        raw_id_fields = ('user', 'academy')
        
        fieldsets = (
            ('기본 정보', {
                'fields': ('user', 'academy', 'platform')
            }),
            ('커스터마이징', {
                'fields': ('custom_title', 'custom_description', 'selected_subjects')
            }),
            ('포함 정보', {
                'fields': ('include_rating', 'include_price', 'include_location')
            }),
            ('추천 컨텍스트', {
                'fields': ('recommendation_reason', 'target_age_group')
            }),
            ('시간', {
                'fields': ('shared_at',)
            })
        )
        
        def academy_name(self, obj):
            return obj.academy.상호명
        academy_name.short_description = '학원명'
    
    @admin.register(ShareAnalytics)
    class ShareAnalyticsAdmin(admin.ModelAdmin):
        """공유 분석 관리자"""
        list_display = ('date', 'platform', 'total_shares', 'unique_users', 'total_clicks')
        list_filter = ('platform', 'date')
        readonly_fields = ('created_at', 'updated_at')
        ordering = ('-date', 'platform')
        
        fieldsets = (
            ('기본 정보', {
                'fields': ('date', 'platform')
            }),
            ('통계', {
                'fields': ('total_shares', 'unique_users', 'total_clicks')
            }),
            ('콘텐츠 유형별', {
                'fields': ('academy_shares', 'comparison_shares', 'review_shares')
            })
        )
    
    @admin.register(PopularContent)
    class PopularContentAdmin(admin.ModelAdmin):
        """인기 콘텐츠 관리자"""
        list_display = ('content_title', 'total_shares', 'weekly_shares', 'viral_score', 'last_calculated')
        list_filter = ('last_calculated',)
        search_fields = ('content__title',)
        readonly_fields = ('last_calculated',)
        ordering = ('-viral_score', '-total_shares')
        
        def content_title(self, obj):
            return obj.content.title
        content_title.short_description = '콘텐츠 제목'


# 테마 관련 관리자 (조건부 등록)
if THEME_MODELS_AVAILABLE:
    @admin.register(ThemeConfiguration)
    class ThemeConfigurationAdmin(admin.ModelAdmin):
        """테마 설정 관리자"""
        list_display = ('get_user_name', 'theme_type', 'color_scheme', 'font_size', 'high_contrast', 'updated_at')
        list_filter = ('theme_type', 'color_scheme', 'font_size', 'high_contrast', 'reduce_motion')
        search_fields = ('user__username', 'user__email', 'user__nickname')
        readonly_fields = ('created_at', 'updated_at')
        raw_id_fields = ('user',)
        
        def get_user_name(self, obj):
            return obj.user.nickname or obj.user.username
        get_user_name.short_description = '사용자'
    
    
    @admin.register(PresetTheme)
    class PresetThemeAdmin(admin.ModelAdmin):
        """프리셋 테마 관리자"""
        list_display = ('display_name', 'name', 'theme_type', 'color_scheme', 'is_system', 'is_active', 'order')
        list_filter = ('theme_type', 'color_scheme', 'is_system', 'is_active')
        search_fields = ('name', 'display_name', 'description')
        readonly_fields = ('created_at', 'updated_at')
        ordering = ('order', 'name')
