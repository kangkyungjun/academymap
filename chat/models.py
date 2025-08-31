from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from main.models import Data as Academy

User = get_user_model()


class ChatRoom(models.Model):
    """채팅방 모델"""
    ROOM_TYPE_CHOICES = [
        ('inquiry', '문의'),
        ('consultation', '상담'),
        ('support', '지원'),
    ]
    
    STATUS_CHOICES = [
        ('active', '활성'),
        ('closed', '종료'),
        ('pending', '대기중'),
    ]
    
    room_id = models.CharField(max_length=100, unique=True, db_index=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES, default='inquiry')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # 참여자
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_chats')
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, related_name='academy_chats')
    academy_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='staff_chats'
    )
    
    # 메타데이터
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # 통계
    message_count = models.PositiveIntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'chat_rooms'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['room_id']),
            models.Index(fields=['student', 'status']),
            models.Index(fields=['academy', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.room_id} - {self.academy.상호명}"
    
    def close_room(self):
        """채팅방 종료"""
        self.status = 'closed'
        self.closed_at = timezone.now()
        self.save()
    
    def get_last_message(self):
        """마지막 메시지 조회"""
        return self.messages.order_by('-created_at').first()
    
    def increment_message_count(self):
        """메시지 카운트 증가"""
        self.message_count += 1
        self.last_message_at = timezone.now()
        self.save(update_fields=['message_count', 'last_message_at'])


class ChatMessage(models.Model):
    """채팅 메시지 모델"""
    MESSAGE_TYPE_CHOICES = [
        ('text', '텍스트'),
        ('image', '이미지'),
        ('file', '파일'),
        ('system', '시스템'),
        ('location', '위치'),
    ]
    
    STATUS_CHOICES = [
        ('sent', '전송됨'),
        ('delivered', '전달됨'),
        ('read', '읽음'),
        ('failed', '실패'),
    ]
    
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    
    # 파일 관련
    file_url = models.URLField(blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    
    # 위치 관련
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # 참조 메시지 (답장용)
    reply_to = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='replies'
    )
    
    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['room', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
    
    def mark_as_read(self):
        """메시지를 읽음으로 표시"""
        if self.status != 'read':
            self.status = 'read'
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at'])
    
    def is_from_student(self):
        """학생이 보낸 메시지인지 확인"""
        return self.sender == self.room.student
    
    def is_from_academy(self):
        """학원에서 보낸 메시지인지 확인"""
        return self.sender == self.room.academy_staff


class ChatParticipant(models.Model):
    """채팅 참여자 모델"""
    ROLE_CHOICES = [
        ('student', '학생'),
        ('academy_staff', '학원 직원'),
        ('admin', '관리자'),
    ]
    
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_participations')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    
    # 상태
    is_active = models.BooleanField(default=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    
    # 알림 설정
    notifications_enabled = models.BooleanField(default=True)
    last_read_message = models.ForeignKey(
        ChatMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    
    # 메타데이터
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'chat_participants'
        unique_together = ['room', 'user']
        indexes = [
            models.Index(fields=['room', 'is_active']),
            models.Index(fields=['user', 'is_online']),
        ]
    
    def __str__(self):
        return f"{self.user.username} in {self.room.room_id}"
    
    def get_unread_count(self):
        """읽지 않은 메시지 수 조회"""
        if not self.last_read_message:
            return self.room.messages.count()
        
        return self.room.messages.filter(
            created_at__gt=self.last_read_message.created_at
        ).exclude(sender=self.user).count()
    
    def mark_messages_as_read(self):
        """모든 메시지를 읽음으로 표시"""
        last_message = self.room.messages.order_by('-created_at').first()
        if last_message:
            self.last_read_message = last_message
            self.save(update_fields=['last_read_message'])


class ChatFile(models.Model):
    """채팅 파일 모델"""
    FILE_TYPE_CHOICES = [
        ('image', '이미지'),
        ('document', '문서'),
        ('video', '비디오'),
        ('audio', '오디오'),
        ('other', '기타'),
    ]
    
    message = models.OneToOneField(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='file_info'
    )
    
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    original_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.PositiveIntegerField()
    mime_type = models.CharField(max_length=100)
    
    # 이미지 전용
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    
    # 메타데이터
    uploaded_at = models.DateTimeField(auto_now_add=True)
    download_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'chat_files'
    
    def __str__(self):
        return f"{self.original_name} ({self.file_type})"
    
    def increment_download_count(self):
        """다운로드 카운트 증가"""
        self.download_count += 1
        self.save(update_fields=['download_count'])


class ChatSession(models.Model):
    """채팅 세션 모델 (연결 관리)"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_sessions')
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='sessions')
    
    # 연결 정보
    session_id = models.CharField(max_length=100, unique=True)
    channel_name = models.CharField(max_length=200)
    
    # 상태
    is_connected = models.BooleanField(default=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    
    # 클라이언트 정보
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'chat_sessions'
        indexes = [
            models.Index(fields=['user', 'is_connected']),
            models.Index(fields=['room', 'is_connected']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.session_id}"
    
    def disconnect(self):
        """세션 연결 해제"""
        self.is_connected = False
        self.disconnected_at = timezone.now()
        self.save()


class ChatNotification(models.Model):
    """채팅 알림 모델"""
    NOTIFICATION_TYPE_CHOICES = [
        ('new_message', '새 메시지'),
        ('room_created', '채팅방 생성'),
        ('room_closed', '채팅방 종료'),
        ('user_joined', '사용자 입장'),
        ('user_left', '사용자 퇴장'),
    ]
    
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_notifications')
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='notifications')
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    # 상태
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'chat_notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"
    
    def mark_as_read(self):
        """알림을 읽음으로 표시"""
        self.is_read = True
        self.read_at = timezone.now()
        self.save()