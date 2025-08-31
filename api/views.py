from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, filters
from rest_framework.decorators import api_view
from django.core.cache import cache
from django.conf import settings
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from .filters import AcademyFilter, PopularAcademyFilter, NearbyAcademyFilter
from .pagination import StandardResultsSetPagination, SmallResultsSetPagination
import math

from main.models import Data
from .serializers import (
    AcademyListSerializer, 
    AcademyDetailSerializer, 
    AcademySearchSerializer,
    AcademySerializer,
    calculate_distance
)

class AcademyListAPIView(generics.ListAPIView):
    """학원 목록 조회 (페이지네이션, 필터링, 검색 지원)"""
    serializer_class = AcademyListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AcademyFilter
    search_fields = ['상호명', '도로명주소', '시도명', '시군구명', '행정동명']
    ordering_fields = ['별점', '상호명', 'id']
    ordering = ['-별점', 'id']  # 기본적으로 평점 높은 순, 같은 평점일 때는 ID 순
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        """성능 최적화된 쿼리셋"""
        # 기본 쿼리셋: 위도/경도가 있는 학원만 (지도 표시용)
        queryset = Data.objects.filter(
            위도__isnull=False,
            경도__isnull=False
        )
        
        # 위치 기반 필터링
        lat = self.request.GET.get('lat')
        lon = self.request.GET.get('lon')
        radius = float(self.request.GET.get('radius', 10))  # 기본 10km
        
        if lat and lon:
            # 사용자 위치를 request에 저장하여 serializer에서 활용
            self.request.user_lat = float(lat)
            self.request.user_lon = float(lon)
            
            # 대략적인 위도/경도 범위로 1차 필터링 (성능 최적화)
            lat_range = radius / 111  # 1도 ≈ 111km
            lon_range = radius / (111 * math.cos(math.radians(float(lat))))
            
            queryset = queryset.filter(
                위도__gte=float(lat) - lat_range,
                위도__lte=float(lat) + lat_range,
                경도__gte=float(lon) - lon_range,
                경도__lte=float(lon) + lon_range
            )
        
        # 과목 필터링
        category = self.request.GET.get('category')
        if category and category != '전체':
            queryset = queryset.filter(**{f'과목_{category}': True})
        
        # 가격 필터링 (Flutter 호환)
        price_min = self.request.GET.get('priceMin')
        price_max = self.request.GET.get('priceMax')
        if price_min or price_max:
            # 수강료가 있는 학원만 대상
            queryset = queryset.exclude(수강료_평균__isnull=True).exclude(수강료_평균='').exclude(수강료_평균='0')
            
            if price_min:
                try:
                    min_price = int(float(price_min))
                    queryset = queryset.extra(
                        where=["CAST(수강료_평균 AS INTEGER) >= %s"],
                        params=[min_price]
                    )
                except ValueError:
                    pass
                    
            if price_max and price_max != '999999999':
                try:
                    max_price = int(float(price_max))
                    queryset = queryset.extra(
                        where=["CAST(수강료_평균 AS INTEGER) <= %s"],
                        params=[max_price]
                    )
                except ValueError:
                    pass
        
        # 연령대 필터링
        age_groups = self.request.GET.getlist('age_groups')
        if age_groups:
            age_filter = Q()
            for age in age_groups:
                age_filter |= Q(**{f'대상_{age}': True})
            queryset = queryset.filter(age_filter)
        
        # 평점 필터링
        rating_min = self.request.GET.get('rating_min')
        if rating_min:
            queryset = queryset.filter(별점__gte=float(rating_min))
        
        # 셔틀버스 필터링
        if self.request.GET.get('shuttle') == 'true':
            queryset = queryset.exclude(셔틀버스__isnull=True).exclude(셔틀버스='')
        
        return queryset

class AcademyDetailAPIView(generics.RetrieveAPIView):
    """학원 상세 정보 조회"""
    queryset = Data.objects.all()
    serializer_class = AcademyDetailSerializer
    lookup_field = 'pk'

