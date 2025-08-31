from django.db import models
from django.conf import settings
from main.models import Data as Academy


class Bookmark(models.Model):
    """즐겨찾기 학원"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='bookmarks',
        verbose_name="사용자"
    )
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='bookmarked_by',
        verbose_name="학원"
    )
    
    # 즐겨찾기 추가 정보
    notes = models.TextField(blank=True, verbose_name="메모")
    priority = models.IntegerField(
        default=1,
        choices=[(1, '낮음'), (2, '보통'), (3, '높음')],
        verbose_name="우선순위"
    )
    
    # 태그 시스템
    tags = models.JSONField(default=list, blank=True, verbose_name="태그")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="추가일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        unique_together = ('user', 'academy')
        verbose_name = "즐겨찾기"
        verbose_name_plural = "즐겨찾기 목록"
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.email} - {self.academy.상호명}"


class BookmarkFolder(models.Model):
    """즐겨찾기 폴더"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookmark_folders',
        verbose_name="사용자"
    )
    name = models.CharField(max_length=50, verbose_name="폴더명")
    description = models.TextField(blank=True, verbose_name="설명")
    color = models.CharField(
        max_length=7, 
        default='#2196F3',
        verbose_name="폴더 색상"
    )
    
    # 폴더 아이콘
    icon = models.CharField(
        max_length=20,
        default='folder',
        choices=[
            ('folder', '📁 폴더'),
            ('star', '⭐ 별'),
            ('heart', '❤️ 하트'),
            ('school', '🏫 학교'),
            ('book', '📚 책'),
            ('target', '🎯 타겟'),
        ],
        verbose_name="아이콘"
    )
    
    bookmarks = models.ManyToManyField(
        Bookmark,
        blank=True,
        related_name='folders',
        verbose_name="즐겨찾기 목록"
    )
    
    is_default = models.BooleanField(default=False, verbose_name="기본 폴더")
    order = models.IntegerField(default=0, verbose_name="정렬 순서")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'name')
        verbose_name = "즐겨찾기 폴더"
        verbose_name_plural = "즐겨찾기 폴더들"
        ordering = ['order', 'name']
        
    def __str__(self):
        return f"{self.user.email} - {self.name}"
    
    def bookmark_count(self):
        return self.bookmarks.count()


class BookmarkCollection(models.Model):
    """즐겨찾기 컬렉션 (공유 가능한 즐겨찾기 목록)"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookmark_collections',
        verbose_name="사용자"
    )
    title = models.CharField(max_length=100, verbose_name="제목")
    description = models.TextField(blank=True, verbose_name="설명")
    
    bookmarks = models.ManyToManyField(
        Bookmark,
        related_name='collections',
        verbose_name="즐겨찾기 목록"
    )
    
    # 공유 설정
    is_public = models.BooleanField(default=False, verbose_name="공개 여부")
    share_code = models.CharField(
        max_length=20, 
        unique=True, 
        blank=True,
        verbose_name="공유 코드"
    )
    
    # 통계
    view_count = models.IntegerField(default=0, verbose_name="조회수")
    like_count = models.IntegerField(default=0, verbose_name="좋아요 수")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "즐겨찾기 컬렉션"
        verbose_name_plural = "즐겨찾기 컬렉션들"
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} by {self.user.email}"
    
    def save(self, *args, **kwargs):
        if not self.share_code:
            import uuid
            self.share_code = str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)