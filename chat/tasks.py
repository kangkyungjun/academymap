import logging
from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import send_mail

from .models import ChatRoom, ChatMessage, ChatNotification
from main.models import Data as Academy

logger = logging.getLogger(__name__)


@shared_task
def send_chat_notification(recipient_id, room_id, message_id, sender_name, content):
    """채팅 알림 발송"""
    try:
        recipient = User.objects.get(id=recipient_id)
        room = ChatRoom.objects.get(id=room_id)
        message = ChatMessage.objects.get(id=message_id)
        
        # 알림 생성
        notification = ChatNotification.objects.create(
            recipient=recipient,
            room=room,
            message=message,
            notification_type='new_message',
            title=f'{sender_name}님의 새 메시지',
            content=content
        )
        
        # 푸시 알림 발송
        send_push_notification.delay(recipient_id, notification.id)
        
        # 이메일 알림 발송 (설정에 따라)
        if should_send_email_notification(recipient, room):
            send_email_notification.delay(recipient_id, notification.id)
        
        logger.info(f"Chat notification sent to user {recipient_id} for message {message_id}")
        
    except Exception as e:
        logger.error(f"Failed to send chat notification: {e}")


@shared_task
def send_push_notification(user_id, notification_id):
    """푸시 알림 발송"""
    try:
        from firebase_admin import messaging
        
        user = User.objects.get(id=user_id)
        notification = ChatNotification.objects.get(id=notification_id)
        
        # FCM 토큰 조회 (사용자 프로필에서)
        fcm_tokens = get_user_fcm_tokens(user)
        
        if not fcm_tokens:
            logger.warning(f"No FCM tokens found for user {user_id}")
            return
        
        # 메시지 구성
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=notification.title,
                body=notification.content,
            ),
            data={
                'type': 'chat_message',
                'room_id': notification.room.room_id,
                'message_id': str(notification.message.id),
            },
            tokens=fcm_tokens,
            android=messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    icon='ic_notification',
                    color='#2563EB',
                    sound='default',
                ),
                priority='high',
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=get_user_unread_count(user),
                    ),
                ),
            ),
        )
        
        # 발송
        response = messaging.send_multicast(message)
        
        # 결과 처리
        if response.success_count > 0:
            notification.is_sent = True
            notification.sent_at = timezone.now()
            notification.save()
            logger.info(f"Push notification sent successfully to {response.success_count} devices")
        
        if response.failure_count > 0:
            logger.warning(f"Failed to send push notification to {response.failure_count} devices")
        
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")


@shared_task
def send_email_notification(user_id, notification_id):
    """이메일 알림 발송"""
    try:
        user = User.objects.get(id=user_id)
        notification = ChatNotification.objects.get(id=notification_id)
        
        # 이메일 템플릿 렌더링
        context = {
            'user': user,
            'notification': notification,
            'room': notification.room,
            'message': notification.message,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        }
        
        subject = f'[AcademyMap] {notification.title}'
        html_message = render_to_string('chat/email/notification.html', context)
        text_message = render_to_string('chat/email/notification.txt', context)
        
        # 이메일 발송
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Email notification sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")


@shared_task
def cleanup_old_chat_sessions():
    """오래된 채팅 세션 정리"""
    try:
        from .models import ChatSession
        
        # 24시간 전 연결 해제된 세션들 삭제
        cutoff_time = timezone.now() - timezone.timedelta(hours=24)
        
        old_sessions = ChatSession.objects.filter(
            is_connected=False,
            disconnected_at__lt=cutoff_time
        )
        
        count = old_sessions.count()
        old_sessions.delete()
        
        logger.info(f"Cleaned up {count} old chat sessions")
        
    except Exception as e:
        logger.error(f"Failed to cleanup old chat sessions: {e}")


@shared_task
def update_room_statistics():
    """채팅방 통계 업데이트"""
    try:
        rooms = ChatRoom.objects.filter(status='active')
        
        for room in rooms:
            # 메시지 수 업데이트
            message_count = room.messages.count()
            if room.message_count != message_count:
                room.message_count = message_count
                room.save(update_fields=['message_count'])
            
            # 마지막 메시지 시간 업데이트
            last_message = room.messages.order_by('-created_at').first()
            if last_message and room.last_message_at != last_message.created_at:
                room.last_message_at = last_message.created_at
                room.save(update_fields=['last_message_at'])
        
        logger.info(f"Updated statistics for {rooms.count()} chat rooms")
        
    except Exception as e:
        logger.error(f"Failed to update room statistics: {e}")


@shared_task
def send_daily_chat_summary():
    """일일 채팅 요약 발송 (학원 운영자용)"""
    try:
        from django.db.models import Count
        
        # 어제 날짜
        yesterday = timezone.now().date() - timezone.timedelta(days=1)
        
        # 활성 채팅방이 있는 학원들
        academies_with_chats = Academy.objects.filter(
            academy_chats__status='active'
        ).distinct()
        
        for academy in academies_with_chats:
            # 어제의 채팅 통계
            yesterday_messages = ChatMessage.objects.filter(
                room__academy=academy,
                created_at__date=yesterday
            )
            
            if not yesterday_messages.exists():
                continue
            
            stats = {
                'academy': academy,
                'total_messages': yesterday_messages.count(),
                'total_rooms': academy.academy_chats.filter(
                    messages__created_at__date=yesterday
                ).distinct().count(),
                'most_active_room': get_most_active_room(academy, yesterday),
                'response_time': calculate_average_response_time(academy, yesterday),
            }
            
            # 학원 운영자에게 이메일 발송
            send_academy_daily_summary.delay(academy.id, stats)
        
        logger.info(f"Sent daily chat summary for {academies_with_chats.count()} academies")
        
    except Exception as e:
        logger.error(f"Failed to send daily chat summary: {e}")


@shared_task
def send_academy_daily_summary(academy_id, stats):
    """학원별 일일 요약 이메일 발송"""
    try:
        academy = Academy.objects.get(id=academy_id)
        
        # 학원 운영자 이메일 조회 (실제 구현에서는 별도 모델 필요)
        # 현재는 예시로 관리자 이메일 사용
        admin_users = User.objects.filter(is_staff=True)
        
        for admin in admin_users:
            context = {
                'admin': admin,
                'academy': academy,
                'stats': stats,
                'date': timezone.now().date() - timezone.timedelta(days=1),
            }
            
            subject = f'[AcademyMap] {academy.상호명} 일일 채팅 요약'
            html_message = render_to_string('chat/email/daily_summary.html', context)
            text_message = render_to_string('chat/email/daily_summary.txt', context)
            
            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin.email],
                html_message=html_message,
                fail_silently=False,
            )
        
        logger.info(f"Daily summary sent for academy {academy.상호명}")
        
    except Exception as e:
        logger.error(f"Failed to send academy daily summary: {e}")


# 헬퍼 함수들
def get_user_fcm_tokens(user):
    """사용자의 FCM 토큰 조회"""
    # 실제 구현에서는 사용자 프로필 모델에서 FCM 토큰을 관리
    # 현재는 예시로 빈 리스트 반환
    return []


def get_user_unread_count(user):
    """사용자의 읽지 않은 메시지 총 개수"""
    from .models import ChatParticipant
    
    participations = ChatParticipant.objects.filter(
        user=user,
        is_active=True
    )
    
    total_unread = 0
    for participation in participations:
        total_unread += participation.get_unread_count()
    
    return total_unread


def should_send_email_notification(user, room):
    """이메일 알림 발송 여부 결정"""
    # 실제 구현에서는 사용자 설정을 확인
    # 현재는 기본적으로 False 반환
    return False


def get_most_active_room(academy, date):
    """해당 날짜에 가장 활발했던 채팅방"""
    return academy.academy_chats.filter(
        messages__created_at__date=date
    ).annotate(
        message_count=Count('messages')
    ).order_by('-message_count').first()


def calculate_average_response_time(academy, date):
    """평균 응답 시간 계산"""
    rooms = academy.academy_chats.filter(
        messages__created_at__date=date
    ).distinct()
    
    total_response_times = []
    
    for room in rooms:
        student_messages = room.messages.filter(
            sender=room.student,
            created_at__date=date
        ).order_by('created_at')
        
        for msg in student_messages:
            next_staff_msg = room.messages.filter(
                sender=room.academy_staff,
                created_at__gt=msg.created_at,
                created_at__date=date
            ).first()
            
            if next_staff_msg:
                diff = (next_staff_msg.created_at - msg.created_at).total_seconds()
                total_response_times.append(diff)
    
    if total_response_times:
        return sum(total_response_times) / len(total_response_times)
    
    return 0