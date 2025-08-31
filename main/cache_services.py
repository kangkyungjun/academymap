"""
캐싱 서비스 모듈
Caching services module for performance optimization
"""

from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone
from datetime import timedelta
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

class CacheService:
    """
    통합 캐시 서비스 클래스
    Unified cache service class
    """
    
    # 캐시 키 접두사
    CACHE_PREFIXES = {
        'academy': 'academy',
        'search': 'search',
        'filter': 'filter',
        'stats': 'stats',
        'user': 'user',
        'api': 'api',
        'template': 'template',
        'recommendation': 'recommendation',
        'analytics': 'analytics'
    }
    
    # 기본 캐시 만료 시간 (초)
    DEFAULT_TIMEOUTS = {
        'short': 300,      # 5분
        'medium': 1800,    # 30분
        'long': 3600,      # 1시간
        'daily': 86400,    # 24시간
        'weekly': 604800   # 7일
    }

    @staticmethod
    def generate_cache_key(prefix: str, identifier: str, **kwargs) -> str:
        """
        캐시 키 생성
        Generate cache key
        """
        key_parts = [prefix, str(identifier)]
        
        # 추가 파라미터 처리
        if kwargs:
            # 정렬하여 일관성 보장
            sorted_params = sorted(kwargs.items())
            param_str = json.dumps(sorted_params, ensure_ascii=False)
            param_hash = hashlib.md5(param_str.encode('utf-8')).hexdigest()[:8]
            key_parts.append(param_hash)
        
        return ':'.join(key_parts)

    @staticmethod
    def get_cache_timeout(timeout_type: str) -> int:
        """
        캐시 만료 시간 반환
        Return cache timeout duration
        """
        return CacheService.DEFAULT_TIMEOUTS.get(timeout_type, 300)

    @classmethod
    def get_or_set(cls, key: str, callable_or_value, timeout: Union[str, int] = 'medium', 
                   version: Optional[int] = None) -> Any:
        """
        캐시에서 값을 가져오거나 설정
        Get value from cache or set if not exists
        """
        if isinstance(timeout, str):
            timeout = cls.get_cache_timeout(timeout)
        
        try:
            # 캐시에서 값 조회
            cached_value = cache.get(key, version=version)
            if cached_value is not None:
                logger.debug(f"Cache hit for key: {key}")
                return cached_value
            
            # 캐시 미스 - 값 생성
            if callable(callable_or_value):
                value = callable_or_value()
            else:
                value = callable_or_value
            
            # 캐시에 저장
            cache.set(key, value, timeout, version=version)
            logger.debug(f"Cache set for key: {key}, timeout: {timeout}")
            return value
            
        except Exception as e:
            logger.error(f"Cache error for key {key}: {str(e)}")
            # 캐시 오류 시 직접 값 반환
            if callable(callable_or_value):
                return callable_or_value()
            return callable_or_value

    @classmethod
    def invalidate(cls, pattern: str = None, keys: List[str] = None) -> bool:
        """
        캐시 무효화
        Invalidate cache entries
        """
        try:
            if keys:
                # 특정 키들 삭제
                cache.delete_many(keys)
                logger.info(f"Invalidated cache keys: {keys}")
                return True
            
            if pattern:
                # 패턴 매칭 캐시 삭제 (Redis 사용시)
                if hasattr(cache, 'delete_pattern'):
                    cache.delete_pattern(f"*{pattern}*")
                    logger.info(f"Invalidated cache pattern: {pattern}")
                    return True
                else:
                    # 로컬 캐시의 경우 전체 클리어
                    cache.clear()
                    logger.warning("Pattern deletion not supported, cleared all cache")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Cache invalidation error: {str(e)}")
            return False

