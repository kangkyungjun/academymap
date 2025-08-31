from rest_framework import serializers
from django.contrib.auth import get_user_model
from .recommendation_models import (
    UserPreferenceProfile, RecommendationHistory, UserBehaviorLog,
    LocationBasedRecommendation
)

User = get_user_model()


class UserPreferenceProfileSerializer(serializers.ModelSerializer):
    """사용자 선호도 프로필 시리얼라이저"""
    
    class Meta:
        model = UserPreferenceProfile
        exclude = ['id', 'user', 'last_updated']
    
    def validate(self, attrs):
        """유효성 검사"""
        
        # 가중치 범위 검사 (1-5)
        weights = ['distance_weight', 'price_weight', 'rating_weight', 
                  'facility_weight', 'teacher_weight']
        
        for weight in weights:
            value = attrs.get(weight)
            if value is not None and not (1 <= value <= 5):
                raise serializers.ValidationError({
                    weight: '가중치는 1-5 사이의 값이어야 합니다.'
                })
        
        # 최대 거리 검사 (0.1-50km)
        max_distance = attrs.get('max_distance')
        if max_distance is not None and not (0.1 <= max_distance <= 50):
            raise serializers.ValidationError({
                'max_distance': '최대 거리는 0.1km-50km 사이여야 합니다.'
            })
        
        # 최소 평점 검사 (1-5)
        min_rating = attrs.get('min_rating')
        if min_rating is not None and not (1.0 <= min_rating <= 5.0):
            raise serializers.ValidationError({
                'min_rating': '최소 평점은 1.0-5.0 사이여야 합니다.'
            })
        
        # 좌표 유효성 검사
        base_lat = attrs.get('base_latitude')
        base_lng = attrs.get('base_longitude')
        
        if base_lat is not None and not (-90 <= base_lat <= 90):
            raise serializers.ValidationError({
                'base_latitude': '위도는 -90~90 범위여야 합니다.'
            })
        
        if base_lng is not None and not (-180 <= base_lng <= 180):
            raise serializers.ValidationError({
                'base_longitude': '경도는 -180~180 범위여야 합니다.'
            })
        
        return attrs


class RecommendationRequestSerializer(serializers.Serializer):
    """추천 요청 시리얼라이저"""
    
    latitude = serializers.FloatField(
        required=False,
        min_value=-90,
        max_value=90,
        help_text="사용자 위도"
    )
    longitude = serializers.FloatField(
        required=False,
        min_value=-180,
        max_value=180,
        help_text="사용자 경도"
    )
    limit = serializers.IntegerField(
        default=10,
        min_value=1,
        max_value=50,
        help_text="추천 개수"
    )
    recommendation_type = serializers.ChoiceField(
        choices=[
            ('distance_based', '거리 기반'),
            ('rating_based', '평점 기반'),
            ('price_based', '가격 기반'),
            ('comprehensive', '종합'),
        ],
        default='comprehensive',
        help_text="추천 방식"
    )
    subjects = serializers.ListField(
        child=serializers.CharField(max_length=20),
        required=False,
        help_text="관심 과목 목록"
    )
    
    def validate(self, attrs):
        """위도/경도 쌍 검증"""
        latitude = attrs.get('latitude')
        longitude = attrs.get('longitude')
        
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                '위도와 경도는 함께 제공되어야 합니다.'
            )
        
        return attrs


class LocationBasedRecommendationSerializer(serializers.Serializer):
    """위치 기반 추천 요청 시리얼라이저"""
    
    latitude = serializers.FloatField(
        min_value=-90,
        max_value=90,
        help_text="위도"
    )
    longitude = serializers.FloatField(
        min_value=-180,
        max_value=180,
        help_text="경도"
    )
    radius = serializers.FloatField(
        default=5.0,
        min_value=0.1,
        max_value=50.0,
        help_text="검색 반경 (km)"
    )
    subjects = serializers.ListField(
        child=serializers.CharField(max_length=20),
        required=False,
        help_text="관심 과목 목록"
    )
    limit = serializers.IntegerField(
        default=10,
        min_value=1,
        max_value=50,
        help_text="추천 개수"
    )


class SimilarAcademyRequestSerializer(serializers.Serializer):
    """유사 학원 추천 요청 시리얼라이저"""
    
    academy_id = serializers.IntegerField(help_text="기준 학원 ID")
    limit = serializers.IntegerField(
        default=5,
        min_value=1,
        max_value=20,
        help_text="추천 개수"
    )


class RecommendationResultSerializer(serializers.Serializer):
    """추천 결과 시리얼라이저"""
    
    academy_id = serializers.IntegerField()
    academy_name = serializers.CharField()
    academy_data = serializers.JSONField()
    score = serializers.FloatField()
    score_details = serializers.JSONField(required=False)
    recommendation_reason = serializers.CharField(required=False)
    distance = serializers.FloatField(required=False)
    similarity_score = serializers.FloatField(required=False)


