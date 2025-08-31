from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """커스텀 사용자 모델"""
    email = models.EmailField(unique=True, verbose_name="이메일")
    nickname = models.CharField(max_length=50, blank=True, verbose_name="닉네임")
    phone = models.CharField(max_length=15, blank=True, verbose_name="전화번호")
    birth_date = models.DateField(null=True, blank=True, verbose_name="생년월일")
    
    # 선호 지역 (JSONField로 여러 지역 저장 가능)
    preferred_areas = models.JSONField(default=list, blank=True, verbose_name="선호 지역")
    
    # 관심 과목
    SUBJECT_CHOICES = [
        ('전체', '전체'),
        ('수학', '수학'),
        ('영어', '영어'), 
        ('국어', '국어'),
        ('과학', '과학'),
        ('사회', '사회'),
        ('예체능', '예체능'),
        ('논술', '논술'),
        ('외국어', '외국어'),
        ('종합', '종합'),
    ]
    interested_subjects = models.JSONField(default=list, blank=True, verbose_name="관심 과목")
    
    # 자녀 연령대
    AGE_CHOICES = [
        ('유아', '유아'),
        ('초등', '초등'),
        ('중등', '중등'),
        ('고등', '고등'),
        ('일반', '일반'),
    ]
    child_ages = models.JSONField(default=list, blank=True, verbose_name="자녀 연령대")
    
    # 계정 설정
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="가입일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    is_active = models.BooleanField(default=True, verbose_name="활성화 상태")
    
    # 소셜 로그인 정보
    social_provider = models.CharField(max_length=20, blank=True, verbose_name="소셜 로그인 제공업체")
    social_id = models.CharField(max_length=100, blank=True, verbose_name="소셜 로그인 ID")
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = "사용자"
        verbose_name_plural = "사용자들"
        
    def __str__(self):
        return f"{self.email} ({self.nickname or self.username})"


class UserPreference(models.Model):
    """사용자 개인화 설정"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preference')
    
    # UI 설정
    theme = models.CharField(max_length=20, default='light', choices=[
        ('light', '라이트 모드'),
        ('dark', '다크 모드'),
        ('auto', '자동'),
    ], verbose_name="테마")
    
    # 지도 기본 설정
    default_location = models.JSONField(default=dict, blank=True, verbose_name="기본 위치")  # {lat, lng, zoom}
    
    # 알림 설정
    email_notifications = models.BooleanField(default=True, verbose_name="이메일 알림")
    push_notifications = models.BooleanField(default=True, verbose_name="푸시 알림")
    new_academy_alerts = models.BooleanField(default=False, verbose_name="새 학원 알림")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "사용자 설정"
        verbose_name_plural = "사용자 설정들"
        
    def __str__(self):
        return f"{self.user.email} 설정"


# 즐겨찾기 관련 모델들
from main.models import Data as Academy


class Bookmark(models.Model):
    """즐겨찾기 학원"""
    user = models.ForeignKey(
        User, 
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
        User,
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


# 리뷰 관련 모델들을 여기에 포함
from .review_models import Review, ReviewImage, ReviewHelpful, ReviewReport

# 비교 관련 모델들을 여기에 포함
from .comparison_models import AcademyComparison, ComparisonTemplate, ComparisonHistory

# 테마 관련 모델들을 여기에 포함
try:
    from .theme_models import (
        ThemeConfiguration, PresetTheme, ThemeUsageStatistics, UserThemeHistory
    )
except ImportError:
    pass

# 소셜 미디어 공유 관련 모델들을 여기에 포함
try:
    from .social_models import (
        SocialPlatform, ShareableContent, SocialShare, 
        AcademyShare, ShareAnalytics, PopularContent
    )
except ImportError:
    pass
