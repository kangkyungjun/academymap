from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from datetime import datetime, timedelta
import json
import logging

from .models import (
    Payment, PaymentMethod, PaymentRefund, 
    PaymentSubscription, PaymentWebhook, PaymentStatistics
)
from .serializers import (
    PaymentMethodSerializer, PaymentCreateSerializer, PaymentSerializer,
    PaymentRefundCreateSerializer, PaymentRefundSerializer,
    PaymentSubscriptionCreateSerializer, PaymentSubscriptionSerializer,
    PaymentStatisticsSerializer
)
from .services import PaymentService
from main.models import Data as Academy

logger = logging.getLogger(__name__)


class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
    """결제 수단 조회"""
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PaymentMethod.objects.filter(is_active=True).order_by('provider', 'method_type')
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """결제 수단을 타입별로 분류하여 반환"""
        payment_methods = self.get_queryset()
        grouped = {}
        
        for method in payment_methods:
            if method.method_type not in grouped:
                grouped[method.method_type] = []
            grouped[method.method_type].append(PaymentMethodSerializer(method).data)
        
        return Response(grouped)


class PaymentViewSet(viewsets.ModelViewSet):
    """결제 관리"""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Payment.objects.select_related(
            'user', 'academy', 'payment_method'
        ).filter(user=user)
        
        # 필터링
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        service_type = self.request.query_params.get('service_type')
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        
        academy_id = self.request.query_params.get('academy_id')
        if academy_id:
            queryset = queryset.filter(academy_id=academy_id)
        
        # 날짜 범위
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    def create_payment(self, request):
        """결제 생성"""
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            academy = Academy.objects.get(id=serializer.validated_data['academy_id'])
            payment_service = PaymentService()
            
            with transaction.atomic():
                payment = payment_service.create_payment(
                    user=request.user,
                    academy=academy,
                    **serializer.validated_data
                )
                
                # 결제 준비
                prepare_result = payment_service.prepare_payment(payment)
                
                return Response({
                    'payment': PaymentSerializer(payment).data,
                    'prepare_result': prepare_result
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"Payment creation failed: {e}")
            return Response(
                {'error': '결제 생성 중 오류가 발생했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """결제 검증"""
        payment = self.get_object()
        
        if payment.status != 'pending':
            return Response(
                {'error': '대기 중인 결제만 검증할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            payment_service = PaymentService()
            
            with transaction.atomic():
                verify_result = payment_service.verify_payment(
                    payment, 
                    request.data.get('imp_uid')
                )
                
                return Response({
                    'payment': PaymentSerializer(payment).data,
                    'verify_result': verify_result
                })
                
        except Exception as e:
            logger.error(f"Payment verification failed: {e}")
            return Response(
                {'error': '결제 검증 중 오류가 발생했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """결제 취소"""
        payment = self.get_object()
        
        if payment.status not in ['paid', 'partially_refunded']:
            return Response(
                {'error': '완료된 결제만 취소할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            reason = request.data.get('reason', '사용자 요청')
            cancel_amount = request.data.get('cancel_amount')
            
            payment_service = PaymentService()
            
            with transaction.atomic():
                cancel_result = payment_service.cancel_payment(
                    payment, reason, cancel_amount
                )
                
                return Response({
                    'payment': PaymentSerializer(payment).data,
                    'cancel_result': cancel_result
                })
                
        except Exception as e:
            logger.error(f"Payment cancellation failed: {e}")
            return Response(
                {'error': '결제 취소 중 오류가 발생했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """결제 통계"""
        user = request.user
        
        # 기간별 결제 통계
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        payments = Payment.objects.filter(
            user=user,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        total_payments = payments.count()
        total_amount = sum(p.final_amount for p in payments if p.status == 'paid')
        successful_payments = payments.filter(status='paid').count()
        
        # 결제 수단별 통계
        method_stats = {}
        for payment in payments:
            method_name = payment.payment_method.name if payment.payment_method else 'Unknown'
            if method_name not in method_stats:
                method_stats[method_name] = {'count': 0, 'amount': 0}
            
            method_stats[method_name]['count'] += 1
            if payment.status == 'paid':
                method_stats[method_name]['amount'] += payment.final_amount
        
        # 서비스 타입별 통계
        service_stats = {}
        for payment in payments:
            service_type = payment.get_service_type_display()
            if service_type not in service_stats:
                service_stats[service_type] = {'count': 0, 'amount': 0}
            
            service_stats[service_type]['count'] += 1
            if payment.status == 'paid':
                service_stats[service_type]['amount'] += payment.final_amount
        
        return Response({
            'period': {'start': start_date, 'end': end_date},
            'total_payments': total_payments,
            'successful_payments': successful_payments,
            'success_rate': (successful_payments / total_payments * 100) if total_payments > 0 else 0,
            'total_amount': total_amount,
            'average_amount': total_amount / successful_payments if successful_payments > 0 else 0,
            'method_statistics': method_stats,
            'service_statistics': service_stats
        })


class PaymentRefundViewSet(viewsets.ModelViewSet):
    """환불 관리"""
    serializer_class = PaymentRefundSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return PaymentRefund.objects.select_related('payment').filter(
            payment__user=user
        ).order_by('-created_at')
    
    def create(self, request):
        """환불 요청"""
        payment_id = request.data.get('payment_id')
        payment = get_object_or_404(Payment, id=payment_id, user=request.user)
        
        if payment.status not in ['paid', 'partially_refunded']:
            return Response(
                {'error': '완료된 결제만 환불할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = PaymentRefundCreateSerializer(
            data=request.data, 
            context={'payment': payment}
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            payment_service = PaymentService()
            
            with transaction.atomic():
                refund = payment_service.create_refund(
                    payment=payment,
                    reason=serializer.validated_data['reason'],
                    refund_amount=serializer.validated_data.get('refund_amount')
                )
                
                return Response(
                    PaymentRefundSerializer(refund).data,
                    status=status.HTTP_201_CREATED
                )
                
        except Exception as e:
            logger.error(f"Refund creation failed: {e}")
            return Response(
                {'error': '환불 요청 중 오류가 발생했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentSubscriptionViewSet(viewsets.ModelViewSet):
    """구독 관리"""
    serializer_class = PaymentSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return PaymentSubscription.objects.select_related(
            'user', 'academy', 'payment_method'
        ).filter(user=user).order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    def create_subscription(self, request):
        """구독 생성"""
        serializer = PaymentSubscriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            academy = Academy.objects.get(id=serializer.validated_data['academy_id'])
            payment_service = PaymentService()
            
            with transaction.atomic():
                subscription = payment_service.create_subscription(
                    user=request.user,
                    academy=academy,
                    **serializer.validated_data
                )
                
                return Response(
                    PaymentSubscriptionSerializer(subscription).data,
                    status=status.HTTP_201_CREATED
                )
                
        except Exception as e:
            logger.error(f"Subscription creation failed: {e}")
            return Response(
                {'error': '구독 생성 중 오류가 발생했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancel_subscription(self, request, pk=None):
        """구독 취소"""
        subscription = self.get_object()
        
        if subscription.status != 'active':
            return Response(
                {'error': '활성화된 구독만 취소할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            reason = request.data.get('reason', '사용자 요청')
            payment_service = PaymentService()
            
            with transaction.atomic():
                cancel_result = payment_service.cancel_subscription(subscription, reason)
                
                return Response({
                    'subscription': PaymentSubscriptionSerializer(subscription).data,
                    'cancel_result': cancel_result
                })
                
        except Exception as e:
            logger.error(f"Subscription cancellation failed: {e}")
            return Response(
                {'error': '구독 취소 중 오류가 발생했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """활성 구독 조회"""
        active_subscriptions = self.get_queryset().filter(status='active')
        serializer = self.get_serializer(active_subscriptions, many=True)
        return Response(serializer.data)


class PaymentStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    """결제 통계 (학원용)"""
    serializer_class = PaymentStatisticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # 학원 관계자만 조회 가능 (추후 권한 체크 추가)
        return PaymentStatistics.objects.select_related('academy').order_by('-period_start')
    
    @action(detail=False, methods=['get'])
    def generate(self, request):
        """통계 생성"""
        academy_id = request.query_params.get('academy_id')
        period_type = request.query_params.get('period_type', 'monthly')  # monthly, weekly, daily
        
        if not academy_id:
            return Response(
                {'error': '학원 ID가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            academy = Academy.objects.get(id=academy_id)
            
            # 기간 설정
            end_date = timezone.now().date()
            if period_type == 'daily':
                start_date = end_date
            elif period_type == 'weekly':
                start_date = end_date - timedelta(days=7)
            else:  # monthly
                start_date = end_date.replace(day=1)
            
            # 기존 통계 조회 또는 생성
            statistics, created = PaymentStatistics.objects.get_or_create(
                academy=academy,
                period_start=start_date,
                period_end=end_date,
                defaults={
                    'total_payments': 0,
                    'total_amount': 0,
                    'total_refunds': 0,
                    'refund_amount': 0,
                    'net_amount': 0,
                    'average_payment': 0,
                    'payment_count_by_method': {}
                }
            )
            
            if created or request.query_params.get('force_update'):
                # 통계 계산
                payments = Payment.objects.filter(
                    academy=academy,
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date,
                    status='paid'
                )
                
                refunds = PaymentRefund.objects.filter(
                    payment__academy=academy,
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date,
                    status='completed'
                )
                
                statistics.total_payments = payments.count()
                statistics.total_amount = sum(p.final_amount for p in payments)
                statistics.total_refunds = refunds.count()
                statistics.refund_amount = sum(r.refund_amount for r in refunds)
                statistics.net_amount = statistics.total_amount - statistics.refund_amount
                statistics.average_payment = statistics.total_amount / statistics.total_payments if statistics.total_payments > 0 else 0
                
                # 결제 수단별 카운트
                method_counts = {}
                for payment in payments:
                    method_name = payment.payment_method.name if payment.payment_method else 'Unknown'
                    method_counts[method_name] = method_counts.get(method_name, 0) + 1
                
                statistics.payment_count_by_method = method_counts
                statistics.save()
            
            return Response(PaymentStatisticsSerializer(statistics).data)
            
        except Academy.DoesNotExist:
            return Response(
                {'error': '존재하지 않는 학원입니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Statistics generation failed: {e}")
            return Response(
                {'error': '통계 생성 중 오류가 발생했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )


@method_decorator(csrf_exempt, name='dispatch')
class IamportWebhookView(APIView):
    """아임포트 웹훅 처리"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            imp_uid = data.get('imp_uid')
            merchant_uid = data.get('merchant_uid')
            status_value = data.get('status')
            
            # 웹훅 로그 저장
            PaymentWebhook.objects.create(
                provider='iamport',
                event_type=status_value,
                webhook_data=data,
                processed=False
            )
            
            # 결제 정보 업데이트
            if imp_uid and merchant_uid:
                try:
                    payment = Payment.objects.get(merchant_uid=merchant_uid)
                    payment_service = PaymentService()
                    
                    with transaction.atomic():
                        payment_service.handle_webhook(payment, data)
                    
                    logger.info(f"Iamport webhook processed: {imp_uid}")
                    
                except Payment.DoesNotExist:
                    logger.warning(f"Payment not found for webhook: {merchant_uid}")
            
            return HttpResponse('OK')
            
        except Exception as e:
            logger.error(f"Iamport webhook error: {e}")
            return HttpResponse('Error', status=400)


@method_decorator(csrf_exempt, name='dispatch')
class TossPaymentsWebhookView(APIView):
    """토스페이먼츠 웹훅 처리"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            payment_key = data.get('paymentKey')
            order_id = data.get('orderId')
            event_type = data.get('eventType')
            
            # 웹훅 로그 저장
            PaymentWebhook.objects.create(
                provider='tosspayments',
                event_type=event_type,
                webhook_data=data,
                processed=False
            )
            
            # 결제 정보 업데이트
            if payment_key and order_id:
                try:
                    payment = Payment.objects.get(merchant_uid=order_id)
                    payment_service = PaymentService()
                    
                    with transaction.atomic():
                        payment_service.handle_webhook(payment, data)
                    
                    logger.info(f"TossPayments webhook processed: {payment_key}")
                    
                except Payment.DoesNotExist:
                    logger.warning(f"Payment not found for webhook: {order_id}")
            
            return HttpResponse('OK')
            
        except Exception as e:
            logger.error(f"TossPayments webhook error: {e}")
            return HttpResponse('Error', status=400)


@method_decorator(csrf_exempt, name='dispatch')
class KakaoPayWebhookView(APIView):
    """카카오페이 웹훅 처리"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            tid = data.get('tid')
            partner_order_id = data.get('partner_order_id')
            event_type = data.get('event_type')
            
            # 웹훅 로그 저장
            PaymentWebhook.objects.create(
                provider='kakaopay',
                event_type=event_type,
                webhook_data=data,
                processed=False
            )
            
            # 결제 정보 업데이트
            if tid and partner_order_id:
                try:
                    payment = Payment.objects.get(merchant_uid=partner_order_id)
                    payment_service = PaymentService()
                    
                    with transaction.atomic():
                        payment_service.handle_webhook(payment, data)
                    
                    logger.info(f"KakaoPay webhook processed: {tid}")
                    
                except Payment.DoesNotExist:
                    logger.warning(f"Payment not found for webhook: {partner_order_id}")
            
            return HttpResponse('OK')
            
        except Exception as e:
            logger.error(f"KakaoPay webhook error: {e}")
            return HttpResponse('Error', status=400)


@method_decorator(csrf_exempt, name='dispatch')
class NaverPayWebhookView(APIView):
    """네이버페이 웹훅 처리"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            payment_id = data.get('paymentId')
            merchant_payment_id = data.get('merchantPaymentId')
            event_type = data.get('eventType')
            
            # 웹훅 로그 저장
            PaymentWebhook.objects.create(
                provider='naverpay',
                event_type=event_type,
                webhook_data=data,
                processed=False
            )
            
            # 결제 정보 업데이트
            if payment_id and merchant_payment_id:
                try:
                    payment = Payment.objects.get(merchant_uid=merchant_payment_id)
                    payment_service = PaymentService()
                    
                    with transaction.atomic():
                        payment_service.handle_webhook(payment, data)
                    
                    logger.info(f"NaverPay webhook processed: {payment_id}")
                    
                except Payment.DoesNotExist:
                    logger.warning(f"Payment not found for webhook: {merchant_payment_id}")
            
            return HttpResponse('OK')
            
        except Exception as e:
            logger.error(f"NaverPay webhook error: {e}")
            return HttpResponse('Error', status=400)