from django.db import models
from django.conf import settings
from main.models import Data as Academy


class AcademyComparison(models.Model):
    """학원 비교"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comparisons',
        verbose_name="사용자"
    )
    name = models.CharField(
        max_length=100,
        verbose_name="비교 목록 이름"
    )
    description = models.TextField(
        blank=True,
        verbose_name="설명"
    )
    
    academies = models.ManyToManyField(
        Academy,
        related_name='comparisons',
        verbose_name="비교 대상 학원들"
    )
    
    # 비교 기준 설정
    compare_tuition = models.BooleanField(
        default=True,
        verbose_name="수강료 비교"
    )
    compare_rating = models.BooleanField(
        default=True,
        verbose_name="평점 비교"
    )
    compare_distance = models.BooleanField(
        default=True,
        verbose_name="거리 비교"
    )
    compare_subjects = models.BooleanField(
        default=True,
        verbose_name="과목 비교"
    )
    compare_facilities = models.BooleanField(
        default=True,
        verbose_name="시설 비교"
    )
    
    # 가중치 설정 (1-5)
    tuition_weight = models.IntegerField(
        default=3,
        choices=[(i, str(i)) for i in range(1, 6)],
        verbose_name="수강료 중요도"
    )
    rating_weight = models.IntegerField(
        default=4,
        choices=[(i, str(i)) for i in range(1, 6)],
        verbose_name="평점 중요도"
    )
    distance_weight = models.IntegerField(
        default=3,
        choices=[(i, str(i)) for i in range(1, 6)],
        verbose_name="거리 중요도"
    )
    quality_weight = models.IntegerField(
        default=5,
        choices=[(i, str(i)) for i in range(1, 6)],
        verbose_name="교육품질 중요도"
    )
    
    # 기준 위치 (거리 계산용)
    base_latitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name="기준 위도"
    )
    base_longitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name="기준 경도"
    )
    base_address = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="기준 주소"
    )
    
    is_public = models.BooleanField(
        default=False,
        verbose_name="공개 여부"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        verbose_name = "학원 비교"
        verbose_name_plural = "학원 비교 목록"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'is_public'], name='comparison_user_public_idx'),
            models.Index(fields=['created_at'], name='comparison_date_idx'),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.name}"
    
    @property
    def academy_count(self):
        return self.academies.count()
    
    def calculate_scores(self):
        """각 학원의 종합 점수 계산"""
        from django.db.models import Avg
        from .review_models import Review
        import math
        
        results = []
        academies = self.academies.all()
        
        for academy in academies:
            score = 0
            details = {}
            
            # 평점 점수 (리뷰 기반)
            if self.compare_rating:
                reviews = Review.objects.filter(academy=academy, is_hidden=False)
                if reviews.exists():
                    avg_rating = reviews.aggregate(Avg('overall_rating'))['overall_rating__avg'] or 0
                    rating_score = (avg_rating / 5) * 100 * (self.rating_weight / 5)
                    score += rating_score
                    details['rating_score'] = round(rating_score, 2)
                    details['average_rating'] = round(avg_rating, 2)
                else:
                    details['rating_score'] = 0
                    details['average_rating'] = 0
            
            # 거리 점수 (기준 위치 기반)
            if self.compare_distance and self.base_latitude and self.base_longitude:
                if academy.위도 and academy.경도:
                    # 하버사인 공식으로 거리 계산
                    lat1, lon1 = math.radians(self.base_latitude), math.radians(self.base_longitude)
                    lat2, lon2 = math.radians(academy.위도), math.radians(academy.경도)
                    
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    a = (math.sin(dlat/2)**2 + 
                         math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2)
                    distance = 2 * math.asin(math.sqrt(a)) * 6371  # km
                    
                    # 거리가 가까울수록 높은 점수 (5km 이내가 만점)
                    distance_score = max(0, (5 - min(distance, 5)) / 5) * 100 * (self.distance_weight / 5)
                    score += distance_score
                    details['distance_score'] = round(distance_score, 2)
                    details['distance_km'] = round(distance, 2)
                else:
                    details['distance_score'] = 0
                    details['distance_km'] = None
            
            # 수강료 점수 (낮을수록 높은 점수)
            if self.compare_tuition and academy.수강료_평균:
                try:
                    tuition = float(academy.수강료_평균.replace(',', '').replace('원', ''))
                    # 10만원 이하가 만점, 50만원 이상이 0점으로 가정
                    tuition_score = max(0, (500000 - min(tuition, 500000)) / 400000) * 100 * (self.tuition_weight / 5)
                    score += tuition_score
                    details['tuition_score'] = round(tuition_score, 2)
                    details['tuition_amount'] = tuition
                except (ValueError, TypeError):
                    details['tuition_score'] = 0
                    details['tuition_amount'] = None
            
            # 교육품질 점수 (리뷰의 세부 평점 기반)
            if reviews.exists():
                quality_avg = reviews.aggregate(
                    teaching=Avg('teaching_rating'),
                    facility=Avg('facility_rating'),
                    management=Avg('management_rating')
                )
                quality_score_val = (
                    (quality_avg['teaching'] or 0) +
                    (quality_avg['facility'] or 0) +
                    (quality_avg['management'] or 0)
                ) / 3
                quality_score = (quality_score_val / 5) * 100 * (self.quality_weight / 5)
                score += quality_score
                details['quality_score'] = round(quality_score, 2)
                details['quality_breakdown'] = {
                    'teaching': round(quality_avg['teaching'] or 0, 2),
                    'facility': round(quality_avg['facility'] or 0, 2),
                    'management': round(quality_avg['management'] or 0, 2)
                }
            else:
                details['quality_score'] = 0
                details['quality_breakdown'] = {
                    'teaching': 0,
                    'facility': 0,
                    'management': 0
                }
            
            results.append({
                'academy': academy,
                'total_score': round(score, 2),
                'details': details
            })
        
        # 점수 순으로 정렬
        results.sort(key=lambda x: x['total_score'], reverse=True)
        return results


class ComparisonTemplate(models.Model):
    """비교 템플릿 (자주 사용하는 비교 기준 저장)"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comparison_templates',
        verbose_name="사용자"
    )
    name = models.CharField(
        max_length=50,
        verbose_name="템플릿 이름"
    )
    description = models.TextField(
        blank=True,
        verbose_name="설명"
    )
    
    # 비교 기준
    compare_tuition = models.BooleanField(default=True)
    compare_rating = models.BooleanField(default=True)
    compare_distance = models.BooleanField(default=True)
    compare_subjects = models.BooleanField(default=True)
    compare_facilities = models.BooleanField(default=True)
    
    # 가중치
    tuition_weight = models.IntegerField(default=3, choices=[(i, str(i)) for i in range(1, 6)])
    rating_weight = models.IntegerField(default=4, choices=[(i, str(i)) for i in range(1, 6)])
    distance_weight = models.IntegerField(default=3, choices=[(i, str(i)) for i in range(1, 6)])
    quality_weight = models.IntegerField(default=5, choices=[(i, str(i)) for i in range(1, 6)])
    
    is_default = models.BooleanField(
        default=False,
        verbose_name="기본 템플릿"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'name')
        verbose_name = "비교 템플릿"
        verbose_name_plural = "비교 템플릿들"
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return f"{self.user.email} - {self.name}"


class ComparisonHistory(models.Model):
    """비교 기록 (사용자의 비교 활동 추적)"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comparison_history',
        verbose_name="사용자"
    )
    comparison = models.ForeignKey(
        AcademyComparison,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name="비교"
    )
    action = models.CharField(
        max_length=20,
        choices=[
            ('created', '생성'),
            ('viewed', '조회'),
            ('modified', '수정'),
            ('shared', '공유'),
            ('exported', '내보내기'),
        ],
        verbose_name="작업"
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="세부사항"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "비교 기록"
        verbose_name_plural = "비교 기록들"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.get_action_display()} - {self.comparison.name}"