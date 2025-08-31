from rest_framework import serializers
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model
from .theme_models import ThemeConfiguration, PresetTheme, UserThemeHistory

User = get_user_model()


class ThemeConfigurationSerializer(serializers.ModelSerializer):
    """테마 설정 시리얼라이저"""
    
    css_variables = serializers.SerializerMethodField()
    theme_classes = serializers.SerializerMethodField()
    
    class Meta:
        model = ThemeConfiguration
        exclude = ['id', 'user', 'created_at', 'updated_at']
    
    def get_css_variables(self, obj):
        """CSS 변수 반환"""
        return obj.get_css_variables()
    
    def get_theme_classes(self, obj):
        """테마 CSS 클래스 반환"""
        return obj.get_theme_classes()
    
    def validate_primary_color(self, value):
        """기본 색상 유효성 검사"""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError('올바른 HEX 색상 코드를 입력하세요 (#RRGGBB)')
        
        try:
            int(value[1:], 16)
        except ValueError:
            raise serializers.ValidationError('올바른 HEX 색상 코드를 입력하세요')
        
        return value
    
    def validate_secondary_color(self, value):
        """보조 색상 유효성 검사"""
        return self.validate_primary_color(value)
    
    def validate_accent_color(self, value):
        """강조 색상 유효성 검사"""
        return self.validate_primary_color(value)
    
    def validate(self, attrs):
        """전체 유효성 검사"""
        
        # 자동 다크모드 시간 검증
        auto_dark_start = attrs.get('auto_dark_start')
        auto_dark_end = attrs.get('auto_dark_end')
        
        if auto_dark_start and auto_dark_end:
            if auto_dark_start == auto_dark_end:
                raise serializers.ValidationError({
                    'auto_dark_end': '시작 시간과 종료 시간이 같을 수 없습니다.'
                })
        
        # 폰트 패밀리 검증
        font_family = attrs.get('font_family')
        if font_family and len(font_family) > 50:
            raise serializers.ValidationError({
                'font_family': '폰트 패밀리명이 너무 깁니다.'
            })
        
        return attrs


class PresetThemeSerializer(serializers.ModelSerializer):
    """프리셋 테마 시리얼라이저"""
    
    preview_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PresetTheme
        fields = [
            'name', 'display_name', 'description', 'theme_type',
            'color_scheme', 'primary_color', 'secondary_color', 
            'accent_color', 'font_size', 'preview_image_url'
        ]
    
    def get_preview_image_url(self, obj):
        """미리보기 이미지 URL"""
        if obj.preview_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.preview_image.url)
            return obj.preview_image.url
        return None


class ThemeUpdateSerializer(serializers.Serializer):
    """테마 업데이트 시리얼라이저"""
    
    theme_type = serializers.ChoiceField(
        choices=ThemeConfiguration.THEME_TYPES,
        required=False
    )
    color_scheme = serializers.ChoiceField(
        choices=ThemeConfiguration.COLOR_SCHEMES,
        required=False
    )
    primary_color = serializers.RegexField(
        regex=r'^#[0-9A-Fa-f]{6}$',
        required=False,
        error_messages={'invalid': '올바른 HEX 색상 코드를 입력하세요 (#RRGGBB)'}
    )
    secondary_color = serializers.RegexField(
        regex=r'^#[0-9A-Fa-f]{6}$',
        required=False,
        error_messages={'invalid': '올바른 HEX 색상 코드를 입력하세요 (#RRGGBB)'}
    )
    accent_color = serializers.RegexField(
        regex=r'^#[0-9A-Fa-f]{6}$',
        required=False,
        error_messages={'invalid': '올바른 HEX 색상 코드를 입력하세요 (#RRGGBB)'}
    )
    font_size = serializers.ChoiceField(
        choices=ThemeConfiguration.FONT_SIZES,
        required=False
    )
    font_family = serializers.CharField(
        max_length=50,
        required=False
    )
    high_contrast = serializers.BooleanField(required=False)
    reduce_motion = serializers.BooleanField(required=False)
    focus_indicators = serializers.BooleanField(required=False)
    sidebar_collapsed = serializers.BooleanField(required=False)
    compact_mode = serializers.BooleanField(required=False)
    show_tooltips = serializers.BooleanField(required=False)
    map_style = serializers.ChoiceField(
        choices=[
            ('default', '기본'),
            ('satellite', '위성'),
            ('terrain', '지형'),
            ('hybrid', '하이브리드'),
        ],
        required=False
    )
    auto_dark_start = serializers.TimeField(required=False, allow_null=True)
    auto_dark_end = serializers.TimeField(required=False, allow_null=True)
    custom_css = serializers.CharField(required=False, allow_blank=True)


