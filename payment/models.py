from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

from main.models import Data as Academy


class PaymentMethod(models.Model):
    """결제 수단 모델"""
    PAYMENT_TYPE_CHOICES = [
        ('card', '신용카드'),
        ('bank_transfer', '계좌이체'),
        ('virtual_account', '가상계좌'),
        ('phone', '휴대폰결제'),
        ('kakao_pay', '카카오페이'),
        ('naver_pay', '네이버페이'),
        ('samsung_pay', '삼성페이'),
        ('payco', 'PAYCO'),
        ('toss', '토스페이'),
        ('point', '적립금'),
    ]
    
    PROVIDER_CHOICES = [
        ('iamport', '아임포트'),
        ('toss_payments', '토스페이먼츠'),
        ('kakao_pay', '카카오페이'),
        ('naver_pay', '네이버페이'),
        ('nice_pay', '나이스페이'),
        ('kg_inicis', 'KG이니시스'),
        ('settle', '세틀뱅크'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='결제수단명')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    
    # 수수료 설정
    fee_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('10.00'))],
        verbose_name='수수료율(%)'
    )
    fixed_fee = models.PositiveIntegerField(default=0, verbose_name='고정수수료(원)')
    
    # 상태
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # 설정
    min_amount = models.PositiveIntegerField(default=1000, verbose_name='최소결제금액')
    max_amount = models.PositiveIntegerField(default=10000000, verbose_name='최대결제금액')
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_methods'
        ordering = ['payment_type', 'name']
        indexes = [
            models.Index(fields=['payment_type', 'is_active']),
            models.Index(fields=['provider']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_payment_type_display()})"
    
    def calculate_fee(self, amount):
        """수수료 계산"""
        rate_fee = amount * self.fee_rate / 100
        total_fee = rate_fee + self.fixed_fee
        return int(total_fee)


class Payment(models.Model):
    """결제 모델"""
    STATUS_CHOICES = [
        ('pending', '결제대기'),
        ('processing', '결제진행중'),
        ('completed', '결제완료'),
        ('failed', '결제실패'),
        ('cancelled', '결제취소'),
        ('partial_refunded', '부분환불'),
        ('refunded', '전액환불'),
    ]
    
    # 기본 정보
    payment_id = models.CharField(max_length=100, unique=True, db_index=True)
    merchant_uid = models.CharField(max_length=100, unique=True)  # 주문번호
    imp_uid = models.CharField(max_length=100, blank=True)  # PG사 거래번호
    
    # 결제자 정보
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, related_name='payments')
    
    # 결제 상품/서비스
    service_type = models.CharField(max_length=50, choices=[
        ('course_fee', '수강료'),
        ('registration_fee', '등록비'),
        ('material_fee', '교재비'),
        ('exam_fee', '시험비'),
        ('consultation_fee', '상담비'),
        ('premium_listing', '프리미엄 등록'),
        ('advertisement', '광고'),
    ])
    
    # 결제 정보
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    amount = models.PositiveIntegerField(verbose_name='결제금액')
    discount_amount = models.PositiveIntegerField(default=0, verbose_name='할인금액')
    fee_amount = models.PositiveIntegerField(default=0, verbose_name='수수료')
    final_amount = models.PositiveIntegerField(verbose_name='최종결제금액')
    
    # 상태
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # 결제 상세 정보
    buyer_name = models.CharField(max_length=100)
    buyer_email = models.EmailField()
    buyer_phone = models.CharField(max_length=20)
    buyer_addr = models.CharField(max_length=255, blank=True)
    buyer_postcode = models.CharField(max_length=10, blank=True)
    
    # 상품 정보
    product_name = models.CharField(max_length=200)
    product_description = models.TextField(blank=True)
    
    # PG사 응답 데이터
    pg_response = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True)
    
    # 시간 정보
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # 기타
    receipt_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_id']),
            models.Index(fields=['merchant_uid']),
            models.Index(fields=['imp_uid']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['academy', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.payment_id} - {self.product_name} ({self.final_amount:,}원)"
    
    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = self.generate_payment_id()
        if not self.merchant_uid:
            self.merchant_uid = self.generate_merchant_uid()
        super().save(*args, **kwargs)
    
    def generate_payment_id(self):
        """결제 ID 생성"""
        return f"PAY_{timezone.now().strftime('%Y%m%d')}_{str(uuid.uuid4())[:8].upper()}"
    
    def generate_merchant_uid(self):
        """주문번호 생성"""
        return f"ORD_{timezone.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8].upper()}"
    
    @property
    def is_paid(self):
        return self.status == 'completed'
    
    @property
    def can_cancel(self):
        return self.status in ['completed'] and not self.is_refunded
    
    @property
    def is_refunded(self):
        return self.status in ['partial_refunded', 'refunded']
    
    def mark_as_paid(self):
        """결제 완료 처리"""
        self.status = 'completed'
        self.paid_at = timezone.now()
        self.save()
    
    def mark_as_failed(self, reason=''):
        """결제 실패 처리"""
        self.status = 'failed'
        self.failure_reason = reason
        self.save()
    
    def mark_as_cancelled(self):
        """결제 취소 처리"""
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.save()


class PaymentRefund(models.Model):
    """환불 모델"""
    REFUND_TYPE_CHOICES = [
        ('full', '전액환불'),
        ('partial', '부분환불'),
    ]
    
    REFUND_STATUS_CHOICES = [
        ('requested', '환불요청'),
        ('processing', '환불처리중'),
        ('completed', '환불완료'),
        ('failed', '환불실패'),
        ('rejected', '환불거부'),
    ]
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    refund_id = models.CharField(max_length=100, unique=True)
    
    # 환불 정보
    refund_type = models.CharField(max_length=20, choices=REFUND_TYPE_CHOICES)
    refund_amount = models.PositiveIntegerField(verbose_name='환불금액')
    refund_reason = models.TextField(verbose_name='환불사유')
    
    # 상태
    status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='requested')
    
    # 처리 정보
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='requested_refunds'
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_refunds'
    )
    
    # PG사 응답
    pg_refund_response = models.JSONField(default=dict, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # 시간 정보
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payment_refunds'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['refund_id']),
            models.Index(fields=['payment', 'status']),
            models.Index(fields=['status', 'requested_at']),
        ]
    
    def __str__(self):
        return f"{self.refund_id} - {self.refund_amount:,}원 환불"
    
    def save(self, *args, **kwargs):
        if not self.refund_id:
            self.refund_id = self.generate_refund_id()
        super().save(*args, **kwargs)
    
    def generate_refund_id(self):
        """환불 ID 생성"""
        return f"REF_{timezone.now().strftime('%Y%m%d')}_{str(uuid.uuid4())[:8].upper()}"


