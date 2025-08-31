"""
데이터 분석 및 리포팅 서비스
"""

from django.db.models import Count, Avg, Sum, Q, F, Max, Min
from django.utils import timezone
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
import json
import statistics
from decimal import Decimal

try:
    from .analytics_models import (
        AnalyticsReport, UserAnalytics, AcademyAnalytics,
        RegionalAnalytics, MarketTrend, ConversionFunnel, CustomDashboard
    )
    from .academy_enhancements import AcademyViewHistory, AcademyStatistics
    from .operator_models import AcademyInquiry
    from .models import Data as Academy
except ImportError:
    pass


class AnalyticsDataService:
    """분석 데이터 수집 및 처리 서비스"""
    
    @staticmethod
    def collect_daily_user_analytics(target_date: date = None) -> Dict[str, Any]:
        """일일 사용자 분석 데이터 수집"""
        if target_date is None:
            target_date = timezone.now().date()
        
        try:
            start_datetime = timezone.datetime.combine(target_date, timezone.datetime.min.time())
            end_datetime = start_datetime + timedelta(days=1)
            
            # 세션 데이터 수집
            daily_sessions = AcademyViewHistory.objects.filter(
                viewed_at__range=(start_datetime, end_datetime)
            )
            
            # 기본 통계
            total_sessions = daily_sessions.count()
            unique_sessions = daily_sessions.values('session_id').distinct().count()
            
            # 평균 세션 시간
            avg_duration = daily_sessions.filter(
                duration__isnull=False
            ).aggregate(avg_duration=Avg('duration'))['avg_duration'] or 0
            
            # 페이지 뷰 통계
            total_pageviews = total_sessions
            unique_pageviews = unique_sessions
            
            # 트래픽 소스 분석
            organic_traffic = daily_sessions.filter(
                referrer__icontains='google'
            ).count() + daily_sessions.filter(
                referrer__icontains='naver'
            ).count()
            
            direct_traffic = daily_sessions.filter(referrer='').count()
            social_traffic = daily_sessions.filter(
                Q(referrer__icontains='facebook') |
                Q(referrer__icontains='twitter') |
                Q(referrer__icontains='instagram')
            ).count()
            
            referral_traffic = total_sessions - organic_traffic - direct_traffic - social_traffic
            
            # 디바이스 분석 (User-Agent 기반)
            mobile_keywords = ['Mobile', 'Android', 'iPhone', 'iPad']
            tablet_keywords = ['iPad', 'Tablet']
            
            mobile_sessions = daily_sessions.filter(
                user_agent__iregex=r'(' + '|'.join(mobile_keywords) + ')'
            ).exclude(
                user_agent__iregex=r'(' + '|'.join(tablet_keywords) + ')'
            )
            
            tablet_sessions = daily_sessions.filter(
                user_agent__iregex=r'(' + '|'.join(tablet_keywords) + ')'
            )
            
            mobile_users = mobile_sessions.count()
            tablet_users = tablet_sessions.count()
            desktop_users = total_sessions - mobile_users - tablet_users
            
            # 이탈률 계산 (1페이지만 보고 나간 세션)
            single_page_sessions = daily_sessions.filter(duration__lt=30).count()
            bounce_rate = (single_page_sessions / total_sessions * 100) if total_sessions > 0 else 0
            
            analytics_data = {
                'date': target_date,
                'total_users': unique_sessions,
                'new_users': unique_sessions,  # 정확한 신규/재방문 구분은 추가 로직 필요
                'returning_users': 0,
                'total_sessions': total_sessions,
                'avg_session_duration': avg_duration,
                'bounce_rate': bounce_rate,
                'total_pageviews': total_pageviews,
                'unique_pageviews': unique_pageviews,
                'avg_pages_per_session': total_pageviews / total_sessions if total_sessions > 0 else 0,
                'organic_traffic': organic_traffic,
                'direct_traffic': direct_traffic,
                'referral_traffic': referral_traffic,
                'social_traffic': social_traffic,
                'desktop_users': desktop_users,
                'mobile_users': mobile_users,
                'tablet_users': tablet_users,
            }
            
            # 데이터베이스에 저장
            UserAnalytics.objects.update_or_create(
                date=target_date,
                defaults=analytics_data
            )
            
            return analytics_data
            
        except Exception as e:
            return {
                'error': f'사용자 분석 데이터 수집 실패: {str(e)}',
                'date': target_date,
                'total_users': 0,
                'total_sessions': 0,
            }
    
    @staticmethod
    def collect_academy_analytics(academy: Academy, target_date: date = None) -> Dict[str, Any]:
        """학원별 분석 데이터 수집"""
        if target_date is None:
            target_date = timezone.now().date()
        
        try:
            start_datetime = timezone.datetime.combine(target_date, timezone.datetime.min.time())
            end_datetime = start_datetime + timedelta(days=1)
            
            # 조회 통계
            academy_views = AcademyViewHistory.objects.filter(
                academy=academy,
                viewed_at__range=(start_datetime, end_datetime)
            )
            
            views = academy_views.count()
            unique_views = academy_views.values('session_id').distinct().count()
            
            avg_view_duration = academy_views.filter(
                duration__isnull=False
            ).aggregate(avg_duration=Avg('duration'))['avg_duration'] or 0
            
            # 문의 통계
            daily_inquiries = AcademyInquiry.objects.filter(
                academy=academy,
                created_at__range=(start_datetime, end_datetime)
            ).count()
            
            # 전환율 계산
            inquiry_conversion = (daily_inquiries / views * 100) if views > 0 else 0
            
            # 학원 통계에서 북마크, 공유 수 가져오기
            stats = getattr(academy, 'statistics', None)
            bookmarks = 0
            shares = 0
            
            if stats:
                # 일일 증가분 계산 (임시로 전체 수치 사용)
                bookmarks = stats.bookmark_count or 0
                shares = stats.share_count or 0
            
            analytics_data = {
                'academy': academy,
                'date': target_date,
                'views': views,
                'unique_views': unique_views,
                'avg_view_duration': avg_view_duration,
                'bookmarks': bookmarks,
                'shares': shares,
                'inquiries': daily_inquiries,
                'conversion_rate': inquiry_conversion,
                'inquiry_conversion': inquiry_conversion,
                'top_keywords': [],  # 검색 키워드 추적은 추가 구현 필요
                'recommendation_score': stats.popularity_score if stats else 0,
                'popularity_rank': stats.local_rank if stats else None,
            }
            
            # 데이터베이스에 저장
            AcademyAnalytics.objects.update_or_create(
                academy=academy,
                date=target_date,
                defaults=analytics_data
            )
            
            return analytics_data
            
        except Exception as e:
            return {
                'error': f'학원 분석 데이터 수집 실패: {str(e)}',
                'academy': academy,
                'date': target_date,
                'views': 0,
                'inquiries': 0,
            }
    
    @staticmethod
    def collect_regional_analytics(region_sido: str, region_sigungu: str, target_date: date = None) -> Dict[str, Any]:
        """지역별 분석 데이터 수집"""
        if target_date is None:
            target_date = timezone.now().date()
        
        try:
            # 해당 지역 학원들
            regional_academies = Academy.objects.filter(
                시도명=region_sido,
                시군구명=region_sigungu
            )
            
            total_academies = regional_academies.count()
            
            # 활성 학원 (최근 30일 내 조회된 학원)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            active_academy_ids = AcademyViewHistory.objects.filter(
                academy__in=regional_academies,
                viewed_at__gte=thirty_days_ago
            ).values('academy_id').distinct()
            
            active_academies = active_academy_ids.count()
            
            # 조회 통계
            start_datetime = timezone.datetime.combine(target_date, timezone.datetime.min.time())
            end_datetime = start_datetime + timedelta(days=1)
            
            daily_views = AcademyViewHistory.objects.filter(
                academy__in=regional_academies,
                viewed_at__range=(start_datetime, end_datetime)
            )
            
            total_views = daily_views.count()
            unique_visitors = daily_views.values('session_id').distinct().count()
            
            # 평균 평점
            avg_rating = regional_academies.exclude(
                별점__isnull=True
            ).aggregate(
                avg_rating=Avg('별점')
            )['avg_rating'] or 0
            
            # 수강료 통계
            tuition_stats = regional_academies.exclude(
                수강료_평균__isnull=True
            ).exclude(
                수강료_평균=''
            ).aggregate(
                avg_tuition=Avg('수강료_평균'),
                min_tuition=Min('수강료_평균'),
                max_tuition=Max('수강료_평균')
            )
            
            # 과목별 분포
            subject_distribution = {}
            subject_fields = [
                ('과목_종합', '종합'),
                ('과목_수학', '수학'),
                ('과목_영어', '영어'),
                ('과목_과학', '과학'),
                ('과목_외국어', '외국어'),
                ('과목_예체능', '예체능'),
                ('과목_컴퓨터', '컴퓨터'),
                ('과목_논술', '논술'),
                ('과목_기타', '기타'),
            ]
            
            for field, label in subject_fields:
                count = regional_academies.filter(**{field: True}).count()
                if count > 0:
                    subject_distribution[label] = count
            
            # 경쟁 지수 (학원 밀도)
            competition_index = total_academies / max(1, unique_visitors) * 100
            market_saturation = min(100, total_academies * 10)  # 임시 공식
            
            analytics_data = {
                'region_sido': region_sido,
                'region_sigungu': region_sigungu,
                'date': target_date,
                'total_academies': total_academies,
                'active_academies': active_academies,
                'total_views': total_views,
                'unique_visitors': unique_visitors,
                'avg_rating': round(avg_rating, 2),
                'avg_tuition': tuition_stats.get('avg_tuition') or 0,
                'tuition_range_min': tuition_stats.get('min_tuition'),
                'tuition_range_max': tuition_stats.get('max_tuition'),
                'subject_distribution': subject_distribution,
                'competition_index': round(competition_index, 2),
                'market_saturation': round(market_saturation, 2),
            }
            
            # 데이터베이스에 저장
            RegionalAnalytics.objects.update_or_create(
                region_sido=region_sido,
                region_sigungu=region_sigungu,
                date=target_date,
                defaults=analytics_data
            )
            
            return analytics_data
            
        except Exception as e:
            return {
                'error': f'지역 분석 데이터 수집 실패: {str(e)}',
                'region_sido': region_sido,
                'region_sigungu': region_sigungu,
                'date': target_date,
            }


