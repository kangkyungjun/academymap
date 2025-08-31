"""
향상된 학원 정보를 위한 직렬화기들
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Data as Academy
from .academy_enhancements import (
    AcademyDetailInfo, AcademyGallery, AcademyStatistics,
    AcademyViewHistory, AcademyFAQ, AcademyNews, AcademyComparison
)

User = get_user_model()


class AcademyDetailInfoSerializer(serializers.ModelSerializer):
    """학원 상세정보 직렬화기"""
    
    facilities_display = serializers.SerializerMethodField()
    establishment_age = serializers.SerializerMethodField()
    
    class Meta:
        model = AcademyDetailInfo
        fields = [
            'facilities', 'facilities_display', 'total_classrooms',
            'max_students_per_class', 'total_teachers', 'teacher_student_ratio',
            'established_year', 'establishment_age', 'website_url', 'social_media',
            'programs', 'special_programs', 'class_schedule',
            'registration_fee', 'material_fee', 'has_scholarship',
            'parking_info', 'transportation_info', 'notice'
        ]
    
    def get_facilities_display(self, obj):
        return obj.get_facilities_display()
    
    def get_establishment_age(self, obj):
        if obj.established_year:
            from datetime import date
            return date.today().year - obj.established_year
        return None


class AcademyGallerySerializer(serializers.ModelSerializer):
    """학원 갤러리 직렬화기"""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = AcademyGallery
        fields = [
            'id', 'image_url', 'category', 'category_display',
            'title', 'description', 'order', 'uploaded_at'
        ]


class AcademyStatisticsSerializer(serializers.ModelSerializer):
    """학원 통계 직렬화기"""
    
    popularity_grade = serializers.SerializerMethodField()
    view_trend = serializers.SerializerMethodField()
    
    class Meta:
        model = AcademyStatistics
        fields = [
            'view_count', 'monthly_views', 'bookmark_count', 'share_count',
            'review_count', 'average_rating', 'local_rank', 'category_rank',
            'popularity_score', 'popularity_grade', 'view_trend', 'last_updated'
        ]
    
    def get_popularity_grade(self, obj):
        if obj.popularity_score >= 80:
            return '매우 인기'
        elif obj.popularity_score >= 60:
            return '인기'
        elif obj.popularity_score >= 40:
            return '보통'
        elif obj.popularity_score >= 20:
            return '관심 필요'
        else:
            return '낮음'
    
    def get_view_trend(self, obj):
        # 간단한 트렌드 계산 (실제로는 더 복잡한 로직 필요)
        if obj.monthly_views > obj.view_count * 0.3:
            return 'increasing'
        elif obj.monthly_views < obj.view_count * 0.1:
            return 'decreasing'
        else:
            return 'stable'


class AcademyFAQSerializer(serializers.ModelSerializer):
    """학원 FAQ 직렬화기"""
    
    class Meta:
        model = AcademyFAQ
        fields = ['id', 'question', 'answer', 'order']


class AcademyNewsSerializer(serializers.ModelSerializer):
    """학원 소식 직렬화기"""
    
    news_type_display = serializers.CharField(source='get_news_type_display', read_only=True)
    is_active = serializers.SerializerMethodField()
    days_since_published = serializers.SerializerMethodField()
    
    class Meta:
        model = AcademyNews
        fields = [
            'id', 'title', 'content', 'news_type', 'news_type_display',
            'is_important', 'is_pinned', 'is_active', 'publish_date',
            'days_since_published'
        ]
    
    def get_is_active(self, obj):
        return obj.is_active()
    
    def get_days_since_published(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.publish_date
        return delta.days


class EnhancedAcademySerializer(serializers.ModelSerializer):
    """향상된 학원 정보 직렬화기"""
    
    detail_info = AcademyDetailInfoSerializer(read_only=True)
    statistics = AcademyStatisticsSerializer(read_only=True)
    gallery = AcademyGallerySerializer(many=True, read_only=True)
    faqs = AcademyFAQSerializer(many=True, read_only=True)
    recent_news = AcademyNewsSerializer(many=True, read_only=True)
    
    # 계산된 필드들
    comprehensive_score = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()
    target_ages = serializers.SerializerMethodField()
    
    class Meta:
        model = Academy
        fields = [
            'id', '상호명', '도로명주소', '시군구명', '시도명',
            '전화번호', '영업시간', '별점', '수강료_평균', '소개글',
            '학원사진', '경도', '위도', '셔틀버스',
            'detail_info', 'statistics', 'gallery', 'faqs', 'recent_news',
            'comprehensive_score', 'distance', 'is_bookmarked',
            'subjects', 'target_ages'
        ]
    
    def get_comprehensive_score(self, obj):
        from .academy_enhancements import AcademyEnhancementService
        return AcademyEnhancementService.calculate_academy_score(obj)
    
    def get_distance(self, obj):
        # 사용자 위치와의 거리 계산 (context에서 사용자 위치를 받아야 함)
        user_lat = self.context.get('user_lat')
        user_lng = self.context.get('user_lng')
        
        if user_lat and user_lng and obj.위도 and obj.경도:
            import math
            # Haversine 공식을 사용한 거리 계산
            lat1, lng1 = math.radians(user_lat), math.radians(user_lng)
            lat2, lng2 = math.radians(obj.위도), math.radians(obj.경도)
            
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
            c = 2 * math.asin(math.sqrt(a))
            distance = 6371 * c  # 지구 반지름 (km)
            
            return round(distance, 1)
        return None
    
    def get_is_bookmarked(self, obj):
        user = self.context.get('user')
        if user and user.is_authenticated:
            return obj.bookmarked_by.filter(user=user).exists()
        return False
    
    def get_subjects(self, obj):
        subjects = []
        subject_fields = [
            ('과목_종합', '종합'), ('과목_수학', '수학'), ('과목_영어', '영어'),
            ('과목_과학', '과학'), ('과목_외국어', '외국어'), ('과목_예체능', '예체능'),
            ('과목_컴퓨터', '컴퓨터'), ('과목_논술', '논술'), ('과목_기타', '기타'),
            ('과목_독서실스터디카페', '독서실/스터디카페')
        ]
        
        for field, label in subject_fields:
            if getattr(obj, field, False):
                subjects.append(label)
        
        return subjects
    
    def get_target_ages(self, obj):
        ages = []
        age_fields = [
            ('대상_유아', '유아'), ('대상_초등', '초등'), ('대상_중등', '중등'),
            ('대상_고등', '고등'), ('대상_특목고', '특목고'), ('대상_일반', '일반'),
            ('대상_기타', '기타')
        ]
        
        for field, label in age_fields:
            if getattr(obj, field, False):
                ages.append(label)
        
        return ages


class AcademyComparisonSerializer(serializers.Serializer):
    """학원 비교 직렬화기"""
    
    base_academy = EnhancedAcademySerializer(read_only=True)
    compare_academies = EnhancedAcademySerializer(many=True, read_only=True)
    comparison_metrics = serializers.SerializerMethodField()
    
    def get_comparison_metrics(self, obj):
        # 비교 메트릭 계산
        base = obj['base_academy']
        comparisons = obj['compare_academies']
        
        metrics = {
            'price_ranking': [],
            'rating_ranking': [],
            'score_ranking': [],
            'facilities_comparison': {},
            'strengths': [],
            'weaknesses': []
        }
        
        # 가격 순위
        all_academies = [base] + list(comparisons)
        all_academies.sort(key=lambda x: float(x.수강료_평균) if x.수강료_평균 else 0)
        
        for i, academy in enumerate(all_academies, 1):
            if academy.id == base.id:
                metrics['price_ranking'] = {
                    'rank': i,
                    'total': len(all_academies),
                    'status': 'cheapest' if i == 1 else 'most_expensive' if i == len(all_academies) else 'middle'
                }
                break
        
        return metrics


class AcademySearchResultSerializer(serializers.ModelSerializer):
    """학원 검색 결과 직렬화기 (간소화)"""
    
    distance = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    main_subject = serializers.SerializerMethodField()
    summary_score = serializers.SerializerMethodField()
    
    class Meta:
        model = Academy
        fields = [
            'id', '상호명', '도로명주소', '시군구명', '별점',
            '수강료_평균', '학원사진', '경도', '위도',
            'distance', 'is_bookmarked', 'main_subject', 'summary_score'
        ]
    
    def get_distance(self, obj):
        # EnhancedAcademySerializer와 동일한 로직
        user_lat = self.context.get('user_lat')
        user_lng = self.context.get('user_lng')
        
        if user_lat and user_lng and obj.위도 and obj.경도:
            import math
            lat1, lng1 = math.radians(user_lat), math.radians(user_lng)
            lat2, lng2 = math.radians(obj.위도), math.radians(obj.경도)
            
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
            c = 2 * math.asin(math.sqrt(a))
            distance = 6371 * c
            
            return round(distance, 1)
        return None
    
    def get_is_bookmarked(self, obj):
        user = self.context.get('user')
        if user and user.is_authenticated:
            return obj.bookmarked_by.filter(user=user).exists()
        return False
    
    def get_main_subject(self, obj):
        # 첫 번째로 True인 과목 반환
        subject_fields = [
            ('과목_종합', '종합'), ('과목_수학', '수학'), ('과목_영어', '영어'),
            ('과목_과학', '과학'), ('과목_외국어', '외국어'), ('과목_예체능', '예체능'),
            ('과목_컴퓨터', '컴퓨터'), ('과목_논술', '논술'), ('과목_기타', '기타')
        ]
        
        for field, label in subject_fields:
            if getattr(obj, field, False):
                return label
        return '기타'
    
    def get_summary_score(self, obj):
        # 간단한 점수 계산
        score = 0
        if obj.별점:
            score += float(obj.별점) * 20  # 5점 만점을 100점으로
        
        # 통계가 있다면 추가 점수
        if hasattr(obj, 'statistics') and obj.statistics:
            score += min(obj.statistics.popularity_score, 50)
        
        return min(round(score, 1), 100)


class AcademyRecommendationSerializer(serializers.Serializer):
    """학원 추천 결과 직렬화기"""
    
    recommended_academies = AcademySearchResultSerializer(many=True, read_only=True)
    recommendation_reason = serializers.CharField()
    recommendation_score = serializers.FloatField()
    filters_applied = serializers.DictField()
    total_count = serializers.IntegerField()


class AcademyViewHistorySerializer(serializers.ModelSerializer):
    """학원 조회 기록 직렬화기"""
    
    academy_name = serializers.CharField(source='academy.상호명', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = AcademyViewHistory
        fields = [
            'id', 'academy_name', 'user_name', 'viewed_at',
            'duration', 'duration_display', 'referrer'
        ]
    
    def get_duration_display(self, obj):
        if obj.duration:
            if obj.duration >= 60:
                minutes = obj.duration // 60
                seconds = obj.duration % 60
                return f"{minutes}분 {seconds}초"
            else:
                return f"{obj.duration}초"
        return "기록없음"