class AcademyCacheService(CacheService):
    """
    학원 데이터 전용 캐시 서비스
    Academy data specific cache service
    """
    
    @classmethod
    def get_academy_list(cls, filters: Dict = None, page: int = 1, limit: int = 20) -> Dict:
        """
        학원 목록 캐시 조회/설정
        Get/set academy list cache
        """
        cache_key = cls.generate_cache_key(
            cls.CACHE_PREFIXES['academy'], 
            'list',
            filters=filters,
            page=page,
            limit=limit
        )
        
        def fetch_academies():
            from .models import Data as Academy
            queryset = Academy.objects.all()
            
            # 필터 적용
            if filters:
                if 'subject' in filters and filters['subject'] != '전체':
                    subject_field = f"과목_{filters['subject']}"
                    if hasattr(Academy, subject_field):
                        queryset = queryset.filter(**{f"{subject_field}__isnull": False})
                
                if 'region' in filters:
                    queryset = queryset.filter(시군구명__icontains=filters['region'])
                
                if 'age_group' in filters:
                    age_field = f"대상_{filters['age_group']}"
                    if hasattr(Academy, age_field):
                        queryset = queryset.filter(**{f"{age_field}__isnull": False})
            
            # 페이징
            start = (page - 1) * limit
            end = start + limit
            academies = list(queryset[start:end].values())
            total_count = queryset.count()
            
            return {
                'academies': academies,
                'total_count': total_count,
                'page': page,
                'limit': limit,
                'has_next': end < total_count
            }
        
        return cls.get_or_set(cache_key, fetch_academies, 'medium')

    @classmethod
    def get_academy_detail(cls, academy_id: int) -> Optional[Dict]:
        """
        학원 상세 정보 캐시 조회/설정
        Get/set academy detail cache
        """
        cache_key = cls.generate_cache_key(
            cls.CACHE_PREFIXES['academy'], 
            'detail',
            id=academy_id
        )
        
        def fetch_academy_detail():
            from .models import Data as Academy
            try:
                academy = Academy.objects.get(id=academy_id)
                return {
                    'id': academy.id,
                    'name': academy.상호명,
                    'address': academy.도로명주소,
                    'phone': academy.전화번호,
                    'subjects': cls._extract_subjects(academy),
                    'age_groups': cls._extract_age_groups(academy),
                    'coordinates': {
                        'lat': float(academy.위도) if academy.위도 else None,
                        'lng': float(academy.경도) if academy.경도 else None
                    },
                    'updated_at': timezone.now().isoformat()
                }
            except Academy.DoesNotExist:
                return None
        
        return cls.get_or_set(cache_key, fetch_academy_detail, 'long')

    @classmethod
    def get_popular_academies(cls, limit: int = 10) -> List[Dict]:
        """
        인기 학원 목록 캐시
        Get popular academies cache
        """
        cache_key = cls.generate_cache_key(
            cls.CACHE_PREFIXES['academy'], 
            'popular',
            limit=limit
        )
        
        def fetch_popular():
            from .models import Data as Academy
            # 평점이나 조회수 기준으로 정렬 (실제 필드에 맞게 수정 필요)
            queryset = Academy.objects.all()[:limit]
            return list(queryset.values(
                'id', '상호명', '도로명주소', '전화번호'
            ))
        
        return cls.get_or_set(cache_key, fetch_popular, 'long')

    @classmethod
    def _extract_subjects(cls, academy) -> List[str]:
        """학원의 과목 정보 추출"""
        subjects = []
        subject_fields = ['수학', '영어', '과학', '외국어', '예체능', '컴퓨터', '논술']
        
        for subject in subject_fields:
            field_name = f"과목_{subject}"
            if hasattr(academy, field_name):
                value = getattr(academy, field_name)
                if value and str(value).strip():
                    subjects.append(subject)
        
        return subjects

    @classmethod
    def _extract_age_groups(cls, academy) -> List[str]:
        """학원의 대상 연령 정보 추출"""
        age_groups = []
        age_fields = ['유아', '초등', '중등', '고등', '일반']
        
        for age in age_fields:
            field_name = f"대상_{age}"
            if hasattr(academy, field_name):
                value = getattr(academy, field_name)
                if value and str(value).strip():
                    age_groups.append(age)
        
        return age_groups

    @classmethod
    def invalidate_academy_cache(cls, academy_id: int = None):
        """
        학원 관련 캐시 무효화
        Invalidate academy related caches
        """
        if academy_id:
            # 특정 학원 캐시 삭제
            detail_key = cls.generate_cache_key(
                cls.CACHE_PREFIXES['academy'], 
                'detail',
                id=academy_id
            )
            cls.invalidate(keys=[detail_key])
        
        # 전체 학원 목록 관련 캐시 삭제
        cls.invalidate(pattern=cls.CACHE_PREFIXES['academy'])

