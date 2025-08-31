"""
성능 최적화 미들웨어
Performance optimization middleware
"""

import time
import logging
import json
from typing import Any, Callable
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.utils.cache import add_never_cache_headers, patch_cache_control
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from .performance_services import performance_monitor
from .cache_services import CacheService

logger = logging.getLogger(__name__)

class PerformanceMonitoringMiddleware:
    """
    성능 모니터링 미들웨어
    Performance monitoring middleware
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # 요청 시작 시간 기록
        start_time = time.time()
        initial_queries = len(connection.queries) if settings.DEBUG else 0
        
        # 요청 처리
        response = self.get_response(request)
        
        # 요청 완료 시간 계산
        end_time = time.time()
        request_time = end_time - start_time
        
        # 쿼리 수 계산
        if settings.DEBUG:
            query_count = len(connection.queries) - initial_queries
            performance_monitor.record_query_count(query_count)
        
        # 성능 메트릭 기록
        performance_monitor.record_request_time(request_time)
        
        # 응답 헤더에 성능 정보 추가 (개발 환경에서만)
        if settings.DEBUG:
            response['X-Request-Time'] = f'{request_time:.3f}s'
            if settings.DEBUG:
                response['X-Query-Count'] = str(query_count)
        
        # 느린 요청 로깅
        if request_time > 1.0:  # 1초 이상
            logger.warning(
                f"Slow request: {request.method} {request.path} "
                f"took {request_time:.3f}s"
            )
        
        return response

class CacheMiddleware:
    """
    고급 캐시 미들웨어
    Advanced cache middleware
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.cache_timeout = getattr(settings, 'CACHE_MIDDLEWARE_SECONDS', 600)
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # 캐시 가능한 요청인지 확인
        if not self._should_cache_request(request):
            return self.get_response(request)
        
        # 캐시 키 생성
        cache_key = self._generate_cache_key(request)
        
        # 캐시에서 응답 조회
        cached_response = cache.get(cache_key)
        if cached_response:
            performance_monitor.record_cache_hit()
            logger.debug(f"Cache hit for key: {cache_key}")
            
            # 캐시된 응답에 헤더 추가
            response = HttpResponse(cached_response['content'])
            for header, value in cached_response.get('headers', {}).items():
                response[header] = value
            response['X-Cache-Status'] = 'HIT'
            return response
        
        # 캐시 미스 - 요청 처리
        performance_monitor.record_cache_miss()
        response = self.get_response(request)
        
        # 응답 캐시 저장
        if self._should_cache_response(response):
            cached_data = {
                'content': response.content.decode('utf-8'),
                'headers': dict(response.items()),
                'status_code': response.status_code
            }
            cache.set(cache_key, cached_data, self.cache_timeout)
            response['X-Cache-Status'] = 'MISS'
            logger.debug(f"Response cached with key: {cache_key}")
        
        return response
    
    def _should_cache_request(self, request: HttpRequest) -> bool:
        """요청이 캐시 가능한지 확인"""
        # GET 요청만 캐시
        if request.method != 'GET':
            return False
        
        # 인증된 사용자 요청은 캐시하지 않음
        if hasattr(request, 'user') and request.user.is_authenticated:
            return False
        
        # API 엔드포인트는 별도 처리
        if request.path.startswith('/api/'):
            return True
        
        # 정적 파일은 캐시하지 않음 (웹서버에서 처리)
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return False
        
        return True
    
    def _should_cache_response(self, response: HttpResponse) -> bool:
        """응답이 캐시 가능한지 확인"""
        # 성공적인 응답만 캐시
        if response.status_code != 200:
            return False
        
        # Content-Type 확인
        content_type = response.get('Content-Type', '')
        cacheable_types = [
            'text/html',
            'application/json',
            'text/plain'
        ]
        
        return any(ct in content_type for ct in cacheable_types)
    
    def _generate_cache_key(self, request: HttpRequest) -> str:
        """요청에 대한 캐시 키 생성"""
        key_parts = [
            'page',
            request.path,
            request.GET.urlencode() if request.GET else 'no-params'
        ]
        return CacheService.generate_cache_key('middleware', ':'.join(key_parts))

class CompressionMiddleware:
    """
    응답 압축 미들웨어
    Response compression middleware
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        
        # 압축 가능한 응답인지 확인
        if self._should_compress(request, response):
            response = self._compress_response(response)
        
        return response
    
    def _should_compress(self, request: HttpRequest, response: HttpResponse) -> bool:
        """압축해야 하는 응답인지 확인"""
        # Accept-Encoding 헤더 확인
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        if 'gzip' not in accept_encoding:
            return False
        
        # 이미 압축된 응답은 제외
        if response.get('Content-Encoding'):
            return False
        
        # 작은 응답은 압축하지 않음
        content_length = len(response.content)
        if content_length < 1000:  # 1KB 미만
            return False
        
        # 압축 가능한 Content-Type 확인
        content_type = response.get('Content-Type', '').split(';')[0]
        compressible_types = [
            'text/html',
            'text/css',
            'text/javascript',
            'application/javascript',
            'application/json',
            'text/xml',
            'text/plain'
        ]
        
        return content_type in compressible_types
    
    def _compress_response(self, response: HttpResponse) -> HttpResponse:
        """응답 압축"""
        try:
            import gzip
            
            # 응답 내용 압축
            compressed_content = gzip.compress(response.content)
            
            # 압축된 내용으로 응답 업데이트
            response.content = compressed_content
            response['Content-Encoding'] = 'gzip'
            response['Content-Length'] = str(len(compressed_content))
            
            # Vary 헤더 추가
            vary = response.get('Vary', '')
            if 'Accept-Encoding' not in vary:
                response['Vary'] = f"{vary}, Accept-Encoding" if vary else 'Accept-Encoding'
            
            logger.debug(f"Response compressed: {len(response.content)} bytes")
            
        except Exception as e:
            logger.error(f"Compression failed: {str(e)}")
        
        return response

class SecurityHeadersMiddleware:
    """
    보안 헤더 미들웨어
    Security headers middleware
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        
        # 보안 헤더 추가
        self._add_security_headers(response)
        
        return response
    
    def _add_security_headers(self, response: HttpResponse) -> None:
        """보안 헤더 추가"""
        # X-Content-Type-Options
        response['X-Content-Type-Options'] = 'nosniff'
        
        # X-Frame-Options
        response['X-Frame-Options'] = 'DENY'
        
        # X-XSS-Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer-Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content-Security-Policy (기본적인 CSP)
        if not response.get('Content-Security-Policy'):
            csp = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'"
            response['Content-Security-Policy'] = csp
        
        # HTTPS에서만 추가할 헤더들
        if getattr(settings, 'SECURE_SSL_REDIRECT', False):
            # Strict-Transport-Security
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

