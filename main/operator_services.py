"""
학원 운영자 대시보드 서비스
"""

from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import math

try:
    from .operator_models import (
        AcademyOwner, OperatorDashboardSettings, AcademyInquiry, 
        AcademyPromotion, RevenueTracking, CompetitorAnalysis
    )
    from .academy_enhancements import AcademyStatistics, AcademyViewHistory
    from .models import Data as Academy
except ImportError:
    # Handle import errors during migrations
    pass


class OperatorDashboardService:
    """운영자 대시보드 핵심 서비스"""
    
    @staticmethod
    def get_academy_overview(academy: Academy, user=None) -> Dict[str, Any]:
        """학원 개요 정보 조회"""
        try:
            # 기본 통계
            stats = getattr(academy, 'statistics', None)
            if not stats:
                from .academy_enhancements import AcademyStatistics
                stats, _ = AcademyStatistics.objects.get_or_create(academy=academy)
            
            # 최근 30일 방문자 수
            thirty_days_ago = timezone.now() - timedelta(days=30)
            recent_views = AcademyViewHistory.objects.filter(
                academy=academy,
                viewed_at__gte=thirty_days_ago
            ).count()
            
            # 미처리 문의 수
            pending_inquiries = AcademyInquiry.objects.filter(
                academy=academy,
                status__in=['new', 'in_progress']
            ).count()
            
            # 활성 프로모션 수
            active_promotions = AcademyPromotion.objects.filter(
                academy=academy,
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            ).count()
            
            return {
                'academy': academy,
                'statistics': {
                    'total_views': stats.view_count,
                    'monthly_views': stats.monthly_views,
                    'recent_views_30d': recent_views,
                    'bookmark_count': stats.bookmark_count,
                    'average_rating': stats.average_rating,
                    'popularity_score': stats.popularity_score,
                    'local_rank': stats.local_rank,
                    'category_rank': stats.category_rank,
                },
                'management': {
                    'pending_inquiries': pending_inquiries,
                    'active_promotions': active_promotions,
                },
                'last_updated': stats.last_updated,
            }
        except Exception as e:
            return {
                'error': f'개요 정보 조회 실패: {str(e)}',
                'academy': academy,
                'statistics': {},
                'management': {},
                'last_updated': timezone.now(),
            }
    
    @staticmethod
    def get_visitor_analytics(academy: Academy, days: int = 30) -> Dict[str, Any]:
        """방문자 분석 데이터"""
        try:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            # 일별 방문자 수
            daily_views = AcademyViewHistory.objects.filter(
                academy=academy,
                viewed_at__gte=start_date
            ).extra({
                'date': "date(viewed_at)"
            }).values('date').annotate(
                count=Count('id')
            ).order_by('date')
            
            # 시간대별 방문 패턴
            hourly_pattern = AcademyViewHistory.objects.filter(
                academy=academy,
                viewed_at__gte=start_date
            ).extra({
                'hour': "strftime('%%H', viewed_at)"
            }).values('hour').annotate(
                count=Count('id')
            ).order_by('hour')
            
            # 방문 경로 분석
            referrer_analysis = AcademyViewHistory.objects.filter(
                academy=academy,
                viewed_at__gte=start_date
            ).exclude(referrer='').values('referrer').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            # 평균 체류 시간
            avg_duration = AcademyViewHistory.objects.filter(
                academy=academy,
                viewed_at__gte=start_date,
                duration__isnull=False
            ).aggregate(avg_duration=Avg('duration'))
            
            # 재방문자 비율
            total_visits = AcademyViewHistory.objects.filter(
                academy=academy,
                viewed_at__gte=start_date
            ).count()
            
            unique_visitors = AcademyViewHistory.objects.filter(
                academy=academy,
                viewed_at__gte=start_date
            ).values('session_id').distinct().count()
            
            return_visitor_rate = 0
            if unique_visitors > 0:
                return_visitor_rate = ((total_visits - unique_visitors) / total_visits) * 100
            
            return {
                'period': f'{days}일',
                'total_visits': total_visits,
                'unique_visitors': unique_visitors,
                'return_visitor_rate': round(return_visitor_rate, 1),
                'avg_duration': avg_duration['avg_duration'] or 0,
                'daily_views': list(daily_views),
                'hourly_pattern': list(hourly_pattern),
                'top_referrers': list(referrer_analysis),
            }
        except Exception as e:
            return {
                'error': f'방문자 분석 실패: {str(e)}',
                'period': f'{days}일',
                'total_visits': 0,
                'unique_visitors': 0,
                'return_visitor_rate': 0,
                'avg_duration': 0,
                'daily_views': [],
                'hourly_pattern': [],
                'top_referrers': [],
            }
    
    @staticmethod
    def get_inquiry_summary(academy: Academy) -> Dict[str, Any]:
        """문의 현황 요약"""
        try:
            # 상태별 문의 수
            status_summary = AcademyInquiry.objects.filter(
                academy=academy
            ).values('status').annotate(
                count=Count('id')
            ).order_by('status')
            
            # 유형별 문의 수 (최근 30일)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            type_summary = AcademyInquiry.objects.filter(
                academy=academy,
                created_at__gte=thirty_days_ago
            ).values('inquiry_type').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # 응답 시간 통계
            response_times = AcademyInquiry.objects.filter(
                academy=academy,
                status='answered',
                responded_at__isnull=False
            ).extra(
                select={
                    'response_time_hours': "(julianday(responded_at) - julianday(created_at)) * 24"
                }
            ).values('response_time_hours')
            
            avg_response_time = 0
            if response_times:
                total_time = sum(float(r['response_time_hours']) for r in response_times)
                avg_response_time = total_time / len(response_times)
            
            # 긴급 처리 필요한 문의
            overdue_inquiries = AcademyInquiry.objects.filter(
                academy=academy,
                status__in=['new', 'in_progress'],
                created_at__lt=timezone.now() - timedelta(hours=48)
            ).count()
            
            # 최근 문의들
            recent_inquiries = AcademyInquiry.objects.filter(
                academy=academy
            ).order_by('-created_at')[:5]
            
            return {
                'status_summary': {item['status']: item['count'] for item in status_summary},
                'type_summary': list(type_summary),
                'avg_response_time_hours': round(avg_response_time, 1),
                'overdue_count': overdue_inquiries,
                'recent_inquiries': recent_inquiries,
                'total_count': sum(item['count'] for item in status_summary),
            }
        except Exception as e:
            return {
                'error': f'문의 현황 조회 실패: {str(e)}',
                'status_summary': {},
                'type_summary': [],
                'avg_response_time_hours': 0,
                'overdue_count': 0,
                'recent_inquiries': [],
                'total_count': 0,
            }
    
    @staticmethod
    def get_promotion_performance(academy: Academy) -> Dict[str, Any]:
        """프로모션 성과 분석"""
        try:
            # 활성 프로모션
            active_promotions = AcademyPromotion.objects.filter(
                academy=academy,
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            ).order_by('-is_featured', '-created_at')
            
            # 종료된 프로모션 성과
            ended_promotions = AcademyPromotion.objects.filter(
                academy=academy,
                end_date__lt=timezone.now()
            ).order_by('-end_date')[:5]
            
            # 프로모션 유형별 통계
            type_stats = AcademyPromotion.objects.filter(
                academy=academy
            ).values('promotion_type').annotate(
                count=Count('id'),
                total_participants=Sum('current_participants')
            ).order_by('-count')
            
            return {
                'active_promotions': active_promotions,
                'ended_promotions': ended_promotions,
                'type_statistics': list(type_stats),
                'total_active': active_promotions.count(),
                'total_ended': ended_promotions.count(),
            }
        except Exception as e:
            return {
                'error': f'프로모션 성과 조회 실패: {str(e)}',
                'active_promotions': [],
                'ended_promotions': [],
                'type_statistics': [],
                'total_active': 0,
                'total_ended': 0,
            }
    
    @staticmethod
    def get_competitor_insights(academy: Academy, radius_km: float = 3.0) -> Dict[str, Any]:
        """경쟁사 인사이트"""
        try:
            if not academy.경도 or not academy.위도:
                return {
                    'error': '학원 위치 정보가 필요합니다',
                    'nearby_competitors': [],
                    'market_analysis': {},
                }
            
            # 주변 경쟁사 찾기 (Haversine 공식 사용)
            # SQLite의 경우 대략적인 계산 사용
            lat_diff = radius_km / 111.0  # 대략 1도 = 111km
            lng_diff = radius_km / (111.0 * math.cos(math.radians(academy.위도)))
            
            nearby_academies = Academy.objects.filter(
                위도__range=(academy.위도 - lat_diff, academy.위도 + lat_diff),
                경도__range=(academy.경도 - lng_diff, academy.경도 + lng_diff)
            ).exclude(id=academy.id)
            
            # 같은 과목을 가르치는 경쟁사 필터링
            subject_filters = []
            if academy.과목_수학:
                subject_filters.append(Q(과목_수학=True))
            if academy.과목_영어:
                subject_filters.append(Q(과목_영어=True))
            if academy.과목_과학:
                subject_filters.append(Q(과목_과학=True))
            
            if subject_filters:
                competitors_query = Q()
                for filter_q in subject_filters:
                    competitors_query |= filter_q
                nearby_competitors = nearby_academies.filter(competitors_query)
            else:
                nearby_competitors = nearby_academies
            
            # 시장 분석
            competitor_count = nearby_competitors.count()
            avg_rating = nearby_competitors.aggregate(
                avg_rating=Avg('별점')
            )['avg_rating'] or 0
            
            # 가격 비교
            from django.db.models import Min, Max
            competitor_fees = nearby_competitors.filter(
                수강료_평균__isnull=False
            ).aggregate(
                avg_fee=Avg('수강료_평균'),
                min_fee=Min('수강료_평균'),
                max_fee=Max('수강료_평균')
            )
            
            return {
                'nearby_competitors': nearby_competitors[:10],
                'market_analysis': {
                    'competitor_count': competitor_count,
                    'market_avg_rating': round(avg_rating, 2),
                    'market_avg_fee': competitor_fees.get('avg_fee'),
                    'market_fee_range': {
                        'min': competitor_fees.get('min_fee'),
                        'max': competitor_fees.get('max_fee'),
                    },
                    'your_position': {
                        'rating_rank': 'N/A',  # 추후 개선
                        'price_rank': 'N/A',   # 추후 개선
                    }
                },
                'radius_km': radius_km,
            }
        except Exception as e:
            return {
                'error': f'경쟁사 분석 실패: {str(e)}',
                'nearby_competitors': [],
                'market_analysis': {},
                'radius_km': radius_km,
            }
    
    @staticmethod
    def generate_weekly_report(academy: Academy) -> Dict[str, Any]:
        """주간 리포트 생성"""
        try:
            week_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)
            week_end = timezone.now()
            
            # 주간 방문자 통계
            weekly_visits = AcademyViewHistory.objects.filter(
                academy=academy,
                viewed_at__range=(week_start, week_end)
            ).count()
            
            # 이전 주와 비교
            prev_week_start = week_start - timedelta(days=7)
            prev_weekly_visits = AcademyViewHistory.objects.filter(
                academy=academy,
                viewed_at__range=(prev_week_start, week_start)
            ).count()
            
            visit_change = 0
            if prev_weekly_visits > 0:
                visit_change = ((weekly_visits - prev_weekly_visits) / prev_weekly_visits) * 100
            
            # 주간 문의 통계
            weekly_inquiries = AcademyInquiry.objects.filter(
                academy=academy,
                created_at__range=(week_start, week_end)
            ).count()
            
            # 주간 프로모션 성과
            active_promotions_week = AcademyPromotion.objects.filter(
                academy=academy,
                start_date__lte=week_end,
                end_date__gte=week_start,
                is_active=True
            ).count()
            
            return {
                'period': {
                    'start': week_start.date(),
                    'end': week_end.date(),
                },
                'visits': {
                    'total': weekly_visits,
                    'change_percent': round(visit_change, 1),
                    'trend': 'up' if visit_change > 0 else 'down' if visit_change < 0 else 'stable',
                },
                'inquiries': {
                    'total': weekly_inquiries,
                    'daily_average': round(weekly_inquiries / 7, 1),
                },
                'promotions': {
                    'active_count': active_promotions_week,
                },
                'generated_at': timezone.now(),
            }
        except Exception as e:
            return {
                'error': f'주간 리포트 생성 실패: {str(e)}',
                'period': {'start': None, 'end': None},
                'visits': {'total': 0, 'change_percent': 0, 'trend': 'stable'},
                'inquiries': {'total': 0, 'daily_average': 0},
                'promotions': {'active_count': 0},
                'generated_at': timezone.now(),
            }


