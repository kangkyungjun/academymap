from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from main.models import Data as Academy


class Review(models.Model):
    """학원 리뷰"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="사용자"
    )
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="학원"
    )
    
    # 평점 정보
    overall_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="종합 평점"
    )
    teaching_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="강의 품질"
    )
    facility_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="시설 평점"
    )
    management_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="운영 관리"
    )
    cost_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="비용 대비 만족도"
    )
    
    # 리뷰 내용
    title = models.CharField(max_length=200, verbose_name="제목")
    content = models.TextField(verbose_name="리뷰 내용")
    
    # 추가 정보
    attendance_period = models.CharField(
        max_length=50,
        choices=[
            ('1개월 미만', '1개월 미만'),
            ('1-3개월', '1-3개월'),
            ('3-6개월', '3-6개월'),
            ('6개월-1년', '6개월-1년'),
            ('1년 이상', '1년 이상'),
        ],
        verbose_name="수강 기간"
    )
    grade_when_attended = models.CharField(
        max_length=20,
        choices=[
            ('유아', '유아'),
            ('초등 저학년', '초등 저학년'),
            ('초등 고학년', '초등 고학년'),
            ('중1', '중1'), ('중2', '중2'), ('중3', '중3'),
            ('고1', '고1'), ('고2', '고2'), ('고3', '고3'),
            ('재수생', '재수생'),
            ('일반인', '일반인'),
        ],
        verbose_name="수강 당시 학년"
    )
    subjects_taken = models.JSONField(
        default=list, 
        blank=True,
        verbose_name="수강 과목"
    )
    
    # 장단점
    pros = models.TextField(blank=True, verbose_name="장점")
    cons = models.TextField(blank=True, verbose_name="단점")
    
    # 추천 여부
    would_recommend = models.BooleanField(
        default=True,
        verbose_name="추천 여부"
    )
    
    # 익명 여부
    is_anonymous = models.BooleanField(
        default=False,
        verbose_name="익명 작성"
    )
    
    # 상태 관리
    is_verified = models.BooleanField(
        default=False,
        verbose_name="인증된 리뷰"
    )
    is_hidden = models.BooleanField(
        default=False,
        verbose_name="숨김 처리"
    )
    
    # 유용성 평가
    helpful_count = models.PositiveIntegerField(
        default=0,
        verbose_name="도움됨 수"
    )
    not_helpful_count = models.PositiveIntegerField(
        default=0,
        verbose_name="도움 안됨 수"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        unique_together = ('user', 'academy')
        verbose_name = "리뷰"
        verbose_name_plural = "리뷰들"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['academy', 'overall_rating'], name='review_academy_rating_idx'),
            models.Index(fields=['created_at'], name='review_date_idx'),
            models.Index(fields=['is_verified', 'is_hidden'], name='review_status_idx'),
        ]
    
    def __str__(self):
        author = "익명" if self.is_anonymous else self.user.nickname or self.user.username
        return f"{self.academy.상호명} - {author} ({self.overall_rating}점)"
    
    @property
    def average_detailed_rating(self):
        """세부 평점의 평균"""
        return (self.teaching_rating + self.facility_rating + 
                self.management_rating + self.cost_rating) / 4
    
    @property
    def helpful_ratio(self):
        """도움됨 비율"""
        total = self.helpful_count + self.not_helpful_count
        if total == 0:
            return 0
        return (self.helpful_count / total) * 100


class ReviewImage(models.Model):
    """리뷰 이미지"""
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="리뷰"
    )
    image = models.ImageField(
        upload_to='review_images/%Y/%m/',
        verbose_name="이미지"
    )
    caption = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="이미지 설명"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="정렬 순서"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "리뷰 이미지"
        verbose_name_plural = "리뷰 이미지들"
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"{self.review.academy.상호명} - 이미지 {self.order}"


class ReviewHelpful(models.Model):
    """리뷰 유용성 평가"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="사용자"
    )
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='helpfulness_votes',
        verbose_name="리뷰"
    )
    is_helpful = models.BooleanField(verbose_name="도움됨 여부")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'review')
        verbose_name = "리뷰 유용성 평가"
        verbose_name_plural = "리뷰 유용성 평가들"
    
    def __str__(self):
        helpful_text = "도움됨" if self.is_helpful else "도움 안됨"
        return f"{self.review.academy.상호명} - {helpful_text}"


class ReviewReport(models.Model):
    """리뷰 신고"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="신고자"
    )
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name="신고된 리뷰"
    )
    reason = models.CharField(
        max_length=50,
        choices=[
            ('inappropriate', '부적절한 내용'),
            ('spam', '스팸/광고'),
            ('fake', '허위 리뷰'),
            ('offensive', '욕설/비방'),
            ('personal_info', '개인정보 노출'),
            ('other', '기타'),
        ],
        verbose_name="신고 사유"
    )
    description = models.TextField(
        blank=True,
        verbose_name="상세 설명"
    )
    
    # 처리 상태
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '대기중'),
            ('reviewing', '검토중'),
            ('resolved', '처리완료'),
            ('rejected', '반려'),
        ],
        default='pending',
        verbose_name="처리 상태"
    )
    admin_notes = models.TextField(
        blank=True,
        verbose_name="관리자 메모"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="신고일")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="처리일")
    
    class Meta:
        unique_together = ('user', 'review')
        verbose_name = "리뷰 신고"
        verbose_name_plural = "리뷰 신고들"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.review.academy.상호명} 리뷰 신고 - {self.get_reason_display()}"