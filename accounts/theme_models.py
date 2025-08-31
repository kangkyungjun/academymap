from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ThemeConfiguration(models.Model):
    """테마 설정 모델"""
    
    THEME_TYPES = [
        ('light', '라이트 모드'),
        ('dark', '다크 모드'),
        ('auto', '시스템 자동'),
        ('high_contrast', '고대비'),
        ('sepia', '세피아'),
    ]
    
    COLOR_SCHEMES = [
        ('default', '기본'),
        ('blue', '블루'),
        ('green', '그린'),
        ('purple', '퍼플'),
        ('orange', '오렌지'),
        ('red', '레드'),
        ('custom', '사용자 정의'),
    ]
    
    FONT_SIZES = [
        ('small', '작게'),
        ('medium', '보통'),
        ('large', '크게'),
        ('extra_large', '매우 크게'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='theme_config',
        verbose_name="사용자"
    )
    
    # 기본 테마 설정
    theme_type = models.CharField(
        max_length=20,
        choices=THEME_TYPES,
        default='light',
        verbose_name="테마 유형"
    )
    
    # 색상 테마
    color_scheme = models.CharField(
        max_length=20,
        choices=COLOR_SCHEMES,
        default='default',
        verbose_name="색상 스키마"
    )
    
    # 사용자 정의 색상
    primary_color = models.CharField(
        max_length=7,
        default='#2196F3',
        verbose_name="기본 색상",
        help_text="HEX 색상 코드 (#RRGGBB)"
    )
    secondary_color = models.CharField(
        max_length=7,
        default='#FF5722',
        verbose_name="보조 색상"
    )
    accent_color = models.CharField(
        max_length=7,
        default='#4CAF50',
        verbose_name="강조 색상"
    )
    
    # 폰트 설정
    font_size = models.CharField(
        max_length=20,
        choices=FONT_SIZES,
        default='medium',
        verbose_name="폰트 크기"
    )
    font_family = models.CharField(
        max_length=50,
        default='system',
        verbose_name="폰트 패밀리",
        help_text="시스템 폰트, Noto Sans KR, Roboto 등"
    )
    
    # 접근성 설정
    high_contrast = models.BooleanField(default=False, verbose_name="고대비 모드")
    reduce_motion = models.BooleanField(default=False, verbose_name="애니메이션 줄이기")
    focus_indicators = models.BooleanField(default=True, verbose_name="포커스 표시")
    
    # 레이아웃 설정
    sidebar_collapsed = models.BooleanField(default=False, verbose_name="사이드바 접기")
    compact_mode = models.BooleanField(default=False, verbose_name="컴팩트 모드")
    show_tooltips = models.BooleanField(default=True, verbose_name="툴팁 표시")
    
    # 지도 테마 설정
    map_style = models.CharField(
        max_length=20,
        choices=[
            ('default', '기본'),
            ('satellite', '위성'),
            ('terrain', '지형'),
            ('hybrid', '하이브리드'),
        ],
        default='default',
        verbose_name="지도 스타일"
    )
    
    # 자동 테마 전환 설정
    auto_dark_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name="다크모드 시작 시간"
    )
    auto_dark_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name="다크모드 종료 시간"
    )
    
    # 사용자 정의 CSS
    custom_css = models.TextField(
        blank=True,
        verbose_name="사용자 정의 CSS",
        help_text="고급 사용자용 커스텀 스타일"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "테마 설정"
        verbose_name_plural = "테마 설정들"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_theme_type_display()}"
    
    def get_css_variables(self):
        """CSS 변수 생성"""
        variables = {
            '--primary-color': self.primary_color,
            '--secondary-color': self.secondary_color,
            '--accent-color': self.accent_color,
        }
        
        # 폰트 크기 매핑
        font_size_map = {
            'small': '14px',
            'medium': '16px',
            'large': '18px',
            'extra_large': '20px',
        }
        variables['--font-size-base'] = font_size_map.get(self.font_size, '16px')
        
        # 폰트 패밀리
        if self.font_family == 'system':
            variables['--font-family'] = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
        else:
            variables['--font-family'] = f'"{self.font_family}", sans-serif'
        
        return variables
    
    def get_theme_classes(self):
        """테마 CSS 클래스 생성"""
        classes = [f'theme-{self.theme_type}']
        
        if self.color_scheme != 'default':
            classes.append(f'color-scheme-{self.color_scheme}')
        
        if self.high_contrast:
            classes.append('high-contrast')
        
        if self.reduce_motion:
            classes.append('reduce-motion')
        
        if self.compact_mode:
            classes.append('compact-mode')
        
        if self.sidebar_collapsed:
            classes.append('sidebar-collapsed')
        
        return ' '.join(classes)