class SearchCacheService(CacheService):
    """
    검색 결과 캐시 서비스
    Search results cache service
    """
    
    @classmethod
    def get_search_results(cls, query: str, filters: Dict = None, page: int = 1) -> Dict:
        """
        검색 결과 캐시
        Cache search results
        """
        cache_key = cls.generate_cache_key(
            cls.CACHE_PREFIXES['search'],
            query,
            filters=filters,
            page=page
        )
        
        def perform_search():
            from .models import Data as Academy
            from django.db.models import Q
            
            # 기본 쿼리셋
            queryset = Academy.objects.all()
            
            # 검색어 적용
            if query and query.strip():
                search_q = Q(상호명__icontains=query) | Q(도로명주소__icontains=query)
                queryset = queryset.filter(search_q)
            
            # 필터 적용
            if filters:
                if 'subject' in filters:
                    subject_field = f"과목_{filters['subject']}"
                    if hasattr(Academy, subject_field):
                        queryset = queryset.filter(**{f"{subject_field}__isnull": False})
            
            # 결과 반환
            results = list(queryset[:20].values())
            total = queryset.count()
            
            return {
                'results': results,
                'total': total,
                'query': query,
                'page': page
            }
        
        return cls.get_or_set(cache_key, perform_search, 'short')

    @classmethod
    def get_search_suggestions(cls, partial_query: str, limit: int = 5) -> List[str]:
        """
        검색 자동완성 제안
        Search auto-completion suggestions
        """
        cache_key = cls.generate_cache_key(
            cls.CACHE_PREFIXES['search'],
            'suggestions',
            query=partial_query,
            limit=limit
        )
        
        def get_suggestions():
            from .models import Data as Academy
            
            if len(partial_query) < 2:
                return []
            
            # 학원명과 주소에서 부분 매칭되는 항목 찾기
            suggestions = set()
            
            # 학원명에서 검색
            academies = Academy.objects.filter(
                상호명__icontains=partial_query
            )[:limit*2].values_list('상호명', flat=True)
            
            for name in academies:
                if name and partial_query.lower() in name.lower():
                    suggestions.add(name)
                    if len(suggestions) >= limit:
                        break
            
            # 지역명에서 검색
            if len(suggestions) < limit:
                regions = Academy.objects.filter(
                    시군구명__icontains=partial_query
                ).distinct().values_list('시군구명', flat=True)[:limit]
                
                for region in regions:
                    if region and len(suggestions) < limit:
                        suggestions.add(region)
            
            return list(suggestions)[:limit]
        
        return cls.get_or_set(cache_key, get_suggestions, 'medium')

