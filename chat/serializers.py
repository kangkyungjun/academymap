from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    ChatRoom, ChatMessage, ChatParticipant, 
    ChatFile, ChatNotification
)
from main.models import Data as Academy


class UserSerializer(serializers.ModelSerializer):
    """사용자 시리얼라이저"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class AcademySerializer(serializers.ModelSerializer):
    """학원 시리얼라이저"""
    
    class Meta:
        model = Academy
        fields = ['id', '상호명', '도로명주소', '전화번호']


class ChatFileSerializer(serializers.ModelSerializer):
    """채팅 파일 시리얼라이저"""
    
    class Meta:
        model = ChatFile
        fields = [
            'id', 'file_type', 'original_name', 'file_path', 
            'file_size', 'mime_type', 'width', 'height',
            'uploaded_at', 'download_count'
        ]


class ChatMessageSerializer(serializers.ModelSerializer):
    """채팅 메시지 시리얼라이저"""
    sender = UserSerializer(read_only=True)
    reply_to = serializers.SerializerMethodField()
    file_info = ChatFileSerializer(read_only=True)
    is_from_current_user = serializers.SerializerMethodField()
    formatted_time = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'sender', 'message_type', 'content', 'status',
            'file_url', 'file_name', 'file_size', 'latitude', 'longitude',
            'created_at', 'updated_at', 'read_at', 'reply_to', 'file_info',
            'is_from_current_user', 'formatted_time'
        ]
    
    def get_reply_to(self, obj):
        """답장 대상 메시지"""
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'content': obj.reply_to.content,
                'sender': obj.reply_to.sender.username,
                'created_at': obj.reply_to.created_at
            }
        return None
    
    def get_is_from_current_user(self, obj):
        """현재 사용자가 보낸 메시지인지"""
        request = self.context.get('request')
        if request and request.user:
            return obj.sender == request.user
        return False
    
    def get_formatted_time(self, obj):
        """포맷된 시간"""
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return obj.created_at.strftime('%Y-%m-%d %H:%M')
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}시간 전"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}분 전"
        else:
            return "방금 전"


class ChatParticipantSerializer(serializers.ModelSerializer):
    """채팅 참여자 시리얼라이저"""
    user = UserSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatParticipant
        fields = [
            'id', 'user', 'role', 'is_active', 'is_online',
            'last_seen', 'notifications_enabled', 'joined_at',
            'unread_count'
        ]
    
    def get_unread_count(self, obj):
        """읽지 않은 메시지 수"""
        return obj.get_unread_count()


class ChatRoomSerializer(serializers.ModelSerializer):
    """채팅방 시리얼라이저"""
    student = UserSerializer(read_only=True)
    academy = AcademySerializer(read_only=True)
    academy_staff = UserSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    participants = ChatParticipantSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'room_id', 'room_type', 'status', 'student', 'academy',
            'academy_staff', 'title', 'description', 'created_at', 'updated_at',
            'closed_at', 'message_count', 'last_message_at', 'last_message',
            'unread_count', 'participants'
        ]
    
    def get_last_message(self, obj):
        """마지막 메시지"""
        last_message = obj.get_last_message()
        if last_message:
            return ChatMessageSerializer(last_message, context=self.context).data
        return None
    
    def get_unread_count(self, obj):
        """현재 사용자의 읽지 않은 메시지 수"""
        request = self.context.get('request')
        if request and request.user:
            try:
                participant = obj.participants.get(user=request.user)
                return participant.get_unread_count()
            except ChatParticipant.DoesNotExist:
                return 0
        return 0


class ChatRoomCreateSerializer(serializers.ModelSerializer):
    """채팅방 생성 시리얼라이저"""
    academy_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ChatRoom
        fields = ['room_type', 'title', 'description', 'academy_id']
    
    def validate_academy_id(self, value):
        """학원 ID 검증"""
        try:
            Academy.objects.get(id=value)
            return value
        except Academy.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 학원입니다.")
    
    def create(self, validated_data):
        """채팅방 생성"""
        academy_id = validated_data.pop('academy_id')
        academy = Academy.objects.get(id=academy_id)
        
        # 룸 ID 생성
        import uuid
        room_id = str(uuid.uuid4())
        
        chat_room = ChatRoom.objects.create(
            room_id=room_id,
            student=self.context['request'].user,
            academy=academy,
            **validated_data
        )
        
        # 학생 참여자 추가
        ChatParticipant.objects.create(
            room=chat_room,
            user=self.context['request'].user,
            role='student'
        )
        
        return chat_room


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    """메시지 생성 시리얼라이저"""
    room_id = serializers.CharField(write_only=True)
    reply_to_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = ChatMessage
        fields = [
            'room_id', 'message_type', 'content', 'file_url', 
            'file_name', 'file_size', 'latitude', 'longitude',
            'reply_to_id'
        ]
    
    def validate_room_id(self, value):
        """채팅방 ID 검증"""
        try:
            room = ChatRoom.objects.get(room_id=value)
            # 권한 확인
            user = self.context['request'].user
            if not (user == room.student or user == room.academy_staff or user.is_staff):
                raise serializers.ValidationError("채팅방에 접근할 권한이 없습니다.")
            return value
        except ChatRoom.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 채팅방입니다.")
    
    def validate_reply_to_id(self, value):
        """답장 메시지 ID 검증"""
        if value:
            try:
                ChatMessage.objects.get(id=value)
                return value
            except ChatMessage.DoesNotExist:
                raise serializers.ValidationError("존재하지 않는 메시지입니다.")
        return value
    
    def create(self, validated_data):
        """메시지 생성"""
        room_id = validated_data.pop('room_id')
        reply_to_id = validated_data.pop('reply_to_id', None)
        
        room = ChatRoom.objects.get(room_id=room_id)
        
        reply_to = None
        if reply_to_id:
            reply_to = ChatMessage.objects.get(id=reply_to_id)
        
        message = ChatMessage.objects.create(
            room=room,
            sender=self.context['request'].user,
            reply_to=reply_to,
            **validated_data
        )
        
        # 채팅방 메시지 카운트 업데이트
        room.increment_message_count()
        
        return message


class ChatNotificationSerializer(serializers.ModelSerializer):
    """채팅 알림 시리얼라이저"""
    room = ChatRoomSerializer(read_only=True)
    message = ChatMessageSerializer(read_only=True)
    
    class Meta:
        model = ChatNotification
        fields = [
            'id', 'room', 'message', 'notification_type', 'title',
            'content', 'is_read', 'is_sent', 'created_at', 'read_at'
        ]


class MessageSearchSerializer(serializers.Serializer):
    """메시지 검색 시리얼라이저"""
    room_id = serializers.CharField()
    query = serializers.CharField()
    message_type = serializers.ChoiceField(
        choices=ChatMessage.MESSAGE_TYPE_CHOICES,
        required=False
    )
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    sender_id = serializers.IntegerField(required=False)


class RoomStatisticsSerializer(serializers.Serializer):
    """채팅방 통계 시리얼라이저"""
    total_messages = serializers.IntegerField()
    total_participants = serializers.IntegerField()
    average_response_time = serializers.FloatField()
    most_active_user = UserSerializer()
    message_types_count = serializers.DictField()
    daily_message_counts = serializers.ListField()