from django.db import models
from django.contrib.auth import get_user_model
from main.models import Data as Academy
import math

User = get_user_model()


class UserPreferenceProfile(models.Model):
    """사용자 선호도 프로필"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preference_profile',
        verbose_name="사용자"
    )
    
    # 가중치 설정 (1-5)
    distance_weight = models.IntegerField(default=4, verbose_name="거리 중요도")
    price_weight = models.IntegerField(default=3, verbose_name="가격 중요도")
    rating_weight = models.IntegerField(default=5, verbose_name="평점 중요도")
    facility_weight = models.IntegerField(default=3, verbose_name="시설 중요도")
    teacher_weight = models.IntegerField(default=4, verbose_name="강사진 중요도")
    
    # 선호 조건
    max_distance = models.FloatField(default=5.0, verbose_name="최대 거리 (km)")
    max_price_range = models.IntegerField(default=500000, verbose_name="최대 가격대")
    min_rating = models.FloatField(default=3.0, verbose_name="최소 평점")
    
    # 선호 과목 (JSONField)
    preferred_subjects = models.JSONField(default=list, verbose_name="선호 과목")
    
    # 선호 학원 유형
    ACADEMY_TYPES = [
        ('large', '대형 학원'),
        ('medium', '중형 학원'),
        ('small', '소형 학원'),
        ('individual', '개인 학원'),
    ]
    preferred_academy_types = models.JSONField(default=list, verbose_name="선호 학원 유형")
    
    # 선호 시간대
    preferred_time_slots = models.JSONField(
        default=list,
        verbose_name="선호 시간대",
        help_text="['morning', 'afternoon', 'evening', 'weekend']"
    )
    
    # 학습 목적
    LEARNING_PURPOSES = [
        ('exam_prep', '시험 준비'),
        ('grade_improvement', '성적 향상'),
        ('basic_learning', '기초 학습'),
        ('advanced_learning', '심화 학습'),
        ('competition', '경시대회'),
    ]
    learning_purposes = models.JSONField(default=list, verbose_name="학습 목적")
    
    # 기준 위치 (집 또는 학교)
    base_latitude = models.FloatField(null=True, blank=True, verbose_name="기준 위도")
    base_longitude = models.FloatField(null=True, blank=True, verbose_name="기준 경도")
    base_address = models.CharField(max_length=200, blank=True, verbose_name="기준 주소")
    
    # 프로필 업데이트 정보
    last_updated = models.DateTimeField(auto_now=True, verbose_name="마지막 업데이트")
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    
    # 학습 이력 기반 자동 업데이트
    auto_update_enabled = models.BooleanField(default=True, verbose_name="자동 업데이트")
    
    class Meta:
        verbose_name = "사용자 선호도 프로필"
        verbose_name_plural = "사용자 선호도 프로필들"
    
    def __str__(self):
        return f"{self.user.username} 선호도 프로필"
    
    def calculate_academy_score(self, academy, user_location=None):
        """학원에 대한 추천 점수 계산"""
        score = 0
        max_score = 0
        details = {}
        
        # 기준 위치 설정
        if user_location:
            base_lat, base_lng = user_location
        elif self.base_latitude and self.base_longitude:
            base_lat, base_lng = self.base_latitude, self.base_longitude
        else:
            # 기준 위치가 없으면 거리 점수 제외
            base_lat = base_lng = None
        
        # 1. 거리 점수 (가중치 적용)
        if base_lat and base_lng and academy.위도 and academy.경도:
            distance = self._calculate_distance(
                base_lat, base_lng,
                float(academy.위도), float(academy.경도)
            )
            
            if distance <= self.max_distance:
                distance_score = max(0, (self.max_distance - distance) / self.max_distance * 100)
                weighted_distance_score = distance_score * (self.distance_weight / 5)
                score += weighted_distance_score
                details['distance'] = {
                    'actual': distance,
                    'score': distance_score,
                    'weighted_score': weighted_distance_score
                }
            max_score += 100 * (self.distance_weight / 5)
        
        # 2. 가격 점수 (가중치 적용)
        if hasattr(academy, '수강료') and academy.수강료:
            try:
                price = float(academy.수강료.replace(',', '').replace('원', ''))
                if price <= self.max_price_range:
                    price_score = max(0, (self.max_price_range - price) / self.max_price_range * 100)
                    weighted_price_score = price_score * (self.price_weight / 5)
                    score += weighted_price_score
                    details['price'] = {
                        'actual': price,
                        'score': price_score,
                        'weighted_score': weighted_price_score
                    }
            except (ValueError, AttributeError):
                pass
        max_score += 100 * (self.price_weight / 5)
        
        # 3. 평점 점수 (리뷰 기반)
        from accounts.review_models import Review
        reviews = Review.objects.filter(academy=academy, is_hidden=False)
        if reviews.exists():
            avg_rating = reviews.aggregate(models.Avg('overall_rating'))['overall_rating__avg']
            if avg_rating >= self.min_rating:
                rating_score = (avg_rating / 5) * 100
                weighted_rating_score = rating_score * (self.rating_weight / 5)
                score += weighted_rating_score
                details['rating'] = {
                    'actual': avg_rating,
                    'score': rating_score,
                    'weighted_score': weighted_rating_score,
                    'review_count': reviews.count()
                }
        max_score += 100 * (self.rating_weight / 5)
        
        # 4. 과목 매칭 점수
        subject_match_score = self._calculate_subject_match_score(academy)
        if subject_match_score > 0:
            weighted_subject_score = subject_match_score * (self.teacher_weight / 5)
            score += weighted_subject_score
            details['subject_match'] = {
                'score': subject_match_score,
                'weighted_score': weighted_subject_score
            }
        max_score += 100 * (self.teacher_weight / 5)
        
        # 5. 시설 점수 (시설 관련 필드가 있는 경우)
        facility_score = self._calculate_facility_score(academy)
        if facility_score > 0:
            weighted_facility_score = facility_score * (self.facility_weight / 5)
            score += weighted_facility_score
            details['facility'] = {
                'score': facility_score,
                'weighted_score': weighted_facility_score
            }
        max_score += 100 * (self.facility_weight / 5)
        
        # 최종 점수 정규화 (0-100)
        final_score = (score / max_score * 100) if max_score > 0 else 0
        
        return {
            'total_score': round(final_score, 2),
            'raw_score': round(score, 2),
            'max_possible_score': round(max_score, 2),
            'details': details
        }
    
    def _calculate_distance(self, lat1, lng1, lat2, lng2):
        """두 지점 간 거리 계산 (Haversine formula)"""
        R = 6371  # 지구 반지름 (km)
        
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _calculate_subject_match_score(self, academy):
        """과목 매칭 점수 계산"""
        if not self.preferred_subjects:
            return 0
        
        subject_fields = [
            '과목_수학', '과목_영어', '과목_국어', '과목_과학', 
            '과목_사회', '과목_예체능', '과목_논술', '과목_외국어'
        ]
        
        matches = 0
        total_subjects = len(self.preferred_subjects)
        
        for subject in self.preferred_subjects:
            field_name = f'과목_{subject}'
            if field_name in subject_fields and hasattr(academy, field_name):
                if getattr(academy, field_name, False):
                    matches += 1
        
        return (matches / total_subjects * 100) if total_subjects > 0 else 0
    
    def _calculate_facility_score(self, academy):
        """시설 점수 계산 (기본 구현)"""
        # 실제 시설 데이터가 있다면 해당 필드들을 사용
        facility_score = 50  # 기본 점수
        
        # 셔틀 서비스 점수
        if hasattr(academy, '셔틀') and academy.셔틀:
            facility_score += 20
        
        # 주차 가능 여부 (추가 필드가 있다면)
        if hasattr(academy, '주차가능') and getattr(academy, '주차가능', False):
            facility_score += 15
        
        # 카페테리아 등 기타 시설 (추가 필드가 있다면)
        if hasattr(academy, '카페테리아') and getattr(academy, '카페테리아', False):
            facility_score += 15
        
        return min(facility_score, 100)


class RecommendationHistory(models.Model):
    """추천 기록"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recommendation_history',
        verbose_name="사용자"
    )
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='recommendation_history',
        verbose_name="학원"
    )
    
    # 추천 정보
    recommendation_score = models.FloatField(verbose_name="추천 점수")
    recommendation_reason = models.TextField(verbose_name="추천 이유")
    score_details = models.JSONField(default=dict, verbose_name="점수 상세")
    
    # 사용자 반응
    user_clicked = models.BooleanField(default=False, verbose_name="클릭 여부")
    user_bookmarked = models.BooleanField(default=False, verbose_name="즐겨찾기 여부")
    user_contacted = models.BooleanField(default=False, verbose_name="문의 여부")
    user_enrolled = models.BooleanField(default=False, verbose_name="등록 여부")
    
    # 피드백
    user_feedback = models.CharField(
        max_length=20,
        choices=[
            ('like', '좋음'),
            ('dislike', '별로'),
            ('not_interested', '관심 없음'),
            ('already_known', '이미 알고 있음'),
        ],
        null=True,
        blank=True,
        verbose_name="사용자 피드백"
    )
    
    # 추천 컨텍스트
    search_query = models.CharField(max_length=200, blank=True, verbose_name="검색어")
    search_location = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="검색 위치"
    )
    recommendation_type = models.CharField(
        max_length=20,
        choices=[
            ('distance_based', '거리 기반'),
            ('rating_based', '평점 기반'),
            ('price_based', '가격 기반'),
            ('comprehensive', '종합'),
            ('similar_users', '유사 사용자'),
        ],
        default='comprehensive',
        verbose_name="추천 방식"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="추천 시간")
    
    class Meta:
        verbose_name = "추천 기록"
        verbose_name_plural = "추천 기록들"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['academy', 'recommendation_score']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.academy.상호명} ({self.recommendation_score:.1f}점)"