class RecommendationHistorySerializer(serializers.ModelSerializer):
    """추천 기록 시리얼라이저"""
    
    academy_name = serializers.CharField(
        source='academy.상호명',
        read_only=True
    )
    user_name = serializers.CharField(
        source='user.username',
        read_only=True
    )
    
    class Meta:
        model = RecommendationHistory
        fields = [
            'id', 'academy_name', 'user_name', 'recommendation_score',
            'recommendation_reason', 'score_details', 'user_clicked',
            'user_bookmarked', 'user_contacted', 'user_enrolled',
            'user_feedback', 'search_query', 'search_location',
            'recommendation_type', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserBehaviorLogSerializer(serializers.ModelSerializer):
    """사용자 행동 로그 시리얼라이저"""
    
    academy_name = serializers.CharField(
        source='academy.상호명',
        read_only=True
    )
    
    class Meta:
        model = UserBehaviorLog
        fields = [
            'id', 'academy_name', 'action_type', 'action_data',
            'user_latitude', 'user_longitude', 'created_at', 'session_id'
        ]
        read_only_fields = ['id', 'created_at']


class BehaviorTrackingSerializer(serializers.Serializer):
    """행동 추적 시리얼라이저"""
    
    ACTION_TYPES = [
        ('search', '검색'),
        ('view', '조회'),
        ('bookmark', '즐겨찾기'),
        ('unbookmark', '즐겨찾기 해제'),
        ('review', '리뷰 작성'),
        ('contact', '문의'),
        ('compare', '비교'),
        ('share', '공유'),
    ]
    
    action_type = serializers.ChoiceField(choices=ACTION_TYPES)
    academy_id = serializers.IntegerField(required=False, help_text="학원 ID")
    action_data = serializers.JSONField(
        required=False,
        default=dict,
        help_text="추가 행동 데이터"
    )
    latitude = serializers.FloatField(
        required=False,
        min_value=-90,
        max_value=90,
        help_text="사용자 위도"
    )
    longitude = serializers.FloatField(
        required=False,
        min_value=-180,
        max_value=180,
        help_text="사용자 경도"
    )
    session_id = serializers.CharField(
        required=False,
        max_length=50,
        help_text="세션 ID"
    )
    
    def validate(self, attrs):
        """유효성 검사"""
        latitude = attrs.get('latitude')
        longitude = attrs.get('longitude')
        
        # 위도/경도는 쌍으로 제공되어야 함
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                '위도와 경도는 함께 제공되어야 합니다.'
            )
        
        return attrs


class RecommendationFeedbackSerializer(serializers.Serializer):
    """추천 피드백 시리얼라이저"""
    
    recommendation_id = serializers.IntegerField(help_text="추천 기록 ID")
    feedback = serializers.ChoiceField(
        choices=[
            ('like', '좋음'),
            ('dislike', '별로'),
            ('not_interested', '관심 없음'),
            ('already_known', '이미 알고 있음'),
        ],
        help_text="피드백"
    )
    clicked = serializers.BooleanField(default=False, help_text="클릭 여부")
    bookmarked = serializers.BooleanField(default=False, help_text="즐겨찾기 여부")
    contacted = serializers.BooleanField(default=False, help_text="문의 여부")
    enrolled = serializers.BooleanField(default=False, help_text="등록 여부")


class PreferenceAnalysisSerializer(serializers.Serializer):
    """선호도 분석 결과 시리얼라이저"""
    
    most_viewed_subjects = serializers.ListField(
        child=serializers.CharField(),
        help_text="가장 많이 본 과목들"
    )
    average_preferred_distance = serializers.FloatField(
        help_text="평균 선호 거리 (km)"
    )
    preferred_price_range = serializers.DictField(
        help_text="선호 가격대"
    )
    activity_patterns = serializers.DictField(
        help_text="활동 패턴"
    )
    location_preferences = serializers.DictField(
        help_text="위치 선호도"
    )
    recommendation_accuracy = serializers.FloatField(
        help_text="추천 정확도 (%)"
    )


class RecommendationStatsSerializer(serializers.Serializer):
    """추천 통계 시리얼라이저"""
    
    total_recommendations = serializers.IntegerField(help_text="총 추천 수")
    clicked_recommendations = serializers.IntegerField(help_text="클릭된 추천 수")
    bookmarked_recommendations = serializers.IntegerField(help_text="즐겨찾기된 추천 수")
    click_through_rate = serializers.FloatField(help_text="클릭률 (%)")
    bookmark_rate = serializers.FloatField(help_text="즐겨찾기율 (%)")
    
    # 추천 방식별 통계
    recommendation_type_stats = serializers.DictField(help_text="추천 방식별 통계")
    
    # 시간대별 통계
    daily_stats = serializers.ListField(
        child=serializers.DictField(),
        help_text="일별 통계"
    )
    weekly_stats = serializers.ListField(
        child=serializers.DictField(),
        help_text="주별 통계"
    )
    
    # 인기 학원
    top_recommended_academies = serializers.ListField(
        child=serializers.DictField(),
        help_text="가장 많이 추천된 학원들"
    )