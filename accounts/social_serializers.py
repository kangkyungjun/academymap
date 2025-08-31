from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import URLValidator

from .social_models import (
    SocialPlatform, ShareableContent, SocialShare, 
    AcademyShare, ShareAnalytics, PopularContent
)
from main.models import Data as Academy

User = get_user_model()


class SocialPlatformSerializer(serializers.ModelSerializer):
    """소셜 플랫폼 직렬화"""
    
    class Meta:
        model = SocialPlatform
        fields = [
            'id', 'name', 'display_name', 'icon', 'color', 
            'is_active', 'order'
        ]
        read_only_fields = ['id']


class ShareableContentSerializer(serializers.ModelSerializer):
    """공유 콘텐츠 직렬화"""
    
    content_type_display = serializers.CharField(
        source='get_content_type_display', 
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.username', 
        read_only=True
    )
    
    class Meta:
        model = ShareableContent
        fields = [
            'id', 'content_type', 'content_type_display',
            'title', 'description', 'url', 'image_url',
            'metadata', 'hashtags', 'og_title', 'og_description', 
            'og_image', 'created_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_url(self, value):
        """URL 유효성 검사"""
        validator = URLValidator()
        try:
            validator(value)
        except ValidationError:
            raise serializers.ValidationError('올바른 URL 형식이 아닙니다.')
        return value


class SocialShareSerializer(serializers.ModelSerializer):
    """소셜 공유 직렬화"""
    
    user_name = serializers.CharField(source='user.username', read_only=True)
    platform_name = serializers.CharField(source='platform.display_name', read_only=True)
    platform_icon = serializers.CharField(source='platform.icon', read_only=True)
    content_title = serializers.CharField(source='content.title', read_only=True)
    content_type = serializers.CharField(source='content.get_content_type_display', read_only=True)
    
    class Meta:
        model = SocialShare
        fields = [
            'id', 'user_name', 'platform_name', 'platform_icon',
            'content_title', 'content_type', 'shared_url', 
            'custom_message', 'clicks', 'engagement_score', 'shared_at'
        ]
        read_only_fields = ['id', 'shared_at']


class AcademyShareSerializer(serializers.ModelSerializer):
    """학원 공유 직렬화"""
    
    user_name = serializers.CharField(source='user.username', read_only=True)
    academy_name = serializers.CharField(source='academy.상호명', read_only=True)
    platform_name = serializers.CharField(source='platform.display_name', read_only=True)
    
    # 생성된 공유 정보 (읽기 전용)
    generated_title = serializers.SerializerMethodField()
    generated_description = serializers.SerializerMethodField()
    generated_hashtags = serializers.SerializerMethodField()
    
    class Meta:
        model = AcademyShare
        fields = [
            'id', 'user_name', 'academy_name', 'platform_name',
            'custom_title', 'custom_description', 'selected_subjects',
            'include_rating', 'include_price', 'include_location',
            'recommendation_reason', 'target_age_group',
            'generated_title', 'generated_description', 'generated_hashtags',
            'shared_at'
        ]
        read_only_fields = ['id', 'shared_at']
    
    def get_generated_title(self, obj):
        return obj.get_share_title()
    
    def get_generated_description(self, obj):
        return obj.get_share_description()
    
    def get_generated_hashtags(self, obj):
        return obj.get_hashtags()


class AcademyShareCreateSerializer(serializers.Serializer):
    """학원 공유 생성 직렬화"""
    
    academy_id = serializers.IntegerField()
    platform = serializers.CharField(max_length=50)
    
    # 커스터마이징 옵션
    custom_title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    custom_description = serializers.CharField(required=False, allow_blank=True)
    custom_message = serializers.CharField(required=False, allow_blank=True)
    
    # 포함할 정보 선택
    selected_subjects = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list
    )
    include_rating = serializers.BooleanField(default=True)
    include_price = serializers.BooleanField(default=False)
    include_location = serializers.BooleanField(default=True)
    
    # 추천 컨텍스트
    recommendation_reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    target_age_group = serializers.CharField(max_length=50, required=False, allow_blank=True)
    
    def validate_academy_id(self, value):
        """학원 존재 확인"""
        try:
            Academy.objects.get(id=value)
        except Academy.DoesNotExist:
            raise serializers.ValidationError('존재하지 않는 학원입니다.')
        return value
    
    def validate_platform(self, value):
        """플랫폼 존재 확인"""
        if not SocialPlatform.objects.filter(name=value, is_active=True).exists():
            raise serializers.ValidationError('지원하지 않는 플랫폼입니다.')
        return value
    
    def validate_selected_subjects(self, value):
        """과목 목록 검증"""
        if len(value) > 10:
            raise serializers.ValidationError('최대 10개의 과목까지 선택 가능합니다.')
        return value


