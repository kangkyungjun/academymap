from rest_framework import serializers
from .comparison_models import AcademyComparison, ComparisonTemplate, ComparisonHistory
from main.models import Data as Academy
from api.serializers import AcademySerializer
from .review_models import Review
from django.db.models import Avg


class ComparisonAcademySerializer(serializers.ModelSerializer):
    """비교용 학원 시리얼라이저 (상세 정보)"""
    subjects = serializers.SerializerMethodField()
    target_ages = serializers.SerializerMethodField()
    review_stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Academy
        fields = [
            'id', '상호명', '도로명주소', '경도', '위도', '별점',
            '수강료_평균', '전화번호', '영업시간', '셔틀버스',
            'subjects', 'target_ages', 'review_stats'
        ]
    
    def get_subjects(self, obj):
        """학원 과목 정보"""
        subjects = []
        if obj.과목_수학: subjects.append('수학')
        if obj.과목_영어: subjects.append('영어')
        if obj.과목_과학: subjects.append('과학')
        if obj.과목_외국어: subjects.append('외국어')
        if obj.과목_예체능: subjects.append('예체능')
        if obj.과목_논술: subjects.append('논술')
        if obj.과목_종합: subjects.append('종합')
        if hasattr(obj, '과목_컴퓨터') and obj.과목_컴퓨터: subjects.append('컴퓨터')
        return subjects
    
    def get_target_ages(self, obj):
        """대상 연령대"""
        ages = []
        if obj.대상_유아: ages.append('유아')
        if obj.대상_초등: ages.append('초등')
        if obj.대상_중등: ages.append('중등')
        if obj.대상_고등: ages.append('고등')
        if obj.대상_일반: ages.append('일반')
        return ages
    
    def get_review_stats(self, obj):
        """리뷰 통계"""
        reviews = Review.objects.filter(academy=obj, is_hidden=False)
        if not reviews.exists():
            return {
                'count': 0,
                'average_rating': 0,
                'average_teaching': 0,
                'average_facility': 0,
                'average_management': 0,
                'average_cost': 0,
                'recommend_percentage': 0
            }
        
        stats = reviews.aggregate(
            average_rating=Avg('overall_rating'),
            average_teaching=Avg('teaching_rating'),
            average_facility=Avg('facility_rating'),
            average_management=Avg('management_rating'),
            average_cost=Avg('cost_rating')
        )
        
        recommend_count = reviews.filter(would_recommend=True).count()
        recommend_percentage = (recommend_count / reviews.count()) * 100
        
        return {
            'count': reviews.count(),
            'average_rating': round(stats['average_rating'] or 0, 2),
            'average_teaching': round(stats['average_teaching'] or 0, 2),
            'average_facility': round(stats['average_facility'] or 0, 2),
            'average_management': round(stats['average_management'] or 0, 2),
            'average_cost': round(stats['average_cost'] or 0, 2),
            'recommend_percentage': round(recommend_percentage, 2)
        }