class OperatorPermissionService:
    """운영자 권한 관리 서비스"""
    
    @staticmethod
    def get_user_academies(user) -> List[Academy]:
        """사용자가 관리하는 학원 목록 조회"""
        try:
            owner_records = AcademyOwner.objects.filter(
                user=user,
                is_verified=True
            ).select_related('academy')
            return [owner.academy for owner in owner_records]
        except:
            return []
    
    @staticmethod
    def can_manage_academy(user, academy: Academy) -> bool:
        """학원 관리 권한 확인"""
        try:
            return AcademyOwner.objects.filter(
                user=user,
                academy=academy,
                is_verified=True
            ).exists()
        except:
            return False
    
    @staticmethod
    def get_user_permissions(user, academy: Academy) -> Dict[str, bool]:
        """사용자의 학원별 세부 권한 조회"""
        try:
            owner = AcademyOwner.objects.get(
                user=user,
                academy=academy,
                is_verified=True
            )
            return {
                'can_edit_info': owner.can_edit_info,
                'can_view_analytics': owner.can_view_analytics,
                'can_manage_content': owner.can_manage_content,
                'can_respond_reviews': owner.can_respond_reviews,
                'role': owner.role,
            }
        except AcademyOwner.DoesNotExist:
            return {
                'can_edit_info': False,
                'can_view_analytics': False,
                'can_manage_content': False,
                'can_respond_reviews': False,
                'role': None,
            }
        except:
            return {
                'can_edit_info': False,
                'can_view_analytics': False,
                'can_manage_content': False,
                'can_respond_reviews': False,
                'role': None,
            }