import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, time
from django.utils import timezone
from django.contrib.auth import get_user_model

from .theme_models import ThemeConfiguration, PresetTheme, ThemeUsageStatistics, UserThemeHistory

User = get_user_model()
logger = logging.getLogger(__name__)


class ThemeService:
    """테마 관리 서비스"""
    
    def __init__(self):
        self.default_themes = self._get_default_themes()
    
    def get_user_theme(self, user: User) -> ThemeConfiguration:
        """사용자 테마 설정 조회/생성"""
        theme_config, created = ThemeConfiguration.objects.get_or_create(
            user=user
        )
        
        if created:
            logger.info(f"새로운 테마 설정 생성: {user.username}")
            
            # 시스템 자동 테마인 경우 현재 시간에 따라 설정
            if theme_config.theme_type == 'auto':
                current_theme = self._determine_auto_theme(theme_config)
                theme_config.theme_type = current_theme
                theme_config.save()
        
        return theme_config
    
    def update_user_theme(
        self,
        user: User,
        theme_data: Dict[str, Any],
        application_method: str = 'manual'
    ) -> ThemeConfiguration:
        """사용자 테마 설정 업데이트"""
        theme_config = self.get_user_theme(user)
        
        # 변경 사항 기록
        old_settings = self._serialize_theme_config(theme_config)
        
        # 설정 업데이트
        for key, value in theme_data.items():
            if hasattr(theme_config, key):
                setattr(theme_config, key, value)
        
        theme_config.save()
        
        # 변경 이력 기록
        self._record_theme_change(
            user=user,
            theme_name=theme_config.get_theme_type_display(),
            theme_settings=self._serialize_theme_config(theme_config),
            application_method=application_method
        )
        
        # 사용 통계 업데이트
        self._update_usage_statistics(theme_config.theme_type)
        
        logger.info(f"테마 설정 업데이트: {user.username} - {theme_config.theme_type}")
        return theme_config
    
    def apply_preset_theme(self, user: User, preset_name: str) -> ThemeConfiguration:
        """프리셋 테마 적용"""
        try:
            preset = PresetTheme.objects.get(name=preset_name, is_active=True)
        except PresetTheme.DoesNotExist:
            raise ValueError(f"프리셋 테마를 찾을 수 없습니다: {preset_name}")
        
        theme_config = preset.apply_to_user(user)
        
        # 변경 이력 기록
        self._record_theme_change(
            user=user,
            theme_name=preset.display_name,
            theme_settings=self._serialize_theme_config(theme_config),
            application_method='preset'
        )
        
        # 사용 통계 업데이트
        self._update_usage_statistics(preset_name)
        
        logger.info(f"프리셋 테마 적용: {user.username} - {preset.display_name}")
        return theme_config
    
    def get_available_presets(self) -> List[Dict[str, Any]]:
        """사용 가능한 프리셋 테마 목록"""
        presets = PresetTheme.objects.filter(is_active=True).order_by('order', 'name')
        
        return [
            {
                'name': preset.name,
                'display_name': preset.display_name,
                'description': preset.description,
                'theme_type': preset.theme_type,
                'color_scheme': preset.color_scheme,
                'primary_color': preset.primary_color,
                'secondary_color': preset.secondary_color,
                'accent_color': preset.accent_color,
                'preview_image': preset.preview_image.url if preset.preview_image else None,
            }
            for preset in presets
        ]
    
    def generate_css_variables(self, theme_config: ThemeConfiguration) -> str:
        """테마에 따른 CSS 변수 생성"""
        variables = theme_config.get_css_variables()
        
        # 테마별 추가 변수
        if theme_config.theme_type == 'dark':
            variables.update({
                '--background-color': '#121212',
                '--surface-color': '#1e1e1e',
                '--text-color': '#ffffff',
                '--text-secondary': '#b3b3b3',
                '--border-color': '#333333',
                '--shadow': 'rgba(255, 255, 255, 0.1)',
            })
        elif theme_config.theme_type == 'light':
            variables.update({
                '--background-color': '#ffffff',
                '--surface-color': '#f5f5f5',
                '--text-color': '#333333',
                '--text-secondary': '#666666',
                '--border-color': '#e0e0e0',
                '--shadow': 'rgba(0, 0, 0, 0.1)',
            })
        elif theme_config.theme_type == 'high_contrast':
            variables.update({
                '--background-color': '#000000',
                '--surface-color': '#1a1a1a',
                '--text-color': '#ffffff',
                '--text-secondary': '#ffffff',
                '--border-color': '#ffffff',
                '--shadow': 'none',
                '--primary-color': '#ffff00',
                '--accent-color': '#00ff00',
            })
        elif theme_config.theme_type == 'sepia':
            variables.update({
                '--background-color': '#f7f3e9',
                '--surface-color': '#efead5',
                '--text-color': '#5c4b37',
                '--text-secondary': '#8b7355',
                '--border-color': '#d4c4a0',
                '--shadow': 'rgba(92, 75, 55, 0.1)',
            })
        
        # CSS 문자열 생성
        css_vars = []
        for key, value in variables.items():
            css_vars.append(f'{key}: {value}')
        
        return ':root { ' + '; '.join(css_vars) + '; }'
    
    def get_theme_classes(self, theme_config: ThemeConfiguration) -> str:
        """테마 CSS 클래스 반환"""
        return theme_config.get_theme_classes()
    
    def auto_switch_theme(self, user: User) -> Optional[str]:
        """자동 테마 전환 (시간 기반)"""
        theme_config = self.get_user_theme(user)
        
        if theme_config.theme_type != 'auto':
            return None
        
        current_theme = self._determine_auto_theme(theme_config)
        
        # 현재 테마와 다르면 전환
        if current_theme != theme_config.theme_type:
            self.update_user_theme(
                user=user,
                theme_data={'theme_type': current_theme},
                application_method='auto'
            )
            return current_theme
        
        return None
    
    def export_theme_settings(self, user: User) -> Dict[str, Any]:
        """테마 설정 내보내기"""
        theme_config = self.get_user_theme(user)
        return self._serialize_theme_config(theme_config)
    
    def import_theme_settings(
        self,
        user: User,
        theme_settings: Dict[str, Any]
    ) -> ThemeConfiguration:
        """테마 설정 가져오기"""
        return self.update_user_theme(
            user=user,
            theme_data=theme_settings,
            application_method='import'
        )
    
    def get_theme_statistics(self) -> Dict[str, Any]:
        """테마 사용 통계"""
        # 전체 사용자 중 테마별 분포
        theme_distribution = {}
        total_users = User.objects.count()
        
        for theme_type, display_name in ThemeConfiguration.THEME_TYPES:
            count = ThemeConfiguration.objects.filter(theme_type=theme_type).count()
            theme_distribution[theme_type] = {
                'display_name': display_name,
                'count': count,
                'percentage': round((count / total_users * 100), 2) if total_users > 0 else 0
            }
        
        # 최근 30일간 프리셋 사용 통계
        recent_presets = ThemeUsageStatistics.objects.filter(
            stats_date__gte=timezone.now().date() - timezone.timedelta(days=30)
        ).order_by('-usage_count')[:10]
        
        preset_stats = []
        for stat in recent_presets:
            preset_stats.append({
                'name': stat.theme_name,
                'usage_count': stat.usage_count,
                'active_users': stat.active_users,
                'date': stat.stats_date.isoformat()
            })
        
        return {
            'theme_distribution': theme_distribution,
            'popular_presets': preset_stats,
            'total_users': total_users
        }
    
    def get_user_theme_history(self, user: User, limit: int = 10) -> List[Dict[str, Any]]:
        """사용자 테마 변경 이력"""
        history = UserThemeHistory.objects.filter(user=user).order_by('-applied_at')[:limit]
        
        return [
            {
                'theme_name': entry.theme_name,
                'theme_settings': entry.theme_settings,
                'application_method': entry.get_application_method_display(),
                'applied_at': entry.applied_at.isoformat()
            }
            for entry in history
        ]
    
    def _determine_auto_theme(self, theme_config: ThemeConfiguration) -> str:
        """자동 테마 결정 (시간 기반)"""
        if not theme_config.auto_dark_start or not theme_config.auto_dark_end:
            # 기본 시간 설정 (18:00 ~ 06:00)
            dark_start = time(18, 0)
            dark_end = time(6, 0)
        else:
            dark_start = theme_config.auto_dark_start
            dark_end = theme_config.auto_dark_end
        
        current_time = timezone.localtime().time()
        
        # 다크 모드 시간 계산
        if dark_start > dark_end:  # 자정을 넘나드는 경우
            is_dark_time = current_time >= dark_start or current_time <= dark_end
        else:
            is_dark_time = dark_start <= current_time <= dark_end
        
        return 'dark' if is_dark_time else 'light'
    
    def _serialize_theme_config(self, theme_config: ThemeConfiguration) -> Dict[str, Any]:
        """테마 설정 직렬화"""
        return {
            'theme_type': theme_config.theme_type,
            'color_scheme': theme_config.color_scheme,
            'primary_color': theme_config.primary_color,
            'secondary_color': theme_config.secondary_color,
            'accent_color': theme_config.accent_color,
            'font_size': theme_config.font_size,
            'font_family': theme_config.font_family,
            'high_contrast': theme_config.high_contrast,
            'reduce_motion': theme_config.reduce_motion,
            'focus_indicators': theme_config.focus_indicators,
            'sidebar_collapsed': theme_config.sidebar_collapsed,
            'compact_mode': theme_config.compact_mode,
            'show_tooltips': theme_config.show_tooltips,
            'map_style': theme_config.map_style,
            'auto_dark_start': theme_config.auto_dark_start.isoformat() if theme_config.auto_dark_start else None,
            'auto_dark_end': theme_config.auto_dark_end.isoformat() if theme_config.auto_dark_end else None,
        }
    
    def _record_theme_change(
        self,
        user: User,
        theme_name: str,
        theme_settings: Dict[str, Any],
        application_method: str
    ):
        """테마 변경 이력 기록"""
        UserThemeHistory.objects.create(
            user=user,
            theme_name=theme_name,
            theme_settings=theme_settings,
            application_method=application_method
        )
    
    def _update_usage_statistics(self, theme_name: str):
        """사용 통계 업데이트"""
        today = timezone.now().date()
        
        stats, created = ThemeUsageStatistics.objects.get_or_create(
            theme_name=theme_name,
            stats_date=today,
            defaults={'usage_count': 1, 'active_users': 1}
        )
        
        if not created:
            stats.usage_count += 1
            stats.save()
    
    def _get_default_themes(self) -> Dict[str, Dict[str, Any]]:
        """기본 테마 정의"""
        return {
            'light_blue': {
                'display_name': '라이트 블루',
                'theme_type': 'light',
                'color_scheme': 'blue',
                'primary_color': '#2196F3',
                'secondary_color': '#FF5722',
                'accent_color': '#4CAF50',
            },
            'dark_blue': {
                'display_name': '다크 블루',
                'theme_type': 'dark',
                'color_scheme': 'blue',
                'primary_color': '#1976D2',
                'secondary_color': '#FF5722',
                'accent_color': '#4CAF50',
            },
            'light_green': {
                'display_name': '라이트 그린',
                'theme_type': 'light',
                'color_scheme': 'green',
                'primary_color': '#4CAF50',
                'secondary_color': '#FF5722',
                'accent_color': '#2196F3',
            },
            'dark_green': {
                'display_name': '다크 그린',
                'theme_type': 'dark',
                'color_scheme': 'green',
                'primary_color': '#388E3C',
                'secondary_color': '#FF5722',
                'accent_color': '#2196F3',
            },
            'high_contrast': {
                'display_name': '고대비',
                'theme_type': 'high_contrast',
                'color_scheme': 'default',
                'primary_color': '#FFFF00',
                'secondary_color': '#FF0000',
                'accent_color': '#00FF00',
            },
            'sepia': {
                'display_name': '세피아',
                'theme_type': 'sepia',
                'color_scheme': 'default',
                'primary_color': '#8B7355',
                'secondary_color': '#D2691E',
                'accent_color': '#CD853F',
            }
        }


# 전역 인스턴스
theme_service = ThemeService()