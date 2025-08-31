from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    PaymentMethod, Payment, PaymentRefund, 
    PaymentSubscription, PaymentWebhook, PaymentStatistics
)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'payment_type', 'fee_display', 'is_active', 'created_at']
    list_filter = ['provider', 'payment_type', 'is_active', 'created_at']
    search_fields = ['name', 'provider']
    ordering = ['provider', 'payment_type', 'name']
    
    def fee_display(self, obj):
        fee_parts = []
        if obj.fee_rate > 0:
            fee_parts.append(f"{obj.fee_rate}%")
        if obj.fixed_fee > 0:
            fee_parts.append(f"{obj.fixed_fee:,}원")
        return " + ".join(fee_parts) if fee_parts else "무료"
    fee_display.short_description = '수수료'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_id', 'merchant_uid', 'user_display', 'academy_display',
        'amount_display', 'status_display', 'service_type', 'created_at'
    ]
    list_filter = [
        'status', 'service_type', 'payment_method__provider', 
        'created_at', 'paid_at'
    ]
    search_fields = [
        'payment_id', 'merchant_uid', 'imp_uid', 'user__username',
        'user__email', 'academy__상호명', 'product_name'
    ]
    readonly_fields = [
        'payment_id', 'imp_uid', 'discount_amount',
        'final_amount', 'fee_amount', 'pg_response', 'receipt_url',
        'created_at', 'paid_at', 'cancelled_at'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('payment_id', 'merchant_uid', 'imp_uid', 'pg_tid')
        }),
        ('결제 정보', {
            'fields': (
                'user', 'academy', 'service_type', 'product_name',
                'amount', 'discount_amount', 'final_amount', 'fee_amount',
                'payment_method'
            )
        }),
        ('상태 정보', {
            'fields': ('status', 'failure_reason', 'pg_response', 'receipt_url')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'paid_at', 'cancelled_at')
        }),
    )
    
    def user_display(self, obj):
        if obj.user:
            return f"{obj.user.get_full_name() or obj.user.username}"
        return '-'
    user_display.short_description = '사용자'
    
    def academy_display(self, obj):
        if obj.academy:
            return obj.academy.상호명
        return '-'
    academy_display.short_description = '학원'
    
    def amount_display(self, obj):
        return f"{obj.final_amount:,}원"
    amount_display.short_description = '결제금액'
    
    def status_display(self, obj):
        colors = {
            'pending': '#ffc107',
            'paid': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
            'partially_refunded': '#fd7e14',
            'refunded': '#17a2b8'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = '상태'


@admin.register(PaymentRefund)
class PaymentRefundAdmin(admin.ModelAdmin):
    list_display = [
        'refund_id', 'payment_display', 'refund_amount_display',
        'status_display', 'reason_short', 'requested_at'
    ]
    list_filter = ['status', 'requested_at', 'processed_at']
    search_fields = [
        'refund_id', 'payment__payment_id', 'payment__merchant_uid',
        'refund_reason'
    ]
    readonly_fields = [
        'refund_id', 'requested_at', 'processed_at'
    ]
    ordering = ['-requested_at']
    
    def payment_display(self, obj):
        return obj.payment.merchant_uid
    payment_display.short_description = '결제'
    
    def refund_amount_display(self, obj):
        return f"{obj.refund_amount:,}원"
    refund_amount_display.short_description = '환불금액'
    
    def status_display(self, obj):
        colors = {
            'pending': '#ffc107',
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = '상태'
    
    def reason_short(self, obj):
        return obj.refund_reason[:50] + '...' if len(obj.refund_reason) > 50 else obj.refund_reason
    reason_short.short_description = '사유'


@admin.register(PaymentSubscription)
class PaymentSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'subscription_id', 'user_display', 'academy_display',
        'plan_name', 'billing_cycle', 'amount_display',
        'status_display', 'next_billing_date'
    ]
    list_filter = [
        'billing_cycle', 'status',
        'created_at', 'next_billing_date'
    ]
    search_fields = [
        'subscription_id', 'user__username',
        'user__email', 'academy__상호명'
    ]
    readonly_fields = [
        'subscription_id', 'next_billing_date', 'created_at', 'updated_at'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    def user_display(self, obj):
        return f"{obj.user.get_full_name() or obj.user.username}"
    user_display.short_description = '사용자'
    
    def academy_display(self, obj):
        return obj.academy.상호명
    academy_display.short_description = '학원'
    
    def amount_display(self, obj):
        return f"{obj.amount:,}원"
    amount_display.short_description = '결제금액'
    
    def status_display(self, obj):
        colors = {
            'trial': '#17a2b8',
            'active': '#28a745',
            'cancelled': '#6c757d',
            'expired': '#dc3545',
            'past_due': '#ffc107'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = '상태'


@admin.register(PaymentWebhook)
class PaymentWebhookAdmin(admin.ModelAdmin):
    list_display = [
        'provider', 'event_type', 'processed_display',
        'received_at', 'processed_at'
    ]
    list_filter = ['provider', 'event_type', 'is_processed', 'received_at']
    search_fields = ['provider', 'event_type']
    readonly_fields = ['raw_data', 'received_at', 'processed_at']
    ordering = ['-received_at']
    
    def processed_display(self, obj):
        if obj.is_processed:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">처리완료</span>'
            )
        else:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">대기중</span>'
            )
    processed_display.short_description = '처리상태'


@admin.register(PaymentStatistics)
class PaymentStatisticsAdmin(admin.ModelAdmin):
    list_display = [
        'academy_display', 'date', 'total_payments',
        'total_amount_display', 'net_amount_display', 'created_at'
    ]
    list_filter = ['date', 'created_at']
    search_fields = ['academy__상호명']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-date', 'academy']
    
    def academy_display(self, obj):
        return obj.academy.상호명 if obj.academy else '전체'
    academy_display.short_description = '학원'
    
    def total_amount_display(self, obj):
        return f"{obj.total_amount:,}원"
    total_amount_display.short_description = '총 결제금액'
    
    def net_amount_display(self, obj):
        net_amount = obj.total_amount - obj.refund_amount
        return f"{net_amount:,}원"
    net_amount_display.short_description = '순 결제금액'


# 사용자 정의 액션
@admin.action(description='선택된 결제를 검증')
def verify_selected_payments(modeladmin, request, queryset):
    from .services import PaymentService
    payment_service = PaymentService()
    
    verified_count = 0
    for payment in queryset.filter(status='pending'):
        try:
            # 실제 구현에서는 imp_uid를 가져와야 함
            payment_service.verify_payment(payment, payment.imp_uid)
            verified_count += 1
        except Exception:
            continue
    
    modeladmin.message_user(request, f'{verified_count}개 결제가 검증되었습니다.')

PaymentAdmin.actions = [verify_selected_payments]