class AcademyComparisonSerializer(serializers.ModelSerializer):
    """학원 비교 시리얼라이저"""
    academies = ComparisonAcademySerializer(many=True, read_only=True)
    academy_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        min_length=2,
        max_length=6
    )
    academy_count = serializers.ReadOnlyField()
    comparison_results = serializers.SerializerMethodField()
    
    class Meta:
        model = AcademyComparison
        fields = [
            'id', 'name', 'description', 'academies', 'academy_ids', 'academy_count',
            'compare_tuition', 'compare_rating', 'compare_distance', 'compare_subjects',
            'compare_facilities', 'tuition_weight', 'rating_weight', 'distance_weight',
            'quality_weight', 'base_latitude', 'base_longitude', 'base_address',
            'is_public', 'created_at', 'updated_at', 'comparison_results'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_comparison_results(self, obj):
        """비교 결과 (점수 포함)"""
        return obj.calculate_scores()
    
    def validate_academy_ids(self, value):
        """학원 ID 유효성 검증"""
        if len(value) < 2:
            raise serializers.ValidationError("최소 2개 이상의 학원을 선택해야 합니다.")
        if len(value) > 6:
            raise serializers.ValidationError("최대 6개까지 학원을 비교할 수 있습니다.")
        
        # 모든 학원이 존재하는지 확인
        existing_ids = Academy.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_ids)
        if missing_ids:
            raise serializers.ValidationError(f"존재하지 않는 학원 ID: {list(missing_ids)}")
        
        return value
    
    def create(self, validated_data):
        """비교 생성"""
        academy_ids = validated_data.pop('academy_ids')
        user = self.context['request'].user
        
        comparison = AcademyComparison.objects.create(
            user=user,
            **validated_data
        )
        
        # 학원들 추가
        academies = Academy.objects.filter(id__in=academy_ids)
        comparison.academies.set(academies)
        
        # 기록 생성
        ComparisonHistory.objects.create(
            user=user,
            comparison=comparison,
            action='created',
            details={'academy_ids': academy_ids}
        )
        
        return comparison
    
    def update(self, instance, validated_data):
        """비교 수정"""
        academy_ids = validated_data.pop('academy_ids', None)
        
        # 기본 필드 업데이트
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # 학원 목록 업데이트
        if academy_ids is not None:
            academies = Academy.objects.filter(id__in=academy_ids)
            instance.academies.set(academies)
        
        # 기록 생성
        ComparisonHistory.objects.create(
            user=self.context['request'].user,
            comparison=instance,
            action='modified',
            details={'academy_ids': academy_ids} if academy_ids else {}
        )
        
        return instance


class ComparisonListSerializer(serializers.ModelSerializer):
    """비교 목록 시리얼라이저 (간단한 정보)"""
    academy_count = serializers.ReadOnlyField()
    academy_names = serializers.SerializerMethodField()
    
    class Meta:
        model = AcademyComparison
        fields = [
            'id', 'name', 'description', 'academy_count', 'academy_names',
            'is_public', 'created_at', 'updated_at'
        ]
    
    def get_academy_names(self, obj):
        """비교 대상 학원명 목록"""
        return [academy.상호명 for academy in obj.academies.all()[:3]]


class ComparisonTemplateSerializer(serializers.ModelSerializer):
    """비교 템플릿 시리얼라이저"""
    
    class Meta:
        model = ComparisonTemplate
        fields = [
            'id', 'name', 'description', 'compare_tuition', 'compare_rating',
            'compare_distance', 'compare_subjects', 'compare_facilities',
            'tuition_weight', 'rating_weight', 'distance_weight', 'quality_weight',
            'is_default', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        """템플릿 생성"""
        user = self.context['request'].user
        return ComparisonTemplate.objects.create(user=user, **validated_data)


class ComparisonHistorySerializer(serializers.ModelSerializer):
    """비교 기록 시리얼라이저"""
    comparison_name = serializers.CharField(source='comparison.name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = ComparisonHistory
        fields = [
            'id', 'comparison', 'comparison_name', 'action', 'action_display',
            'details', 'created_at'
        ]


class QuickComparisonSerializer(serializers.Serializer):
    """빠른 비교 시리얼라이저"""
    academy_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=2,
        max_length=6
    )
    base_latitude = serializers.FloatField(required=False)
    base_longitude = serializers.FloatField(required=False)
    weights = serializers.DictField(
        child=serializers.IntegerField(min_value=1, max_value=5),
        required=False
    )
    
    def validate_academy_ids(self, value):
        """학원 ID 유효성 검증"""
        existing_ids = Academy.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_ids)
        if missing_ids:
            raise serializers.ValidationError(f"존재하지 않는 학원 ID: {list(missing_ids)}")
        return value


class ComparisonExportSerializer(serializers.Serializer):
    """비교 결과 내보내기 시리얼라이저"""
    format = serializers.ChoiceField(
        choices=[
            ('json', 'JSON'),
            ('csv', 'CSV'),
            ('excel', 'Excel')
        ],
        default='json'
    )
    include_details = serializers.BooleanField(default=True)
    include_scores = serializers.BooleanField(default=True)