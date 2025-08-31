from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
import json

from .theme_models import ThemeConfiguration, PresetTheme, UserThemeHistory
from .theme_serializers import (
    ThemeConfigurationSerializer, PresetThemeSerializer,
    ThemeUpdateSerializer, PresetApplySerializer,
    ThemeExportSerializer, ThemeImportSerializer,
    UserThemeHistorySerializer, ThemeStatisticsSerializer,
    ColorPaletteSerializer, ThemePreviewSerializer,
    AccessibilitySettingsSerializer
)
from .theme_services import theme_service


class ThemeConfigurationViewSet(viewsets.ModelViewSet):
    """테마 설정 ViewSet"""
    
    serializer_class = ThemeConfigurationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """사용자 테마 설정 조회/생성"""
        return theme_service.get_user_theme(self.request.user)
    
    def list(self, request):
        """테마 설정 조회"""
        theme_config = self.get_object()
        serializer = self.get_serializer(theme_config)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """테마 설정 업데이트"""
        serializer = ThemeUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            theme_config = theme_service.update_user_theme(
                user=request.user,
                theme_data=serializer.validated_data
            )
            
            response_serializer = self.get_serializer(theme_config)
            return Response({
                'message': '테마 설정이 업데이트되었습니다.',
                'theme': response_serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def css(self, request):
        """테마 CSS 생성"""
        theme_config = self.get_object()
        css_content = theme_service.generate_css_variables(theme_config)
        
        response = HttpResponse(css_content, content_type='text/css')
        response['Cache-Control'] = 'max-age=3600'  # 1시간 캐시
        return response
    
    @action(detail=False, methods=['get'])
    def classes(self, request):
        """테마 CSS 클래스 반환"""
        theme_config = self.get_object()
        classes = theme_service.get_theme_classes(theme_config)
        
        return Response({
            'theme_classes': classes,
            'css_variables': theme_config.get_css_variables()
        })
    
    @action(detail=False, methods=['post'])
    def reset(self, request):
        """기본 테마로 초기화"""
        theme_config = self.get_object()
        
        # 기본값으로 초기화
        default_data = {
            'theme_type': 'light',
            'color_scheme': 'default',
            'primary_color': '#2196F3',
            'secondary_color': '#FF5722',
            'accent_color': '#4CAF50',
            'font_size': 'medium',
            'font_family': 'system',
            'high_contrast': False,
            'reduce_motion': False,
            'focus_indicators': True,
            'sidebar_collapsed': False,
            'compact_mode': False,
            'show_tooltips': True,
            'map_style': 'default',
        }
        
        theme_config = theme_service.update_user_theme(
            user=request.user,
            theme_data=default_data
        )
        
        serializer = self.get_serializer(theme_config)
        return Response({
            'message': '테마가 기본값으로 초기화되었습니다.',
            'theme': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def toggle_dark_mode(self, request):
        """다크모드 토글"""
        theme_config = self.get_object()
        
        new_theme_type = 'light' if theme_config.theme_type == 'dark' else 'dark'
        
        theme_config = theme_service.update_user_theme(
            user=request.user,
            theme_data={'theme_type': new_theme_type}
        )
        
        serializer = self.get_serializer(theme_config)
        return Response({
            'message': f'{new_theme_type.title()} 모드로 전환되었습니다.',
            'theme': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def apply_preset(self, request):
        """프리셋 테마 적용"""
        serializer = PresetApplySerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                theme_config = theme_service.apply_preset_theme(
                    user=request.user,
                    preset_name=serializer.validated_data['preset_name']
                )
                
                response_serializer = self.get_serializer(theme_config)
                return Response({
                    'message': '프리셋 테마가 적용되었습니다.',
                    'theme': response_serializer.data
                })
                
            except ValueError as e:
                return Response({
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """테마 설정 내보내기"""
        theme_settings = theme_service.export_theme_settings(request.user)
        
        export_data = {
            'theme_name': f"{request.user.username}_theme",
            'theme_settings': theme_settings,
            'exported_at': timezone.now(),
            'user_name': request.user.username
        }
        
        serializer = ThemeExportSerializer(data=export_data)
        serializer.is_valid()
        
        response = HttpResponse(
            json.dumps(serializer.data, indent=2, ensure_ascii=False),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="{request.user.username}_theme.json"'
        return response
    
    @action(detail=False, methods=['post'])
    def import_theme(self, request):
        """테마 설정 가져오기"""
        serializer = ThemeImportSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                theme_config = theme_service.import_theme_settings(
                    user=request.user,
                    theme_settings=serializer.validated_data['theme_settings']
                )
                
                response_serializer = self.get_serializer(theme_config)
                return Response({
                    'message': '테마 설정을 가져왔습니다.',
                    'theme': response_serializer.data
                })
                
            except Exception as e:
                return Response({
                    'error': f'테마 가져오기 실패: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def preview(self, request):
        """테마 미리보기"""
        serializer = ThemePreviewSerializer(data=request.data)
        
        if serializer.is_valid():
            # 임시 테마 설정 객체 생성 (저장하지 않음)
            temp_config = ThemeConfiguration(
                theme_type=serializer.validated_data['theme_type'],
                primary_color=serializer.validated_data['primary_color'],
                secondary_color=serializer.validated_data['secondary_color'],
                accent_color=serializer.validated_data['accent_color']
            )
            
            css_variables = temp_config.get_css_variables()
            theme_classes = temp_config.get_theme_classes()
            
            return Response({
                'css_variables': css_variables,
                'theme_classes': theme_classes,
                'preview_css': theme_service.generate_css_variables(temp_config)
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PresetThemeViewSet(viewsets.ReadOnlyModelViewSet):
    """프리셋 테마 ViewSet"""
    
    serializer_class = PresetThemeSerializer
    queryset = PresetTheme.objects.filter(is_active=True).order_by('order', 'name')
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """테마 카테고리별 분류"""
        presets = self.get_queryset()
        
        categories = {
            'light': [],
            'dark': [],
            'high_contrast': [],
            'custom': []
        }
        
        for preset in presets:
            serializer = self.get_serializer(preset)
            category = preset.theme_type if preset.theme_type in categories else 'custom'
            categories[category].append(serializer.data)
        
        return Response(categories)
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """인기 프리셋 테마"""
        # 사용 통계 기반으로 인기 테마 조회
        popular_presets = self.get_queryset()[:6]  # 상위 6개
        serializer = self.get_serializer(popular_presets, many=True)
        
        return Response({
            'message': '인기 프리셋 테마',
            'presets': serializer.data
        })


class ThemeHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """테마 변경 이력 ViewSet"""
    
    serializer_class = UserThemeHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserThemeHistory.objects.filter(
            user=self.request.user
        ).order_by('-applied_at')
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """이전 테마로 복원"""
        history_entry = get_object_or_404(
            UserThemeHistory,
            pk=pk,
            user=request.user
        )
        
        theme_config = theme_service.update_user_theme(
            user=request.user,
            theme_data=history_entry.theme_settings,
            application_method='manual'
        )
        
        theme_serializer = ThemeConfigurationSerializer(theme_config)
        return Response({
            'message': f'{history_entry.theme_name} 테마로 복원되었습니다.',
            'theme': theme_serializer.data
        })


class ThemeUtilityViewSet(viewsets.ViewSet):
    """테마 유틸리티 ViewSet"""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def color_palettes(self, request):
        """추천 색상 팔레트"""
        palettes = [
            {
                'name': 'material_blue',
                'display_name': '머티리얼 블루',
                'colors': ['#E3F2FD', '#2196F3', '#1976D2', '#0D47A1'],
                'is_recommended': True
            },
            {
                'name': 'material_green',
                'display_name': '머티리얼 그린',
                'colors': ['#E8F5E8', '#4CAF50', '#388E3C', '#1B5E20'],
                'is_recommended': True
            },
            {
                'name': 'material_purple',
                'display_name': '머티리얼 퍼플',
                'colors': ['#F3E5F5', '#9C27B0', '#7B1FA2', '#4A148C'],
                'is_recommended': False
            },
            {
                'name': 'material_orange',
                'display_name': '머티리얼 오렌지',
                'colors': ['#FFF3E0', '#FF9800', '#F57C00', '#E65100'],
                'is_recommended': False
            },
            {
                'name': 'high_contrast',
                'display_name': '고대비',
                'colors': ['#FFFFFF', '#FFFF00', '#00FF00', '#FF0000'],
                'is_recommended': False
            }
        ]
        
        serializer = ColorPaletteSerializer(palettes, many=True)
        return Response({
            'palettes': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def accessibility_check(self, request):
        """접근성 검사"""
        theme_config = theme_service.get_user_theme(request.user)
        
        issues = []
        recommendations = []
        
        # 색상 대비 검사
        if theme_config.theme_type not in ['high_contrast'] and theme_config.high_contrast is False:
            issues.append('색상 대비가 충분하지 않을 수 있습니다.')
            recommendations.append('고대비 모드를 활성화하거나 고대비 테마를 사용하세요.')
        
        # 폰트 크기 검사
        if theme_config.font_size == 'small':
            issues.append('폰트 크기가 작아 가독성이 떨어질 수 있습니다.')
            recommendations.append('폰트 크기를 중간 이상으로 설정하세요.')
        
        # 애니메이션 검사
        if not theme_config.reduce_motion:
            recommendations.append('움직임에 민감한 사용자를 위해 애니메이션 줄이기를 고려하세요.')
        
        return Response({
            'accessibility_score': max(0, 100 - len(issues) * 20),
            'issues': issues,
            'recommendations': recommendations,
            'current_settings': {
                'high_contrast': theme_config.high_contrast,
                'reduce_motion': theme_config.reduce_motion,
                'focus_indicators': theme_config.focus_indicators,
                'font_size': theme_config.font_size
            }
        })
    
    @action(detail=False, methods=['post'])
    def accessibility_settings(self, request):
        """접근성 설정 업데이트"""
        serializer = AccessibilitySettingsSerializer(data=request.data)
        
        if serializer.is_valid():
            theme_config = theme_service.update_user_theme(
                user=request.user,
                theme_data=serializer.validated_data
            )
            
            theme_serializer = ThemeConfigurationSerializer(theme_config)
            return Response({
                'message': '접근성 설정이 업데이트되었습니다.',
                'theme': theme_serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def auto_switch(self, request):
        """자동 테마 전환"""
        switched_theme = theme_service.auto_switch_theme(request.user)
        
        if switched_theme:
            theme_config = theme_service.get_user_theme(request.user)
            theme_serializer = ThemeConfigurationSerializer(theme_config)
            
            return Response({
                'message': f'{switched_theme.title()} 모드로 자동 전환되었습니다.',
                'theme': theme_serializer.data,
                'switched': True
            })
        else:
            return Response({
                'message': '자동 전환할 테마가 없습니다.',
                'switched': False
            })


class AdminThemeViewSet(viewsets.ViewSet):
    """관리자용 테마 관리 ViewSet"""
    
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """테마 사용 통계"""
        stats = theme_service.get_theme_statistics()
        serializer = ThemeStatisticsSerializer(data=stats)
        serializer.is_valid()
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def create_preset(self, request):
        """새 프리셋 테마 생성"""
        # 관리자용 프리셋 생성 로직
        # 실제로는 별도의 시리얼라이저와 뷰가 필요
        return Response({
            'message': '프리셋 생성 기능은 별도 구현 필요'
        })
    
    @action(detail=False, methods=['get'])
    def user_themes(self, request):
        """사용자별 테마 사용 현황"""
        # 사용자별 테마 설정 조회
        theme_configs = ThemeConfiguration.objects.select_related('user').all()
        
        user_themes = []
        for config in theme_configs[:50]:  # 최대 50개
            user_themes.append({
                'user_id': config.user.id,
                'username': config.user.username,
                'theme_type': config.theme_type,
                'color_scheme': config.color_scheme,
                'updated_at': config.updated_at.isoformat()
            })
        
        return Response({
            'total_users': theme_configs.count(),
            'user_themes': user_themes
        })