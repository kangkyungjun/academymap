from rest_framework import serializers
from .models import Bookmark, BookmarkFolder
from main.models import Data as Academy
from api.serializers import AcademySerializer


class BookmarkSerializer(serializers.ModelSerializer):
    """즐겨찾기 시리얼라이저"""
    academy = AcademySerializer(read_only=True)
    academy_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Bookmark
        fields = [
            'id', 'academy', 'academy_id', 'notes', 'priority', 'tags',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        
    def validate_academy_id(self, value):
        try:
            Academy.objects.get(id=value)
            return value
        except Academy.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 학원입니다.")
            
    def create(self, validated_data):
        academy_id = validated_data.pop('academy_id')
        academy = Academy.objects.get(id=academy_id)
        user = self.context['request'].user
        
        bookmark, created = Bookmark.objects.get_or_create(
            user=user,
            academy=academy,
            defaults=validated_data
        )
        
        if not created:
            raise serializers.ValidationError("이미 즐겨찾기에 추가된 학원입니다.")
            
        return bookmark


class BookmarkListSerializer(serializers.ModelSerializer):
    """즐겨찾기 목록 시리얼라이저 (간단한 정보)"""
    academy_name = serializers.CharField(source='academy.상호명', read_only=True)
    academy_address = serializers.CharField(source='academy.도로명주소', read_only=True)
    academy_subjects = serializers.SerializerMethodField()
    
    class Meta:
        model = Bookmark
        fields = [
            'id', 'academy_id', 'academy_name', 'academy_address', 
            'academy_subjects', 'notes', 'priority', 'tags', 'created_at'
        ]
        
    def get_academy_subjects(self, obj):
        """학원 과목 정보"""
        subjects = []
        academy = obj.academy
        
        if academy.과목_수학: subjects.append('수학')
        if academy.과목_영어: subjects.append('영어')
        if academy.과목_과학: subjects.append('과학')
        if academy.과목_외국어: subjects.append('외국어')
        if academy.과목_예체능: subjects.append('예체능')
        if academy.과목_논술: subjects.append('논술')
        if academy.과목_종합: subjects.append('종합')
        if hasattr(academy, '과목_컴퓨터') and academy.과목_컴퓨터: subjects.append('컴퓨터')
        if hasattr(academy, '과목_기타') and academy.과목_기타: subjects.append('기타')
        
        return subjects


class BookmarkFolderSerializer(serializers.ModelSerializer):
    """즐겨찾기 폴더 시리얼라이저"""
    bookmark_count = serializers.ReadOnlyField()
    bookmarks = BookmarkListSerializer(many=True, read_only=True)
    
    class Meta:
        model = BookmarkFolder
        fields = [
            'id', 'name', 'description', 'color', 'icon', 'is_default', 
            'order', 'bookmark_count', 'bookmarks', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        
    def create(self, validated_data):
        user = self.context['request'].user
        return BookmarkFolder.objects.create(user=user, **validated_data)


class BookmarkFolderListSerializer(serializers.ModelSerializer):
    """즐겨찾기 폴더 목록 시리얼라이저 (간단한 정보)"""
    bookmark_count = serializers.ReadOnlyField()
    
    class Meta:
        model = BookmarkFolder
        fields = [
            'id', 'name', 'description', 'color', 'icon', 
            'is_default', 'order', 'bookmark_count'
        ]


class BookmarkBulkActionSerializer(serializers.Serializer):
    """즐겨찾기 일괄 작업 시리얼라이저"""
    bookmark_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    action = serializers.ChoiceField(choices=[
        ('delete', '삭제'),
        ('move_to_folder', '폴더 이동'),
        ('add_tags', '태그 추가'),
        ('remove_tags', '태그 제거'),
        ('set_priority', '우선순위 설정'),
    ])
    folder_id = serializers.IntegerField(required=False)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False
    )
    priority = serializers.IntegerField(
        min_value=1, max_value=3, required=False
    )
    
    def validate(self, attrs):
        action = attrs['action']
        
        if action == 'move_to_folder' and not attrs.get('folder_id'):
            raise serializers.ValidationError("폴더 ID가 필요합니다.")
        if action in ['add_tags', 'remove_tags'] and not attrs.get('tags'):
            raise serializers.ValidationError("태그가 필요합니다.")
        if action == 'set_priority' and not attrs.get('priority'):
            raise serializers.ValidationError("우선순위가 필요합니다.")
            
        return attrs