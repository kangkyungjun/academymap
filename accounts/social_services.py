import logging
from typing import Dict, List, Optional
from urllib.parse import quote, urlencode
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, F, Q
from django.core.cache import cache

from .social_models import (
    SocialPlatform, ShareableContent, SocialShare, 
    AcademyShare, ShareAnalytics, PopularContent
)
from main.models import Data as Academy

User = get_user_model()
logger = logging.getLogger(__name__)


class SocialSharingService:
    """소셜 미디어 공유 서비스"""
    
    def __init__(self):
        self.platforms = self._get_active_platforms()
    
    def _get_active_platforms(self):
        """활성화된 플랫폼 목록 조회 (캐시 사용)"""
        cache_key = 'active_social_platforms'
        platforms = cache.get(cache_key)
        
        if platforms is None:
            try:
                platforms = list(SocialPlatform.objects.filter(is_active=True).order_by('order'))
                cache.set(cache_key, platforms, 3600)  # 1시간 캐시
            except Exception:
                # 테이블이 없거나 마이그레이션 전인 경우 빈 리스트 반환
                platforms = []
        
        return platforms
    
    def get_share_platforms(self) -> List[Dict]:
        """공유 가능한 플랫폼 목록"""
        return [
            {
                'id': platform.id,
                'name': platform.name,
                'display_name': platform.display_name,
                'icon': platform.icon,
                'color': platform.color
            }
            for platform in self.platforms
        ]
    
    def create_shareable_content(self, content_type: str, title: str, 
                               description: str, url: str, 
                               user: User = None, **kwargs) -> ShareableContent:
        """공유 가능한 콘텐츠 생성"""
        
        content = ShareableContent.objects.create(
            content_type=content_type,
            title=title,
            description=description,
            url=url,
            created_by=user,
            **kwargs
        )
        
        logger.info(f"Created shareable content: {content.id} - {title}")
        return content
    
    def generate_share_url(self, platform_name: str, content: ShareableContent,
                          custom_message: str = None) -> str:
        """플랫폼별 공유 URL 생성"""
        
        try:
            platform = next(p for p in self.platforms if p.name == platform_name)
        except StopIteration:
            raise ValueError(f"Unknown platform: {platform_name}")
        
        # URL 파라미터 준비
        params = {
            'url': content.url,
            'title': content.title,
            'description': custom_message or content.description,
            'hashtags': content.hashtags
        }
        
        # 플랫폼별 URL 생성
        share_url = self._build_platform_url(platform, params)
        
        logger.info(f"Generated share URL for {platform_name}: {share_url[:100]}...")
        return share_url
    
    def _build_platform_url(self, platform: SocialPlatform, params: Dict) -> str:
        """플랫폼별 공유 URL 구성"""
        
        # URL 인코딩
        encoded_params = {k: quote(str(v)) if v else '' for k, v in params.items()}
        
        # 템플릿 기반 URL 생성
        try:
            share_url = platform.share_url_template.format(**encoded_params)
        except KeyError as e:
            logger.error(f"Invalid template for {platform.name}: missing {e}")
            # 기본 템플릿 사용
            share_url = f"{platform.share_url_template}?{urlencode(params)}"
        
        return share_url
    
    def share_academy(self, user: User, academy: Academy, platform_name: str,
                     custom_options: Dict = None) -> AcademyShare:
        """학원 정보 공유"""
        
        # 플랫폼 조회
        try:
            platform = SocialPlatform.objects.get(name=platform_name, is_active=True)
        except SocialPlatform.DoesNotExist:
            raise ValueError(f"Platform not found or inactive: {platform_name}")
        
        # 기본 옵션 설정
        options = custom_options or {}
        
        # 학원 공유 생성
        academy_share = AcademyShare.objects.create(
            user=user,
            academy=academy,
            platform=platform,
            custom_title=options.get('title', ''),
            custom_description=options.get('description', ''),
            selected_subjects=options.get('subjects', []),
            include_rating=options.get('include_rating', True),
            include_price=options.get('include_price', False),
            include_location=options.get('include_location', True),
            recommendation_reason=options.get('reason', ''),
            target_age_group=options.get('target_age', '')
        )
        
        # 공유 콘텐츠 생성
        content = self._create_academy_share_content(academy_share)
        
        # 공유 기록
        share_record = SocialShare.objects.create(
            user=user,
            platform=platform,
            content=content,
            shared_url=self.generate_share_url(platform_name, content),
            custom_message=options.get('message', '')
        )
        
        # 분석 데이터 업데이트
        self._update_analytics(platform, 'academy')
        
        logger.info(f"Academy shared: {academy.상호명} by {user.username} on {platform_name}")
        return academy_share
    
    def _create_academy_share_content(self, academy_share: AcademyShare) -> ShareableContent:
        """학원 공유를 위한 콘텐츠 생성"""
        
        academy = academy_share.academy
        
        # URL 생성 (실제 학원 상세 페이지로)
        academy_url = f"/academy/{academy.id}/"  # 실제 URL 패턴에 맞게 수정
        
        # 메타데이터 구성
        metadata = {
            'academy_id': academy.id,
            'academy_name': academy.상호명,
            'subjects': academy_share.selected_subjects,
            'location': {
                'address': academy.도로명주소 or academy.지번주소,
                'region': academy.시군구명
            }
        }
        
        # OG 태그 설정
        og_title = academy_share.get_share_title()
        og_description = academy_share.get_share_description()
        
        return ShareableContent.objects.create(
            content_type='academy',
            title=og_title,
            description=og_description,
            url=academy_url,
            metadata=metadata,
            hashtags=academy_share.get_hashtags(),
            og_title=og_title,
            og_description=og_description,
            created_by=academy_share.user
        )
    
    def get_share_statistics(self, user: User = None, 
                           days: int = 30) -> Dict:
        """공유 통계 조회"""
        
        # 기간 설정
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=days)
        
        base_query = SocialShare.objects.filter(
            shared_at__date__gte=start_date,
            shared_at__date__lte=end_date
        )
        
        if user:
            base_query = base_query.filter(user=user)
        
        # 플랫폼별 통계
        platform_stats = base_query.values('platform__display_name').annotate(
            count=Count('id'),
            clicks=Count('clicks')
        ).order_by('-count')
        
        # 콘텐츠 유형별 통계
        content_type_stats = base_query.values('content__content_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 일별 통계
        daily_stats = base_query.extra(
            select={'date': 'DATE(shared_at)'}
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': days
            },
            'total_shares': base_query.count(),
            'platform_breakdown': list(platform_stats),
            'content_type_breakdown': list(content_type_stats),
            'daily_trends': list(daily_stats)
        }
    
    def get_popular_content(self, content_type: str = None, 
                          limit: int = 10) -> List[Dict]:
        """인기 콘텐츠 조회"""
        
        query = PopularContent.objects.select_related('content')
        
        if content_type:
            query = query.filter(content__content_type=content_type)
        
        popular_items = query[:limit]
        
        return [
            {
                'content_id': item.content.id,
                'title': item.content.title,
                'content_type': item.content.content_type,
                'total_shares': item.total_shares,
                'weekly_shares': item.weekly_shares,
                'viral_score': item.viral_score,
                'url': item.content.url
            }
            for item in popular_items
        ]
    
    def get_user_share_history(self, user: User, limit: int = 20) -> List[Dict]:
        """사용자 공유 기록"""
        
        shares = SocialShare.objects.filter(user=user).select_related(
            'platform', 'content'
        ).order_by('-shared_at')[:limit]
        
        return [
            {
                'id': share.id,
                'platform': share.platform.display_name,
                'platform_icon': share.platform.icon,
                'content_title': share.content.title,
                'content_type': share.content.get_content_type_display(),
                'shared_at': share.shared_at,
                'clicks': share.clicks,
                'engagement_score': share.engagement_score
            }
            for share in shares
        ]
    
    def _update_analytics(self, platform: SocialPlatform, content_type: str):
        """분석 데이터 업데이트"""
        
        today = timezone.now().date()
        
        # 일별 분석 데이터 생성 또는 업데이트
        analytics, created = ShareAnalytics.objects.get_or_create(
            date=today,
            platform=platform,
            defaults={
                'total_shares': 0,
                'unique_users': 0,
                'academy_shares': 0,
                'comparison_shares': 0,
                'review_shares': 0
            }
        )
        
        # 카운터 증가
        analytics.total_shares = F('total_shares') + 1
        
        if content_type == 'academy':
            analytics.academy_shares = F('academy_shares') + 1
        elif content_type == 'comparison':
            analytics.comparison_shares = F('comparison_shares') + 1
        elif content_type == 'review':
            analytics.review_shares = F('review_shares') + 1
        
        analytics.save(update_fields=['total_shares', f'{content_type}_shares'])
    
    def update_popular_content_scores(self):
        """인기 콘텐츠 점수 업데이트 (주기적 실행)"""
        
        # 모든 공유 콘텐츠에 대해 점수 계산
        content_items = ShareableContent.objects.all()
        
        for content in content_items:
            # 공유 통계 계산
            shares = SocialShare.objects.filter(content=content)
            
            total_shares = shares.count()
            weekly_shares = shares.filter(
                shared_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).count()
            monthly_shares = shares.filter(
                shared_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).count()
            
            avg_engagement = shares.aggregate(
                avg=Count('engagement_score')
            )['avg'] or 0.0
            
            # 인기 콘텐츠 업데이트 또는 생성
            popular, created = PopularContent.objects.update_or_create(
                content=content,
                defaults={
                    'total_shares': total_shares,
                    'weekly_shares': weekly_shares,
                    'monthly_shares': monthly_shares,
                    'average_engagement': avg_engagement
                }
            )
            
            # 바이럴 점수 계산
            popular.calculate_viral_score()
        
        logger.info("Updated popular content scores")


