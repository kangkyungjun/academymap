"""
SEO 최적화 Views
"""

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from django.core.paginator import Paginator
import xml.etree.ElementTree as ET

try:
    from .seo_models import (
        SEOMetadata, AcademySEO, SearchKeyword, 
        SitemapEntry, RobotsRule, SEOAudit
    )
    from .seo_services import (
        SEOMetadataService, AcademySEOService, SearchKeywordService,
        SitemapService, RobotsService, SEOAuditService
    )
    from .models import Data as Academy
except ImportError:
    # 마이그레이션 중이거나 모델이 아직 생성되지 않은 경우
    pass


def sitemap_xml(request):
    """XML 사이트맵"""
    try:
        xml_content = SitemapService.generate_sitemap_xml()
        
        if not xml_content:
            # 기본 사이트맵 생성
            xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://academymap.co.kr/</loc>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
</urlset>'''
        
        return HttpResponse(xml_content, content_type='application/xml')
        
    except Exception as e:
        return HttpResponse(
            '<?xml version="1.0" encoding="UTF-8"?><error>Sitemap generation failed</error>',
            content_type='application/xml',
            status=500
        )


def robots_txt(request):
    """robots.txt"""
    try:
        robots_content = RobotsService.generate_robots_txt()
        
        if not robots_content:
            # 기본 robots.txt
            robots_content = """User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/
Disallow: /manage/

Sitemap: https://academymap.co.kr/sitemap.xml"""
        
        return HttpResponse(robots_content, content_type='text/plain')
        
    except Exception as e:
        return HttpResponse(
            "User-agent: *\nDisallow:",
            content_type='text/plain'
        )


@staff_member_required
def seo_dashboard(request):
    """SEO 대시보드"""
    try:
        context = {
            'page_title': 'SEO 대시보드',
            'total_academies': Academy.objects.count(),
            'seo_optimized': AcademySEO.objects.filter(seo_score__gte=70).count(),
            'sitemap_entries': SitemapEntry.objects.filter(is_active=True).count(),
            'total_keywords': SearchKeyword.objects.values('keyword').distinct().count(),
            'recent_audits': SEOAudit.objects.order_by('-audit_date')[:10],
            'top_keywords': SearchKeywordService.get_trending_keywords(30)[:10],
        }
        
        return render(request, 'seo/dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f'대시보드 로드 중 오류가 발생했습니다: {e}')
        return render(request, 'seo/dashboard.html', {'error': str(e)})


@staff_member_required
def academy_seo_list(request):
    """학원 SEO 목록"""
    try:
        academy_seos = AcademySEO.objects.select_related('academy').all()
        
        # 필터링
        score_filter = request.GET.get('score')
        region_filter = request.GET.get('region')
        
        if score_filter:
            if score_filter == 'high':
                academy_seos = academy_seos.filter(seo_score__gte=80)
            elif score_filter == 'medium':
                academy_seos = academy_seos.filter(seo_score__range=(50, 79))
            elif score_filter == 'low':
                academy_seos = academy_seos.filter(seo_score__lt=50)
        
        if region_filter:
            academy_seos = academy_seos.filter(
                academy__시도명__icontains=region_filter
            )
        
        # 페이지네이션
        paginator = Paginator(academy_seos, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_title': '학원 SEO 관리',
            'page_obj': page_obj,
            'current_filters': {
                'score': score_filter,
                'region': region_filter,
            }
        }
        
        return render(request, 'seo/academy_seo_list.html', context)
        
    except Exception as e:
        messages.error(request, f'SEO 목록 조회 중 오류가 발생했습니다: {e}')
        return render(request, 'seo/academy_seo_list.html', {'error': str(e)})


@staff_member_required
def academy_seo_detail(request, academy_id):
    """학원 SEO 상세"""
    try:
        academy = get_object_or_404(Academy, id=academy_id)
        
        # SEO 데이터 가져오기 또는 생성
        academy_seo = AcademySEO.objects.filter(academy=academy).first()
        if not academy_seo:
            academy_seo = AcademySEOService.optimize_academy_seo(academy)
        
        # 메타데이터 생성
        metadata = SEOMetadataService.create_academy_metadata(academy)
        
        context = {
            'page_title': f'{academy.상호명} - SEO 상세',
            'academy': academy,
            'academy_seo': academy_seo,
            'metadata': metadata,
        }
        
        return render(request, 'seo/academy_seo_detail.html', context)
        
    except Exception as e:
        messages.error(request, f'SEO 상세 조회 중 오류가 발생했습니다: {e}')
        return render(request, 'seo/academy_seo_detail.html', {'error': str(e)})


@staff_member_required
def keyword_analytics(request):
    """키워드 분석"""
    try:
        # 기간 필터
        days = int(request.GET.get('days', 30))
        category_filter = request.GET.get('category')
        
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=days)
        
        keywords_query = SearchKeyword.objects.filter(
            date__range=(start_date, end_date)
        )
        
        if category_filter:
            keywords_query = keywords_query.filter(category=category_filter)
        
        # 통계 계산
        top_keywords = keywords_query.values('keyword').annotate(
            total_searches=models.Sum('search_count'),
            total_clicks=models.Sum('click_count'),
            avg_ctr=models.Avg('ctr')
        ).order_by('-total_searches')[:20]
        
        category_stats = keywords_query.values('category').annotate(
            count=Count('keyword', distinct=True),
            total_searches=models.Sum('search_count')
        ).order_by('-total_searches')
        
        context = {
            'page_title': '키워드 분석',
            'top_keywords': top_keywords,
            'category_stats': category_stats,
            'days': days,
            'category_filter': category_filter,
            'categories': SearchKeyword.objects.values_list(
                'category', flat=True
            ).distinct(),
        }
        
        return render(request, 'seo/keyword_analytics.html', context)
        
    except Exception as e:
        messages.error(request, f'키워드 분석 조회 중 오류가 발생했습니다: {e}')
        return render(request, 'seo/keyword_analytics.html', {'error': str(e)})


@staff_member_required
def sitemap_management(request):
    """사이트맵 관리"""
    try:
        entries = SitemapEntry.objects.all().order_by('-priority', 'page_type')
        
        # 페이지 타입별 통계
        type_stats = entries.values('page_type').annotate(
            count=Count('id'),
            active_count=Count('id', filter=Q(is_active=True))
        )
        
        context = {
            'page_title': '사이트맵 관리',
            'entries': entries[:100],  # 상위 100개만 표시
            'type_stats': type_stats,
            'total_entries': entries.count(),
        }
        
        return render(request, 'seo/sitemap_management.html', context)
        
    except Exception as e:
        messages.error(request, f'사이트맵 관리 조회 중 오류가 발생했습니다: {e}')
        return render(request, 'seo/sitemap_management.html', {'error': str(e)})


@staff_member_required
@require_http_methods(['POST'])
def regenerate_sitemap(request):
    """사이트맵 재생성"""
    try:
        entries_count = SitemapService.generate_sitemap_entries()
        messages.success(request, f'사이트맵이 재생성되었습니다. ({entries_count}개 엔트리)')
        
    except Exception as e:
        messages.error(request, f'사이트맵 재생성 중 오류가 발생했습니다: {e}')
    
    return JsonResponse({'success': True, 'redirect': '/seo/sitemap/'})


@staff_member_required
@require_http_methods(['POST'])
def optimize_academy_seo_bulk(request):
    """학원 SEO 일괄 최적화"""
    try:
        academy_ids = request.POST.getlist('academy_ids')
        
        if not academy_ids:
            academies = Academy.objects.all()[:100]  # 상위 100개
        else:
            academies = Academy.objects.filter(id__in=academy_ids)
        
        optimized_count = 0
        for academy in academies:
            if AcademySEOService.optimize_academy_seo(academy):
                optimized_count += 1
        
        messages.success(request, f'{optimized_count}개 학원의 SEO가 최적화되었습니다.')
        
        return JsonResponse({
            'success': True,
            'optimized_count': optimized_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def track_search_api(request):
    """검색 추적 API"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        keyword = request.POST.get('keyword')
        region_sido = request.POST.get('region_sido', '')
        region_sigungu = request.POST.get('region_sigungu', '')
        
        if not keyword:
            return JsonResponse({'error': 'keyword required'}, status=400)
        
        search_keyword = SearchKeywordService.track_search(
            keyword=keyword,
            region_sido=region_sido,
            region_sigungu=region_sigungu
        )
        
        return JsonResponse({
            'success': True,
            'keyword_id': search_keyword.id if search_keyword else None
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def track_click_api(request):
    """클릭 추적 API"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        keyword = request.POST.get('keyword')
        
        if not keyword:
            return JsonResponse({'error': 'keyword required'}, status=400)
        
        SearchKeywordService.track_click(keyword)
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def seo_meta_api(request):
    """SEO 메타데이터 API"""
    try:
        path = request.GET.get('path', '/')
        metadata = SEOMetadataService.get_metadata(path)
        
        if not metadata:
            # 기본 메타데이터
            metadata = {
                'title': 'AcademyMap - 전국 학원 정보',
                'description': '전국 학원 정보를 한 곳에서 확인하세요.',
                'keywords': '학원, 교육, 수강료, 위치'
            }
        
        return JsonResponse(metadata)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)