class PresetApplySerializer(serializers.Serializer):
    """프리셋 적용 시리얼라이저"""
    
    preset_name = serializers.CharField(
        max_length=50,
        help_text="적용할 프리셋 테마 이름"
    )
    
    def validate_preset_name(self, value):
        """프리셋 존재 확인"""
        if not PresetTheme.objects.filter(name=value, is_active=True).exists():
            raise serializers.ValidationError('존재하지 않는 프리셋 테마입니다.')
        return value


class ThemeExportSerializer(serializers.Serializer):
    """테마 내보내기 시리얼라이저"""
    
    theme_name = serializers.CharField(read_only=True)
    theme_settings = serializers.DictField(read_only=True)
    exported_at = serializers.DateTimeField(read_only=True)
    user_name = serializers.CharField(read_only=True)


class ThemeImportSerializer(serializers.Serializer):
    """테마 가져오기 시리얼라이저"""
    
    theme_settings = serializers.DictField(
        help_text="가져올 테마 설정 데이터"
    )
    
    def validate_theme_settings(self, value):
        """테마 설정 유효성 검사"""
        required_fields = ['theme_type', 'primary_color']
        
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f'필수 필드가 누락되었습니다: {field}')
        
        # 색상 코드 검증
        color_fields = ['primary_color', 'secondary_color', 'accent_color']
        for field in color_fields:
            if field in value:
                color_value = value[field]
                if not isinstance(color_value, str) or not color_value.startswith('#') or len(color_value) != 7:
                    raise serializers.ValidationError(f'{field}: 올바른 HEX 색상 코드가 아닙니다.')
        
        return value


class UserThemeHistorySerializer(serializers.ModelSerializer):
    """사용자 테마 변경 이력 시리얼라이저"""
    
    application_method_display = serializers.CharField(
        source='get_application_method_display',
        read_only=True
    )
    
    class Meta:
        model = UserThemeHistory
        fields = [
            'id', 'theme_name', 'theme_settings', 'applied_at',
            'application_method', 'application_method_display'
        ]
        read_only_fields = ['id', 'applied_at']


class ThemeStatisticsSerializer(serializers.Serializer):
    """테마 통계 시리얼라이저"""
    
    theme_distribution = serializers.DictField()
    popular_presets = serializers.ListField(
        child=serializers.DictField()
    )
    total_users = serializers.IntegerField()


class ColorPaletteSerializer(serializers.Serializer):
    """색상 팔레트 시리얼라이저"""
    
    name = serializers.CharField()
    display_name = serializers.CharField()
    colors = serializers.ListField(
        child=serializers.CharField(
            validators=[
                RegexValidator(
                    regex=r'^#[0-9A-Fa-f]{6}$',
                    message='올바른 HEX 색상 코드를 입력하세요'
                )
            ]
        )
    )
    is_recommended = serializers.BooleanField(default=False)


class ThemePreviewSerializer(serializers.Serializer):
    """테마 미리보기 시리얼라이저"""
    
    theme_type = serializers.ChoiceField(
        choices=ThemeConfiguration.THEME_TYPES
    )
    primary_color = serializers.RegexField(
        regex=r'^#[0-9A-Fa-f]{6}$'
    )
    secondary_color = serializers.RegexField(
        regex=r'^#[0-9A-Fa-f]{6}$'
    )
    accent_color = serializers.RegexField(
        regex=r'^#[0-9A-Fa-f]{6}$'
    )
    
    def validate(self, attrs):
        """미리보기 데이터 검증"""
        # 색상 대비 검증 (접근성)
        if attrs['theme_type'] == 'high_contrast':
            # 고대비 모드에서는 밝은 색상 사용
            colors = [attrs['primary_color'], attrs['secondary_color'], attrs['accent_color']]
            for color in colors:
                # 색상 밝기 계산 (간단한 방법)
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                brightness = (r * 299 + g * 587 + b * 114) / 1000
                
                if brightness < 128:  # 너무 어두운 색상
                    raise serializers.ValidationError(
                        f'고대비 모드에서는 밝은 색상을 사용해야 합니다: {color}'
                    )
        
        return attrs


class AccessibilitySettingsSerializer(serializers.Serializer):
    """접근성 설정 시리얼라이저"""
    
    high_contrast = serializers.BooleanField(default=False)
    reduce_motion = serializers.BooleanField(default=False)
    focus_indicators = serializers.BooleanField(default=True)
    font_size = serializers.ChoiceField(
        choices=ThemeConfiguration.FONT_SIZES,
        default='medium'
    )
    
    # 추가 접근성 옵션
    screen_reader_support = serializers.BooleanField(default=False)
    keyboard_navigation = serializers.BooleanField(default=True)
    color_blind_friendly = serializers.BooleanField(default=False)