class RateLimitMiddleware:
    """
    요청 제한 미들웨어 (간단한 구현)
    Rate limiting middleware (simple implementation)
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.rate_limit = getattr(settings, 'RATE_LIMIT_PER_MINUTE', 60)
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # IP 기반 요청 제한 확인
        client_ip = self._get_client_ip(request)
        
        if self._is_rate_limited(client_ip):
            from django.http import HttpResponseTooManyRequests
            return HttpResponseTooManyRequests(
                "Too many requests. Please try again later.",
                content_type="text/plain"
            )
        
        response = self.get_response(request)
        
        # 요청 카운트 증가
        self._increment_request_count(client_ip)
        
        return response
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def _is_rate_limited(self, client_ip: str) -> bool:
        """요청 제한 확인"""
        cache_key = f"rate_limit:{client_ip}"
        current_count = cache.get(cache_key, 0)
        return current_count >= self.rate_limit
    
    def _increment_request_count(self, client_ip: str) -> None:
        """요청 카운트 증가"""
        cache_key = f"rate_limit:{client_ip}"
        current_count = cache.get(cache_key, 0)
        cache.set(cache_key, current_count + 1, 60)  # 1분간 유지

class DatabaseOptimizationMiddleware:
    """
    데이터베이스 최적화 미들웨어
    Database optimization middleware
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # 요청 처리 전 데이터베이스 연결 최적화
        if settings.DEBUG:
            initial_queries = len(connection.queries)
        
        response = self.get_response(request)
        
        # 요청 처리 후 분석
        if settings.DEBUG:
            total_queries = len(connection.queries) - initial_queries
            
            # 과도한 쿼리 경고
            if total_queries > 20:
                logger.warning(
                    f"High query count: {total_queries} queries for {request.path}"
                )
            
            # N+1 쿼리 패턴 감지
            self._detect_n_plus_one_queries(connection.queries[initial_queries:])
        
        return response
    
    def _detect_n_plus_one_queries(self, queries: list) -> None:
        """N+1 쿼리 패턴 감지"""
        # 유사한 쿼리 패턴 찾기
        query_patterns = {}
        
        for query in queries:
            sql = query['sql']
            # 파라미터를 제거한 쿼리 패턴 추출
            pattern = self._extract_query_pattern(sql)
            
            if pattern in query_patterns:
                query_patterns[pattern] += 1
            else:
                query_patterns[pattern] = 1
        
        # N+1 패턴 감지
        for pattern, count in query_patterns.items():
            if count > 5:  # 동일한 패턴이 5번 이상 실행
                logger.warning(f"Potential N+1 query detected: {pattern} ({count} times)")
    
    def _extract_query_pattern(self, sql: str) -> str:
        """쿼리에서 패턴 추출 (파라미터 제거)"""
        import re
        # 숫자와 문자열 리터럴을 플레이스홀더로 변경
        pattern = re.sub(r'\b\d+\b', '?', sql)
        pattern = re.sub(r"'[^']*'", '?', pattern)
        pattern = re.sub(r'"[^"]*"', '?', pattern)
        return pattern[:100]  # 처음 100자만 사용

class ResponseOptimizationMiddleware:
    """
    응답 최적화 미들웨어
    Response optimization middleware
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        
        # 응답 최적화 적용
        self._optimize_response(request, response)
        
        return response
    
    def _optimize_response(self, request: HttpRequest, response: HttpResponse) -> None:
        """응답 최적화"""
        # ETag 설정 (캐시 효율성 향상)
        if response.status_code == 200 and not response.get('ETag'):
            import hashlib
            content_hash = hashlib.md5(response.content).hexdigest()[:16]
            response['ETag'] = f'"{content_hash}"'
        
        # 캐시 제어 헤더 설정
        if request.path.startswith('/api/'):
            # API 응답은 짧은 캐시
            patch_cache_control(response, max_age=300, public=True)
        elif request.path.startswith('/static/'):
            # 정적 파일은 긴 캐시
            patch_cache_control(response, max_age=86400, public=True)
        
        # 불필요한 공백 제거 (HTML 응답에서)
        if response.get('Content-Type', '').startswith('text/html'):
            content = response.content.decode('utf-8')
            # 간단한 공백 제거 (프로덕션에서는 더 정교한 minifier 사용 권장)
            import re
            content = re.sub(r'\s+', ' ', content)
            content = re.sub(r'>\s+<', '><', content)
            response.content = content.encode('utf-8')
            response['Content-Length'] = str(len(response.content))