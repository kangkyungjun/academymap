import json
import uuid
from datetime import datetime
from django.contrib.auth.models import User
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async

from .models import ChatRoom, ChatMessage, ChatParticipant, ChatSession
from .serializers import ChatMessageSerializer, ChatRoomSerializer


class ChatConsumer(AsyncWebsocketConsumer):
    """실시간 채팅 WebSocket Consumer"""
    
    async def connect(self):
        """WebSocket 연결 처리"""
        # URL에서 room_id 추출
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        
        # 사용자 인증 확인
        self.user = self.scope.get('user')
        if not self.user or self.user.is_anonymous:
            await self.close()
            return
        
        # 채팅방 존재 여부 확인
        self.chat_room = await self.get_chat_room()
        if not self.chat_room:
            await self.close()
            return
        
        # 사용자 권한 확인
        if not await self.check_room_permission():
            await self.close()
            return
        
        # 그룹에 참여
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # WebSocket 연결 수락
        await self.accept()
        
        # 세션 생성
        self.session_id = str(uuid.uuid4())
        await self.create_chat_session()
        
        # 참여자 온라인 상태 업데이트
        await self.update_participant_status(is_online=True)
        
        # 사용자 입장 알림
        await self.notify_user_joined()
        
        print(f"User {self.user.username} connected to room {self.room_id}")
    
    async def disconnect(self, close_code):
        """WebSocket 연결 해제 처리"""
        if hasattr(self, 'room_group_name'):
            # 그룹에서 제거
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
            # 세션 종료
            if hasattr(self, 'session_id'):
                await self.disconnect_chat_session()
            
            # 참여자 오프라인 상태 업데이트
            await self.update_participant_status(is_online=False)
            
            # 사용자 퇴장 알림
            await self.notify_user_left()
            
            print(f"User {getattr(self, 'user', {}).get('username', 'Unknown')} disconnected from room {getattr(self, 'room_id', 'Unknown')}")
    
    async def receive(self, text_data):
        """메시지 수신 처리"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            if message_type == 'message':
                await self.handle_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
            elif message_type == 'file_upload':
                await self.handle_file_upload(data)
            else:
                await self.send_error("Unknown message type")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            await self.send_error(f"Error processing message: {str(e)}")
    
    async def handle_message(self, data):
        """텍스트 메시지 처리"""
        content = data.get('content', '').strip()
        if not content:
            await self.send_error("Message content cannot be empty")
            return
        
        reply_to_id = data.get('reply_to')
        
        # 메시지 저장
        message = await self.save_message(
            content=content,
            message_type='text',
            reply_to_id=reply_to_id
        )
        
        # 직렬화
        message_data = await self.serialize_message(message)
        
        # 그룹에 메시지 브로드캐스트
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_data
            }
        )
        
        # 알림 발송
        await self.send_notification(message)
    
    async def handle_typing(self, data):
        """타이핑 상태 처리"""
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_status',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': is_typing
            }
        )
    
    async def handle_read_receipt(self, data):
        """읽음 확인 처리"""
        message_id = data.get('message_id')
        if message_id:
            await self.mark_message_as_read(message_id)
            
            # 읽음 확인 브로드캐스트
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'read_receipt',
                    'message_id': message_id,
                    'user_id': self.user.id,
                    'read_at': timezone.now().isoformat()
                }
            )
    
    async def handle_file_upload(self, data):
        """파일 업로드 처리"""
        file_url = data.get('file_url')
        file_name = data.get('file_name')
        file_size = data.get('file_size')
        message_type = data.get('message_type', 'file')
        
        if not file_url:
            await self.send_error("File URL is required")
            return
        
        # 파일 메시지 저장
        message = await self.save_message(
            content=f"파일을 공유했습니다: {file_name}",
            message_type=message_type,
            file_url=file_url,
            file_name=file_name,
            file_size=file_size
        )
        
        # 직렬화 및 브로드캐스트
        message_data = await self.serialize_message(message)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_data
            }
        )
    
    # WebSocket 이벤트 핸들러들
    async def chat_message(self, event):
        """채팅 메시지 전송"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message']
        }))
    
    async def typing_status(self, event):
        """타이핑 상태 전송"""
        # 자신의 타이핑 상태는 전송하지 않음
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            }))
    
    async def read_receipt(self, event):
        """읽음 확인 전송"""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'read_at': event['read_at']
        }))
    
    async def user_joined(self, event):
        """사용자 입장 알림"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'user_id': event['user_id'],
                'username': event['username']
            }))
    
    async def user_left(self, event):
        """사용자 퇴장 알림"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_left',
                'user_id': event['user_id'],
                'username': event['username']
            }))
    
    async def room_closed(self, event):
        """채팅방 종료 알림"""
        await self.send(text_data=json.dumps({
            'type': 'room_closed',
            'message': '채팅방이 종료되었습니다.'
        }))
        await self.close()
    
    # 데이터베이스 작업 메서드들
    @database_sync_to_async
    def get_chat_room(self):
        """채팅방 조회"""
        try:
            return ChatRoom.objects.get(room_id=self.room_id)
        except ChatRoom.DoesNotExist:
            return None
    
    @database_sync_to_async
    def check_room_permission(self):
        """채팅방 접근 권한 확인"""
        return (
            self.user == self.chat_room.student or
            self.user == self.chat_room.academy_staff or
            self.user.is_staff
        )
    
    @database_sync_to_async
    def save_message(self, content, message_type='text', reply_to_id=None, 
                    file_url=None, file_name=None, file_size=None):
        """메시지 저장"""
        reply_to = None
        if reply_to_id:
            try:
                reply_to = ChatMessage.objects.get(id=reply_to_id, room=self.chat_room)
            except ChatMessage.DoesNotExist:
                pass
        
        message = ChatMessage.objects.create(
            room=self.chat_room,
            sender=self.user,
            content=content,
            message_type=message_type,
            reply_to=reply_to,
            file_url=file_url or '',
            file_name=file_name or '',
            file_size=file_size
        )
        
        # 채팅방 메시지 카운트 업데이트
        self.chat_room.increment_message_count()
        
        return message
    
    @database_sync_to_async
    def serialize_message(self, message):
        """메시지 직렬화"""
        serializer = ChatMessageSerializer(message)
        return serializer.data
    
    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """메시지 읽음 처리"""
        try:
            message = ChatMessage.objects.get(id=message_id, room=self.chat_room)
            if message.sender != self.user:
                message.mark_as_read()
                
                # 참여자의 마지막 읽은 메시지 업데이트
                participant, _ = ChatParticipant.objects.get_or_create(
                    room=self.chat_room,
                    user=self.user
                )
                participant.last_read_message = message
                participant.save()
                
        except ChatMessage.DoesNotExist:
            pass
    
    @database_sync_to_async
    def create_chat_session(self):
        """채팅 세션 생성"""
        user_agent = self.scope.get('headers', {}).get(b'user-agent', b'').decode()
        
        ChatSession.objects.create(
            user=self.user,
            room=self.chat_room,
            session_id=self.session_id,
            channel_name=self.channel_name,
            user_agent=user_agent
        )
    
    @database_sync_to_async
    def disconnect_chat_session(self):
        """채팅 세션 종료"""
        try:
            session = ChatSession.objects.get(session_id=self.session_id)
            session.disconnect()
        except ChatSession.DoesNotExist:
            pass
    
    @database_sync_to_async
    def update_participant_status(self, is_online):
        """참여자 온라인 상태 업데이트"""
        participant, created = ChatParticipant.objects.get_or_create(
            room=self.chat_room,
            user=self.user,
            defaults={'role': self.get_user_role()}
        )
        participant.is_online = is_online
        participant.save()
    
    def get_user_role(self):
        """사용자 역할 결정"""
        if self.user == self.chat_room.student:
            return 'student'
        elif self.user == self.chat_room.academy_staff:
            return 'academy_staff'
        else:
            return 'admin'
    
    async def notify_user_joined(self):
        """사용자 입장 알림"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': self.user.id,
                'username': self.user.username
            }
        )
    
    async def notify_user_left(self):
        """사용자 퇴장 알림"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': self.user.id,
                'username': self.user.username
            }
        )
    
    @database_sync_to_async
    def send_notification(self, message):
        """푸시 알림 발송"""
        from .tasks import send_chat_notification
        
        # 알림 받을 사용자 결정
        if message.sender == self.chat_room.student:
            recipient = self.chat_room.academy_staff
        else:
            recipient = self.chat_room.student
        
        if recipient:
            send_chat_notification.delay(
                recipient_id=recipient.id,
                room_id=self.chat_room.id,
                message_id=message.id,
                sender_name=message.sender.username,
                content=message.content[:100]
            )
    
    async def send_error(self, error_message):
        """에러 메시지 전송"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message
        }))