import hashlib
import hmac
import json
import logging
import requests
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional

from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Payment, PaymentMethod, PaymentRefund, PaymentWebhook

logger = logging.getLogger(__name__)


class PaymentGatewayError(Exception):
    """결제 게이트웨이 에러"""
    pass


class BasePaymentService:
    """기본 결제 서비스 클래스"""
    
    def __init__(self):
        self.api_key = None
        self.api_secret = None
        self.base_url = None
    
    def prepare_payment(self, payment: Payment) -> Dict[str, Any]:
        """결제 준비"""
        raise NotImplementedError
    
    def verify_payment(self, payment: Payment, pg_response: Dict[str, Any]) -> bool:
        """결제 검증"""
        raise NotImplementedError
    
    def cancel_payment(self, payment: Payment, reason: str = '') -> Dict[str, Any]:
        """결제 취소"""
        raise NotImplementedError
    
    def refund_payment(self, refund: PaymentRefund) -> Dict[str, Any]:
        """환불 처리"""
        raise NotImplementedError


class IamportService(BasePaymentService):
    """아임포트 결제 서비스"""
    
    def __init__(self):
        super().__init__()
        self.api_key = getattr(settings, 'IAMPORT_API_KEY', '')
        self.api_secret = getattr(settings, 'IAMPORT_API_SECRET', '')
        self.base_url = 'https://api.iamport.kr'
        self.access_token = None
    
    def get_access_token(self) -> str:
        """액세스 토큰 획득"""
        if self.access_token:
            return self.access_token
        
        url = f"{self.base_url}/users/getToken"
        data = {
            'imp_key': self.api_key,
            'imp_secret': self.api_secret
        }
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 0:
                self.access_token = result['response']['access_token']
                return self.access_token
            else:
                raise PaymentGatewayError(f"토큰 획득 실패: {result.get('message')}")
                
        except requests.RequestException as e:
            raise PaymentGatewayError(f"아임포트 API 요청 실패: {str(e)}")
    
    def prepare_payment(self, payment: Payment) -> Dict[str, Any]:
        """결제 준비"""
        return {
            'merchant_uid': payment.merchant_uid,
            'name': payment.product_name,
            'amount': payment.final_amount,
            'buyer_email': payment.buyer_email,
            'buyer_name': payment.buyer_name,
            'buyer_tel': payment.buyer_phone,
            'buyer_addr': payment.buyer_addr,
            'buyer_postcode': payment.buyer_postcode,
            'custom_data': {
                'payment_id': payment.payment_id,
                'service_type': payment.service_type,
            }
        }
    
    def verify_payment(self, payment: Payment, pg_response: Dict[str, Any]) -> bool:
        """결제 검증"""
        imp_uid = pg_response.get('imp_uid')
        if not imp_uid:
            return False
        
        token = self.get_access_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        url = f"{self.base_url}/payments/{imp_uid}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') != 0:
                logger.error(f"결제 조회 실패: {result.get('message')}")
                return False
            
            payment_data = result['response']
            
            # 결제 정보 검증
            if (payment_data.get('merchant_uid') == payment.merchant_uid and
                payment_data.get('amount') == payment.final_amount and
                payment_data.get('status') == 'paid'):
                
                # 결제 정보 업데이트
                payment.imp_uid = imp_uid
                payment.pg_response = payment_data
                payment.receipt_url = payment_data.get('receipt_url', '')
                payment.mark_as_paid()
                
                logger.info(f"결제 검증 성공: {payment.payment_id}")
                return True
            
            logger.error(f"결제 정보 불일치: {payment.payment_id}")
            return False
            
        except requests.RequestException as e:
            logger.error(f"결제 검증 API 요청 실패: {str(e)}")
            return False
    
    def cancel_payment(self, payment: Payment, reason: str = '') -> Dict[str, Any]:
        """결제 취소"""
        if not payment.imp_uid:
            raise PaymentGatewayError("결제 취소할 imp_uid가 없습니다.")
        
        token = self.get_access_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        url = f"{self.base_url}/payments/cancel"
        data = {
            'imp_uid': payment.imp_uid,
            'reason': reason or '사용자 요청',
            'amount': payment.final_amount,
            'checksum': payment.final_amount
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 0:
                payment.mark_as_cancelled()
                logger.info(f"결제 취소 성공: {payment.payment_id}")
                return result['response']
            else:
                raise PaymentGatewayError(f"결제 취소 실패: {result.get('message')}")
                
        except requests.RequestException as e:
            raise PaymentGatewayError(f"결제 취소 API 요청 실패: {str(e)}")
    
    def refund_payment(self, refund: PaymentRefund) -> Dict[str, Any]:
        """환불 처리"""
        payment = refund.payment
        
        if not payment.imp_uid:
            raise PaymentGatewayError("환불할 imp_uid가 없습니다.")
        
        token = self.get_access_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        url = f"{self.base_url}/payments/cancel"
        data = {
            'imp_uid': payment.imp_uid,
            'reason': refund.refund_reason,
            'amount': refund.refund_amount,
            'checksum': payment.final_amount - refund.refund_amount
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 0:
                refund.status = 'completed'
                refund.completed_at = timezone.now()
                refund.pg_refund_response = result['response']
                refund.save()
                
                # 결제 상태 업데이트
                if refund.refund_amount == payment.final_amount:
                    payment.status = 'refunded'
                else:
                    payment.status = 'partial_refunded'
                payment.save()
                
                logger.info(f"환불 처리 성공: {refund.refund_id}")
                return result['response']
            else:
                refund.status = 'failed'
                refund.rejection_reason = result.get('message', '')
                refund.save()
                raise PaymentGatewayError(f"환불 처리 실패: {result.get('message')}")
                
        except requests.RequestException as e:
            refund.status = 'failed'
            refund.rejection_reason = str(e)
            refund.save()
            raise PaymentGatewayError(f"환불 API 요청 실패: {str(e)}")


class TossPaymentsService(BasePaymentService):
    """토스페이먼츠 서비스"""
    
    def __init__(self):
        super().__init__()
        self.client_key = getattr(settings, 'TOSS_CLIENT_KEY', '')
        self.secret_key = getattr(settings, 'TOSS_SECRET_KEY', '')
        self.base_url = 'https://api.tosspayments.com/v1'
    
    def prepare_payment(self, payment: Payment) -> Dict[str, Any]:
        """결제 준비"""
        return {
            'orderId': payment.merchant_uid,
            'orderName': payment.product_name,
            'amount': payment.final_amount,
            'customerEmail': payment.buyer_email,
            'customerName': payment.buyer_name,
            'customerMobilePhone': payment.buyer_phone,
            'successUrl': f"{settings.SITE_URL}/payment/success/",
            'failUrl': f"{settings.SITE_URL}/payment/fail/",
        }
    
    def verify_payment(self, payment: Payment, pg_response: Dict[str, Any]) -> bool:
        """결제 검증"""
        payment_key = pg_response.get('paymentKey')
        if not payment_key:
            return False
        
        import base64
        auth_string = base64.b64encode(f"{self.secret_key}:".encode()).decode()
        headers = {
            'Authorization': f'Basic {auth_string}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}/payments/{payment_key}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            payment_data = response.json()
            
            # 결제 정보 검증
            if (payment_data.get('orderId') == payment.merchant_uid and
                payment_data.get('totalAmount') == payment.final_amount and
                payment_data.get('status') == 'DONE'):
                
                # 결제 정보 업데이트
                payment.imp_uid = payment_key
                payment.pg_response = payment_data
                payment.receipt_url = payment_data.get('receipt', {}).get('url', '')
                payment.mark_as_paid()
                
                logger.info(f"토스페이먼츠 결제 검증 성공: {payment.payment_id}")
                return True
            
            logger.error(f"토스페이먼츠 결제 정보 불일치: {payment.payment_id}")
            return False
            
        except requests.RequestException as e:
            logger.error(f"토스페이먼츠 결제 검증 실패: {str(e)}")
            return False
    
    def cancel_payment(self, payment: Payment, reason: str = '') -> Dict[str, Any]:
        """결제 취소"""
        if not payment.imp_uid:
            raise PaymentGatewayError("결제 취소할 paymentKey가 없습니다.")
        
        import base64
        auth_string = base64.b64encode(f"{self.secret_key}:".encode()).decode()
        headers = {
            'Authorization': f'Basic {auth_string}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}/payments/{payment.imp_uid}/cancel"
        data = {
            'cancelReason': reason or '사용자 요청'
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            payment.mark_as_cancelled()
            logger.info(f"토스페이먼츠 결제 취소 성공: {payment.payment_id}")
            return result
            
        except requests.RequestException as e:
            raise PaymentGatewayError(f"토스페이먼츠 결제 취소 실패: {str(e)}")


class PaymentService:
    """통합 결제 서비스"""
    
    def __init__(self):
        self.services = {
            'iamport': IamportService(),
            'toss_payments': TossPaymentsService(),
        }
    
    def get_service(self, provider: str) -> BasePaymentService:
        """결제 서비스 획득"""
        service = self.services.get(provider)
        if not service:
            raise PaymentGatewayError(f"지원하지 않는 결제 서비스: {provider}")
        return service
    
    def create_payment(self, user, academy, service_type: str, amount: int, 
                      product_name: str, payment_method_id: int = None,
                      **kwargs) -> Payment:
        """결제 생성"""
        try:
            # 결제 수단 조회
            payment_method = None
            if payment_method_id:
                payment_method = PaymentMethod.objects.get(
                    id=payment_method_id, 
                    is_active=True
                )
            else:
                payment_method = PaymentMethod.objects.filter(
                    is_active=True, 
                    is_default=True
                ).first()
            
            if not payment_method:
                raise ValidationError("유효한 결제 수단이 없습니다.")
            
            # 금액 검증
            if amount < payment_method.min_amount or amount > payment_method.max_amount:
                raise ValidationError(
                    f"결제 금액은 {payment_method.min_amount:,}원 ~ {payment_method.max_amount:,}원 사이여야 합니다."
                )
            
            # 할인 금액 계산
            discount_amount = kwargs.get('discount_amount', 0)
            
            # 수수료 계산
            fee_amount = payment_method.calculate_fee(amount - discount_amount)
            
            # 최종 결제 금액
            final_amount = amount - discount_amount
            
            # 결제 생성
            payment = Payment.objects.create(
                user=user,
                academy=academy,
                service_type=service_type,
                payment_method=payment_method,
                amount=amount,
                discount_amount=discount_amount,
                fee_amount=fee_amount,
                final_amount=final_amount,
                product_name=product_name,
                product_description=kwargs.get('product_description', ''),
                buyer_name=kwargs.get('buyer_name', user.get_full_name() or user.username),
                buyer_email=kwargs.get('buyer_email', user.email),
                buyer_phone=kwargs.get('buyer_phone', ''),
                buyer_addr=kwargs.get('buyer_addr', ''),
                buyer_postcode=kwargs.get('buyer_postcode', ''),
            )
            
            logger.info(f"결제 생성 완료: {payment.payment_id}")
            return payment
            
        except Exception as e:
            logger.error(f"결제 생성 실패: {str(e)}")
            raise
    
    def prepare_payment(self, payment: Payment) -> Dict[str, Any]:
        """결제 준비"""
        if not payment.payment_method:
            raise PaymentGatewayError("결제 수단이 설정되지 않았습니다.")
        
        service = self.get_service(payment.payment_method.provider)
        return service.prepare_payment(payment)
    
    def verify_payment(self, payment_id: str, pg_response: Dict[str, Any]) -> bool:
        """결제 검증"""
        try:
            payment = Payment.objects.get(payment_id=payment_id)
            
            if payment.status == 'completed':
                return True
            
            service = self.get_service(payment.payment_method.provider)
            
            if service.verify_payment(payment, pg_response):
                # 결제 완료 후 처리 로직
                self._process_payment_completion(payment)
                return True
            else:
                payment.mark_as_failed('결제 검증 실패')
                return False
                
        except Payment.DoesNotExist:
            logger.error(f"존재하지 않는 결제 ID: {payment_id}")
            return False
        except Exception as e:
            logger.error(f"결제 검증 중 오류: {str(e)}")
            return False
    
    def cancel_payment(self, payment_id: str, reason: str = '') -> bool:
        """결제 취소"""
        try:
            payment = Payment.objects.get(payment_id=payment_id)
            
            if not payment.can_cancel:
                raise ValidationError("취소할 수 없는 결제입니다.")
            
            service = self.get_service(payment.payment_method.provider)
            service.cancel_payment(payment, reason)
            
            logger.info(f"결제 취소 완료: {payment_id}")
            return True
            
        except Payment.DoesNotExist:
            logger.error(f"존재하지 않는 결제 ID: {payment_id}")
            return False
        except Exception as e:
            logger.error(f"결제 취소 실패: {str(e)}")
            raise
    
    def request_refund(self, payment_id: str, refund_amount: int, 
                      refund_reason: str, requested_by) -> PaymentRefund:
        """환불 요청"""
        try:
            payment = Payment.objects.get(payment_id=payment_id)
            
            if not payment.is_paid:
                raise ValidationError("환불할 수 없는 결제입니다.")
            
            # 이미 환불된 금액 확인
            refunded_amount = payment.refunds.filter(
                status='completed'
            ).aggregate(
                total=models.Sum('refund_amount')
            )['total'] or 0
            
            if refunded_amount + refund_amount > payment.final_amount:
                raise ValidationError("환불 가능한 금액을 초과했습니다.")
            
            # 환불 유형 결정
            refund_type = 'full' if refund_amount == payment.final_amount else 'partial'
            
            # 환불 생성
            refund = PaymentRefund.objects.create(
                payment=payment,
                refund_type=refund_type,
                refund_amount=refund_amount,
                refund_reason=refund_reason,
                requested_by=requested_by
            )
            
            logger.info(f"환불 요청 생성: {refund.refund_id}")
            return refund
            
        except Payment.DoesNotExist:
            logger.error(f"존재하지 않는 결제 ID: {payment_id}")
            raise ValidationError("존재하지 않는 결제입니다.")
        except Exception as e:
            logger.error(f"환불 요청 실패: {str(e)}")
            raise
    
    def process_refund(self, refund_id: str, processed_by) -> bool:
        """환불 처리"""
        try:
            refund = PaymentRefund.objects.get(refund_id=refund_id)
            
            if refund.status != 'requested':
                raise ValidationError("처리할 수 없는 환불 요청입니다.")
            
            refund.status = 'processing'
            refund.processed_by = processed_by
            refund.processed_at = timezone.now()
            refund.save()
            
            service = self.get_service(refund.payment.payment_method.provider)
            service.refund_payment(refund)
            
            logger.info(f"환불 처리 완료: {refund_id}")
            return True
            
        except PaymentRefund.DoesNotExist:
            logger.error(f"존재하지 않는 환불 ID: {refund_id}")
            return False
        except Exception as e:
            logger.error(f"환불 처리 실패: {str(e)}")
            raise
    
    def process_webhook(self, provider: str, event_type: str, data: Dict[str, Any]) -> bool:
        """웹훅 처리"""
        try:
            # 웹훅 로그 저장
            webhook = PaymentWebhook.objects.create(
                provider=provider,
                event_type=event_type,
                raw_data=data
            )
            
            # 이벤트 타입에 따른 처리
            if event_type == 'payment.paid':
                self._handle_payment_webhook(webhook, data)
            elif event_type == 'payment.cancelled':
                self._handle_cancel_webhook(webhook, data)
            elif event_type == 'payment.failed':
                self._handle_failure_webhook(webhook, data)
            
            webhook.mark_as_processed()
            return True
            
        except Exception as e:
            logger.error(f"웹훅 처리 실패: {str(e)}")
            if 'webhook' in locals():
                webhook.mark_as_failed(str(e))
            return False
    
    def _process_payment_completion(self, payment: Payment):
        """결제 완료 후 처리"""
        # 결제 완료 알림 발송
        from .tasks import send_payment_notification
        send_payment_notification.delay(payment.id)
        
        # 구독 결제인 경우 다음 결제일 설정
        if hasattr(payment, 'subscription'):
            self._update_subscription_billing(payment.subscription)
    
    def _handle_payment_webhook(self, webhook: PaymentWebhook, data: Dict[str, Any]):
        """결제 완료 웹훅 처리"""
        merchant_uid = data.get('merchant_uid')
        if merchant_uid:
            try:
                payment = Payment.objects.get(merchant_uid=merchant_uid)
                webhook.payment = payment
                webhook.save()
                
                if payment.status != 'completed':
                    payment.mark_as_paid()
                    self._process_payment_completion(payment)
                    
            except Payment.DoesNotExist:
                logger.warning(f"웹훅 처리 중 결제를 찾을 수 없음: {merchant_uid}")
    
    def _handle_cancel_webhook(self, webhook: PaymentWebhook, data: Dict[str, Any]):
        """결제 취소 웹훅 처리"""
        merchant_uid = data.get('merchant_uid')
        if merchant_uid:
            try:
                payment = Payment.objects.get(merchant_uid=merchant_uid)
                webhook.payment = payment
                webhook.save()
                
                if payment.status != 'cancelled':
                    payment.mark_as_cancelled()
                    
            except Payment.DoesNotExist:
                logger.warning(f"웹훅 처리 중 결제를 찾을 수 없음: {merchant_uid}")
    
    def _handle_failure_webhook(self, webhook: PaymentWebhook, data: Dict[str, Any]):
        """결제 실패 웹훅 처리"""
        merchant_uid = data.get('merchant_uid')
        if merchant_uid:
            try:
                payment = Payment.objects.get(merchant_uid=merchant_uid)
                webhook.payment = payment
                webhook.save()
                
                failure_reason = data.get('fail_reason', '결제 실패')
                payment.mark_as_failed(failure_reason)
                
            except Payment.DoesNotExist:
                logger.warning(f"웹훅 처리 중 결제를 찾을 수 없음: {merchant_uid}")