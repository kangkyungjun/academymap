from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from django.core.cache import cache

from .social_models import (
    SocialPlatform, ShareableContent, SocialShare,
    AcademyShare, ShareAnalytics, PopularContent
)
from .social_serializers import (
    SocialPlatformSerializer, ShareableContentSerializer,
    SocialShareSerializer, AcademyShareSerializer,
    AcademyShareCreateSerializer, ShareUrlRequestSerializer,
    ShareUrlResponseSerializer, ShareStatisticsSerializer,
    PopularContentSerializer, ShareAnalyticsSerializer,
    SocialSharePreviewSerializer, BulkShareRequestSerializer,
    UserShareHistorySerializer
)
from .social_services import social_service
from main.models import Data as Academy


class SocialPlatformViewSet(viewsets.ReadOnlyModelViewSet):
    """소셜 플랫폼 ViewSet"""
    
    serializer_class = SocialPlatformSerializer
    queryset = SocialPlatform.objects.filter(is_active=True).order_by('order')
    permission_classes = []  # 공개 접근 허용
    
    @action(detail=False, methods=['get'])
    def list_for_sharing(self, request):
        """공유용 플랫폼 목록"""
        platforms = social_service.get_share_platforms()
        
        return Response({
            'platforms': platforms,
            'total_count': len(platforms)
        })


