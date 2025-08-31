"""
향상된 학원 정보를 위한 REST API 뷰들
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg, F, Case, When, FloatField
from django.db.models.functions import Cast
from django.utils import timezone
from django.core.cache import cache
import json

from .models import Data as Academy
from .academy_enhancements import (
    AcademyDetailInfo, AcademyGallery, AcademyStatistics,
    AcademyViewHistory, AcademyFAQ, AcademyNews,
    AcademyEnhancementService
)
from .enhanced_serializers import (
    EnhancedAcademySerializer, AcademySearchResultSerializer,
    AcademyGallerySerializer, AcademyNewsSerializer,
    AcademyFAQSerializer, AcademyStatisticsSerializer,
    AcademyRecommendationSerializer, AcademyViewHistorySerializer
)


class EnhancedAcademyViewSet(viewsets.ReadOnlyModelViewSet):
    """향상된 학원 정보 ViewSet"""
    
    queryset = Academy.objects.all()
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AcademySearchResultSerializer
        return EnhancedAcademySerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        
        # 사용자 위치 정보 추가 (요청에서 받기)
        user_lat = self.request.query_params.get('user_lat')
        user_lng = self.request.query_params.get('user_lng')
        
        if user_lat and user_lng:
            try:
                context['user_lat'] = float(user_lat)
                context['user_lng'] = float(user_lng)
            except ValueError:
                pass
        
        context['user'] = self.request.user
        return context
    
    def retrieve(self, request, *args, **kwargs):
        """학원 상세 정보 조회"""
        instance = self.get_object()
        
        # 조회 기록
        AcademyEnhancementService.record_academy_view(instance, request)
        
        # 향상된 데이터 조회
        enhanced_data = AcademyEnhancementService.get_enhanced_academy_data(
            instance, request.user
        )
        
        serializer = self.get_serializer(instance)
        response_data = serializer.data
        
        # 추가 정보들
        response_data.update({
            'price_comparison': self._get_price_comparison(instance),
            'similar_academies': self._get_similar_academies(instance),
            'recent_reviews': self._get_recent_reviews(instance),
            'social_share_data': self._get_social_share_data(instance),
        })
        
        return Response(response_data)
    
    def list(self, request, *args, **kwargs):
        """학원 목록 조회 (필터링 및 검색 지원)"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # 검색어 처리
        search_query = request.query_params.get('search', '').strip()
        if search_query:
            queryset = self._apply_search_filters(queryset, search_query)
        
        # 필터 적용
        queryset = self._apply_advanced_filters(queryset, request.query_params)
        
        # 정렬
        queryset = self._apply_sorting(queryset, request.query_params)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def _apply_search_filters(self, queryset, search_query):
        """검색 필터 적용"""
        search_terms = search_query.split()
        search_filter = Q()
        
        for term in search_terms:
            term_filter = (
                Q(상호명__icontains=term) |
                Q(도로명주소__icontains=term) |
                Q(시도명__icontains=term) |
                Q(시군구명__icontains=term) |
                Q(소개글__icontains=term)
            )
            search_filter &= term_filter
        
        return queryset.filter(search_filter)
    
    def _apply_advanced_filters(self, queryset, params):
        """고급 필터 적용"""
        
        # 가격 범위
        price_min = params.get('price_min')
        price_max = params.get('price_max')
        if price_min or price_max:
            queryset = queryset.annotate(
                price_float=Cast('수강료_평균', FloatField())
            )
            if price_min:
                queryset = queryset.filter(price_float__gte=float(price_min))
            if price_max:
                queryset = queryset.filter(price_float__lte=float(price_max))
        
        # 과목 필터
        subjects = params.getlist('subjects')
        if subjects:
            subject_filter = Q()
            subject_mapping = {
                '수학': '과목_수학', '영어': '과목_영어', '과학': '과목_과학',
                '외국어': '과목_외국어', '예체능': '과목_예체능',
                '컴퓨터': '과목_컴퓨터', '논술': '과목_논술', '기타': '과목_기타'
            }
            for subject in subjects:
                if subject in subject_mapping:
                    subject_filter |= Q(**{subject_mapping[subject]: True})
            if subject_filter:
                queryset = queryset.filter(subject_filter)
        
        # 대상 연령 필터
        age_groups = params.getlist('age_groups')
        if age_groups:
            age_filter = Q()
            age_mapping = {
                '유아': '대상_유아', '초등': '대상_초등', '중등': '대상_중등',
                '고등': '대상_고등', '특목고': '대상_특목고', '일반': '대상_일반'
            }
            for age in age_groups:
                if age in age_mapping:
                    age_filter |= Q(**{age_mapping[age]: True})
            if age_filter:
                queryset = queryset.filter(age_filter)
        
        # 지역 필터
        region = params.get('region')
        if region:
            queryset = queryset.filter(
                Q(시도명__icontains=region) | Q(시군구명__icontains=region)
            )
        
        # 평점 필터
        min_rating = params.get('min_rating')
        if min_rating:
            queryset = queryset.filter(별점__gte=float(min_rating))
        
        # 시설 필터
        facilities = params.getlist('facilities')
        if facilities:
            queryset = queryset.filter(
                detail_info__facilities__contains=facilities
            )
        
        return queryset
    
    def _apply_sorting(self, queryset, params):
        """정렬 적용"""
        sort_by = params.get('sort_by', 'popularity')
        sort_order = params.get('sort_order', 'desc')
        
        order_prefix = '-' if sort_order == 'desc' else ''
        
        if sort_by == 'popularity':
            queryset = queryset.select_related('statistics').order_by(
                f'{order_prefix}statistics__popularity_score',
                f'{order_prefix}별점'
            )
        elif sort_by == 'rating':
            queryset = queryset.order_by(f'{order_prefix}별점')
        elif sort_by == 'price':
            queryset = queryset.annotate(
                price_float=Cast('수강료_평균', FloatField())
            ).order_by(f'{order_prefix}price_float')
        elif sort_by == 'name':
            queryset = queryset.order_by(f'{order_prefix}상호명')
        elif sort_by == 'recent':
            # 최근 업데이트된 순 (통계 업데이트 시간 기준)
            queryset = queryset.select_related('statistics').order_by(
                f'{order_prefix}statistics__last_updated'
            )
        
        return queryset
    
    def _get_price_comparison(self, academy):
        """가격 비교 데이터"""
        # enhanced_views.py의 로직 재사용
        from .enhanced_views import get_enhanced_price_comparison
        return get_enhanced_price_comparison(academy)
    
    def _get_similar_academies(self, academy):
        """유사한 학원들"""
        similar = AcademyEnhancementService.get_similar_academies(academy, limit=5)
        serializer = AcademySearchResultSerializer(
            similar, many=True, context=self.get_serializer_context()
        )
        return serializer.data
    
    def _get_recent_reviews(self, academy):
        """최근 리뷰들"""
        from .enhanced_views import get_recent_reviews
        return get_recent_reviews(academy, limit=3)
    
    def _get_social_share_data(self, academy):
        """소셜 공유 데이터"""
        from .enhanced_views import get_social_share_data
        return get_social_share_data(academy)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def toggle_bookmark(self, request, pk=None):
        """즐겨찾기 토글"""
        academy = self.get_object()
        
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
            AcademyEnhancementService.update_academy_statistics(academy)
            
            return Response({
                'success': True,
                'is_bookmarked': is_bookmarked,
                'message': '즐겨찾기에 추가되었습니다.' if is_bookmarked else '즐겨찾기에서 제거되었습니다.'
            })
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """학원 통계 정보"""
        academy = self.get_object()
        stats = AcademyEnhancementService.update_academy_statistics(academy)
        score_data = AcademyEnhancementService.calculate_academy_score(academy)
        
        serializer = AcademyStatisticsSerializer(stats)
        return Response({
            'statistics': serializer.data,
            'score': score_data
        })
    
    @action(detail=True, methods=['get'])
    def gallery(self, request, pk=None):
        """학원 갤러리"""
        academy = self.get_object()
        category = request.query_params.get('category', 'all')
        
        gallery_query = academy.gallery.all()
        if category != 'all':
            gallery_query = gallery_query.filter(category=category)
        
        serializer = AcademyGallerySerializer(
            gallery_query.order_by('category', 'order'), 
            many=True
        )
        
        return Response({
            'gallery': serializer.data,
            'categories': dict(AcademyGallery.CATEGORY_CHOICES)
        })
    
    @action(detail=True, methods=['get'])
    def news(self, request, pk=None):
        """학원 소식"""
        academy = self.get_object()
        news_type = request.query_params.get('type', 'all')
        
        news_query = academy.news.filter(
            publish_date__lte=timezone.now()
        ).filter(
            Q(end_date__gte=timezone.now()) | Q(end_date__isnull=True)
        )
        
        if news_type != 'all':
            news_query = news_query.filter(news_type=news_type)
        
        serializer = AcademyNewsSerializer(
            news_query.order_by('-is_pinned', '-is_important', '-publish_date')[:20],
            many=True
        )
        
        return Response({
            'news': serializer.data,
            'news_types': dict(AcademyNews.NEWS_TYPES)
        })
    
    @action(detail=True, methods=['get'])
    def faqs(self, request, pk=None):
        """학원 FAQ"""
        academy = self.get_object()
        faqs = academy.faqs.filter(is_active=True).order_by('order')
        
        serializer = AcademyFAQSerializer(faqs, many=True)
        return Response({'faqs': serializer.data})
    
    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """학원 추천"""
        user = request.user
        
        # 추천 로직 구현
        recommended_academies = self._get_recommendations_for_user(user, request)
        
        serializer = AcademyRecommendationSerializer(data={
            'recommended_academies': recommended_academies,
            'recommendation_reason': '사용자 선호도 및 인기도 기반 추천',
            'recommendation_score': 85.5,
            'filters_applied': self._get_applied_filters(request.query_params),
            'total_count': len(recommended_academies)
        })
        serializer.is_valid()
        
        return Response(serializer.data)
    
    def _get_recommendations_for_user(self, user, request):
        """사용자 맞춤 추천"""
        
        # 기본 추천: 인기도 높은 학원들
        popular_academies = Academy.objects.select_related('statistics')\
            .filter(statistics__popularity_score__gt=0)\
            .order_by('-statistics__popularity_score', '-별점')[:20]
        
        # 사용자가 로그인했다면 개인화
        if user.is_authenticated:
            # 사용자의 즐겨찾기 패턴 분석
            bookmarked_subjects = self._analyze_user_preferences(user)
            if bookmarked_subjects:
                # 선호 과목 기반 필터링
                subject_filter = Q()
                for subject in bookmarked_subjects:
                    if hasattr(Academy, f'과목_{subject}'):
                        subject_filter |= Q(**{f'과목_{subject}': True})
                
                if subject_filter:
                    popular_academies = popular_academies.filter(subject_filter)
        
        # 시리얼라이저 적용
        serializer = AcademySearchResultSerializer(
            popular_academies[:10], 
            many=True,
            context=self.get_serializer_context()
        )
        
        return serializer.data
    
    def _analyze_user_preferences(self, user):
        """사용자 선호도 분석"""
        try:
            from accounts.models import Bookmark
            bookmarks = Bookmark.objects.filter(user=user).select_related('academy')
            
            # 북마크한 학원들의 과목 분포 분석
            subject_counts = {}
            subject_fields = ['수학', '영어', '과학', '외국어', '예체능', '컴퓨터', '논술']
            
            for bookmark in bookmarks:
                academy = bookmark.academy
                for subject in subject_fields:
                    if getattr(academy, f'과목_{subject}', False):
                        subject_counts[subject] = subject_counts.get(subject, 0) + 1
            
            # 가장 많이 선택한 과목들 반환
            sorted_subjects = sorted(subject_counts.items(), key=lambda x: x[1], reverse=True)
            return [subject for subject, count in sorted_subjects[:3]]
        
        except:
            return []
    
    def _get_applied_filters(self, params):
        """적용된 필터들"""
        filters = {}
        if params.get('price_min'):
            filters['min_price'] = params.get('price_min')
        if params.get('price_max'):
            filters['max_price'] = params.get('price_max')
        if params.getlist('subjects'):
            filters['subjects'] = params.getlist('subjects')
        if params.getlist('age_groups'):
            filters['age_groups'] = params.getlist('age_groups')
        if params.get('region'):
            filters['region'] = params.get('region')
        
        return filters
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """인기 학원 목록"""
        
        # 캐시 키
        cache_key = 'popular_academies'
        cache_time = request.query_params.get('cache_time', '3600')  # 1시간 기본
        
        # 캐시에서 조회
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        # 인기 학원 조회
        popular_academies = Academy.objects.select_related('statistics')\
            .annotate(
                popularity_score=Case(
                    When(statistics__popularity_score__gt=0, 
                         then=F('statistics__popularity_score')),
                    default=0,
                    output_field=FloatField()
                )
            ).filter(popularity_score__gt=0)\
            .order_by('-popularity_score', '-별점')[:50]
        
        serializer = AcademySearchResultSerializer(
            popular_academies, 
            many=True,
            context=self.get_serializer_context()
        )
        
        response_data = {
            'popular_academies': serializer.data,
            'generated_at': timezone.now(),
            'total_count': len(serializer.data)
        }
        
        # 캐시에 저장
        try:
            cache.set(cache_key, response_data, int(cache_time))
        except:
            pass
        
        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """주변 학원"""
        user_lat = request.query_params.get('lat')
        user_lng = request.query_params.get('lng')
        radius = float(request.query_params.get('radius', '5'))  # 기본 5km
        
        if not user_lat or not user_lng:
            return Response({
                'error': '위치 정보가 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_lat = float(user_lat)
            user_lng = float(user_lng)
        except ValueError:
            return Response({
                'error': '올바른 위치 정보를 입력하세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 간단한 거리 계산을 위한 바운딩 박스 생성
        # 1도 ≈ 111km
        lat_delta = radius / 111
        lng_delta = radius / (111 * abs(user_lat) * 0.01745329)
        
        nearby_academies = Academy.objects.filter(
            위도__gte=user_lat - lat_delta,
            위도__lte=user_lat + lat_delta,
            경도__gte=user_lng - lng_delta,
            경도__lte=user_lng + lng_delta
        )
        
        serializer = AcademySearchResultSerializer(
            nearby_academies,
            many=True,
            context={
                **self.get_serializer_context(),
                'user_lat': user_lat,
                'user_lng': user_lng
            }
        )
        
        # 실제 거리로 필터링 및 정렬
        nearby_data = []
        for academy_data in serializer.data:
            if academy_data.get('distance') and academy_data['distance'] <= radius:
                nearby_data.append(academy_data)
        
        # 거리순 정렬
        nearby_data.sort(key=lambda x: x.get('distance', float('inf')))
        
        return Response({
            'nearby_academies': nearby_data[:20],  # 최대 20개
            'center': {'lat': user_lat, 'lng': user_lng},
            'radius': radius,
            'total_count': len(nearby_data)
        })


class AcademyAnalyticsViewSet(viewsets.ViewSet):
    """학원 분석 데이터 ViewSet"""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """학원 트렌드 분석"""
        
        # 최근 30일간 인기 상승 학원
        trending_academies = Academy.objects.select_related('statistics')\
            .filter(statistics__monthly_views__gt=F('statistics__view_count') * 0.3)\
            .order_by('-statistics__monthly_views')[:10]
        
        # 지역별 인기 학원
        popular_by_region = Academy.objects.values('시도명')\
            .annotate(
                avg_popularity=Avg('statistics__popularity_score'),
                academy_count=Count('id')
            ).filter(avg_popularity__gt=0)\
            .order_by('-avg_popularity')[:10]
        
        # 과목별 인기 동향
        subject_trends = self._analyze_subject_trends()
        
        return Response({
            'trending_academies': AcademySearchResultSerializer(
                trending_academies, many=True, context={'user': request.user}
            ).data,
            'popular_by_region': list(popular_by_region),
            'subject_trends': subject_trends,
            'generated_at': timezone.now()
        })
    
    def _analyze_subject_trends(self):
        """과목별 트렌드 분석"""
        subjects = ['수학', '영어', '과학', '외국어', '예체능', '컴퓨터', '논술']
        trends = []
        
        for subject in subjects:
            academy_count = Academy.objects.filter(**{f'과목_{subject}': True}).count()
            avg_popularity = Academy.objects.filter(
                **{f'과목_{subject}': True}
            ).select_related('statistics').aggregate(
                avg_pop=Avg('statistics__popularity_score')
            )['avg_pop'] or 0
            
            trends.append({
                'subject': subject,
                'academy_count': academy_count,
                'avg_popularity': round(avg_popularity, 1),
                'trend': 'increasing' if avg_popularity > 50 else 'stable'
            })
        
        return sorted(trends, key=lambda x: x['avg_popularity'], reverse=True)
    
    @action(detail=False, methods=['get'])
    def comparison_data(self, request):
        """학원 비교 데이터"""
        academy_ids = request.query_params.get('academies', '').split(',')
        
        if len(academy_ids) < 2:
            return Response({
                'error': '최소 2개의 학원을 선택하세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            academies = Academy.objects.filter(id__in=academy_ids)
            
            comparison_data = []
            for academy in academies:
                score = AcademyEnhancementService.calculate_academy_score(academy)
                comparison_data.append({
                    'academy': EnhancedAcademySerializer(
                        academy, context={'user': request.user}
                    ).data,
                    'score': score,
                    'strengths': self._identify_strengths(academy),
                    'weaknesses': self._identify_weaknesses(academy)
                })
            
            return Response({
                'comparison': comparison_data,
                'summary': self._generate_comparison_summary(comparison_data)
            })
        
        except Exception as e:
            return Response({
                'error': f'비교 데이터 생성 실패: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _identify_strengths(self, academy):
        """학원 강점 식별"""
        strengths = []
        
        if academy.별점 and float(academy.별점) >= 4.0:
            strengths.append('높은 평점')
        
        if hasattr(academy, 'statistics') and academy.statistics:
            if academy.statistics.review_count >= 10:
                strengths.append('다수의 리뷰')
            if academy.statistics.popularity_score >= 70:
                strengths.append('높은 인기도')
        
        if hasattr(academy, 'detail_info') and academy.detail_info:
            if len(academy.detail_info.facilities) >= 5:
                strengths.append('다양한 시설')
            if academy.detail_info.teacher_student_ratio and academy.detail_info.teacher_student_ratio <= 10:
                strengths.append('낮은 학생-교사 비율')
        
        return strengths
    
    def _identify_weaknesses(self, academy):
        """학원 약점 식별"""
        weaknesses = []
        
        if not academy.별점 or float(academy.별점) < 3.0:
            weaknesses.append('평점 부족')
        
        if hasattr(academy, 'statistics') and academy.statistics:
            if academy.statistics.review_count < 5:
                weaknesses.append('리뷰 부족')
        
        if not hasattr(academy, 'detail_info') or not academy.detail_info:
            weaknesses.append('상세 정보 부족')
        elif len(academy.detail_info.facilities) < 3:
            weaknesses.append('시설 정보 부족')
        
        if not academy.소개글:
            weaknesses.append('소개글 없음')
        
        return weaknesses
    
    def _generate_comparison_summary(self, comparison_data):
        """비교 요약 생성"""
        if len(comparison_data) < 2:
            return {}
        
        # 가장 높은 점수의 학원
        best_academy = max(comparison_data, key=lambda x: x['score']['total_score'])
        
        # 가장 저렴한 학원
        cheapest = None
        for data in comparison_data:
            academy_data = data['academy']
            if academy_data['수강료_평균']:
                try:
                    price = float(academy_data['수강료_평균'])
                    if cheapest is None or price < cheapest['price']:
                        cheapest = {
                            'academy': academy_data,
                            'price': price
                        }
                except:
                    pass
        
        return {
            'best_overall': best_academy['academy']['상호명'],
            'best_score': best_academy['score']['total_score'],
            'cheapest': cheapest['academy']['상호명'] if cheapest else None,
            'price_range': {
                'min': cheapest['price'] if cheapest else None,
                'max': max(
                    [float(d['academy']['수강료_평균']) for d in comparison_data 
                     if d['academy']['수강료_평균']], 
                    default=None
                )
            }
        }