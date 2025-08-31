"""
학원 운영자용 대시보드를 위한 모델들
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import Data as Academy
from decimal import Decimal

User = get_user_model()


class AcademyOwner(models.Model):
    """학원 소유자/운영자 관리"""
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='owned_academies',
        verbose_name="사용자"
    )
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='owners',
        verbose_name="학원"
    )
    
    ROLE_CHOICES = [
        ('owner', '원장'),
        ('manager', '관리자'),
        ('staff', '직원'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='owner',
        verbose_name="역할"
    )
    
    # 권한 설정
    can_edit_info = models.BooleanField(default=True, verbose_name="정보 수정 권한")
    can_view_analytics = models.BooleanField(default=True, verbose_name="분석 조회 권한")
    can_manage_content = models.BooleanField(default=True, verbose_name="콘텐츠 관리 권한")
    can_respond_reviews = models.BooleanField(default=True, verbose_name="리뷰 응답 권한")
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False, verbose_name="인증 여부")
    verification_documents = models.TextField(blank=True, verbose_name="인증 문서")
    
    class Meta:
        unique_together = ['user', 'academy']
        verbose_name = "학원 운영자"
        verbose_name_plural = "학원 운영자들"
    
    def __str__(self):
        return f"{self.academy.상호명} - {self.user.username} ({self.get_role_display()})"


class OperatorDashboardSettings(models.Model):
    """운영자 대시보드 설정"""
    
    owner = models.OneToOneField(
        AcademyOwner,
        on_delete=models.CASCADE,
        related_name='dashboard_settings',
        verbose_name="운영자"
    )
    
    # 알림 설정
    email_notifications = models.BooleanField(default=True, verbose_name="이메일 알림")
    sms_notifications = models.BooleanField(default=False, verbose_name="SMS 알림")
    review_alerts = models.BooleanField(default=True, verbose_name="리뷰 알림")
    inquiry_alerts = models.BooleanField(default=True, verbose_name="문의 알림")
    
    # 대시보드 표시 설정
    show_visitor_stats = models.BooleanField(default=True, verbose_name="방문자 통계 표시")
    show_ranking_info = models.BooleanField(default=True, verbose_name="순위 정보 표시")
    show_competitor_analysis = models.BooleanField(default=False, verbose_name="경쟁사 분석 표시")
    show_revenue_tracking = models.BooleanField(default=False, verbose_name="매출 추적 표시")
    
    # 보고서 설정
    weekly_report = models.BooleanField(default=True, verbose_name="주간 리포트")
    monthly_report = models.BooleanField(default=True, verbose_name="월간 리포트")
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "대시보드 설정"
        verbose_name_plural = "대시보드 설정들"
    
    def __str__(self):
        return f"{self.owner.academy.상호명} 대시보드 설정"


class AcademyInquiry(models.Model):
    """학원 문의 관리"""
    
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='inquiries',
        verbose_name="학원"
    )
    
    INQUIRY_TYPE_CHOICES = [
        ('enrollment', '입학 문의'),
        ('curriculum', '커리큘럼 문의'),
        ('tuition', '수강료 문의'),
        ('schedule', '시간표 문의'),
        ('facility', '시설 문의'),
        ('other', '기타 문의'),
    ]
    
    inquiry_type = models.CharField(
        max_length=20,
        choices=INQUIRY_TYPE_CHOICES,
        verbose_name="문의 유형"
    )
    
    # 문의자 정보
    inquirer_name = models.CharField(max_length=100, verbose_name="문의자명")
    inquirer_phone = models.CharField(max_length=15, verbose_name="연락처")
    inquirer_email = models.EmailField(blank=True, verbose_name="이메일")
    
    # 문의 내용
    subject = models.CharField(max_length=200, verbose_name="제목")
    content = models.TextField(verbose_name="문의 내용")
    
    # 상태 관리
    STATUS_CHOICES = [
        ('new', '신규'),
        ('in_progress', '처리중'),
        ('answered', '답변완료'),
        ('closed', '완료'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name="처리 상태"
    )
    
    # 응답 정보
    response = models.TextField(blank=True, verbose_name="응답 내용")
    responded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inquiry_responses',
        verbose_name="응답자"
    )
    responded_at = models.DateTimeField(null=True, blank=True, verbose_name="응답 시간")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="문의 시간")
    priority = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="우선순위"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "학원 문의"
        verbose_name_plural = "학원 문의들"
    
    def __str__(self):
        return f"{self.academy.상호명} - {self.subject} ({self.get_status_display()})"
    
    def is_overdue(self):
        """문의 처리 기한 초과 여부 (48시간)"""
        if self.status in ['answered', 'closed']:
            return False
        return (timezone.now() - self.created_at).total_seconds() > 48 * 3600


class AcademyPromotion(models.Model):
    """학원 프로모션/이벤트 관리"""
    
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='promotions',
        verbose_name="학원"
    )
    
    title = models.CharField(max_length=200, verbose_name="프로모션 제목")
    description = models.TextField(verbose_name="프로모션 설명")
    
    PROMOTION_TYPE_CHOICES = [
        ('discount', '할인 혜택'),
        ('free_trial', '무료 체험'),
        ('gift', '사은품 증정'),
        ('package', '패키지 상품'),
        ('seasonal', '시즌 특가'),
        ('referral', '추천 이벤트'),
    ]
    
    promotion_type = models.CharField(
        max_length=20,
        choices=PROMOTION_TYPE_CHOICES,
        verbose_name="프로모션 유형"
    )
    
    # 할인 정보
    discount_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        verbose_name="할인율(%)"
    )
    discount_amount = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="할인 금액(원)"
    )
    
    # 기간 설정
    start_date = models.DateTimeField(verbose_name="시작일")
    end_date = models.DateTimeField(verbose_name="종료일")
    
    # 조건 설정
    min_months = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="최소 수강 개월"
    )
    max_participants = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="최대 참여자 수"
    )
    current_participants = models.IntegerField(default=0, verbose_name="현재 참여자 수")
    
    # 상태
    is_active = models.BooleanField(default=True, verbose_name="활성 상태")
    is_featured = models.BooleanField(default=False, verbose_name="추천 프로모션")
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_promotions',
        verbose_name="생성자"
    )
    
    class Meta:
        ordering = ['-is_featured', '-created_at']
        verbose_name = "학원 프로모션"
        verbose_name_plural = "학원 프로모션들"
    
    def __str__(self):
        return f"{self.academy.상호명} - {self.title}"
    
    def is_valid(self):
        """프로모션 유효성 확인"""
        now = timezone.now()
        return (
            self.is_active and 
            self.start_date <= now <= self.end_date and
            (self.max_participants is None or 
             self.current_participants < self.max_participants)
        )
    
    def remaining_days(self):
        """프로모션 남은 일수"""
        if not self.is_valid():
            return 0
        return (self.end_date - timezone.now()).days


class RevenueTracking(models.Model):
    """매출 추적 (선택적 기능)"""
    
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='revenue_records',
        verbose_name="학원"
    )
    
    # 매출 기간
    year = models.IntegerField(verbose_name="년도")
    month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="월"
    )
    
    # 매출 정보
    student_count = models.IntegerField(default=0, verbose_name="학생 수")
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="총 매출"
    )
    average_tuition = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="평균 수강료"
    )
    
    # 비용 정보
    operating_costs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="운영비용"
    )
    marketing_costs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="마케팅 비용"
    )
    
    # 자동 계산 필드
    net_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="순이익"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['academy', 'year', 'month']
        ordering = ['-year', '-month']
        verbose_name = "매출 추적"
        verbose_name_plural = "매출 추적들"
    
    def __str__(self):
        return f"{self.academy.상호명} - {self.year}년 {self.month}월"
    
    def save(self, *args, **kwargs):
        # 순이익 자동 계산
        self.net_profit = self.total_revenue - self.operating_costs - self.marketing_costs
        
        # 평균 수강료 자동 계산
        if self.student_count > 0:
            self.average_tuition = self.total_revenue / self.student_count
        
        super().save(*args, **kwargs)


class CompetitorAnalysis(models.Model):
    """경쟁사 분석"""
    
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='competitor_analyses',
        verbose_name="기준 학원"
    )
    competitor = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='as_competitor',
        verbose_name="경쟁 학원"
    )
    
    # 분석 데이터
    distance_km = models.FloatField(verbose_name="거리(km)")
    price_comparison = models.CharField(
        max_length=20,
        choices=[
            ('cheaper', '더 저렴'),
            ('similar', '비슷함'),
            ('expensive', '더 비쌈'),
        ],
        verbose_name="가격 비교"
    )
    
    rating_difference = models.FloatField(
        null=True,
        blank=True,
        verbose_name="평점 차이"
    )
    
    # 분석 메모
    strengths = models.JSONField(default=list, verbose_name="경쟁 우위")
    weaknesses = models.JSONField(default=list, verbose_name="경쟁 열위")
    opportunities = models.JSONField(default=list, verbose_name="기회 요소")
    
    last_analyzed = models.DateTimeField(auto_now=True, verbose_name="최종 분석일")
    
    class Meta:
        unique_together = ['academy', 'competitor']
        verbose_name = "경쟁사 분석"
        verbose_name_plural = "경쟁사 분석들"
    
    def __str__(self):
        return f"{self.academy.상호명} vs {self.competitor.상호명}"