class PaymentSubscription(models.Model):
    """구독 결제 모델"""
    SUBSCRIPTION_STATUS_CHOICES = [
        ('active', '활성'),
        ('paused', '일시정지'),
        ('cancelled', '취소'),
        ('expired', '만료'),
    ]
    
    BILLING_CYCLE_CHOICES = [
        ('monthly', '월간'),
        ('quarterly', '분기'),
        ('yearly', '연간'),
    ]
    
    subscription_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, related_name='subscriptions')
    
    # 구독 정보
    plan_name = models.CharField(max_length=100)
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES)
    amount = models.PositiveIntegerField(verbose_name='구독료')
    
    # 상태
    status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES, default='active')
    
    # 날짜 정보
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField()
    
    # 결제 정보
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    last_payment = models.ForeignKey(
        Payment, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='+'
    )
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_subscriptions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subscription_id']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'next_billing_date']),
        ]
    
    def __str__(self):
        return f"{self.subscription_id} - {self.plan_name}"
    
    def save(self, *args, **kwargs):
        if not self.subscription_id:
            self.subscription_id = self.generate_subscription_id()
        super().save(*args, **kwargs)
    
    def generate_subscription_id(self):
        """구독 ID 생성"""
        return f"SUB_{timezone.now().strftime('%Y%m%d')}_{str(uuid.uuid4())[:8].upper()}"
    
    @property
    def is_active(self):
        return self.status == 'active'
    
    def cancel_subscription(self):
        """구독 취소"""
        self.status = 'cancelled'
        self.end_date = timezone.now()
        self.save()


class PaymentWebhook(models.Model):
    """웹훅 로그 모델"""
    webhook_id = models.CharField(max_length=100, unique=True)
    provider = models.CharField(max_length=50)
    event_type = models.CharField(max_length=50)
    
    # 데이터
    raw_data = models.JSONField()
    processed_data = models.JSONField(default=dict, blank=True)
    
    # 처리 상태
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    
    # 관련 결제
    payment = models.ForeignKey(
        Payment, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='webhooks'
    )
    
    # 시간 정보
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payment_webhooks'
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['provider', 'event_type']),
            models.Index(fields=['is_processed', 'received_at']),
        ]
    
    def __str__(self):
        return f"{self.provider} - {self.event_type} ({self.webhook_id})"
    
    def save(self, *args, **kwargs):
        if not self.webhook_id:
            self.webhook_id = str(uuid.uuid4())
        super().save(*args, **kwargs)
    
    def mark_as_processed(self):
        """처리 완료 표시"""
        self.is_processed = True
        self.processed_at = timezone.now()
        self.save()
    
    def mark_as_failed(self, error_message):
        """처리 실패 표시"""
        self.processing_error = error_message
        self.retry_count += 1
        self.save()


class PaymentStatistics(models.Model):
    """결제 통계 모델"""
    date = models.DateField()
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, null=True, blank=True)
    
    # 결제 통계
    total_payments = models.PositiveIntegerField(default=0)
    total_amount = models.PositiveBigIntegerField(default=0)
    successful_payments = models.PositiveIntegerField(default=0)
    failed_payments = models.PositiveIntegerField(default=0)
    cancelled_payments = models.PositiveIntegerField(default=0)
    
    # 환불 통계
    total_refunds = models.PositiveIntegerField(default=0)
    refund_amount = models.PositiveBigIntegerField(default=0)
    
    # 결제수단별 통계
    card_payments = models.PositiveIntegerField(default=0)
    card_amount = models.PositiveBigIntegerField(default=0)
    transfer_payments = models.PositiveIntegerField(default=0)
    transfer_amount = models.PositiveBigIntegerField(default=0)
    mobile_payments = models.PositiveIntegerField(default=0)
    mobile_amount = models.PositiveBigIntegerField(default=0)
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_statistics'
        unique_together = ['date', 'academy']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['academy', 'date']),
        ]
    
    def __str__(self):
        academy_name = self.academy.상호명 if self.academy else '전체'
        return f"{self.date} - {academy_name} 결제통계"