# 기본 소셜 플랫폼 데이터
DEFAULT_PLATFORMS = [
    {
        'name': 'facebook',
        'display_name': '페이스북',
        'icon': 'fab fa-facebook-f',
        'color': '#1877F2',
        'share_url_template': 'https://www.facebook.com/sharer/sharer.php?u={url}&quote={title}',
        'order': 1
    },
    {
        'name': 'twitter',
        'display_name': '트위터',
        'icon': 'fab fa-twitter',
        'color': '#1DA1F2',
        'share_url_template': 'https://twitter.com/intent/tweet?url={url}&text={title}&hashtags={hashtags}',
        'order': 2
    },
    {
        'name': 'kakaotalk',
        'display_name': '카카오톡',
        'icon': 'fab fa-kickstarter',
        'color': '#FFCD00',
        'share_url_template': 'https://sharer.kakao.com/talk/friends/picker/link?url={url}&text={title}',
        'order': 3
    },
    {
        'name': 'line',
        'display_name': '라인',
        'icon': 'fab fa-line',
        'color': '#00C300',
        'share_url_template': 'https://social-plugins.line.me/lineit/share?url={url}&text={title}',
        'order': 4
    },
    {
        'name': 'linkedin',
        'display_name': '링크드인',
        'icon': 'fab fa-linkedin-in',
        'color': '#0A66C2',
        'share_url_template': 'https://www.linkedin.com/sharing/share-offsite/?url={url}&title={title}&summary={description}',
        'order': 5
    },
    {
        'name': 'telegram',
        'display_name': '텔레그램',
        'icon': 'fab fa-telegram-plane',
        'color': '#0088CC',
        'share_url_template': 'https://t.me/share/url?url={url}&text={title}',
        'order': 6
    }
]


def initialize_social_platforms():
    """기본 소셜 플랫폼 데이터 초기화"""
    
    for platform_data in DEFAULT_PLATFORMS:
        platform, created = SocialPlatform.objects.get_or_create(
            name=platform_data['name'],
            defaults=platform_data
        )
        
        if created:
            logger.info(f"Created social platform: {platform.display_name}")


# 싱글톤 서비스 인스턴스
social_service = SocialSharingService()