class UserBehaviorLog(models.Model):
    """사용자 행동 로그"""
    
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
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='behavior_logs',
        verbose_name="사용자"
    )
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='user_behaviors',
        verbose_name="학원"
    )
    
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, verbose_name="행동 유형")
    action_data = models.JSONField(default=dict, verbose_name="행동 데이터")
    
    # 위치 정보
    user_latitude = models.FloatField(null=True, blank=True, verbose_name="사용자 위도")
    user_longitude = models.FloatField(null=True, blank=True, verbose_name="사용자 경도")
    
    # 시간 정보
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="행동 시간")
    session_id = models.CharField(max_length=50, blank=True, verbose_name="세션 ID")
    
    class Meta:
        verbose_name = "사용자 행동 로그"
        verbose_name_plural = "사용자 행동 로그들"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action_type']),
            models.Index(fields=['academy', 'action_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        academy_name = self.academy.상호명 if self.academy else "전체"
        return f"{self.user.username} - {self.get_action_type_display()} - {academy_name}"


class LocationBasedRecommendation(models.Model):
    """위치 기반 추천 캐시"""
    
    # 위치 정보 (반경 내 추천 캐싱)
    latitude = models.FloatField(verbose_name="위도")
    longitude = models.FloatField(verbose_name="경도")
    radius = models.FloatField(default=5.0, verbose_name="반경 (km)")
    
    # 추천 대상
    target_subjects = models.JSONField(default=list, verbose_name="대상 과목")
    target_age_groups = models.JSONField(default=list, verbose_name="대상 연령")
    
    # 추천 결과 (캐시된 데이터)
    recommended_academies = models.JSONField(default=list, verbose_name="추천 학원 목록")
    
    # 캐시 정보
    cache_key = models.CharField(max_length=100, unique=True, verbose_name="캐시 키")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성 시간")
    expires_at = models.DateTimeField(verbose_name="만료 시간")
    hit_count = models.IntegerField(default=0, verbose_name="조회 수")
    
    class Meta:
        verbose_name = "위치 기반 추천 캐시"
        verbose_name_plural = "위치 기반 추천 캐시들"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"({self.latitude:.4f}, {self.longitude:.4f}) - {self.radius}km"
    
    def is_expired(self):
        """캐시 만료 여부 확인"""
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def increment_hit_count(self):
        """조회 수 증가"""
        self.hit_count += 1
        self.save(update_fields=['hit_count'])