class AcademyNearbyAPIView(APIView):
    """위치 기반 주변 학원 조회"""
    
    def get(self, request):
        lat = request.GET.get('lat')
        lon = request.GET.get('lon')
        radius = float(request.GET.get('radius', 5))  # 기본 5km
        limit = int(request.GET.get('limit', 20))  # 기본 20개
        
        if not lat or not lon:
            return Response(
                {'error': '위도(lat)와 경도(lon)가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            lat = float(lat)
            lon = float(lon)
        except ValueError:
            return Response(
                {'error': '올바른 위도, 경도 값을 입력해주세요.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 대략적인 위도/경도 범위로 1차 필터링
        lat_range = radius / 111
        lon_range = radius / (111 * math.cos(math.radians(lat)))
        
        queryset = Data.objects.filter(
            위도__gte=lat - lat_range,
            위도__lte=lat + lat_range,
            경도__gte=lon - lon_range,
            경도__lte=lon + lon_range
        )
        
        # 거리 계산 및 정렬
        academies_with_distance = []
        for academy in queryset:
            if academy.위도 and academy.경도:
                distance = calculate_distance(lat, lon, academy.위도, academy.경도)
                if distance and distance <= radius:
                    academies_with_distance.append((academy, distance))
        
        # 거리순 정렬
        academies_with_distance.sort(key=lambda x: x[1])
        nearby_academies = [item[0] for item in academies_with_distance[:limit]]
        
        # 사용자 위치를 request에 저장
        request.user_lat = lat
        request.user_lon = lon
        
        serializer = AcademyListSerializer(nearby_academies, many=True, context={'request': request})
        
        return Response({
            'count': len(nearby_academies),
            'results': serializer.data
        })

@api_view(['GET'])
def categories_view(request):
    """사용 가능한 카테고리 목록 반환 (캐싱 적용)"""
    cache_key = 'api:categories'
    categories = cache.get(cache_key)
    
    if categories is None:
        categories = [
            {'key': '종합', 'name': '종합'},
            {'key': '수학', 'name': '수학'},
            {'key': '영어', 'name': '영어'},
            {'key': '과학', 'name': '과학'},
            {'key': '외국어', 'name': '외국어'},
            {'key': '예체능', 'name': '예체능'},
            {'key': '컴퓨터', 'name': '컴퓨터'},
            {'key': '논술', 'name': '논술'},
            {'key': '기타', 'name': '기타'},
            {'key': '독서실스터디카페', 'name': '독서실/스터디카페'},
        ]
        cache.set(cache_key, categories, getattr(settings, 'STATS_CACHE_TIMEOUT', 3600))
    
    return Response({'categories': categories})

@api_view(['GET'])
def regions_view(request):
    """사용 가능한 지역 목록 반환"""
    regions = Data.objects.values('시도명', '시군구명').distinct().order_by('시도명', '시군구명')
    
    # 시도명별로 그룹핑
    regions_dict = {}
    for region in regions:
        시도 = region['시도명']
        시군구 = region['시군구명']
        
        if 시도 not in regions_dict:
            regions_dict[시도] = []
        if 시군구 and 시군구 not in regions_dict[시도]:
            regions_dict[시도].append(시군구)
    
    # 정렬
    for key in regions_dict:
        regions_dict[key].sort()
    
    return Response({'regions': regions_dict})

class AcademySearchAPIView(APIView):
    """고급 검색 API"""
    
    def post(self, request):
        search_serializer = AcademySearchSerializer(data=request.data)
        
        if not search_serializer.is_valid():
            return Response(search_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = search_serializer.validated_data
        queryset = Data.objects.all()
        
        # 텍스트 검색
        query = data.get('query')
        if query:
            queryset = queryset.filter(
                Q(상호명__icontains=query) |
                Q(도로명주소__icontains=query) |
                Q(시도명__icontains=query) |
                Q(시군구명__icontains=query) |
                Q(행정동명__icontains=query)
            )
        
        # 카테고리 필터
        category = data.get('category')
        if category and category != '전체':
            queryset = queryset.filter(**{f'과목_{category}': True})
        
        # 가격 필터 (수강료_평균 필드 기준)
        price_min = data.get('price_min')
        price_max = data.get('price_max')
        if price_min or price_max:
            # 수강료가 있는 학원만 대상
            price_queryset = queryset.exclude(수강료_평균__isnull=True).exclude(수강료_평균='').exclude(수강료_평균='0')
            
            if price_min:
                try:
                    min_price = int(price_min)
                    # Cast를 사용해 문자열을 정수로 변환하여 비교
                    from django.db.models import Cast, IntegerField
                    price_queryset = price_queryset.extra(
                        where=["CAST(수강료_평균 AS INTEGER) >= %s"],
                        params=[min_price]
                    )
                except ValueError:
                    pass
                    
            if price_max:
                try:
                    max_price = int(price_max) if price_max != '999999999' else 10000000
                    from django.db.models import Cast, IntegerField  
                    price_queryset = price_queryset.extra(
                        where=["CAST(수강료_평균 AS INTEGER) <= %s"],
                        params=[max_price]
                    )
                except ValueError:
                    pass
                    
            queryset = price_queryset
        
        # 연령대 필터
        age_groups = data.get('age_groups', [])
        if age_groups:
            age_filter = Q()
            for age in age_groups:
                age_filter |= Q(**{f'대상_{age}': True})
            queryset = queryset.filter(age_filter)
        
        # 평점 필터
        rating_min = data.get('rating_min')
        if rating_min:
            queryset = queryset.filter(별점__gte=rating_min)
        
        # 셔틀버스 필터
        if data.get('shuttle'):
            queryset = queryset.exclude(셔틀버스__isnull=True).exclude(셔틀버스='')
        
        # 위치 기반 필터링
        lat = data.get('lat')
        lon = data.get('lon')
        radius = data.get('radius', 5.0)
        
        if lat and lon:
            request.user_lat = lat
            request.user_lon = lon
            
            # 대략적인 범위로 1차 필터링
            lat_range = radius / 111
            lon_range = radius / (111 * math.cos(math.radians(lat)))
            
            queryset = queryset.filter(
                위도__gte=lat - lat_range,
                위도__lte=lat + lat_range,
                경도__gte=lon - lon_range,
                경도__lte=lon + lon_range
            )
        
        # 페이지네이션은 DRF의 기본 설정 사용
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        
        serializer = AcademyListSerializer(
            paginated_queryset, 
            many=True, 
            context={'request': request}
        )
        
        return paginator.get_paginated_response(serializer.data)

# 추가 특화 뷰들
class PopularAcademiesAPIView(generics.ListAPIView):
    """인기 학원 목록 (평점, 사진 기준)"""
    serializer_class = AcademyListSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = PopularAcademyFilter
    ordering = ['-별점', 'id']
    
    def get_queryset(self):
        # 평점이 있고, 사진이 있는 학원들만 추천
        return Data.objects.filter(
            별점__isnull=False,
            별점__gte=4.0
        ).exclude(
            학원사진__isnull=True
        ).exclude(
            학원사진=''
        )

class RecommendedAcademiesAPIView(APIView):
    """추천 학원 목록 (다양한 기준 조합)"""
    
    def get(self, request):
        category = request.GET.get('category')
        age_group = request.GET.get('age_group')
        limit = int(request.GET.get('limit', 10))
        
        # 기본 추천 기준: 평점 높고 정보가 충실한 학원들
        base_queryset = Data.objects.filter(
            별점__isnull=False,
            별점__gte=3.5
        )
        
        # 카테고리 기반 추천
        if category and category != '전체':
            base_queryset = base_queryset.filter(**{f'과목_{category}': True})
        
        # 연령대 기반 추천
        if age_group:
            base_queryset = base_queryset.filter(**{f'대상_{age_group}': True})
        
        # 추천 알고리즘: 평점 + 정보 완성도
        recommended = base_queryset.extra(
            select={
                'score': """
                    CASE 
                        WHEN 별점 >= 4.5 THEN 100
                        WHEN 별점 >= 4.0 THEN 80
                        WHEN 별점 >= 3.5 THEN 60
                        ELSE 40
                    END +
                    CASE WHEN 학원사진 IS NOT NULL AND 학원사진 != '' THEN 20 ELSE 0 END +
                    CASE WHEN 소개글 IS NOT NULL AND 소개글 != '' THEN 10 ELSE 0 END +
                    CASE WHEN 전화번호 IS NOT NULL AND 전화번호 != '' THEN 10 ELSE 0 END +
                    CASE WHEN 셔틀버스 IS NOT NULL AND 셔틀버스 != '' THEN 5 ELSE 0 END
                """
            }
        ).order_by('-score', '-별점', 'id')[:limit]
        
        serializer = AcademyListSerializer(recommended, many=True, context={'request': request})
        
        return Response({
            'count': len(recommended),
            'results': serializer.data,
            'recommendation_criteria': {
                'category': category,
                'age_group': age_group,
                'min_rating': 3.5,
                'factors': ['rating', 'photo', 'description', 'contact', 'shuttle']
            }
        })

@api_view(['GET'])
def academy_stats_view(request):
    """학원 통계 정보 (캐싱 적용)"""
    cache_key = 'api:academy_stats'
    stats = cache.get(cache_key)
    
    if stats is None:
        from django.db.models import Count, Avg
        
        # 전체 통계
        total_count = Data.objects.count()
        avg_rating = Data.objects.filter(별점__isnull=False).aggregate(Avg('별점'))['별점__avg']
        
        # 지역별 통계
        region_stats = Data.objects.values('시도명').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # 과목별 통계
        subject_stats = {}
        subjects = ['종합', '수학', '영어', '과학', '외국어', '예체능', '컴퓨터', '논술', '기타', '독서실스터디카페']
        for subject in subjects:
            count = Data.objects.filter(**{f'과목_{subject}': True}).count()
            subject_stats[subject] = count
        
        # 연령대별 통계
        age_stats = {}
        ages = ['유아', '초등', '중등', '고등', '특목고', '일반', '기타']
        for age in ages:
            count = Data.objects.filter(**{f'대상_{age}': True}).count()
            age_stats[age] = count
        
        stats = {
            'total_academies': total_count,
            'average_rating': round(avg_rating, 2) if avg_rating else None,
            'top_regions': list(region_stats),
            'subject_distribution': subject_stats,
            'age_group_distribution': age_stats,
            'academies_with_photos': Data.objects.exclude(
                학원사진__isnull=True
            ).exclude(학원사진='').count(),
            'academies_with_shuttle': Data.objects.exclude(
                셔틀버스__isnull=True
            ).exclude(셔틀버스='').count(),
        }
        
        cache.set(cache_key, stats, getattr(settings, 'STATS_CACHE_TIMEOUT', 3600))
    
    return Response(stats)

@api_view(['POST'])
def autocomplete_view(request):
    """자동완성 API"""
    query = request.data.get('query', '').strip()
    limit = int(request.data.get('limit', 10))
    
    if len(query) < 2:
        return Response({'suggestions': []})
    
    # 학원명 자동완성
    academy_names = Data.objects.filter(
        상호명__icontains=query
    ).values_list('상호명', flat=True).distinct()[:limit//2]
    
    # 지역 자동완성
    regions = Data.objects.filter(
        Q(시도명__icontains=query) |
        Q(시군구명__icontains=query) |
        Q(행정동명__icontains=query)
    ).values('시도명', '시군구명', '행정동명').distinct()[:limit//2]
    
    region_suggestions = []
    for region in regions:
        region_text = f"{region['시도명']} {region['시군구명']} {region['행정동명']}"
        region_suggestions.append(region_text)
    
    suggestions = {
        'academies': list(academy_names),
        'regions': region_suggestions,
        'total': len(academy_names) + len(region_suggestions)
    }
    
    return Response({'suggestions': suggestions})

# API 헬스체크 및 정보 제공
@api_view(['GET'])
def api_info_view(request):
    """API 정보 및 헬스체크"""
    from django.db import connection
    import time
    
    start_time = time.time()
    
    # 데이터베이스 연결 테스트
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = "healthy"
        db_time = round((time.time() - start_time) * 1000, 2)  # ms
    except Exception as e:
        db_status = "error"
        db_time = None
    
    api_info = {
        'api_version': 'v1',
        'service': 'AcademyMap API',
        'status': 'healthy',
        'timestamp': time.time(),
        'database': {
            'status': db_status,
            'response_time_ms': db_time
        },
        'endpoints': {
            'academies': '/api/v1/academies/',
            'academy_detail': '/api/v1/academies/{id}/',
            'nearby': '/api/v1/academies/nearby/',
            'search': '/api/v1/academies/search/',
            'popular': '/api/v1/academies/popular/',
            'recommended': '/api/v1/academies/recommended/',
            'categories': '/api/v1/categories/',
            'regions': '/api/v1/regions/',
            'stats': '/api/v1/stats/',
            'autocomplete': '/api/v1/autocomplete/',
        },
        'features': [
            'location-based search',
            'advanced filtering',
            'recommendation system',
            'autocomplete',
            'pagination',
            'caching',
            'real-time distance calculation'
        ]
    }
    
    return Response(api_info)

# 하위 호환성을 위한 기존 뷰
class AcademyListAPIViewLegacy(AcademyListAPIView):
    """기존 API 호환성을 위한 뷰"""
    serializer_class = AcademySerializer