class ShareUrlRequestSerializer(serializers.Serializer):
    """공유 URL 요청 직렬화"""
    
    platform = serializers.CharField(max_length=50)
    content_type = serializers.ChoiceField(choices=ShareableContent.CONTENT_TYPES)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField()
    url = serializers.URLField()
    hashtags = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_platform(self, value):
        """플랫폼 유효성 검사"""
        if not SocialPlatform.objects.filter(name=value, is_active=True).exists():
            raise serializers.ValidationError('지원하지 않는 플랫폼입니다.')
        return value


class ShareUrlResponseSerializer(serializers.Serializer):
    """공유 URL 응답 직렬화"""
    
    platform = serializers.CharField()
    share_url = serializers.URLField()
    content_id = serializers.IntegerField()


class ShareStatisticsSerializer(serializers.Serializer):
    """공유 통계 직렬화"""
    
    period = serializers.DictField()
    total_shares = serializers.IntegerField()
    platform_breakdown = serializers.ListField()
    content_type_breakdown = serializers.ListField()
    daily_trends = serializers.ListField()


class PopularContentSerializer(serializers.ModelSerializer):
    """인기 콘텐츠 직렬화"""
    
    content_title = serializers.CharField(source='content.title')
    content_type = serializers.CharField(source='content.get_content_type_display')
    content_url = serializers.URLField(source='content.url')
    content_description = serializers.CharField(source='content.description')
    
    class Meta:
        model = PopularContent
        fields = [
            'id', 'content_title', 'content_type', 'content_url',
            'content_description', 'total_shares', 'weekly_shares',
            'monthly_shares', 'average_engagement', 'viral_score',
            'last_calculated'
        ]


class ShareAnalyticsSerializer(serializers.ModelSerializer):
    """공유 분석 직렬화"""
    
    platform_name = serializers.CharField(source='platform.display_name')
    platform_icon = serializers.CharField(source='platform.icon')
    
    class Meta:
        model = ShareAnalytics
        fields = [
            'id', 'date', 'platform_name', 'platform_icon',
            'total_shares', 'unique_users', 'total_clicks',
            'academy_shares', 'comparison_shares', 'review_shares'
        ]


class SocialSharePreviewSerializer(serializers.Serializer):
    """소셜 공유 미리보기 직렬화"""
    
    title = serializers.CharField()
    description = serializers.CharField()
    hashtags = serializers.CharField()
    url = serializers.URLField()
    platform = serializers.CharField()
    
    # OG 태그 정보
    og_title = serializers.CharField()
    og_description = serializers.CharField()
    og_image = serializers.URLField(required=False)
    
    # 플랫폼별 공유 URL
    share_url = serializers.URLField()


class BulkShareRequestSerializer(serializers.Serializer):
    """대량 공유 요청 직렬화"""
    
    academy_ids = serializers.ListField(
        child=serializers.IntegerField(),
        max_length=50  # 최대 50개 제한
    )
    platforms = serializers.ListField(
        child=serializers.CharField(max_length=50),
        max_length=10  # 최대 10개 플랫폼
    )
    
    # 공통 설정
    include_rating = serializers.BooleanField(default=True)
    include_location = serializers.BooleanField(default=True)
    custom_message = serializers.CharField(required=False, allow_blank=True)
    
    def validate_academy_ids(self, value):
        """학원 ID 목록 검증"""
        if len(value) == 0:
            raise serializers.ValidationError('최소 1개 이상의 학원을 선택하세요.')
        
        # 존재하는 학원인지 확인
        existing_count = Academy.objects.filter(id__in=value).count()
        if existing_count != len(value):
            raise serializers.ValidationError('존재하지 않는 학원이 포함되어 있습니다.')
        
        return value
    
    def validate_platforms(self, value):
        """플랫폼 목록 검증"""
        if len(value) == 0:
            raise serializers.ValidationError('최소 1개 이상의 플랫폼을 선택하세요.')
        
        # 활성화된 플랫폼인지 확인
        active_platforms = set(
            SocialPlatform.objects.filter(is_active=True).values_list('name', flat=True)
        )
        invalid_platforms = set(value) - active_platforms
        
        if invalid_platforms:
            raise serializers.ValidationError(
                f'지원하지 않는 플랫폼: {", ".join(invalid_platforms)}'
            )
        
        return value


class UserShareHistorySerializer(serializers.Serializer):
    """사용자 공유 기록 직렬화"""
    
    id = serializers.IntegerField()
    platform = serializers.CharField()
    platform_icon = serializers.CharField()
    content_title = serializers.CharField()
    content_type = serializers.CharField()
    shared_at = serializers.DateTimeField()
    clicks = serializers.IntegerField()
    engagement_score = serializers.FloatField()