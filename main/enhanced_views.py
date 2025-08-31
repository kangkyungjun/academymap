"""
향상된 학원 상세 페이지 뷰들
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from django.core.paginator import Paginator
from django.db import transaction
import json

from .models import Data as Academy
from .academy_enhancements import (
    AcademyDetailInfo, AcademyGallery, AcademyStatistics,
    AcademyViewHistory, AcademyFAQ, AcademyNews, AcademyComparison,
    AcademyEnhancementService
)
from accounts.models import User


def enhanced_academy_detail(request, pk):
    """향상된 학원 상세 페이지"""
    
    academy = get_object_or_404(Academy, pk=pk)
    
    # 조회 기록 및 통계 업데이트
    AcademyEnhancementService.record_academy_view(academy, request)
    
    # 향상된 데이터 조회
    enhanced_data = AcademyEnhancementService.get_enhanced_academy_data(
        academy, request.user
    )
    
    # 학원 종합 점수 계산
    academy_score = AcademyEnhancementService.calculate_academy_score(academy)
    
    # 유사한 학원 추천
    similar_academies = AcademyEnhancementService.get_similar_academies(academy)
    
    # 가격 비교 데이터 (기존 로직 유지하되 개선)
    price_comparison = get_enhanced_price_comparison(academy)
    
    # 최근 리뷰들
    recent_reviews = get_recent_reviews(academy, limit=5)
    
    # 학원 통계 정보
    statistics = enhanced_data['statistics']
    if not statistics:
        statistics = AcademyEnhancementService.update_academy_statistics(academy)
    
    context = {
        **enhanced_data,  # 기본 향상된 데이터
        'academy_score': academy_score,
        'similar_academies': similar_academies,
        'price_comparison': price_comparison,
        'recent_reviews': recent_reviews,
        'statistics': statistics,
        
        # 추가 UI 데이터
        'facility_icons': get_facility_icons(),
        'social_share_data': get_social_share_data(academy),
        'breadcrumbs': get_breadcrumbs(academy),
        
        # SEO 메타 데이터
        'meta': get_seo_meta_data(academy),
    }
    
    return render(request, 'main/enhanced_academy_detail.html', context)


def get_enhanced_price_comparison(academy: Academy) -> dict:
    """향상된 가격 비교 데이터"""
    
    try:
        current_tuition = float(academy.수강료_평균) if academy.수강료_평균 else 0
    except (TypeError, ValueError):
        current_tuition = 0
    
    # 과목 분류 찾기
    subject_fields = [
        ('과목_종합', '종합'), ('과목_수학', '수학'), ('과목_영어', '영어'),
        ('과목_과학', '과학'), ('과목_외국어', '외국어'), ('과목_예체능', '예체능'),
        ('과목_컴퓨터', '컴퓨터'), ('과목_논술', '논술'), ('과목_기타', '기타'),
    ]
    
    subject_field = None
    subject_label = None
    for field, label in subject_fields:
        if getattr(academy, field):
            subject_field = field
            subject_label = label
            break
    
    comparison_data = {
        'current_tuition': current_tuition,
        'subject_label': subject_label,
        'comparisons': {},
        'percentiles': {},
        'competitors': []
    }
    
    if subject_field and current_tuition > 0:
        from django.db.models import FloatField, Cast, Avg, Count
        
        base_queryset = Academy.objects.filter(**{subject_field: True})\
            .exclude(수강료_평균__iexact='false')\
            .annotate(tuition=Cast('수강료_평균', FloatField()))\
            .filter(tuition__gt=0)
        
        # 각 지역별 비교
        regions = [
            ('district', academy.시군구명, '시군구'),
            ('province', academy.시도명, '시도'),
            ('nation', None, '전국'),
        ]
        
        for region_key, region_value, region_name in regions:
            if region_key == 'nation':
                queryset = base_queryset
            elif region_key == 'province':
                queryset = base_queryset.filter(시도명=region_value)
            else:
                queryset = base_queryset.filter(시군구명=region_value)
            
            stats = queryset.aggregate(
                avg=Avg('tuition'),
                count=Count('id')
            )
            
            if stats['avg']:
                avg_price = stats['avg']
                diff = current_tuition - avg_price
                percentage = ((current_tuition / avg_price) - 1) * 100
                
                comparison_data['comparisons'][region_key] = {
                    'region_name': region_name,
                    'region_value': region_value or '전국',
                    'avg_price': round(avg_price, 0),
                    'diff': round(diff, 0),
                    'percentage': round(percentage, 1),
                    'count': stats['count'],
                    'status': 'higher' if diff > 0 else 'lower' if diff < 0 else 'same'
                }
        
        # 백분위 계산
        all_tuitions = list(base_queryset.values_list('tuition', flat=True))
        if all_tuitions:
            all_tuitions.sort()
            current_rank = sum(1 for t in all_tuitions if t <= current_tuition)
            percentile = (current_rank / len(all_tuitions)) * 100
            
            comparison_data['percentiles'] = {
                'current_percentile': round(percentile, 1),
                'total_academies': len(all_tuitions),
                'rank': current_rank,
                'cheaper_than': round((1 - current_rank / len(all_tuitions)) * 100, 1)
            }
        
        # 비슷한 가격대의 경쟁 학원들
        price_range = current_tuition * 0.2  # ±20%
        competitors = base_queryset.filter(
            tuition__gte=current_tuition - price_range,
            tuition__lte=current_tuition + price_range,
            시군구명=academy.시군구명
        ).exclude(id=academy.id).order_by('tuition')[:5]
        
        comparison_data['competitors'] = [
            {
                'id': comp.id,
                'name': comp.상호명,
                'tuition': comp.tuition,
                'diff': comp.tuition - current_tuition,
                'rating': comp.별점,
                'address': comp.도로명주소
            }
            for comp in competitors
        ]
    
    return comparison_data


def get_recent_reviews(academy: Academy, limit: int = 5) -> list:
    """최근 리뷰 조회"""
    try:
        from accounts.review_models import Review
        reviews = Review.objects.filter(
            academy=academy,
            is_hidden=False
        ).select_related('user').order_by('-created_at')[:limit]
        
        return [
            {
                'id': review.id,
                'author': review.user.nickname or review.user.username if not review.is_anonymous else '익명',
                'rating': review.overall_rating,
                'title': review.title,
                'content': review.content[:100] + ('...' if len(review.content) > 100 else ''),
                'created_at': review.created_at,
                'helpful_count': review.helpful_count,
                'is_verified': review.is_verified
            }
            for review in reviews
        ]
    except:
        return []


def get_facility_icons() -> dict:
    """시설별 아이콘 매핑"""
    return {
        'parking': '🅿️',
        'elevator': '🛗',
        'wheelchair': '♿',
        'cafe': '☕',
        'library': '📚',
        'computer_room': '💻',
        'science_lab': '🔬',
        'auditorium': '🎭',
        'sports': '⚽',
        'air_conditioning': '❄️',
    }


def get_social_share_data(academy: Academy) -> dict:
    """소셜 공유 데이터"""
    return {
        'title': f"{academy.상호명} - AcademyMap",
        'description': academy.소개글[:100] + '...' if academy.소개글 else f"{academy.상호명} 학원 정보",
        'image': academy.학원사진 or '',
        'url': f"/academy/{academy.id}/",
        'hashtags': f"#{academy.상호명.replace(' ', '')} #학원 #교육 #{academy.시군구명}"
    }


def get_breadcrumbs(academy: Academy) -> list:
    """브레드크럼 생성"""
    return [
        {'name': '홈', 'url': '/'},
        {'name': '학원 검색', 'url': '/search/'},
        {'name': academy.시도명, 'url': f'/search/?region={academy.시도명}'},
        {'name': academy.시군구명, 'url': f'/search/?region={academy.시군구명}'},
        {'name': academy.상호명, 'url': f'/academy/{academy.id}/'}
    ]


def get_seo_meta_data(academy: Academy) -> dict:
    """SEO 메타 데이터"""
    description = academy.소개글[:150] if academy.소개글 else f"{academy.상호명} - {academy.시군구명}에 위치한 학원"
    
    return {
        'title': f"{academy.상호명} | {academy.시군구명} 학원 정보 - AcademyMap",
        'description': description,
        'keywords': f"{academy.상호명}, {academy.시군구명}, 학원, 교육, 학습",
        'og_title': f"{academy.상호명} - AcademyMap",
        'og_description': description,
        'og_image': academy.학원사진 or '',
        'og_url': f"/academy/{academy.id}/",
    }


@csrf_exempt
def academy_statistics_api(request, pk):
    """학원 통계 정보 API"""
    
    academy = get_object_or_404(Academy, pk=pk)
    
    if request.method == 'GET':
        stats = AcademyEnhancementService.update_academy_statistics(academy)
        score_data = AcademyEnhancementService.calculate_academy_score(academy)
        
        return JsonResponse({
            'success': True,
            'statistics': {
                'view_count': stats.view_count,
                'bookmark_count': stats.bookmark_count,
                'share_count': stats.share_count,
                'review_count': stats.review_count,
                'average_rating': stats.average_rating,
                'popularity_score': stats.popularity_score,
                'local_rank': stats.local_rank,
                'category_rank': stats.category_rank,
            },
            'score': score_data
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})


@csrf_exempt
def record_view_duration(request, pk):
    """조회 시간 기록"""
    
    if request.method == 'POST':
        data = json.loads(request.body)
        duration = data.get('duration', 0)
        
        # 세션 기반으로 최근 조회 기록 업데이트
        session_id = request.session.session_key
        if session_id:
            try:
                view_history = AcademyViewHistory.objects.filter(
                    academy_id=pk,
                    session_id=session_id
                ).order_by('-viewed_at').first()
                
                if view_history:
                    view_history.duration = duration
                    view_history.save()
                
                return JsonResponse({'success': True})
            except:
                pass
    
    return JsonResponse({'success': False})


@login_required
def toggle_bookmark(request, pk):
    """즐겨찾기 토글"""
    
    if request.method == 'POST':
        academy = get_object_or_404(Academy, pk=pk)
        
        try:
            from accounts.models import Bookmark
            bookmark, created = Bookmark.objects.get_or_create(
                user=request.user,
                academy=academy
            )
            
            if not created:
                bookmark.delete()
                is_bookmarked = False
            else:
                is_bookmarked = True
            
            # 통계 업데이트
            stats, _ = AcademyStatistics.objects.get_or_create(academy=academy)
            stats.bookmark_count = academy.bookmarked_by.count()
            stats.save()
            
            return JsonResponse({
                'success': True,
                'is_bookmarked': is_bookmarked,
                'bookmark_count': stats.bookmark_count
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})


def academy_gallery_api(request, pk):
    """학원 갤러리 API"""
    
    academy = get_object_or_404(Academy, pk=pk)
    category = request.GET.get('category', 'all')
    
    gallery_query = academy.gallery.all()
    if category != 'all':
        gallery_query = gallery_query.filter(category=category)
    
    gallery_data = []
    for image in gallery_query.order_by('category', 'order'):
        gallery_data.append({
            'id': image.id,
            'image_url': image.image_url,
            'category': image.category,
            'category_display': image.get_category_display(),
            'title': image.title,
            'description': image.description
        })
    
    # 카테고리별 그룹화
    categories = {}
    for item in gallery_data:
        cat = item['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    
    return JsonResponse({
        'success': True,
        'gallery': gallery_data,
        'categories': categories,
        'total_count': len(gallery_data)
    })


def academy_news_api(request, pk):
    """학원 소식 API"""
    
    academy = get_object_or_404(Academy, pk=pk)
    news_type = request.GET.get('type', 'all')
    
    news_query = academy.news.filter(
        publish_date__lte=timezone.now()
    ).filter(
        Q(end_date__gte=timezone.now()) | Q(end_date__isnull=True)
    )
    
    if news_type != 'all':
        news_query = news_query.filter(news_type=news_type)
    
    news_data = []
    for news in news_query.order_by('-is_pinned', '-is_important', '-publish_date')[:20]:
        news_data.append({
            'id': news.id,
            'title': news.title,
            'content': news.content[:200] + ('...' if len(news.content) > 200 else ''),
            'news_type': news.news_type,
            'news_type_display': news.get_news_type_display(),
            'is_important': news.is_important,
            'is_pinned': news.is_pinned,
            'publish_date': news.publish_date.strftime('%Y-%m-%d'),
            'is_active': news.is_active()
        })
    
    return JsonResponse({
        'success': True,
        'news': news_data,
        'total_count': len(news_data)
    })


def similar_academies_api(request, pk):
    """유사한 학원 추천 API"""
    
    academy = get_object_or_404(Academy, pk=pk)
    similar_academies = AcademyEnhancementService.get_similar_academies(academy, limit=10)
    
    similar_data = []
    for sim_academy in similar_academies:
        score_data = AcademyEnhancementService.calculate_academy_score(sim_academy)
        
        similar_data.append({
            'id': sim_academy.id,
            'name': sim_academy.상호명,
            'rating': sim_academy.별점,
            'address': sim_academy.도로명주소,
            'tuition': sim_academy.수강료_평균,
            'category': sim_academy.상권업종소분류명,
            'distance': None,  # TODO: 거리 계산 추가
            'score': score_data['total_score'],
            'grade': score_data['grade']
        })
    
    return JsonResponse({
        'success': True,
        'similar_academies': similar_data,
        'total_count': len(similar_data)
    })


def academy_comparison_api(request, pk):
    """학원 비교 API"""
    
    academy = get_object_or_404(Academy, pk=pk)
    compare_ids = request.GET.get('compare_with', '').split(',')
    
    # 기본 비교 대상이 없으면 유사한 학원들로
    if not compare_ids or compare_ids == ['']:
        similar_academies = AcademyEnhancementService.get_similar_academies(academy, limit=3)
        compare_ids = [str(a.id) for a in similar_academies]
    
    comparison_data = {
        'base_academy': {
            'id': academy.id,
            'name': academy.상호명,
            'rating': academy.별점,
            'tuition': academy.수강료_평균,
            'score': AcademyEnhancementService.calculate_academy_score(academy)
        },
        'compare_academies': []
    }
    
    for comp_id in compare_ids:
        try:
            comp_academy = Academy.objects.get(id=int(comp_id))
            comparison_data['compare_academies'].append({
                'id': comp_academy.id,
                'name': comp_academy.상호명,
                'rating': comp_academy.별점,
                'tuition': comp_academy.수강료_평균,
                'score': AcademyEnhancementService.calculate_academy_score(comp_academy)
            })
        except (Academy.DoesNotExist, ValueError):
            continue
    
    return JsonResponse({
        'success': True,
        'comparison': comparison_data
    })