class StatisticsCacheService(CacheService):
    """
    통계 데이터 캐시 서비스
    Statistics data cache service
    """
    
    @classmethod
    def get_dashboard_stats(cls) -> Dict:
        """
        대시보드 통계 캐시
        Dashboard statistics cache
        """
        cache_key = cls.generate_cache_key(
            cls.CACHE_PREFIXES['stats'],
            'dashboard'
        )
        
        def calculate_stats():
            from .models import Data as Academy
            from django.db.models import Count, Avg
            
            total_academies = Academy.objects.count()
            
            # 지역별 통계
            region_stats = list(
                Academy.objects.values('시군구명')
                .annotate(count=Count('id'))
                .order_by('-count')[:10]
            )
            
            # 과목별 통계 (대략적인 계산)
            subject_stats = {}
            subjects = ['수학', '영어', '과학', '외국어', '예체능', '컴퓨터']
            for subject in subjects:
                field_name = f"과목_{subject}"
                if hasattr(Academy, field_name):
                    count = Academy.objects.filter(**{f"{field_name}__isnull": False}).count()
                    if count > 0:
                        subject_stats[subject] = count
            
            return {
                'total_academies': total_academies,
                'region_stats': region_stats,
                'subject_stats': subject_stats,
                'last_updated': timezone.now().isoformat()
            }
        
        return cls.get_or_set(cache_key, calculate_stats, 'daily')

    @classmethod
    def get_performance_metrics(cls) -> Dict:
        """
        성능 메트릭 캐시
        Performance metrics cache
        """
        cache_key = cls.generate_cache_key(
            cls.CACHE_PREFIXES['stats'],
            'performance'
        )
        
        def collect_metrics():
            import psutil
            import os
            from django.db import connection
            
            # 시스템 메트릭
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 데이터베이스 연결 수
            db_connections = len(connection.queries)
            
            # 캐시 히트율 (Redis 사용시)
            cache_stats = {'hit_rate': 0.95}  # 예시값
            
            return {
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used_mb': memory.used / 1024 / 1024,
                    'disk_percent': (disk.used / disk.total) * 100
                },
                'database': {
                    'query_count': db_connections,
                    'connection_count': 1  # SQLite는 단일 연결
                },
                'cache': cache_stats,
                'timestamp': timezone.now().isoformat()
            }
        
        return cls.get_or_set(cache_key, collect_metrics, 'short')

class TemplateCacheService(CacheService):
    """
    템플릿 캐시 서비스
    Template cache service
    """
    
    @classmethod
    def get_template_fragment_key(cls, fragment_name: str, *args) -> str:
        """
        템플릿 프래그먼트 캐시 키 생성
        Generate template fragment cache key
        """
        return make_template_fragment_key(fragment_name, args)

    @classmethod
    def invalidate_template_cache(cls, fragment_name: str, *args):
        """
        템플릿 프래그먼트 캐시 무효화
        Invalidate template fragment cache
        """
        cache_key = cls.get_template_fragment_key(fragment_name, *args)
        cache.delete(cache_key)
        logger.info(f"Invalidated template cache: {fragment_name}")

# 캐시 워밍업 (서버 시작 시 실행)
def warm_up_cache():
    """
    캐시 워밍업 - 자주 사용되는 데이터 미리 로드
    Cache warm-up - preload frequently used data
    """
    logger.info("Starting cache warm-up...")
    
    try:
        # 인기 학원 목록 로드
        AcademyCacheService.get_popular_academies()
        
        # 대시보드 통계 로드
        StatisticsCacheService.get_dashboard_stats()
        
        # 성능 메트릭 로드
        StatisticsCacheService.get_performance_metrics()
        
        logger.info("Cache warm-up completed successfully")
        
    except Exception as e:
        logger.error(f"Cache warm-up failed: {str(e)}")

# 캐시 상태 모니터링
def get_cache_status() -> Dict:
    """
    캐시 상태 정보 반환
    Return cache status information
    """
    try:
        # 테스트 키로 캐시 연결 확인
        test_key = 'cache_test'
        cache.set(test_key, 'test_value', 10)
        test_result = cache.get(test_key)
        cache.delete(test_key)
        
        is_working = test_result == 'test_value'
        
        return {
            'status': 'healthy' if is_working else 'unhealthy',
            'backend': settings.CACHES['default']['BACKEND'],
            'location': settings.CACHES['default'].get('LOCATION', 'Memory'),
            'test_passed': is_working,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }