import uuid
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, Http404
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    ChatRoom, ChatMessage, ChatParticipant, 
    ChatNotification, ChatSession
)
from .serializers import (
    ChatRoomSerializer, ChatMessageSerializer, ChatRoomCreateSerializer,
    ChatMessageCreateSerializer, ChatNotificationSerializer,
    MessageSearchSerializer, RoomStatisticsSerializer
)
from main.models import Data as Academy


class ChatRoomPagination(PageNumberPagination):
    """채팅방 페이지네이션"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ChatMessagePagination(PageNumberPagination):
    """채팅 메시지 페이지네이션"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class ChatRoomViewSet(viewsets.ModelViewSet):
    """채팅방 ViewSet"""
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ChatRoomPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'room_type']
    search_fields = ['title', 'academy__상호명']
    ordering_fields = ['created_at', 'updated_at', 'last_message_at']
    ordering = ['-updated_at']
    
    def get_queryset(self):
        """현재 사용자가 참여한 채팅방만 반환"""
        return ChatRoom.objects.filter(
            Q(student=self.request.user) | 
            Q(academy_staff=self.request.user)
        ).select_related('student', 'academy', 'academy_staff')
    
    def get_serializer_class(self):
        """액션에 따른 시리얼라이저 선택"""
        if self.action == 'create':
            return ChatRoomCreateSerializer
        return ChatRoomSerializer
    
    def perform_create(self, serializer):
        """채팅방 생성"""
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """채팅방 종료"""
        room = self.get_object()
        
        # 권한 확인 (학생 또는 학원 직원만 종료 가능)
        if request.user not in [room.student, room.academy_staff] and not request.user.is_staff:
            return Response(
                {'error': '채팅방을 종료할 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        room.close_room()
        
        # WebSocket으로 종료 알림
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{room.room_id}',
            {
                'type': 'room_closed',
                'message': '채팅방이 종료되었습니다.'
            }
        )
        
        return Response({'message': '채팅방이 종료되었습니다.'})
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """채팅방의 메시지 목록 조회"""
        room = self.get_object()
        
        # 메시지 조회
        messages = ChatMessage.objects.filter(room=room).select_related(
            'sender', 'reply_to', 'reply_to__sender'
        ).order_by('-created_at')
        
        # 페이지네이션
        paginator = ChatMessagePagination()
        page = paginator.paginate_queryset(messages, request)
        
        serializer = ChatMessageSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """채팅방 참여 (학원 직원용)"""
        room = self.get_object()
        
        # 학원 직원만 참여 가능
        if not request.user.is_staff:
            return Response(
                {'error': '학원 직원만 참여할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 이미 참여 중인지 확인
        if room.academy_staff:
            return Response(
                {'error': '이미 다른 직원이 참여 중입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        room.academy_staff = request.user
        room.status = 'active'
        room.save()
        
        # 참여자 생성
        ChatParticipant.objects.get_or_create(
            room=room,
            user=request.user,
            defaults={'role': 'academy_staff'}
        )
        
        return Response({'message': '채팅방에 참여했습니다.'})
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """채팅방 통계"""
        room = self.get_object()
        
        # 기본 통계
        total_messages = room.messages.count()
        total_participants = room.participants.count()
        
        # 응답 시간 계산 (학원 직원이 학생 메시지에 응답하는 평균 시간)
        student_messages = room.messages.filter(sender=room.student).order_by('created_at')
        response_times = []
        
        for msg in student_messages:
            next_staff_msg = room.messages.filter(
                sender=room.academy_staff,
                created_at__gt=msg.created_at
            ).first()
            
            if next_staff_msg:
                diff = (next_staff_msg.created_at - msg.created_at).total_seconds()
                response_times.append(diff)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # 가장 활발한 사용자
        most_active_user = room.messages.values('sender').annotate(
            count=Count('id')
        ).order_by('-count').first()
        
        if most_active_user:
            most_active_user = User.objects.get(id=most_active_user['sender'])
        
        # 메시지 타입별 개수
        message_types_count = dict(
            room.messages.values('message_type').annotate(
                count=Count('id')
            ).values_list('message_type', 'count')
        )
        
        # 일별 메시지 수 (최근 7일)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=6)
        
        daily_counts = []
        for i in range(7):
            date = start_date + timedelta(days=i)
            count = room.messages.filter(
                created_at__date=date
            ).count()
            daily_counts.append({
                'date': date.isoformat(),
                'count': count
            })
        
        stats_data = {
            'total_messages': total_messages,
            'total_participants': total_participants,
            'average_response_time': avg_response_time,
            'most_active_user': most_active_user,
            'message_types_count': message_types_count,
            'daily_message_counts': daily_counts
        }
        
        serializer = RoomStatisticsSerializer(stats_data)
        return Response(serializer.data)


class ChatMessageViewSet(viewsets.ModelViewSet):
    """채팅 메시지 ViewSet"""
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ChatMessagePagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['message_type', 'status']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """현재 사용자가 참여한 채팅방의 메시지만 반환"""
        user_rooms = ChatRoom.objects.filter(
            Q(student=self.request.user) | 
            Q(academy_staff=self.request.user)
        ).values_list('id', flat=True)
        
        return ChatMessage.objects.filter(
            room_id__in=user_rooms
        ).select_related('sender', 'room', 'reply_to')
    
    def get_serializer_class(self):
        """액션에 따른 시리얼라이저 선택"""
        if self.action == 'create':
            return ChatMessageCreateSerializer
        return ChatMessageSerializer
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """메시지 검색"""
        serializer = MessageSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        room_id = data['room_id']
        query = data['query']
        
        # 채팅방 권한 확인
        try:
            room = ChatRoom.objects.get(room_id=room_id)
            if request.user not in [room.student, room.academy_staff] and not request.user.is_staff:
                return Response(
                    {'error': '검색 권한이 없습니다.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': '존재하지 않는 채팅방입니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 검색 조건 구성
        search_filter = Q(room=room) & Q(content__icontains=query)
        
        if data.get('message_type'):
            search_filter &= Q(message_type=data['message_type'])
        
        if data.get('start_date'):
            search_filter &= Q(created_at__gte=data['start_date'])
        
        if data.get('end_date'):
            search_filter &= Q(created_at__lte=data['end_date'])
        
        if data.get('sender_id'):
            search_filter &= Q(sender_id=data['sender_id'])
        
        # 검색 실행
        messages = ChatMessage.objects.filter(search_filter).select_related(
            'sender', 'reply_to'
        ).order_by('-created_at')
        
        # 페이지네이션
        paginator = ChatMessagePagination()
        page = paginator.paginate_queryset(messages, request)
        
        message_serializer = ChatMessageSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(message_serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """메시지 읽음 처리"""
        message = self.get_object()
        
        # 자신이 보낸 메시지는 읽음 처리 불가
        if message.sender == request.user:
            return Response(
                {'error': '자신이 보낸 메시지입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message.mark_as_read()
        
        # 참여자 정보 업데이트
        try:
            participant = ChatParticipant.objects.get(
                room=message.room,
                user=request.user
            )
            participant.last_read_message = message
            participant.save()
        except ChatParticipant.DoesNotExist:
            pass
        
        return Response({'message': '메시지를 읽음으로 처리했습니다.'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def chat_notifications(request):
    """채팅 알림 목록 조회"""
    notifications = ChatNotification.objects.filter(
        recipient=request.user
    ).select_related('room', 'message').order_by('-created_at')
    
    # 읽지 않은 알림만 필터링
    if request.GET.get('unread_only') == 'true':
        notifications = notifications.filter(is_read=False)
    
    # 페이지네이션
    paginator = PageNumberPagination()
    paginator.page_size = 20
    page = paginator.paginate_queryset(notifications, request)
    
    serializer = ChatNotificationSerializer(page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_notifications_read(request):
    """알림 읽음 처리"""
    notification_ids = request.data.get('notification_ids', [])
    
    if notification_ids:
        ChatNotification.objects.filter(
            id__in=notification_ids,
            recipient=request.user
        ).update(is_read=True, read_at=timezone.now())
    else:
        # 모든 알림 읽음 처리
        ChatNotification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
    
    return Response({'message': '알림을 읽음으로 처리했습니다.'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def unread_message_count(request):
    """읽지 않은 메시지 총 개수"""
    user_participations = ChatParticipant.objects.filter(
        user=request.user,
        is_active=True
    )
    
    total_unread = 0
    for participation in user_participations:
        total_unread += participation.get_unread_count()
    
    return Response({'unread_count': total_unread})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def online_users(request, room_id):
    """채팅방의 온라인 사용자 목록"""
    try:
        room = ChatRoom.objects.get(room_id=room_id)
        
        # 권한 확인
        if request.user not in [room.student, room.academy_staff] and not request.user.is_staff:
            return Response(
                {'error': '접근 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 온라인 참여자 조회
        online_participants = room.participants.filter(
            is_online=True,
            is_active=True
        ).select_related('user')
        
        users_data = []
        for participant in online_participants:
            users_data.append({
                'user_id': participant.user.id,
                'username': participant.user.username,
                'role': participant.role,
                'last_seen': participant.last_seen
            })
        
        return Response({'online_users': users_data})
        
    except ChatRoom.DoesNotExist:
        return Response(
            {'error': '존재하지 않는 채팅방입니다.'},
            status=status.HTTP_404_NOT_FOUND
        )


# 템플릿 뷰들
@login_required
def chat_room_list(request):
    """채팅방 목록 페이지"""
    return render(request, 'chat/room_list.html')


@login_required
def chat_room_detail(request, room_id):
    """채팅방 상세 페이지"""
    room = get_object_or_404(ChatRoom, room_id=room_id)
    
    # 권한 확인
    if request.user not in [room.student, room.academy_staff] and not request.user.is_staff:
        raise Http404("채팅방에 접근할 권한이 없습니다.")
    
    context = {
        'room': room,
        'room_id': room_id,
        'user_role': 'student' if request.user == room.student else 'academy_staff'
    }
    
    return render(request, 'chat/room_detail.html', context)


@login_required
def create_chat_room(request, academy_id):
    """채팅방 생성 페이지"""
    academy = get_object_or_404(Academy, id=academy_id)
    
    # 이미 해당 학원과의 활성 채팅방이 있는지 확인
    existing_room = ChatRoom.objects.filter(
        student=request.user,
        academy=academy,
        status__in=['active', 'pending']
    ).first()
    
    if existing_room:
        return redirect('chat:room_detail', room_id=existing_room.room_id)
    
    if request.method == 'POST':
        # 새 채팅방 생성
        room_id = str(uuid.uuid4())
        room = ChatRoom.objects.create(
            room_id=room_id,
            student=request.user,
            academy=academy,
            room_type=request.POST.get('room_type', 'inquiry'),
            title=request.POST.get('title', f'{academy.상호명} 문의'),
            description=request.POST.get('description', '')
        )
        
        # 학생 참여자 추가
        ChatParticipant.objects.create(
            room=room,
            user=request.user,
            role='student'
        )
        
        return redirect('chat:room_detail', room_id=room.room_id)
    
    context = {
        'academy': academy
    }
    
    return render(request, 'chat/create_room.html', context)