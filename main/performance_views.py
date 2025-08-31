"""
성능 모니터링 뷰
Performance monitoring views
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db import connection
from django.core.cache import cache
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
from .performance_services import (
    DatabaseOptimizationService,
    QueryOptimizationService,
    PerformanceMonitoringService,
    performance_monitor,
    get_system_metrics,
    optimize_settings_for_production
)
from .cache_services import (
    AcademyCacheService,
    SearchCacheService,
    StatisticsCacheService,
    get_cache_status
)

def performance_dashboard(request):
    """
    성능 모니터링 대시보드
    Performance monitoring dashboard
    """
    context = {
        'title': 'Performance Dashboard',
        'current_time': timezone.now(),
        'debug_mode': settings.DEBUG
    }
    return render(request, 'main/performance/dashboard.html', context)

def performance_metrics_api(request):
    """
    성능 메트릭 API (캐시 최적화)
    Performance metrics API (cache optimized)
    """
    try:
        # 캐시에서 확인 (30초 캐시)
        cache_key = 'performance_metrics_full'
        cached_data = cache.get(cache_key)
        if cached_data:
            return JsonResponse({
                'status': 'success',
                'data': cached_data,
                'cached': True
            })
            
        # 기본 성능 메트릭
        performance_summary = performance_monitor.get_performance_summary()
        
        # 시스템 메트릭
        system_metrics = get_system_metrics()
        
        # 캐시 상태
        cache_status = get_cache_status()
        
        # 데이터베이스 분석
        db_analysis = DatabaseOptimizationService.analyze_query_performance()
        
        data = {
            'performance': performance_summary,
            'system': system_metrics,
            'cache': cache_status,
            'database': db_analysis,
            'timestamp': timezone.now().isoformat()
        }
        
        # 캐시에 저장 (30초)
        cache.set(cache_key, data, 30)
        
        return JsonResponse({
            'status': 'success',
            'data': data,
            'cached': False
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)

@staff_member_required
def cache_management_api(request):
    """
    캐시 관리 API
    Cache management API
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'clear_all':
                cache.clear()
                return JsonResponse({
                    'status': 'success',
                    'message': 'All cache cleared successfully'
                })
            
            elif action == 'clear_academy':
                AcademyCacheService.invalidate_academy_cache()
                return JsonResponse({
                    'status': 'success',
                    'message': 'Academy cache cleared successfully'
                })
            
            elif action == 'warm_up':
                from .cache_services import warm_up_cache
                warm_up_cache()
                return JsonResponse({
                    'status': 'success',
                    'message': 'Cache warm-up completed successfully'
                })
            
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid action'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)
    
    elif request.method == 'GET':
        # 캐시 상태 정보 반환
        try:
            cache_status = get_cache_status()
            return JsonResponse({
                'status': 'success',
                'data': cache_status
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)

@staff_member_required
def database_optimization_api(request):
    """
    데이터베이스 최적화 API
    Database optimization API
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'create_indexes':
                result = DatabaseOptimizationService.create_recommended_indexes()
                return JsonResponse({
                    'status': 'success' if result['success'] else 'error',
                    'data': result
                })
            
            elif action == 'analyze_queries':
                analysis = DatabaseOptimizationService.analyze_query_performance()
                return JsonResponse({
                    'status': 'success',
                    'data': analysis
                })
            
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid action'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)
    
    elif request.method == 'GET':
        # 데이터베이스 최적화 제안사항 반환
        try:
            suggestions = DatabaseOptimizationService.optimize_database_indexes()
            return JsonResponse({
                'status': 'success',
                'data': suggestions
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)

@staff_member_required
def system_health_api(request):
    """
    시스템 상태 API
    System health API
    """
    try:
        # 시스템 메트릭 수집
        system_metrics = get_system_metrics()
        
        # 성능 메트릭
        performance_summary = performance_monitor.get_performance_summary()
        
        # 캐시 상태
        cache_status = get_cache_status()
        
        # 전체 상태 평가
        health_score = calculate_health_score(
            system_metrics, 
            performance_summary, 
            cache_status
        )
        
        return JsonResponse({
            'status': 'success',
            'data': {
                'health_score': health_score,
                'system': system_metrics,
                'performance': performance_summary,
                'cache': cache_status,
                'timestamp': timezone.now().isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)

def calculate_health_score(system_metrics, performance_summary, cache_status):
    """
    시스템 상태 점수 계산
    Calculate system health score
    """
    score = 100
    
    # CPU 사용률 체크
    if 'system' in system_metrics:
        cpu_percent = system_metrics['system'].get('cpu_percent', 0)
        if cpu_percent > 80:
            score -= 20
        elif cpu_percent > 60:
            score -= 10
    
    # 메모리 사용률 체크
    if 'system' in system_metrics:
        memory_percent = system_metrics['system']['memory'].get('percent', 0)
        if memory_percent > 90:
            score -= 20
        elif memory_percent > 75:
            score -= 10
    
    # 응답 시간 체크
    avg_time = performance_summary['request_performance'].get('avg_time', 0)
    if avg_time > 1.0:
        score -= 20
    elif avg_time > 0.5:
        score -= 10
    
    # 캐시 히트율 체크
    cache_hit_rate = performance_summary['cache_performance'].get('hit_rate', 0)
    if cache_hit_rate < 0.5:
        score -= 15
    elif cache_hit_rate < 0.7:
        score -= 5
    
    # 캐시 상태 체크
    if cache_status.get('status') != 'healthy':
        score -= 15
    
    return max(0, score)

@staff_member_required  
def production_readiness_api(request):
    """
    프로덕션 준비도 API
    Production readiness API
    """
    try:
        # 프로덕션 최적화 제안사항
        optimization_suggestions = optimize_settings_for_production()
        
        # 보안 체크
        security_checks = perform_security_checks()
        
        # 성능 체크
        performance_checks = perform_performance_checks()
        
        # 전체 준비도 점수 계산
        readiness_score = calculate_readiness_score(
            optimization_suggestions,
            security_checks,
            performance_checks
        )
        
        return JsonResponse({
            'status': 'success',
            'data': {
                'readiness_score': readiness_score,
                'optimization': optimization_suggestions,
                'security': security_checks,
                'performance': performance_checks,
                'timestamp': timezone.now().isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)

def perform_security_checks():
    """보안 체크 수행"""
    checks = []
    
    # DEBUG 설정 확인
    if settings.DEBUG:
        checks.append({
            'name': 'DEBUG Setting',
            'status': 'warning',
            'message': 'DEBUG is True in production environment'
        })
    else:
        checks.append({
            'name': 'DEBUG Setting', 
            'status': 'pass',
            'message': 'DEBUG is properly set to False'
        })
    
    # SECRET_KEY 확인
    if 'django-insecure' in settings.SECRET_KEY:
        checks.append({
            'name': 'SECRET_KEY',
            'status': 'fail',
            'message': 'Using insecure default SECRET_KEY'
        })
    else:
        checks.append({
            'name': 'SECRET_KEY',
            'status': 'pass', 
            'message': 'SECRET_KEY appears to be secure'
        })
    
    # ALLOWED_HOSTS 확인
    if '*' in settings.ALLOWED_HOSTS:
        checks.append({
            'name': 'ALLOWED_HOSTS',
            'status': 'warning',
            'message': 'ALLOWED_HOSTS contains wildcard'
        })
    else:
        checks.append({
            'name': 'ALLOWED_HOSTS',
            'status': 'pass',
            'message': 'ALLOWED_HOSTS is properly configured'
        })
    
    return checks

def perform_performance_checks():
    """성능 체크 수행"""
    checks = []
    
    # 데이터베이스 확인
    db_engine = settings.DATABASES['default']['ENGINE']
    if 'sqlite3' in db_engine:
        checks.append({
            'name': 'Database',
            'status': 'warning',
            'message': 'Using SQLite - consider PostgreSQL for production'
        })
    else:
        checks.append({
            'name': 'Database',
            'status': 'pass',
            'message': 'Using production-grade database'
        })
    
    # 캐시 확인
    cache_backend = settings.CACHES['default']['BACKEND']
    if 'locmem' in cache_backend or 'dummy' in cache_backend:
        checks.append({
            'name': 'Cache Backend',
            'status': 'warning', 
            'message': 'Using local memory cache - consider Redis'
        })
    else:
        checks.append({
            'name': 'Cache Backend',
            'status': 'pass',
            'message': 'Using distributed cache backend'
        })
    
    return checks

def calculate_readiness_score(optimization, security, performance):
    """프로덕션 준비도 점수 계산"""
    total_score = 100
    
    # 최적화 제안사항 감점
    high_priority = optimization.get('high_priority', 0)
    total_score -= (high_priority * 15)
    
    # 보안 체크 감점
    security_fails = len([c for c in security if c['status'] == 'fail'])
    security_warnings = len([c for c in security if c['status'] == 'warning']) 
    total_score -= (security_fails * 20)
    total_score -= (security_warnings * 10)
    
    # 성능 체크 감점  
    performance_warnings = len([c for c in performance if c['status'] == 'warning'])
    total_score -= (performance_warnings * 15)
    
    return max(0, total_score)

@csrf_exempt
@require_http_methods(["POST"])
def performance_alert_api(request):
    """
    성능 알림 API (모니터링 시스템에서 호출)
    Performance alert API (called by monitoring systems)
    """
    try:
        data = json.loads(request.body)
        alert_type = data.get('type')
        severity = data.get('severity', 'info')
        message = data.get('message', '')
        
        # 알림 로깅
        logger_method = getattr(logger, severity, logger.info)
        logger_method(f"Performance Alert [{alert_type}]: {message}")
        
        # 여기에 알림 처리 로직 추가 (이메일, 슬랙 등)
        # process_performance_alert(alert_type, severity, message)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Alert processed successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)

@staff_member_required
def performance_report_api(request):
    """
    성능 리포트 API
    Performance report API
    """
    try:
        # 리포트 기간 설정
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)  # 지난 7일
        
        # 성능 메트릭 수집
        performance_summary = performance_monitor.get_performance_summary()
        
        # 시스템 메트릭
        system_metrics = get_system_metrics()
        
        # 데이터베이스 분석
        db_analysis = DatabaseOptimizationService.analyze_query_performance()
        
        # 리포트 생성
        report = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'summary': {
                'total_requests': performance_summary['request_performance']['total_requests'],
                'avg_response_time': performance_summary['request_performance']['avg_time'],
                'cache_hit_rate': performance_summary['cache_performance']['hit_rate'],
                'error_count': performance_summary['error_rate']['total_errors']
            },
            'recommendations': generate_performance_recommendations(
                performance_summary, system_metrics, db_analysis
            ),
            'generated_at': timezone.now().isoformat()
        }
        
        return JsonResponse({
            'status': 'success',
            'data': report
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)

def generate_performance_recommendations(performance_summary, system_metrics, db_analysis):
    """성능 개선 권장사항 생성"""
    recommendations = []
    
    # 응답 시간 분석
    avg_time = performance_summary['request_performance']['avg_time']
    if avg_time > 0.5:
        recommendations.append({
            'category': 'Response Time',
            'priority': 'high',
            'issue': f'Average response time is {avg_time:.3f}s',
            'recommendation': 'Consider implementing caching or optimizing database queries'
        })
    
    # 캐시 히트율 분석
    cache_hit_rate = performance_summary['cache_performance']['hit_rate']
    if cache_hit_rate < 0.7:
        recommendations.append({
            'category': 'Cache Performance',
            'priority': 'medium',
            'issue': f'Cache hit rate is {cache_hit_rate:.1%}',
            'recommendation': 'Implement more aggressive caching strategy'
        })
    
    # 데이터베이스 쿼리 분석
    if 'slow_queries' in db_analysis and len(db_analysis['slow_queries']) > 0:
        recommendations.append({
            'category': 'Database Performance',
            'priority': 'high',
            'issue': f'{len(db_analysis["slow_queries"])} slow queries detected',
            'recommendation': 'Optimize slow queries and add database indexes'
        })
    
    return recommendations