class PresetTheme(models.Model):
    """미리 정의된 테마"""
    
    name = models.CharField(max_length=50, unique=True, verbose_name="테마 이름")
    display_name = models.CharField(max_length=100, verbose_name="표시명")
    description = models.TextField(blank=True, verbose_name="설명")
    
    # 테마 설정값들
    theme_type = models.CharField(max_length=20, choices=ThemeConfiguration.THEME_TYPES)
    color_scheme = models.CharField(max_length=20, choices=ThemeConfiguration.COLOR_SCHEMES)
    primary_color = models.CharField(max_length=7, default='#2196F3')
    secondary_color = models.CharField(max_length=7, default='#FF5722')
    accent_color = models.CharField(max_length=7, default='#4CAF50')
    font_size = models.CharField(max_length=20, choices=ThemeConfiguration.FONT_SIZES, default='medium')
    
    # 미리보기 이미지
    preview_image = models.ImageField(
        upload_to='theme_previews/',
        null=True,
        blank=True,
        verbose_name="미리보기 이미지"
    )
    
    # 테마 메타정보
    is_system = models.BooleanField(default=False, verbose_name="시스템 테마")
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    order = models.IntegerField(default=0, verbose_name="정렬 순서")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "프리셋 테마"
        verbose_name_plural = "프리셋 테마들"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.display_name
    
    def apply_to_user(self, user):
        """사용자에게 테마 적용"""
        theme_config, created = ThemeConfiguration.objects.get_or_create(
            user=user,
            defaults={
                'theme_type': self.theme_type,
                'color_scheme': self.color_scheme,
                'primary_color': self.primary_color,
                'secondary_color': self.secondary_color,
                'accent_color': self.accent_color,
                'font_size': self.font_size,
            }
        )
        
        if not created:
            # 기존 설정 업데이트
            theme_config.theme_type = self.theme_type
            theme_config.color_scheme = self.color_scheme
            theme_config.primary_color = self.primary_color
            theme_config.secondary_color = self.secondary_color
            theme_config.accent_color = self.accent_color
            theme_config.font_size = self.font_size
            theme_config.save()
        
        return theme_config


class ThemeUsageStatistics(models.Model):
    """테마 사용 통계"""
    
    theme_name = models.CharField(max_length=50, verbose_name="테마 이름")
    usage_count = models.IntegerField(default=0, verbose_name="사용 횟수")
    active_users = models.IntegerField(default=0, verbose_name="활성 사용자 수")
    
    # 통계 데이터
    stats_date = models.DateField(auto_now_add=True, verbose_name="통계 날짜")
    
    class Meta:
        verbose_name = "테마 사용 통계"
        verbose_name_plural = "테마 사용 통계들"
        unique_together = ['theme_name', 'stats_date']
        ordering = ['-stats_date', '-usage_count']
    
    def __str__(self):
        return f"{self.theme_name} - {self.stats_date}"


class UserThemeHistory(models.Model):
    """사용자 테마 변경 이력"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='theme_history',
        verbose_name="사용자"
    )
    
    theme_name = models.CharField(max_length=50, verbose_name="테마 이름")
    theme_settings = models.JSONField(verbose_name="테마 설정")
    
    # 적용 시점
    applied_at = models.DateTimeField(auto_now_add=True, verbose_name="적용 시간")
    
    # 적용 방식
    APPLICATION_METHODS = [
        ('manual', '수동 선택'),
        ('auto', '자동 전환'),
        ('preset', '프리셋 적용'),
        ('import', '설정 가져오기'),
    ]
    application_method = models.CharField(
        max_length=20,
        choices=APPLICATION_METHODS,
        default='manual',
        verbose_name="적용 방식"
    )
    
    class Meta:
        verbose_name = "테마 변경 이력"
        verbose_name_plural = "테마 변경 이력들"
        ordering = ['-applied_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.theme_name} ({self.applied_at.strftime('%Y-%m-%d %H:%M')})"