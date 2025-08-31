"""
성능 최적화 서비스 모듈
Performance optimization services module
"""

from django.db import connection, transaction
from django.db.models import Prefetch, Q, Count, Avg, Max, Min
from django.core.paginator import Paginator
from django.utils import timezone
from django.conf import settings
from django.core.management.color import no_style
from django.core.cache import cache
from typing import Dict, List, Any, Optional, Tuple
import logging
import time
import json
from datetime import timedelta, datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

class DatabaseOptimizationService:
    """
    데이터베이스 최적화 서비스
    Database optimization service
    """
    
    @staticmethod
    def analyze_query_performance() -> Dict[str, Any]:
        """
        쿼리 성능 분석
        Analyze query performance
        """
        try:
            # SQLite는 EXPLAIN QUERY PLAN 지원
            with connection.cursor() as cursor:
                # 느린 쿼리 분석을 위한 기본 통계
                queries_stats = {
                    'total_queries': len(connection.queries),
                    'query_time': sum(float(q['time']) for q in connection.queries),
                    'slow_queries': [
                        q for q in connection.queries 
                        if float(q['time']) > 0.1  # 100ms 이상
                    ],
                    'duplicate_queries': DatabaseOptimizationService._find_duplicate_queries(),
                    'analysis_time': timezone.now().isoformat()
                }
                
                return queries_stats
                
        except Exception as e:
            logger.error(f"Query performance analysis failed: {str(e)}")
            return {'error': str(e)}

    @staticmethod
    def _find_duplicate_queries() -> List[Dict]:
        """중복 쿼리 찾기"""
        query_counts = defaultdict(int)
        query_times = defaultdict(list)
        
        for query in connection.queries:
            sql = query['sql']
            query_counts[sql] += 1
            query_times[sql].append(float(query['time']))
        
        duplicates = []
        for sql, count in query_counts.items():
            if count > 1:
                total_time = sum(query_times[sql])
                duplicates.append({
                    'query': sql[:100] + '...' if len(sql) > 100 else sql,
                    'count': count,
                    'total_time': total_time,
                    'avg_time': total_time / count
                })
        
        return sorted(duplicates, key=lambda x: x['total_time'], reverse=True)

    @staticmethod
    def optimize_database_indexes() -> Dict[str, Any]:
        """
        데이터베이스 인덱스 최적화 제안
        Database index optimization suggestions
        """
        suggestions = []
        
        # 자주 사용되는 필터 필드에 대한 인덱스 제안
        index_suggestions = [
            {
                'table': 'main_data',
                'field': '시군구명',
                'reason': 'Region filtering is frequently used',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_main_data_region ON main_data (시군구명);'
            },
            {
                'table': 'main_data',
                'field': '상호명',
                'reason': 'Academy name searching is common',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_main_data_name ON main_data (상호명);'
            },
            {
                'table': 'main_data',
                'fields': ['위도', '경도'],
                'reason': 'Location-based queries need spatial indexing',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_main_data_location ON main_data (위도, 경도);'
            }
        ]
        
        return {
            'suggestions': index_suggestions,
            'total_suggestions': len(index_suggestions),
            'estimated_performance_gain': '20-40%'
        }

    @staticmethod
    def create_recommended_indexes() -> Dict[str, Any]:
        """
        권장 인덱스 생성
        Create recommended indexes
        """
        results = []
        
        try:
            with connection.cursor() as cursor:
                # 지역 인덱스
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_main_data_region 
                    ON main_data (시군구명)
                ''')
                results.append('Region index created')
                
                # 학원명 인덱스
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_main_data_name 
                    ON main_data (상호명)
                ''')
                results.append('Academy name index created')
                
                # 좌표 복합 인덱스
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_main_data_location 
                    ON main_data (위도, 경도)
                ''')
                results.append('Location composite index created')
                
                return {
                    'success': True,
                    'created_indexes': results,
                    'message': 'Recommended indexes created successfully'
                }
                
        except Exception as e:
            logger.error(f"Index creation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

class QueryOptimizationService:
    """
    쿼리 최적화 서비스
    Query optimization service
    """
    
    @staticmethod
    def optimize_academy_queries():
        """
        학원 관련 쿼리 최적화 클래스
        Optimized academy query methods
        """
        from .models import Data as Academy
        
        class OptimizedAcademyQueries:
            
            @staticmethod
            def get_academies_with_prefetch(region: str = None, subject: str = None) -> List[Academy]:
                """
                미리 로드를 사용한 최적화된 학원 조회
                Optimized academy query with prefetching
                """
                queryset = Academy.objects.select_related().all()
                
                if region:
                    queryset = queryset.filter(시군구명__icontains=region)
                
                if subject and subject != '전체':
                    subject_field = f"과목_{subject}"
                    if hasattr(Academy, subject_field):
                        queryset = queryset.filter(**{f"{subject_field}__isnull": False})
                
                # 필요한 필드만 선택
                return queryset.only(
                    'id', '상호명', '도로명주소', '전화번호', 
                    '위도', '경도', '시군구명'
                )
            
            @staticmethod
            def get_academies_paginated(page: int = 1, per_page: int = 20, **filters) -> Tuple[List[Academy], Dict]:
                """
                페이지네이션과 함께 최적화된 조회
                Optimized query with pagination
                """
                queryset = OptimizedAcademyQueries.get_academies_with_prefetch(
                    filters.get('region'), 
                    filters.get('subject')
                )
                
                paginator = Paginator(queryset, per_page)
                page_obj = paginator.get_page(page)
                
                return page_obj.object_list, {
                    'total_pages': paginator.num_pages,
                    'current_page': page,
                    'per_page': per_page,
                    'total_count': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                }
            
            @staticmethod
            def search_academies_optimized(query: str, filters: Dict = None) -> List[Academy]:
                """
                최적화된 학원 검색
                Optimized academy search
                """
                if not query or len(query.strip()) < 2:
                    return []
                
                # 인덱스를 활용한 검색 쿼리
                search_q = Q(상호명__icontains=query) | Q(도로명주소__icontains=query)
                
                queryset = Academy.objects.filter(search_q).only(
                    'id', '상호명', '도로명주소', '전화번호', '위도', '경도'
                )
                
                if filters:
                    if filters.get('region'):
                        queryset = queryset.filter(시군구명__icontains=filters['region'])
                
                return queryset[:20]  # 결과 제한
            
            @staticmethod
            def get_academy_statistics() -> Dict[str, Any]:
                """
                최적화된 통계 쿼리
                Optimized statistics query
                """
                from django.db.models import Count, Q
                
                # 한 번의 쿼리로 여러 통계 계산
                stats = Academy.objects.aggregate(
                    total_count=Count('id'),
                    region_count=Count('시군구명', distinct=True)
                )
                
                # 상위 지역 통계
                top_regions = Academy.objects.values('시군구명')\
                    .annotate(count=Count('id'))\
                    .order_by('-count')[:10]
                
                # 과목별 통계 (효율적 계산)
                subject_stats = {}
                subjects = ['수학', '영어', '과학', '외국어', '예체능']
                for subject in subjects:
                    field_name = f"과목_{subject}"
                    if hasattr(Academy, field_name):
                        count = Academy.objects.filter(
                            **{f"{field_name}__isnull": False}
                        ).count()
                        if count > 0:
                            subject_stats[subject] = count
                
                return {
                    **stats,
                    'top_regions': list(top_regions),
                    'subject_stats': subject_stats
                }
        
        return OptimizedAcademyQueries

class PerformanceMonitoringService:
    """
    성능 모니터링 서비스
    Performance monitoring service
    """
    
    def __init__(self):
        self.metrics = {
            'request_times': [],
            'query_counts': [],
            'cache_hits': 0,
            'cache_misses': 0,
            'error_count': 0
        }
    
    def record_request_time(self, request_time: float):
        """요청 처리 시간 기록"""
        self.metrics['request_times'].append({
            'time': request_time,
            'timestamp': timezone.now()
        })
        
        # 최근 100개 요청만 유지
        if len(self.metrics['request_times']) > 100:
            self.metrics['request_times'] = self.metrics['request_times'][-100:]
    
    def record_query_count(self, count: int):
        """쿼리 수 기록"""
        self.metrics['query_counts'].append({
            'count': count,
            'timestamp': timezone.now()
        })
    
    def record_cache_hit(self):
        """캐시 히트 기록"""
        self.metrics['cache_hits'] += 1
    
    def record_cache_miss(self):
        """캐시 미스 기록"""
        self.metrics['cache_misses'] += 1
    
    def record_error(self):
        """에러 발생 기록"""
        self.metrics['error_count'] += 1
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 요약 정보 반환"""
        request_times = [m['time'] for m in self.metrics['request_times']]
        query_counts = [m['count'] for m in self.metrics['query_counts']]
        
        cache_total = self.metrics['cache_hits'] + self.metrics['cache_misses']
        cache_hit_rate = (self.metrics['cache_hits'] / cache_total) if cache_total > 0 else 0
        
        return {
            'request_performance': {
                'avg_time': sum(request_times) / len(request_times) if request_times else 0,
                'max_time': max(request_times) if request_times else 0,
                'min_time': min(request_times) if request_times else 0,
                'total_requests': len(request_times)
            },
            'query_performance': {
                'avg_queries_per_request': sum(query_counts) / len(query_counts) if query_counts else 0,
                'max_queries': max(query_counts) if query_counts else 0,
                'total_queries': sum(query_counts)
            },
            'cache_performance': {
                'hit_rate': cache_hit_rate,
                'total_hits': self.metrics['cache_hits'],
                'total_misses': self.metrics['cache_misses']
            },
            'error_rate': {
                'total_errors': self.metrics['error_count']
            },
            'timestamp': timezone.now().isoformat()
        }

class CompressionService:
    """
    압축 서비스
    Compression service for static assets
    """
    
    @staticmethod
    def get_compression_settings() -> Dict[str, Any]:
        """
        압축 설정 정보
        Compression settings information
        """
        return {
            'gzip_enabled': True,
            'compression_types': [
                'text/html',
                'text/css', 
                'text/javascript',
                'application/javascript',
                'application/json',
                'text/xml'
            ],
            'compression_level': 6,
            'min_size': 1000,  # 1KB 이상 파일만 압축
        }
    
    @staticmethod
    def analyze_static_files() -> Dict[str, Any]:
        """
        정적 파일 분석
        Static files analysis
        """
        import os
        from django.contrib.staticfiles import finders
        
        total_size = 0
        file_types = defaultdict(list)
        
        try:
            # STATIC_ROOT에서 파일 분석
            static_root = settings.STATIC_ROOT
            if static_root and os.path.exists(static_root):
                for root, dirs, files in os.walk(static_root):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)
                        file_ext = os.path.splitext(file)[1].lower()
                        
                        total_size += file_size
                        file_types[file_ext].append({
                            'name': file,
                            'size': file_size,
                            'path': file_path
                        })
            
            # 파일 타입별 통계
            type_stats = {}
            for ext, files in file_types.items():
                type_stats[ext] = {
                    'count': len(files),
                    'total_size': sum(f['size'] for f in files),
                    'avg_size': sum(f['size'] for f in files) / len(files) if files else 0
                }
            
            return {
                'total_files': sum(len(files) for files in file_types.values()),
                'total_size': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'file_types': type_stats,
                'compressible_size': CompressionService._calculate_compressible_size(file_types),
                'compression_potential': '30-50% size reduction'
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def _calculate_compressible_size(file_types: Dict) -> int:
        """압축 가능한 파일 크기 계산"""
        compressible_extensions = ['.css', '.js', '.html', '.json', '.xml', '.txt']
        compressible_size = 0
        
        for ext, files in file_types.items():
            if ext in compressible_extensions:
                compressible_size += sum(f['size'] for f in files)
        
        return compressible_size

# 성능 모니터링 인스턴스
performance_monitor = PerformanceMonitoringService()

def get_system_metrics() -> Dict[str, Any]:
    """
    시스템 전체 성능 메트릭 (캐시 적용)
    Overall system performance metrics (cached)
    """
    from django.core.cache import cache
    
    # 캐시에서 확인 (10초 캐시)
    cache_key = 'system_metrics'
    cached_metrics = cache.get(cache_key)
    if cached_metrics:
        return cached_metrics
        
    try:
        import psutil
        import os
        
        # CPU 및 메모리 정보 (캐시된 값 사용으로 성능 향상)
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 프로세스 정보
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()
        
        result = {
            'system': {
                'cpu_percent': cpu_percent,
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                }
            },
            'process': {
                'memory_rss': process_memory.rss,
                'memory_vms': process_memory.vms,
                'cpu_percent': process.cpu_percent(),
                'num_threads': process.num_threads()
            },
            'django': {
                'debug': settings.DEBUG,
                'database_queries': len(connection.queries)
            },
            'timestamp': timezone.now().isoformat()
        }
        
        # 캐시에 저장 (10초)
        cache.set(cache_key, result, 10)
        return result
        
    except ImportError:
        return {
            'error': 'psutil not available',
            'basic_metrics': {
                'database_queries': len(connection.queries),
                'debug_mode': settings.DEBUG
            }
        }

def optimize_settings_for_production() -> Dict[str, Any]:
    """
    프로덕션 환경을 위한 설정 최적화 제안
    Production settings optimization suggestions
    """
    suggestions = []
    current_settings = {}
    
    # DEBUG 설정 확인
    if settings.DEBUG:
        suggestions.append({
            'setting': 'DEBUG',
            'current': True,
            'recommended': False,
            'reason': 'DEBUG should be False in production for security and performance',
            'impact': 'High'
        })
    
    # 캐시 설정 확인
    cache_backend = settings.CACHES['default']['BACKEND']
    if 'locmem' in cache_backend or 'dummy' in cache_backend:
        suggestions.append({
            'setting': 'CACHES',
            'current': cache_backend,
            'recommended': 'Redis or Memcached',
            'reason': 'Use distributed cache for better performance',
            'impact': 'Medium'
        })
    
    # 데이터베이스 설정 확인
    if 'sqlite3' in settings.DATABASES['default']['ENGINE']:
        suggestions.append({
            'setting': 'DATABASE',
            'current': 'SQLite',
            'recommended': 'PostgreSQL or MySQL',
            'reason': 'Use production-grade database for better performance and scalability',
            'impact': 'High'
        })
    
    return {
        'suggestions': suggestions,
        'total_suggestions': len(suggestions),
        'high_priority': len([s for s in suggestions if s['impact'] == 'High']),
        'estimated_performance_improvement': '50-80%'
    }