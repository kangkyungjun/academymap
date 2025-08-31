from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'payment'

router = DefaultRouter()
router.register(r'methods', views.PaymentMethodViewSet, basename='payment-method')
router.register(r'payments', views.PaymentViewSet, basename='payment')
router.register(r'refunds', views.PaymentRefundViewSet, basename='payment-refund')
router.register(r'subscriptions', views.PaymentSubscriptionViewSet, basename='payment-subscription')
router.register(r'statistics', views.PaymentStatisticsViewSet, basename='payment-statistics')

urlpatterns = [
    path('api/', include(router.urls)),
    
    # 웹훅 엔드포인트
    path('webhook/iamport/', views.IamportWebhookView.as_view(), name='iamport-webhook'),
    path('webhook/tosspayments/', views.TossPaymentsWebhookView.as_view(), name='tosspayments-webhook'),
    path('webhook/kakaopay/', views.KakaoPayWebhookView.as_view(), name='kakaopay-webhook'),
    path('webhook/naverpay/', views.NaverPayWebhookView.as_view(), name='naverpay-webhook'),
]