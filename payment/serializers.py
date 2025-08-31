from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Payment, PaymentMethod, PaymentRefund, 
    PaymentSubscription, PaymentWebhook, PaymentStatistics
)
from main.models import Data as Academy

User = get_user_model()


class PaymentMethodSerializer(serializers.ModelSerializer):
    fee_display = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'provider', 'method_type', 'fee_rate', 
                 'fixed_fee', 'minimum_amount', 'maximum_amount', 
                 'is_active', 'fee_display']
        read_only_fields = ['id']
    
    def get_fee_display(self, obj):
        fee_parts = []
        if obj.fee_rate > 0:
            fee_parts.append(f"{obj.fee_rate}%")
        if obj.fixed_fee > 0:
            fee_parts.append(f"{obj.fixed_fee:,}원")
        return " + ".join(fee_parts) if fee_parts else "무료"


class PaymentCreateSerializer(serializers.Serializer):
    academy_id = serializers.IntegerField()
    service_type = serializers.ChoiceField(choices=[
        ('consultation', '상담'),
        ('course_registration', '수강신청'),
        ('premium_listing', '프리미엄 등록'),
        ('advertisement', '광고'),
        ('subscription', '구독'),
    ])
    amount = serializers.IntegerField(min_value=100)
    product_name = serializers.CharField(max_length=100)
    payment_method_id = serializers.IntegerField()
    return_url = serializers.URLField(required=False)
    notice_url = serializers.URLField(required=False)
    
    def validate_academy_id(self, value):
        try:
            Academy.objects.get(id=value)
            return value
        except Academy.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 학원입니다.")
    
    def validate_payment_method_id(self, value):
        try:
            payment_method = PaymentMethod.objects.get(id=value, is_active=True)
            return value
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError("사용할 수 없는 결제 수단입니다.")


class PaymentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    academy_name = serializers.CharField(source='academy.상호명', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'payment_id', 'merchant_uid', 'imp_uid', 'pg_tid',
            'user', 'user_name', 'academy', 'academy_name',
            'service_type', 'service_type_display', 'amount', 'discount_amount',
            'final_amount', 'fee_amount', 'product_name',
            'payment_method', 'payment_method_name', 'status', 'status_display',
            'pg_response', 'failure_reason', 'receipt_url',
            'created_at', 'paid_at', 'failed_at', 'cancelled_at'
        ]
        read_only_fields = [
            'id', 'payment_id', 'imp_uid', 'pg_tid', 'discount_amount',
            'final_amount', 'fee_amount', 'pg_response', 'failure_reason',
            'receipt_url', 'created_at', 'paid_at', 'failed_at', 'cancelled_at'
        ]


class PaymentRefundCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)
    refund_amount = serializers.IntegerField(min_value=100, required=False)
    
    def validate(self, attrs):
        payment = self.context['payment']
        refund_amount = attrs.get('refund_amount')
        
        if refund_amount and refund_amount > payment.final_amount:
            raise serializers.ValidationError("환불 금액이 결제 금액을 초과할 수 없습니다.")
        
        return attrs


class PaymentRefundSerializer(serializers.ModelSerializer):
    payment_merchant_uid = serializers.CharField(source='payment.merchant_uid', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PaymentRefund
        fields = [
            'id', 'refund_id', 'payment', 'payment_merchant_uid',
            'refund_amount', 'reason', 'status', 'status_display',
            'pg_response', 'failure_reason', 'created_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'refund_id', 'pg_response', 'failure_reason',
            'created_at', 'processed_at'
        ]


class PaymentSubscriptionCreateSerializer(serializers.Serializer):
    academy_id = serializers.IntegerField()
    subscription_type = serializers.ChoiceField(choices=[
        ('basic', '기본'),
        ('premium', '프리미엄'),
        ('enterprise', '엔터프라이즈'),
    ])
    billing_cycle = serializers.ChoiceField(choices=[
        ('monthly', '월간'),
        ('quarterly', '분기'),
        ('yearly', '연간'),
    ])
    payment_method_id = serializers.IntegerField()
    
    def validate_academy_id(self, value):
        try:
            Academy.objects.get(id=value)
            return value
        except Academy.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 학원입니다.")
    
    def validate_payment_method_id(self, value):
        try:
            PaymentMethod.objects.get(id=value, is_active=True, method_type='card')
            return value
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError("구독 결제는 카드만 가능합니다.")


class PaymentSubscriptionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    academy_name = serializers.CharField(source='academy.상호명', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    subscription_type_display = serializers.CharField(source='get_subscription_type_display', read_only=True)
    billing_cycle_display = serializers.CharField(source='get_billing_cycle_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PaymentSubscription
        fields = [
            'id', 'subscription_id', 'customer_uid', 'user', 'user_name',
            'academy', 'academy_name', 'subscription_type', 'subscription_type_display',
            'billing_cycle', 'billing_cycle_display', 'amount', 'payment_method',
            'payment_method_name', 'status', 'status_display', 'trial_end_date',
            'next_billing_date', 'cancelled_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'subscription_id', 'customer_uid', 'trial_end_date',
            'next_billing_date', 'cancelled_at', 'created_at', 'updated_at'
        ]


class PaymentStatisticsSerializer(serializers.ModelSerializer):
    academy_name = serializers.CharField(source='academy.상호명', read_only=True)
    
    class Meta:
        model = PaymentStatistics
        fields = [
            'id', 'academy', 'academy_name', 'period_start', 'period_end',
            'total_payments', 'total_amount', 'total_refunds', 'refund_amount',
            'net_amount', 'average_payment', 'payment_count_by_method',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']