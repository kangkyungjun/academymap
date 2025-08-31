from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
    ChatRoom, ChatMessage, ChatParticipant, 
    ChatFile, ChatSession, ChatNotification
)


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = [
        'room_id', 'academy_name', 'student_name', 'staff_name',
        'room_type', 'status', 'message_count', 'created_at', 'actions'
    ]
    list_filter = ['status', 'room_type', 'created_at']
    search_fields = [
        'room_id', 'title', 'student__username', 
        'academy__상호명', 'academy_staff__username'
    ]
    readonly_fields = ['room_id', 'message_count', 'last_message_at']
    date_hierarchy = 'created_at'
    
    fieldsets = [
        ('기본 정보', {
            'fields': ['room_id', 'room_type', 'status', 'title', 'description']
        }),
        ('참여자', {
            'fields': ['student', 'academy', 'academy_staff']
        }),
        ('통계', {
            'fields': ['message_count', 'last_message_at', 'created_at', 'closed_at'],
            'classes': ['collapse']
        })
    ]
    
    def academy_name(self, obj):
        return obj.academy.상호명
    academy_name.short_description = '학원명'
    
    def student_name(self, obj):
        return obj.student.username
    student_name.short_description = '학생'
    
    def staff_name(self, obj):
        return obj.academy_staff.username if obj.academy_staff else '-'
    staff_name.short_description = '담당자'
    
    def actions(self, obj):
        return format_html(
            '<a href="{}" class="button">메시지 보기</a>',
            reverse('admin:chat_chatmessage_changelist') + f'?room__id__exact={obj.id}'
        )
    actions.short_description = '작업'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'student', 'academy', 'academy_staff'
        )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'room_link', 'sender_name', 'message_type', 
        'content_preview', 'status', 'created_at'
    ]
    list_filter = ['message_type', 'status', 'created_at']
    search_fields = ['content', 'sender__username', 'room__room_id']
    readonly_fields = ['created_at', 'updated_at', 'read_at']
    date_hierarchy = 'created_at'
    
    fieldsets = [
        ('메시지 정보', {
            'fields': ['room', 'sender', 'message_type', 'content', 'status']
        }),
        ('파일 정보', {
            'fields': ['file_url', 'file_name', 'file_size'],
            'classes': ['collapse']
        }),
        ('위치 정보', {
            'fields': ['latitude', 'longitude'],
            'classes': ['collapse']
        }),
        ('참조', {
            'fields': ['reply_to'],
            'classes': ['collapse']
        }),
        ('메타데이터', {
            'fields': ['created_at', 'updated_at', 'read_at'],
            'classes': ['collapse']
        })
    ]
    
    def room_link(self, obj):
        url = reverse('admin:chat_chatroom_change', args=[obj.room.id])
        return format_html('<a href="{}">{}</a>', url, obj.room.room_id)
    room_link.short_description = '채팅방'
    
    def sender_name(self, obj):
        return obj.sender.username
    sender_name.short_description = '발신자'
    
    def content_preview(self, obj):
        if obj.message_type == 'text':
            return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
        elif obj.message_type == 'file':
            return f'파일: {obj.file_name}'
        elif obj.message_type == 'image':
            return f'이미지: {obj.file_name}'
        else:
            return f'{obj.get_message_type_display()} 메시지'
    content_preview.short_description = '내용'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'room', 'sender', 'reply_to'
        )


@admin.register(ChatParticipant)
class ChatParticipantAdmin(admin.ModelAdmin):
    list_display = [
        'user_name', 'room_link', 'role', 'is_active', 
        'is_online', 'unread_count', 'joined_at'
    ]
    list_filter = ['role', 'is_active', 'is_online', 'joined_at']
    search_fields = ['user__username', 'room__room_id']
    readonly_fields = ['joined_at', 'left_at', 'last_seen']
    
    def user_name(self, obj):
        return obj.user.username
    user_name.short_description = '사용자'
    
    def room_link(self, obj):
        url = reverse('admin:chat_chatroom_change', args=[obj.room.id])
        return format_html('<a href="{}">{}</a>', url, obj.room.room_id)
    room_link.short_description = '채팅방'
    
    def unread_count(self, obj):
        return obj.get_unread_count()
    unread_count.short_description = '읽지 않은 메시지'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'room')


@admin.register(ChatFile)
class ChatFileAdmin(admin.ModelAdmin):
    list_display = [
        'original_name', 'file_type', 'file_size_mb', 
        'message_link', 'uploaded_at', 'download_count'
    ]
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['original_name', 'message__content']
    readonly_fields = ['uploaded_at', 'download_count']
    
    def file_size_mb(self, obj):
        return f"{obj.file_size / (1024 * 1024):.2f} MB"
    file_size_mb.short_description = '파일 크기'
    
    def message_link(self, obj):
        url = reverse('admin:chat_chatmessage_change', args=[obj.message.id])
        return format_html('<a href="{}">메시지 #{}</a>', url, obj.message.id)
    message_link.short_description = '메시지'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('message')


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = [
        'session_id', 'user_name', 'room_link', 'is_connected',
        'connected_at', 'disconnected_at', 'duration'
    ]
    list_filter = ['is_connected', 'connected_at']
    search_fields = ['session_id', 'user__username', 'room__room_id']
    readonly_fields = ['connected_at', 'disconnected_at']
    
    def user_name(self, obj):
        return obj.user.username
    user_name.short_description = '사용자'
    
    def room_link(self, obj):
        url = reverse('admin:chat_chatroom_change', args=[obj.room.id])
        return format_html('<a href="{}">{}</a>', url, obj.room.room_id)
    room_link.short_description = '채팅방'
    
    def duration(self, obj):
        if obj.disconnected_at:
            duration = obj.disconnected_at - obj.connected_at
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return '-'
    duration.short_description = '접속 시간'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'room')


@admin.register(ChatNotification)
class ChatNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'recipient_name', 'notification_type', 
        'is_read', 'is_sent', 'created_at'
    ]
    list_filter = [
        'notification_type', 'is_read', 'is_sent', 'created_at'
    ]
    search_fields = ['title', 'content', 'recipient__username']
    readonly_fields = ['created_at', 'read_at', 'sent_at']
    
    actions = ['mark_as_read', 'mark_as_sent']
    
    def recipient_name(self, obj):
        return obj.recipient.username
    recipient_name.short_description = '수신자'
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated}개의 알림을 읽음으로 처리했습니다.')
    mark_as_read.short_description = '선택된 알림을 읽음으로 처리'
    
    def mark_as_sent(self, request, queryset):
        updated = queryset.update(is_sent=True)
        self.message_user(request, f'{updated}개의 알림을 발송완료로 처리했습니다.')
    mark_as_sent.short_description = '선택된 알림을 발송완료로 처리'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'recipient', 'room', 'message'
        )


# 커스텀 관리 액션들
def close_rooms(modeladmin, request, queryset):
    """선택된 채팅방들을 종료"""
    count = 0
    for room in queryset:
        if room.status != 'closed':
            room.close_room()
            count += 1
    
    modeladmin.message_user(
        request, 
        f'{count}개의 채팅방을 종료했습니다.'
    )

close_rooms.short_description = '선택된 채팅방 종료'

# ChatRoomAdmin에 액션 추가
ChatRoomAdmin.actions = [close_rooms]


# 관리자 사이트 커스터마이징
admin.site.site_header = 'AcademyMap 채팅 관리'
admin.site.site_title = 'AcademyMap 채팅'
admin.site.index_title = '채팅 시스템 관리'