class AnalyticsReportService:
    """분석 리포트 생성 서비스"""
    
    @staticmethod
    def generate_traffic_report(start_date: date, end_date: date) -> Dict[str, Any]:
        """트래픽 분석 리포트 생성"""
        try:
            # 기간 내 사용자 분석 데이터
            user_analytics = UserAnalytics.objects.filter(
                date__range=(start_date, end_date)
            ).order_by('date')
            
            if not user_analytics.exists():
                return {
                    'error': '해당 기간의 데이터가 없습니다.',
                    'start_date': start_date,
                    'end_date': end_date,
                }
            
            # 집계 데이터
            total_data = user_analytics.aggregate(
                total_users=Sum('total_users'),
                total_sessions=Sum('total_sessions'),
                total_pageviews=Sum('total_pageviews'),
                avg_session_duration=Avg('avg_session_duration'),
                avg_bounce_rate=Avg('bounce_rate'),
            )
            
            # 일별 데이터
            daily_data = [
                {
                    'date': item.date.isoformat(),
                    'users': item.total_users,
                    'sessions': item.total_sessions,
                    'pageviews': item.total_pageviews,
                    'bounce_rate': item.bounce_rate,
                }
                for item in user_analytics
            ]
            
            # 트래픽 소스 분석
            traffic_sources = user_analytics.aggregate(
                organic=Sum('organic_traffic'),
                direct=Sum('direct_traffic'),
                referral=Sum('referral_traffic'),
                social=Sum('social_traffic'),
            )
            
            # 디바이스 분석
            device_data = user_analytics.aggregate(
                desktop=Sum('desktop_users'),
                mobile=Sum('mobile_users'),
                tablet=Sum('tablet_users'),
            )
            
            # 인사이트 생성
            insights = []
            
            # 트렌드 분석
            if len(daily_data) >= 7:
                recent_week = daily_data[-7:]
                previous_week = daily_data[-14:-7] if len(daily_data) >= 14 else []
                
                if previous_week:
                    recent_avg = statistics.mean([d['users'] for d in recent_week])
                    previous_avg = statistics.mean([d['users'] for d in previous_week])
                    
                    if recent_avg > previous_avg * 1.1:
                        insights.append("최근 일주일 동안 사용자 수가 10% 이상 증가했습니다.")
                    elif recent_avg < previous_avg * 0.9:
                        insights.append("최근 일주일 동안 사용자 수가 10% 이상 감소했습니다.")
            
            # 이탈률 분석
            avg_bounce_rate = total_data['avg_bounce_rate']
            if avg_bounce_rate > 70:
                insights.append("이탈률이 높습니다. 랜딩 페이지 개선을 고려해보세요.")
            elif avg_bounce_rate < 40:
                insights.append("이탈률이 낮아 사용자 참여도가 높습니다.")
            
            # 모바일 사용률
            total_device_users = sum(device_data.values())
            if total_device_users > 0:
                mobile_rate = (device_data['mobile'] / total_device_users) * 100
                if mobile_rate > 60:
                    insights.append("모바일 사용자가 60% 이상입니다. 모바일 최적화가 중요합니다.")
            
            # 추천사항
            recommendations = []
            
            if avg_bounce_rate > 60:
                recommendations.append("사용자 경험 개선을 통해 이탈률을 낮춰보세요.")
            
            if traffic_sources['organic'] / sum(traffic_sources.values()) < 0.3:
                recommendations.append("SEO 최적화를 통해 자연 검색 유입을 늘려보세요.")
            
            report_data = {
                'summary': f"{start_date}부터 {end_date}까지 총 {total_data['total_users']:,}명의 사용자가 {total_data['total_sessions']:,}개의 세션을 생성했습니다.",
                'total_stats': total_data,
                'daily_data': daily_data,
                'traffic_sources': traffic_sources,
                'device_data': device_data,
                'insights': insights,
                'recommendations': recommendations,
            }
            
            return report_data
            
        except Exception as e:
            return {
                'error': f'트래픽 리포트 생성 실패: {str(e)}',
                'start_date': start_date,
                'end_date': end_date,
            }
    
    @staticmethod
    def generate_academy_performance_report(academy: Academy, start_date: date, end_date: date) -> Dict[str, Any]:
        """학원 성과 분석 리포트 생성"""
        try:
            # 기간 내 학원 분석 데이터
            academy_analytics = AcademyAnalytics.objects.filter(
                academy=academy,
                date__range=(start_date, end_date)
            ).order_by('date')
            
            if not academy_analytics.exists():
                return {
                    'error': '해당 기간의 데이터가 없습니다.',
                    'academy': academy.상호명,
                    'start_date': start_date,
                    'end_date': end_date,
                }
            
            # 집계 데이터
            total_data = academy_analytics.aggregate(
                total_views=Sum('views'),
                total_unique_views=Sum('unique_views'),
                total_inquiries=Sum('inquiries'),
                avg_conversion_rate=Avg('conversion_rate'),
                avg_view_duration=Avg('avg_view_duration'),
            )
            
            # 일별 데이터
            daily_data = [
                {
                    'date': item.date.isoformat(),
                    'views': item.views,
                    'inquiries': item.inquiries,
                    'conversion_rate': item.conversion_rate,
                }
                for item in academy_analytics
            ]
            
            # 인사이트 생성
            insights = []
            
            # 성과 트렌드
            if len(daily_data) >= 7:
                recent_views = sum([d['views'] for d in daily_data[-7:]])
                recent_inquiries = sum([d['inquiries'] for d in daily_data[-7:]])
                
                if recent_inquiries > 0:
                    insights.append(f"최근 일주일 동안 {recent_inquiries}건의 문의가 접수되었습니다.")
                
                if recent_views > 100:
                    insights.append("높은 관심을 받고 있는 학원입니다.")
            
            # 전환율 분석
            avg_conversion = total_data['avg_conversion_rate']
            if avg_conversion > 5:
                insights.append("문의 전환율이 우수합니다.")
            elif avg_conversion < 1:
                insights.append("문의 전환율이 낮습니다. 학원 정보나 사진 개선을 고려해보세요.")
            
            # 추천사항
            recommendations = []
            
            if avg_conversion < 2:
                recommendations.append("학원 소개글과 사진을 더 매력적으로 업데이트해보세요.")
                recommendations.append("연락처와 위치 정보를 명확하게 표시해보세요.")
            
            if total_data['total_views'] < 50:
                recommendations.append("검색 노출을 늘리기 위해 키워드를 최적화해보세요.")
            
            report_data = {
                'academy': academy.상호명,
                'summary': f"{start_date}부터 {end_date}까지 {total_data['total_views']:,}회 조회되고 {total_data['total_inquiries']}건의 문의가 접수되었습니다.",
                'total_stats': total_data,
                'daily_data': daily_data,
                'insights': insights,
                'recommendations': recommendations,
            }
            
            return report_data
            
        except Exception as e:
            return {
                'error': f'학원 성과 리포트 생성 실패: {str(e)}',
                'academy': academy.상호명 if academy else 'Unknown',
                'start_date': start_date,
                'end_date': end_date,
            }
    
    @staticmethod
    def generate_market_analysis_report(region_sido: str = None, region_sigungu: str = None) -> Dict[str, Any]:
        """시장 분석 리포트 생성"""
        try:
            # 최근 30일 데이터 기준
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
            
            # 지역 필터링
            if region_sido and region_sigungu:
                regional_data = RegionalAnalytics.objects.filter(
                    region_sido=region_sido,
                    region_sigungu=region_sigungu,
                    date__range=(start_date, end_date)
                ).order_by('-date')
                
                title_region = f"{region_sido} {region_sigungu}"
            else:
                # 전국 데이터
                regional_data = RegionalAnalytics.objects.filter(
                    date__range=(start_date, end_date)
                ).order_by('-date')
                
                title_region = "전국"
            
            if not regional_data.exists():
                return {
                    'error': '해당 지역의 분석 데이터가 없습니다.',
                    'region': title_region,
                    'start_date': start_date,
                    'end_date': end_date,
                }
            
            # 최신 데이터 선택
            latest_data = regional_data.first()
            
            # 과목별 인기도 분석
            subject_popularity = latest_data.subject_distribution
            most_popular_subject = max(subject_popularity.items(), key=lambda x: x[1]) if subject_popularity else None
            
            # 시장 포화도 분석
            competition_level = "높음" if latest_data.competition_index > 50 else "보통" if latest_data.competition_index > 20 else "낮음"
            
            # 인사이트 생성
            insights = []
            
            if most_popular_subject:
                insights.append(f"가장 인기 있는 과목은 {most_popular_subject[0]}입니다 ({most_popular_subject[1]}개 학원).")
            
            insights.append(f"시장 경쟁 수준은 {competition_level}입니다.")
            
            if latest_data.avg_rating > 4.0:
                insights.append("지역 내 학원들의 평균 만족도가 높습니다.")
            
            # 추천사항
            recommendations = []
            
            if latest_data.competition_index > 70:
                recommendations.append("경쟁이 치열한 지역입니다. 차별화된 서비스나 전문 과목으로 승부하세요.")
            
            if latest_data.avg_tuition > 0:
                recommendations.append(f"지역 평균 수강료는 {latest_data.avg_tuition:,}원입니다. 가격 경쟁력을 고려하세요.")
            
            report_data = {
                'region': title_region,
                'summary': f"{title_region} 지역에는 총 {latest_data.total_academies}개의 학원이 있으며, 평균 평점은 {latest_data.avg_rating}점입니다.",
                'market_stats': {
                    'total_academies': latest_data.total_academies,
                    'active_academies': latest_data.active_academies,
                    'avg_rating': latest_data.avg_rating,
                    'avg_tuition': latest_data.avg_tuition,
                    'competition_index': latest_data.competition_index,
                    'market_saturation': latest_data.market_saturation,
                },
                'subject_popularity': subject_popularity,
                'insights': insights,
                'recommendations': recommendations,
            }
            
            return report_data
            
        except Exception as e:
            return {
                'error': f'시장 분석 리포트 생성 실패: {str(e)}',
                'region': title_region if 'title_region' in locals() else 'Unknown',
            }