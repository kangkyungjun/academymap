from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    UserPreference, UserBehavior, AcademyVector,
    Recommendation, RecommendationLog, AcademySimilarity
)
from main.models import Data as Academy
import json

User = get_user_model()


class UserPreferenceSerializer(serializers.ModelSerializer):
    preference_data = serializers.SerializerMethodField()
    preference_type_display = serializers.CharField(source='get_preference_type_display', read_only=True)
    
    class Meta:
        model = UserPreference
        fields = [
            'id', 'preference_type', 'preference_type_display',
            'preference_value', 'preference_data', 'weight',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_preference_data(self, obj):
        """선호도 데이터를 파싱하여 반환"""
        return obj.get_preference_data()
    
    def validate_preference_value(self, value):
        """선호도 값 검증"""
        try:
            # JSON 형태인지 확인
            if isinstance(value, str):
                json.loads(value)
            return value
        except (json.JSONDecodeError, TypeError):
            # 문자열인 경우 그대로 반환
            return value
    
    def validate_weight(self, value):
        """가중치 검증"""
        if value < 0.0 or value > 5.0:
            raise serializers.ValidationError("가중치는 0.0에서 5.0 사이의 값이어야 합니다.")
        return value


class UserBehaviorSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    academy_name = serializers.CharField(source='academy.상호명', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = UserBehavior
        fields = [
            'id', 'user', 'user_name', 'academy', 'academy_name',
            'action', 'action_display', 'search_query', 'filter_criteria',
            'session_id', 'page_url', 'referrer', 'duration', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class AcademyVectorSerializer(serializers.ModelSerializer):
    academy_name = serializers.CharField(source='academy.상호명', read_only=True)
    
    class Meta:
        model = AcademyVector
        fields = [
            'id', 'academy', 'academy_name',
            'subject_vector', 'location_vector', 'price_vector',
            'quality_vector', 'facility_vector',
            'popularity_score', 'rating_score', 'engagement_score',
            'vector_version', 'last_updated'
        ]
        read_only_fields = ['id', 'last_updated']


class RecommendationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    academy_name = serializers.CharField(source='academy.상호명', read_only=True)
    model_name = serializers.CharField(source='model.name', read_only=True)
    
    class Meta:
        model = Recommendation
        fields = [
            'id', 'user', 'user_name', 'academy', 'academy_name',
            'model', 'model_name', 'confidence_score', 'relevance_score',
            'final_score', 'reason_type', 'reason_details', 'explanation',
            'context', 'session_id', 'is_clicked', 'is_contacted',
            'feedback_score', 'recommended_at', 'clicked_at'
        ]
        read_only_fields = [
            'id', 'recommended_at', 'clicked_at'
        ]


class AcademyRecommendationSerializer(serializers.ModelSerializer):
    """추천용 학원 정보 시리얼라이저"""
    
    # 기본 정보
    subjects = serializers.SerializerMethodField()
    location_info = serializers.SerializerMethodField()
    contact_info = serializers.SerializerMethodField()
    
    # 추가 정보
    has_shuttle = serializers.SerializerMethodField()
    price_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Academy
        fields = [
            'id', '상호명', '시도명', '시군구명', '도로명주소',
            '위도', '경도', 'subjects', 'location_info', 'contact_info',
            'has_shuttle', 'price_info'
        ]
    
    def get_subjects(self, obj):
        """과목 정보 추출"""
        subjects = {}
        subject_fields = ['과목_유아', '과목_초등', '과목_중등', '과목_고등', '과목_성인']
        
        for field in subject_fields:
            value = getattr(obj, field, None)
            if value and str(value).strip().lower() not in ['nan', '']:
                age_group = field.replace('과목_', '')
                subjects[age_group] = str(value).split(',') if ',' in str(value) else [str(value)]
        
        return subjects
    
    def get_location_info(self, obj):
        """위치 정보"""
        return {
            'address': obj.도로명주소 or '',
            'sido': obj.시도명 or '',
            'sigungu': obj.시군구명 or '',
            'coordinates': {
                'lat': float(obj.위도) if obj.위도 else None,
                'lng': float(obj.경도) if obj.경도 else None
            }
        }
    
    def get_contact_info(self, obj):
        """연락처 정보"""
        contact = {}
        
        if hasattr(obj, '전화번호') and obj.전화번호:
            contact['phone'] = obj.전화번호
        
        if hasattr(obj, '홈페이지') and obj.홈페이지:
            contact['website'] = obj.홈페이지
            
        return contact
    
    def get_has_shuttle(self, obj):
        """셔틀버스 여부"""
        if hasattr(obj, '셔틀버스') and obj.셔틀버스:
            shuttle_info = str(obj.셔틀버스).lower()
            return shuttle_info not in ['nan', '', '없음', 'x', 'no']
        return False
    
    def get_price_info(self, obj):
        """가격 정보"""
        price_info = {'available': False}
        
        if hasattr(obj, '수강료') and obj.수강료:
            fee_str = str(obj.수강료)
            if fee_str.lower() not in ['nan', '']:
                price_info['available'] = True
                price_info['raw_value'] = fee_str
                
                # 숫자 추출 시도
                import re
                numbers = re.findall(r'[\d,]+', fee_str)
                if numbers:
                    try:
                        numeric_value = int(numbers[0].replace(',', ''))
                        price_info['numeric_value'] = numeric_value
                        
                        # 가격 레벨 분류
                        if numeric_value < 100000:
                            price_info['level'] = 'low'
                        elif numeric_value < 300000:
                            price_info['level'] = 'medium'
                        else:
                            price_info['level'] = 'high'
                    except ValueError:
                        pass
        
        return price_info


class AcademySimilaritySerializer(serializers.ModelSerializer):
    academy1_name = serializers.CharField(source='academy1.상호명', read_only=True)
    academy2_name = serializers.CharField(source='academy2.상호명', read_only=True)
    
    class Meta:
        model = AcademySimilarity
        fields = [
            'id', 'academy1', 'academy1_name', 'academy2', 'academy2_name',
            'content_similarity', 'location_similarity', 'user_similarity',
            'overall_similarity', 'calculation_method', 'calculated_at'
        ]
        read_only_fields = ['id', 'calculated_at']


class RecommendationLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    log_type_display = serializers.CharField(source='get_log_type_display', read_only=True)
    
    class Meta:
        model = RecommendationLog
        fields = [
            'id', 'user', 'user_name', 'log_type', 'log_type_display',
            'message', 'data', 'processing_time', 'recommendation_count',
            'session_id', 'ip_address', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class BehaviorTrackingSerializer(serializers.Serializer):
    """행동 추적용 시리얼라이저"""
    academy_id = serializers.IntegerField(required=False, allow_null=True)
    action = serializers.ChoiceField(choices=UserBehavior.ACTION_CHOICES)
    search_query = serializers.CharField(max_length=500, required=False, allow_blank=True)
    filter_criteria = serializers.JSONField(required=False)
    session_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    page_url = serializers.URLField(required=False, allow_blank=True)
    referrer = serializers.URLField(required=False, allow_blank=True)
    duration = serializers.IntegerField(min_value=0, required=False)
    
    def validate_academy_id(self, value):
        """학원 ID 검증"""
        if value is not None:
            try:
                Academy.objects.get(id=value)
                return value
            except Academy.DoesNotExist:
                raise serializers.ValidationError("존재하지 않는 학원입니다.")
        return value


class PreferenceUpdateSerializer(serializers.Serializer):
    """선호도 업데이트용 시리얼라이저"""
    preferences = serializers.JSONField()
    
    def validate_preferences(self, value):
        """선호도 데이터 검증"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("선호도는 딕셔너리 형태여야 합니다.")
        
        valid_types = [choice[0] for choice in UserPreference.PREFERENCE_TYPE_CHOICES]
        
        for pref_type, pref_data in value.items():
            if pref_type not in valid_types:
                raise serializers.ValidationError(f"잘못된 선호도 타입: {pref_type}")
        
        return value


class RecommendationRequestSerializer(serializers.Serializer):
    """추천 요청용 시리얼라이저"""
    limit = serializers.IntegerField(min_value=1, max_value=50, default=10)
    session_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    context = serializers.JSONField(required=False)
    
    # 필터링 옵션
    exclude_academy_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    
    # 위치 기반 필터
    location_filter = serializers.JSONField(required=False)
    
    # 과목 필터
    subject_filter = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    
    def validate_exclude_academy_ids(self, value):
        """제외할 학원 ID 검증"""
        if value:
            existing_ids = set(Academy.objects.filter(id__in=value).values_list('id', flat=True))
            invalid_ids = set(value) - existing_ids
            if invalid_ids:
                raise serializers.ValidationError(f"존재하지 않는 학원 ID: {list(invalid_ids)}")
        return value


class FeedbackSerializer(serializers.Serializer):
    """추천 피드백용 시리얼라이저"""
    score = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_score(self, value):
        """피드백 점수 검증"""
        if not (1 <= value <= 5):
            raise serializers.ValidationError("피드백 점수는 1에서 5 사이의 값이어야 합니다.")
        return value


class RecommendationStatsSerializer(serializers.Serializer):
    """추천 통계용 시리얼라이저"""
    total_recommendations = serializers.IntegerField()
    click_rate = serializers.FloatField()
    contact_rate = serializers.FloatField()
    avg_feedback_score = serializers.FloatField()
    total_feedback = serializers.IntegerField()


class BehaviorStatsSerializer(serializers.Serializer):
    """행동 통계용 시리얼라이저"""
    action = serializers.CharField()
    count = serializers.IntegerField()


class PopularAcademySerializer(serializers.Serializer):
    """인기 학원 통계용 시리얼라이저"""
    academy__상호명 = serializers.CharField()
    recommendation_count = serializers.IntegerField()
    click_count = serializers.IntegerField()


class SystemStatsSerializer(serializers.Serializer):
    """시스템 통계 전체 응답용 시리얼라이저"""
    recommendation_stats = RecommendationStatsSerializer()
    behavior_stats = BehaviorStatsSerializer(many=True)
    popular_academies = PopularAcademySerializer(many=True)