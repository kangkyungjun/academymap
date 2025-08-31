"""
데이터 분석 및 리포팅 Views
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import datetime, date, timedelta
import json
import csv

try:
    from .analytics_models import (
        AnalyticsReport, UserAnalytics, AcademyAnalytics, 
        RegionalAnalytics, MarketTrend, ConversionFunnel, CustomDashboard
    )
    from .analytics_services import AnalyticsDataService, AnalyticsReportService
    from .models import Data as Academy
except ImportError:
    # 마이그레이션 중이거나 모델이 아직 생성되지 않은 경우
    pass

@login_required
def analytics_dashboard(request):
    """분석 대시보드 메인 페이지"""
    try:
        context = {
            'page_title': '데이터 분석 대시보드',
            'total_reports': AnalyticsReport.objects.count(),
            'recent_reports': AnalyticsReport.objects.filter(
                generated_by=request.user
            ).order_by('-generated_at')[:5],
            'user_dashboards': CustomDashboard.objects.filter(
                user=request.user
            ).order_by('-is_default', 'name'),
        }
        
        # 최신 통계 정보
        today = timezone.now().date()
        context.update({
            'today_users': UserAnalytics.objects.filter(date=today).first(),
            'today_academies': AcademyAnalytics.objects.filter(date=today).count(),
            'active_trends': MarketTrend.objects.filter(
                date__gte=today - timedelta(days=7)
            ).count(),
        })
        
        return render(request, 'main/analytics/dashboard.html', context)
    except Exception as e:
        messages.error(request, f'대시보드 로드 중 오류가 발생했습니다: {e}')
        return redirect('main:index')

@login_required
def analytics_reports(request):
    """분석 리포트 목록 및 관리"""
    try:
        reports = AnalyticsReport.objects.all().order_by('-generated_at')
        
        # 필터링
        report_type = request.GET.get('type')
        category = request.GET.get('category')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if report_type:
            reports = reports.filter(report_type=report_type)
        if category:
            reports = reports.filter(category=category)
        if date_from:
            reports = reports.filter(start_date__gte=date_from)
        if date_to:
            reports = reports.filter(end_date__lte=date_to)
        
        # 페이지네이션
        paginator = Paginator(reports, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_title': '분석 리포트',
            'page_obj': page_obj,
            'report_types': AnalyticsReport.REPORT_TYPE_CHOICES,
            'categories': AnalyticsReport.REPORT_CATEGORY_CHOICES,
            'current_filters': {
                'type': report_type,
                'category': category,
                'date_from': date_from,
                'date_to': date_to,
            }
        }
        
        return render(request, 'main/analytics/reports.html', context)
    except Exception as e:
        messages.error(request, f'리포트 목록 로드 중 오류가 발생했습니다: {e}')
        return redirect('main:analytics_dashboard')

@login_required
def analytics_report_detail(request, report_id):
    """분석 리포트 상세 조회"""
    try:
        report = get_object_or_404(AnalyticsReport, id=report_id)
        
        # 권한 확인 (공개 리포트가 아닌 경우)
        if not report.is_public and report.generated_by != request.user:
            messages.error(request, '해당 리포트에 접근할 권한이 없습니다.')
            return redirect('main:analytics_reports')
        
        context = {
            'page_title': f'리포트: {report.title}',
            'report': report,
        }
        
        return render(request, 'main/analytics/report_detail.html', context)
    except Exception as e:
        messages.error(request, f'리포트 조회 중 오류가 발생했습니다: {e}')
        return redirect('main:analytics_reports')

@login_required
@require_http_methods(['GET', 'POST'])
def analytics_report_create(request):
    """새 분석 리포트 생성"""
    if request.method == 'GET':
        context = {
            'page_title': '새 리포트 생성',
            'report_types': AnalyticsReport.REPORT_TYPE_CHOICES,
            'categories': AnalyticsReport.REPORT_CATEGORY_CHOICES,
        }
        return render(request, 'main/analytics/report_create.html', context)
    
    try:
        # 리포트 데이터 수집
        title = request.POST.get('title')
        report_type = request.POST.get('report_type')
        category = request.POST.get('category')
        start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date()
        is_public = request.POST.get('is_public') == 'on'
        
        # 리포트 서비스를 통한 생성
        service = AnalyticsReportService()
        report = service.generate_report(
            report_type=report_type,
            category=category,
            start_date=start_date,
            end_date=end_date,
            title=title,
            generated_by=request.user,
            is_public=is_public
        )
        
        messages.success(request, f'리포트 "{title}"가 성공적으로 생성되었습니다.')
        return redirect('main:analytics_report_detail', report_id=report.id)
        
    except Exception as e:
        messages.error(request, f'리포트 생성 중 오류가 발생했습니다: {e}')
        return redirect('main:analytics_report_create')

@login_required
def academy_analytics(request, academy_id):
    """개별 학원 분석 페이지"""
    try:
        academy = get_object_or_404(Academy, id=academy_id)
        
        # 최근 30일간의 분석 데이터
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        analytics_data = AcademyAnalytics.objects.filter(
            academy=academy,
            date__range=(start_date, end_date)
        ).order_by('date')
        
        # 통계 집계
        total_views = sum(data.views for data in analytics_data)
        total_unique_views = sum(data.unique_views for data in analytics_data)
        avg_rating = analytics_data.aggregate(avg_rating=Avg('recommendation_score'))['avg_rating'] or 0
        
        context = {
            'page_title': f'{academy.상호명} 분석',
            'academy': academy,
            'analytics_data': analytics_data,
            'stats': {
                'total_views': total_views,
                'total_unique_views': total_unique_views,
                'avg_rating': round(avg_rating, 2),
                'data_points': len(analytics_data),
            },
            'chart_data': {
                'dates': [data.date.strftime('%Y-%m-%d') for data in analytics_data],
                'views': [data.views for data in analytics_data],
                'unique_views': [data.unique_views for data in analytics_data],
            }
        }
        
        return render(request, 'main/analytics/academy_analytics.html', context)
    except Exception as e:
        messages.error(request, f'학원 분석 조회 중 오류가 발생했습니다: {e}')
        return redirect('main:index')

@login_required
def regional_analytics(request):
    """지역별 분석 페이지"""
    try:
        # 최신 지역 분석 데이터
        latest_date = RegionalAnalytics.objects.aggregate(
            max_date=models.Max('date')
        )['max_date']
        
        if not latest_date:
            context = {
                'page_title': '지역별 분석',
                'no_data': True,
                'message': '지역별 분석 데이터가 없습니다.'
            }
            return render(request, 'main/analytics/regional_analytics.html', context)
        
        regional_data = RegionalAnalytics.objects.filter(
            date=latest_date
        ).order_by('region_sido', 'region_sigungu')
        
        # 시도별 집계
        sido_stats = {}
        for data in regional_data:
            if data.region_sido not in sido_stats:
                sido_stats[data.region_sido] = {
                    'total_academies': 0,
                    'total_views': 0,
                    'avg_rating': 0,
                    'regions': []
                }
            sido_stats[data.region_sido]['total_academies'] += data.total_academies
            sido_stats[data.region_sido]['total_views'] += data.total_views
            sido_stats[data.region_sido]['regions'].append(data)
        
        # 평균 평점 계산
        for sido, stats in sido_stats.items():
            if stats['regions']:
                stats['avg_rating'] = sum(r.avg_rating for r in stats['regions']) / len(stats['regions'])
        
        context = {
            'page_title': '지역별 분석',
            'latest_date': latest_date,
            'regional_data': regional_data,
            'sido_stats': sido_stats,
        }
        
        return render(request, 'main/analytics/regional_analytics.html', context)
    except Exception as e:
        messages.error(request, f'지역별 분석 조회 중 오류가 발생했습니다: {e}')
        return redirect('main:analytics_dashboard')

@login_required
def market_trends(request):
    """시장 트렌드 분석 페이지"""
    try:
        # 최근 30일간의 트렌드 데이터
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        trends = MarketTrend.objects.filter(
            date__range=(start_date, end_date)
        ).order_by('-date', 'trend_type')
        
        # 트렌드 유형별 그룹화
        trend_groups = {}
        for trend in trends:
            if trend.trend_type not in trend_groups:
                trend_groups[trend.trend_type] = []
            trend_groups[trend.trend_type].append(trend)
        
        context = {
            'page_title': '시장 트렌드',
            'trend_groups': trend_groups,
            'trend_types': MarketTrend.TREND_TYPE_CHOICES,
            'date_range': {
                'start': start_date,
                'end': end_date
            }
        }
        
        return render(request, 'main/analytics/market_trends.html', context)
    except Exception as e:
        messages.error(request, f'시장 트렌드 조회 중 오류가 발생했습니다: {e}')
        return redirect('main:analytics_dashboard')

@login_required
def conversion_funnel(request):
    """전환 퍼널 분석 페이지"""
    try:
        # 최근 30일간의 퍼널 데이터
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        funnel_data = ConversionFunnel.objects.filter(
            date__range=(start_date, end_date)
        ).order_by('date')
        
        # 전체 통계 계산
        if funnel_data:
            total_visitors = sum(data.stage_1_visitors for data in funnel_data)
            total_searches = sum(data.stage_2_search for data in funnel_data)
            total_inquiries = sum(data.stage_5_inquiry for data in funnel_data)
            
            overall_conversion = (total_inquiries / total_visitors * 100) if total_visitors > 0 else 0
        else:
            total_visitors = total_searches = total_inquiries = overall_conversion = 0
        
        context = {
            'page_title': '전환 퍼널 분석',
            'funnel_data': funnel_data,
            'stats': {
                'total_visitors': total_visitors,
                'total_searches': total_searches,
                'total_inquiries': total_inquiries,
                'overall_conversion': round(overall_conversion, 2)
            },
            'chart_data': {
                'dates': [data.date.strftime('%Y-%m-%d') for data in funnel_data],
                'visitors': [data.stage_1_visitors for data in funnel_data],
                'searches': [data.stage_2_search for data in funnel_data],
                'views': [data.stage_3_view for data in funnel_data],
                'details': [data.stage_4_detail for data in funnel_data],
                'inquiries': [data.stage_5_inquiry for data in funnel_data],
            }
        }
        
        return render(request, 'main/analytics/conversion_funnel.html', context)
    except Exception as e:
        messages.error(request, f'전환 퍼널 분석 조회 중 오류가 발생했습니다: {e}')
        return redirect('main:analytics_dashboard')

@login_required
@csrf_exempt
def export_analytics_data(request):
    """분석 데이터 CSV 내보내기"""
    if request.method != 'POST':
        return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)
    
    try:
        data_type = request.POST.get('data_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        if not all([data_type, start_date, end_date]):
            return JsonResponse({'error': '필수 파라미터가 누락되었습니다.'}, status=400)
        
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="analytics_{data_type}_{start_date}_{end_date}.csv"'
        
        writer = csv.writer(response)
        
        if data_type == 'user_analytics':
            writer.writerow(['날짜', '총 사용자 수', '신규 사용자', '재방문 사용자', '총 세션', '평균 세션 시간', '이탈률'])
            data = UserAnalytics.objects.filter(date__range=(start_date, end_date))
            for item in data:
                writer.writerow([
                    item.date, item.total_users, item.new_users, item.returning_users,
                    item.total_sessions, item.avg_session_duration, item.bounce_rate
                ])
        
        elif data_type == 'academy_analytics':
            writer.writerow(['날짜', '학원명', '조회수', '순 조회수', '북마크', '공유', '문의'])
            data = AcademyAnalytics.objects.filter(date__range=(start_date, end_date))
            for item in data:
                writer.writerow([
                    item.date, item.academy.상호명, item.views, item.unique_views,
                    item.bookmarks, item.shares, item.inquiries
                ])
        
        else:
            return JsonResponse({'error': '지원하지 않는 데이터 유형입니다.'}, status=400)
        
        return response
        
    except Exception as e:
        return JsonResponse({'error': f'데이터 내보내기 중 오류가 발생했습니다: {e}'}, status=500)

@login_required
def custom_dashboard(request, dashboard_id=None):
    """사용자 정의 대시보드"""
    try:
        if dashboard_id:
            dashboard = get_object_or_404(CustomDashboard, id=dashboard_id)
            
            # 권한 확인
            if dashboard.user != request.user and not dashboard.is_shared:
                messages.error(request, '해당 대시보드에 접근할 권한이 없습니다.')
                return redirect('main:analytics_dashboard')
        else:
            # 기본 대시보드 찾기
            dashboard = CustomDashboard.objects.filter(
                user=request.user, is_default=True
            ).first()
            
            if not dashboard:
                # 기본 대시보드가 없으면 첫 번째 대시보드 사용
                dashboard = CustomDashboard.objects.filter(user=request.user).first()
        
        context = {
            'page_title': '사용자 정의 대시보드',
            'dashboard': dashboard,
            'user_dashboards': CustomDashboard.objects.filter(user=request.user),
        }
        
        return render(request, 'main/analytics/custom_dashboard.html', context)
    except Exception as e:
        messages.error(request, f'대시보드 조회 중 오류가 발생했습니다: {e}')
        return redirect('main:analytics_dashboard')