class SocialShareViewSet(viewsets.ModelViewSet):
    """소셜 공유 ViewSet"""
    
    serializer_class = SocialShareSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SocialShare.objects.filter(user=self.request.user).order_by('-shared_at')
    
    @action(detail=False, methods=['post'])
    def share_academy(self, request):
        """학원 공유하기"""
        serializer = AcademyShareCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # 학원과 플랫폼 조회
                academy = get_object_or_404(Academy, id=serializer.validated_data['academy_id'])
                platform_name = serializer.validated_data['platform']
                
                # 커스터마이징 옵션 준비
                custom_options = {
                    'title': serializer.validated_data.get('custom_title', ''),
                    'description': serializer.validated_data.get('custom_description', ''),
                    'message': serializer.validated_data.get('custom_message', ''),
                    'subjects': serializer.validated_data.get('selected_subjects', []),
                    'include_rating': serializer.validated_data.get('include_rating', True),
                    'include_price': serializer.validated_data.get('include_price', False),
                    'include_location': serializer.validated_data.get('include_location', True),
                    'reason': serializer.validated_data.get('recommendation_reason', ''),
                    'target_age': serializer.validated_data.get('target_age_group', '')
                }
                
                # 학원 공유 실행
                academy_share = social_service.share_academy(
                    user=request.user,
                    academy=academy,
                    platform_name=platform_name,
                    custom_options=custom_options
                )
                
                # 응답 데이터 생성
                share_serializer = AcademyShareSerializer(academy_share)
                
                return Response({
                    'message': f'{academy.상호명}이(가) {academy_share.platform.display_name}에 공유되었습니다.',
                    'share_data': share_serializer.data,
                    'share_url': academy_share.get_share_title()  # 실제로는 생성된 공유 URL
                }, status=status.HTTP_201_CREATED)
                
            except ValueError as e:
                return Response({
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({
                    'error': '공유 처리 중 오류가 발생했습니다.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def generate_share_url(self, request):
        """공유 URL 생성"""
        serializer = ShareUrlRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # 공유 콘텐츠 생성
                content = social_service.create_shareable_content(
                    content_type=serializer.validated_data['content_type'],
                    title=serializer.validated_data['title'],
                    description=serializer.validated_data['description'],
                    url=serializer.validated_data['url'],
                    hashtags=serializer.validated_data.get('hashtags', ''),
                    user=request.user
                )
                
                # 공유 URL 생성
                share_url = social_service.generate_share_url(
                    platform_name=serializer.validated_data['platform'],
                    content=content
                )
                
                response_data = {
                    'platform': serializer.validated_data['platform'],
                    'share_url': share_url,
                    'content_id': content.id
                }
                
                response_serializer = ShareUrlResponseSerializer(data=response_data)
                response_serializer.is_valid()
                
                return Response(response_serializer.data)
                
            except Exception as e:
                return Response({
                    'error': f'공유 URL 생성 실패: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def preview_share(self, request):
        """공유 미리보기"""
        academy_id = request.data.get('academy_id')
        platform_name = request.data.get('platform')
        custom_options = request.data.get('options', {})
        
        if not academy_id or not platform_name:
            return Response({
                'error': 'academy_id와 platform이 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            academy = get_object_or_404(Academy, id=academy_id)
            platform = get_object_or_404(SocialPlatform, name=platform_name, is_active=True)
            
            # 임시 AcademyShare 객체 생성 (저장하지 않음)
            temp_share = AcademyShare(
                academy=academy,
                platform=platform,
                user=request.user,
                custom_title=custom_options.get('title', ''),
                custom_description=custom_options.get('description', ''),
                selected_subjects=custom_options.get('subjects', []),
                include_rating=custom_options.get('include_rating', True),
                include_price=custom_options.get('include_price', False),
                include_location=custom_options.get('include_location', True),
                recommendation_reason=custom_options.get('reason', ''),
                target_age_group=custom_options.get('target_age', '')
            )
            
            # 미리보기 데이터 생성
            preview_data = {
                'title': temp_share.get_share_title(),
                'description': temp_share.get_share_description(),
                'hashtags': temp_share.get_hashtags(),
                'url': f"/academy/{academy.id}/",
                'platform': platform.display_name,
                'og_title': temp_share.get_share_title(),
                'og_description': temp_share.get_share_description(),
                'share_url': '#'  # 실제 공유할 때 생성됨
            }
            
            serializer = SocialSharePreviewSerializer(data=preview_data)
            serializer.is_valid()
            
            return Response(serializer.data)
            
        except Exception as e:
            return Response({
                'error': f'미리보기 생성 실패: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_share(self, request):
        """대량 공유"""
        serializer = BulkShareRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                academy_ids = serializer.validated_data['academy_ids']
                platforms = serializer.validated_data['platforms']
                
                results = []
                errors = []
                
                for academy_id in academy_ids:
                    try:
                        academy = Academy.objects.get(id=academy_id)
                        
                        for platform_name in platforms:
                            custom_options = {
                                'include_rating': serializer.validated_data['include_rating'],
                                'include_location': serializer.validated_data['include_location'],
                                'message': serializer.validated_data.get('custom_message', '')
                            }
                            
                            academy_share = social_service.share_academy(
                                user=request.user,
                                academy=academy,
                                platform_name=platform_name,
                                custom_options=custom_options
                            )
                            
                            results.append({
                                'academy_id': academy_id,
                                'academy_name': academy.상호명,
                                'platform': platform_name,
                                'status': 'success'
                            })
                            
                    except Exception as e:
                        errors.append({
                            'academy_id': academy_id,
                            'error': str(e)
                        })
                
                return Response({
                    'message': f'{len(results)}개 공유 완료, {len(errors)}개 실패',
                    'successful_shares': results,
                    'errors': errors,
                    'total_processed': len(academy_ids) * len(platforms)
                })
                
            except Exception as e:
                return Response({
                    'error': f'대량 공유 처리 실패: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def my_shares(self, request):
        """내 공유 기록"""
        limit = int(request.query_params.get('limit', 20))
        shares = social_service.get_user_share_history(request.user, limit)
        
        serializer = UserShareHistorySerializer(shares, many=True)
        
        return Response({
            'shares': serializer.data,
            'total_count': len(shares)
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """공유 통계"""
        days = int(request.query_params.get('days', 30))
        stats = social_service.get_share_statistics(request.user, days)
        
        serializer = ShareStatisticsSerializer(data=stats)
        serializer.is_valid()
        
        return Response(serializer.data)


class PopularContentViewSet(viewsets.ReadOnlyModelViewSet):
    """인기 콘텐츠 ViewSet"""
    
    serializer_class = PopularContentSerializer
    permission_classes = []  # 공개 접근
    
    def get_queryset(self):
        content_type = self.request.query_params.get('content_type')
        query = PopularContent.objects.select_related('content')
        
        if content_type:
            query = query.filter(content__content_type=content_type)
        
        return query.order_by('-viral_score')[:50]  # 상위 50개
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """트렌딩 콘텐츠"""
        content_type = request.query_params.get('content_type')
        limit = int(request.query_params.get('limit', 10))
        
        trending_content = social_service.get_popular_content(content_type, limit)
        
        return Response({
            'trending_content': trending_content,
            'period': 'weekly',
            'generated_at': timezone.now()
        })


class ShareAnalyticsViewSet(viewsets.ViewSet):
    """공유 분석 ViewSet"""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """분석 대시보드"""
        # 기본 통계
        user_stats = social_service.get_share_statistics(request.user, 30)
        
        # 최근 7일 트렌드
        recent_shares = SocialShare.objects.filter(
            user=request.user,
            shared_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()
        
        # 가장 인기 있는 플랫폼
        top_platform = SocialShare.objects.filter(
            user=request.user
        ).values('platform__display_name').annotate(
            count=Count('id')
        ).order_by('-count').first()
        
        # 총 참여도 점수
        total_engagement = SocialShare.objects.filter(
            user=request.user
        ).aggregate(
            total=Count('engagement_score')
        )['total'] or 0
        
        return Response({
            'overview': {
                'total_shares_30d': user_stats['total_shares'],
                'recent_shares_7d': recent_shares,
                'total_engagement': total_engagement,
                'top_platform': top_platform['platform__display_name'] if top_platform else None
            },
            'detailed_stats': user_stats,
            'generated_at': timezone.now()
        })
    
    @action(detail=False, methods=['get'])
    def platform_comparison(self, request):
        """플랫폼별 성과 비교"""
        days = int(request.query_params.get('days', 30))
        
        platform_stats = SocialShare.objects.filter(
            user=request.user,
            shared_at__gte=timezone.now() - timezone.timedelta(days=days)
        ).values(
            'platform__name',
            'platform__display_name',
            'platform__color'
        ).annotate(
            total_shares=Count('id'),
            total_clicks=Count('clicks'),
            avg_engagement=Count('engagement_score')
        ).order_by('-total_shares')
        
        return Response({
            'platform_comparison': list(platform_stats),
            'period_days': days,
            'generated_at': timezone.now()
        })


class AdminSocialViewSet(viewsets.ViewSet):
    """관리자용 소셜 미디어 ViewSet"""
    
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def global_statistics(self, request):
        """전체 공유 통계"""
        days = int(request.query_params.get('days', 30))
        
        # 전체 통계
        global_stats = social_service.get_share_statistics(days=days)
        
        # 플랫폼별 분석 데이터
        analytics = ShareAnalytics.objects.filter(
            date__gte=timezone.now().date() - timezone.timedelta(days=days)
        ).order_by('-date')
        
        analytics_serializer = ShareAnalyticsSerializer(analytics, many=True)
        
        return Response({
            'global_statistics': global_stats,
            'daily_analytics': analytics_serializer.data,
            'period_days': days
        })
    
    @action(detail=False, methods=['post'])
    def update_popular_scores(self, request):
        """인기 콘텐츠 점수 업데이트"""
        try:
            social_service.update_popular_content_scores()
            
            return Response({
                'message': '인기 콘텐츠 점수가 업데이트되었습니다.',
                'updated_at': timezone.now()
            })
            
        except Exception as e:
            return Response({
                'error': f'업데이트 실패: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def platform_management(self, request):
        """플랫폼 관리"""
        platforms = SocialPlatform.objects.all().order_by('order')
        serializer = SocialPlatformSerializer(platforms, many=True)
        
        # 각 플랫폼별 사용 통계
        platform_usage = {}
        for platform in platforms:
            usage_count = SocialShare.objects.filter(platform=platform).count()
            platform_usage[platform.id] = usage_count
        
        return Response({
            'platforms': serializer.data,
            'usage_statistics': platform_usage,
            'total_platforms': platforms.count()
        })


# 캐시 무효화 및 성능 최적화 유틸리티 뷰
class SocialCacheViewSet(viewsets.ViewSet):
    """소셜 미디어 캐시 관리 ViewSet"""
    
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['post'])
    def clear_platform_cache(self, request):
        """플랫폼 캐시 삭제"""
        cache.delete('active_social_platforms')
        
        return Response({
            'message': '플랫폼 캐시가 삭제되었습니다.'
        })
    
    @action(detail=False, methods=['get'])
    def cache_status(self, request):
        """캐시 상태 확인"""
        platforms_cached = cache.get('active_social_platforms') is not None
        
        return Response({
            'cache_status': {
                'platforms_cached': platforms_cached
            },
            'checked_at': timezone.now()
        })