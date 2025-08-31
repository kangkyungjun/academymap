"""
데이터 분석 및 리포팅 REST API Serializers
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

try:
    from .analytics_models import (
        AnalyticsReport, UserAnalytics, AcademyAnalytics,
        RegionalAnalytics, MarketTrend, ConversionFunnel, CustomDashboard
    )
    from .models import Data as Academy
except ImportError:
    # 마이그레이션 중이거나 모델이 아직 생성되지 않은 경우
    pass

User = get_user_model()


class AnalyticsReportSerializer(serializers.ModelSerializer):
    """분석 리포트 시리얼라이저"""
    generated_by_username = serializers.CharField(source='generated_by.username', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = AnalyticsReport
        fields = [
            'id', 'title', 'report_type', 'report_type_display',
            'category', 'category_display', 'start_date', 'end_date',
            'data', 'summary', 'insights', 'recommendations',
            'generated_at', 'generated_by', 'generated_by_username', 'is_public'
        ]
        read_only_fields = ['id', 'generated_at', 'generated_by']


class AnalyticsReportCreateSerializer(serializers.ModelSerializer):
    """분석 리포트 생성 시리얼라이저"""
    
    class Meta:
        model = AnalyticsReport
        fields = [
            'title', 'report_type', 'category', 'start_date', 'end_date', 'is_public'
        ]
    
    def validate(self, data):
        """날짜 유효성 검증"""
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("시작일은 종료일보다 이전이어야 합니다.")
        return data


class UserAnalyticsSerializer(serializers.ModelSerializer):
    """사용자 분석 시리얼라이저"""
    
    class Meta:
        model = UserAnalytics
        fields = [
            'id', 'date', 'total_users', 'new_users', 'returning_users',
            'total_sessions', 'avg_session_duration', 'bounce_rate',
            'total_pageviews', 'unique_pageviews', 'avg_pages_per_session',
            'organic_traffic', 'direct_traffic', 'referral_traffic', 'social_traffic',
            'desktop_users', 'mobile_users', 'tablet_users',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AcademyAnalyticsSerializer(serializers.ModelSerializer):
    """학원 분석 시리얼라이저"""
    academy_name = serializers.CharField(source='academy.상호명', read_only=True)
    academy_address = serializers.CharField(source='academy.도로명주소', read_only=True)
    
    class Meta:
        model = AcademyAnalytics
        fields = [
            'id', 'academy', 'academy_name', 'academy_address', 'date',
            'views', 'unique_views', 'avg_view_duration',
            'bookmarks', 'shares', 'inquiries',
            'conversion_rate', 'inquiry_conversion',
            'top_keywords', 'recommendation_score', 'popularity_rank',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RegionalAnalyticsSerializer(serializers.ModelSerializer):
    """지역 분석 시리얼라이저"""
    
    class Meta:
        model = RegionalAnalytics
        fields = [
            'id', 'region_sido', 'region_sigungu', 'date',
            'total_academies', 'active_academies',
            'total_views', 'unique_visitors', 'avg_rating',
            'avg_tuition', 'tuition_range_min', 'tuition_range_max',
            'subject_distribution', 'competition_index', 'market_saturation',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MarketTrendSerializer(serializers.ModelSerializer):
    """시장 트렌드 시리얼라이저"""
    trend_type_display = serializers.CharField(source='get_trend_type_display', read_only=True)
    change_direction_display = serializers.CharField(source='get_change_direction_display', read_only=True)
    
    class Meta:
        model = MarketTrend
        fields = [
            'id', 'trend_type', 'trend_type_display', 'date',
            'trend_data', 'trend_score', 'change_rate', 'change_direction',
            'change_direction_display', 'prediction_data', 'confidence_level',
            'description', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ConversionFunnelSerializer(serializers.ModelSerializer):
    """전환 퍼널 시리얼라이저"""
    
    class Meta:
        model = ConversionFunnel
        fields = [
            'id', 'date',
            'stage_1_visitors', 'stage_2_search', 'stage_3_view',
            'stage_4_detail', 'stage_5_inquiry',
            'search_conversion', 'view_conversion', 'detail_conversion',
            'inquiry_conversion', 'stage_1_drop', 'stage_2_drop',
            'stage_3_drop', 'stage_4_drop', 'overall_conversion',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomDashboardSerializer(serializers.ModelSerializer):
    """사용자 정의 대시보드 시리얼라이저"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    shared_with_usernames = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomDashboard
        fields = [
            'id', 'user', 'user_username', 'name', 'description',
            'layout_config', 'widget_config', 'filter_config',
            'is_shared', 'shared_with', 'shared_with_usernames',
            'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_shared_with_usernames(self, obj):
        """공유 대상 사용자명 목록"""
        return [user.username for user in obj.shared_with.all()]


class CustomDashboardCreateSerializer(serializers.ModelSerializer):
    """사용자 정의 대시보드 생성 시리얼라이저"""
    
    class Meta:
        model = CustomDashboard
        fields = [
            'name', 'description', 'layout_config', 'widget_config',
            'filter_config', 'is_shared', 'is_default'
        ]
    
    def validate_name(self, value):
        """대시보드 이름 중복 검증"""
        user = self.context['request'].user
        if CustomDashboard.objects.filter(user=user, name=value).exists():
            raise serializers.ValidationError("같은 이름의 대시보드가 이미 존재합니다.")
        return value


class AnalyticsSummarySerializer(serializers.Serializer):
    """분석 요약 정보 시리얼라이저"""
    total_users = serializers.IntegerField()
    total_sessions = serializers.IntegerField()
    total_academies = serializers.IntegerField()
    total_views = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
    top_regions = serializers.ListField()
    trending_subjects = serializers.ListField()
    recent_reports_count = serializers.IntegerField()


class AnalyticsChartDataSerializer(serializers.Serializer):
    """차트 데이터 시리얼라이저"""
    labels = serializers.ListField(child=serializers.CharField())
    datasets = serializers.ListField()
    
    
class AnalyticsFilterSerializer(serializers.Serializer):
    """분석 필터 시리얼라이저"""
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    region_sido = serializers.CharField(required=False, allow_blank=True)
    region_sigungu = serializers.CharField(required=False, allow_blank=True)
    academy_id = serializers.IntegerField(required=False)
    subject = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """필터 유효성 검증"""
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("시작일은 종료일보다 이전이어야 합니다.")
        return data


class ExportDataSerializer(serializers.Serializer):
    """데이터 내보내기 시리얼라이저"""
    data_type = serializers.ChoiceField(choices=[
        ('user_analytics', '사용자 분석'),
        ('academy_analytics', '학원 분석'),
        ('regional_analytics', '지역 분석'),
        ('market_trends', '시장 트렌드'),
        ('conversion_funnel', '전환 퍼널'),
    ])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    format = serializers.ChoiceField(choices=[
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('json', 'JSON'),
    ], default='csv')
    
    def validate(self, data):
        """내보내기 유효성 검증"""
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("시작일은 종료일보다 이전이어야 합니다.")
        return data