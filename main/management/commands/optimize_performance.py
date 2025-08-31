"""
성능 최적화 관리 명령어
Performance optimization management command
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from main.performance_services import (
    DatabaseOptimizationService,
    QueryOptimizationService,
    performance_monitor
)
from main.cache_services import warm_up_cache, get_cache_status
import time

class Command(BaseCommand):
    help = '성능 최적화 작업 수행 (Performance optimization tasks)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            default='all',
            choices=[
                'all', 'cache', 'database', 'indexes', 
                'analyze', 'warmup', 'status'
            ],
            help='수행할 최적화 작업 선택'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='상세한 출력 표시'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 실행 없이 계획만 표시'
        )

    def handle(self, *args, **options):
        action = options['action']
        verbose = options['verbose']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'🚀 성능 최적화 시작 - {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('⚠️  DRY RUN 모드 - 실제 변경사항 없음')
            )
        
        start_time = time.time()
        
        try:
            if action == 'all' or action == 'status':
                self._show_system_status(verbose)
            
            if action == 'all' or action == 'cache':
                self._optimize_cache(dry_run, verbose)
            
            if action == 'all' or action == 'database':
                self._optimize_database(dry_run, verbose)
            
            if action == 'all' or action == 'indexes':
                self._create_indexes(dry_run, verbose)
            
            if action == 'all' or action == 'analyze':
                self._analyze_performance(verbose)
            
            if action == 'all' or action == 'warmup':
                self._warmup_cache(dry_run, verbose)
            
            end_time = time.time()
            duration = end_time - start_time
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ 성능 최적화 완료! 소요시간: {duration:.2f}초'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 최적화 중 오류 발생: {str(e)}')
            )

    def _show_system_status(self, verbose):
        """시스템 상태 표시"""
        self.stdout.write('\n📊 시스템 상태 확인')
        self.stdout.write('-' * 50)
        
        # 캐시 상태
        cache_status = get_cache_status()
        cache_icon = '✅' if cache_status['status'] == 'healthy' else '❌'
        self.stdout.write(f'{cache_icon} 캐시 시스템: {cache_status["status"]}')
        
        if verbose:
            self.stdout.write(f'   - 백엔드: {cache_status.get("backend", "N/A")}')
            self.stdout.write(f'   - 위치: {cache_status.get("location", "N/A")}')
        
        # 데이터베이스 상태
        query_count = len(connection.queries)
        self.stdout.write(f'🗄️  데이터베이스 쿼리 수: {query_count}')
        
        # 성능 메트릭
        perf_summary = performance_monitor.get_performance_summary()
        avg_time = perf_summary['request_performance']['avg_time']
        self.stdout.write(f'⏱️  평균 응답시간: {avg_time:.3f}초')
        
        if verbose:
            cache_hit_rate = perf_summary['cache_performance']['hit_rate']
            self.stdout.write(f'   - 캐시 적중률: {cache_hit_rate:.1%}')
            self.stdout.write(f'   - 총 요청 수: {perf_summary["request_performance"]["total_requests"]}')

    def _optimize_cache(self, dry_run, verbose):
        """캐시 최적화"""
        self.stdout.write('\n🚀 캐시 최적화')
        self.stdout.write('-' * 50)
        
        if dry_run:
            self.stdout.write('계획된 작업:')
            self.stdout.write('  - 캐시 클리어 및 재설정')
            self.stdout.write('  - 캐시 설정 최적화')
            return
        
        try:
            # 캐시 클리어
            cache.clear()
            self.stdout.write('✅ 캐시 클리어 완료')
            
            # 캐시 상태 확인
            status = get_cache_status()
            if status['status'] == 'healthy':
                self.stdout.write('✅ 캐시 시스템 정상 동작')
            else:
                self.stdout.write('⚠️ 캐시 시스템 문제 감지')
            
        except Exception as e:
            self.stdout.write(f'❌ 캐시 최적화 실패: {str(e)}')

    def _optimize_database(self, dry_run, verbose):
        """데이터베이스 최적화"""
        self.stdout.write('\n🗄️ 데이터베이스 최적화')
        self.stdout.write('-' * 50)
        
        # 쿼리 성능 분석
        analysis = DatabaseOptimizationService.analyze_query_performance()
        
        if 'error' not in analysis:
            self.stdout.write(f'📈 총 쿼리 수: {analysis["total_queries"]}')
            self.stdout.write(f'⏱️ 총 쿼리 시간: {analysis["query_time"]:.3f}초')
            
            slow_queries = analysis.get('slow_queries', [])
            if slow_queries:
                self.stdout.write(f'🐌 느린 쿼리: {len(slow_queries)}개')
                if verbose:
                    for query in slow_queries[:3]:  # 상위 3개만 표시
                        self.stdout.write(f'   - {query["time"]}초: {query["sql"][:100]}...')
            
            duplicates = analysis.get('duplicate_queries', [])
            if duplicates:
                self.stdout.write(f'🔄 중복 쿼리: {len(duplicates)}개')
                if verbose:
                    for dup in duplicates[:3]:
                        self.stdout.write(f'   - {dup["count"]}회: {dup["query"]}')
        
        if dry_run:
            self.stdout.write('\n계획된 최적화:')
            self.stdout.write('  - 쿼리 최적화 적용')
            self.stdout.write('  - 불필요한 쿼리 제거')

    def _create_indexes(self, dry_run, verbose):
        """인덱스 생성"""
        self.stdout.write('\n📚 데이터베이스 인덱스 최적화')
        self.stdout.write('-' * 50)
        
        # 인덱스 제안사항 분석
        suggestions = DatabaseOptimizationService.optimize_database_indexes()
        
        self.stdout.write(f'💡 제안된 인덱스: {suggestions["total_suggestions"]}개')
        self.stdout.write(f'📈 예상 성능 향상: {suggestions["estimated_performance_gain"]}')
        
        if verbose:
            for suggestion in suggestions['suggestions']:
                self.stdout.write(f'   - {suggestion["table"]}.{suggestion.get("field", suggestion.get("fields"))}')
                self.stdout.write(f'     이유: {suggestion["reason"]}')
        
        if dry_run:
            self.stdout.write('\n계획된 인덱스 생성:')
            for suggestion in suggestions['suggestions']:
                self.stdout.write(f'   - {suggestion["sql"]}')
            return
        
        # 실제 인덱스 생성
        result = DatabaseOptimizationService.create_recommended_indexes()
        
        if result['success']:
            self.stdout.write('✅ 권장 인덱스 생성 완료')
            for index in result['created_indexes']:
                self.stdout.write(f'   - {index}')
        else:
            self.stdout.write(f'❌ 인덱스 생성 실패: {result["error"]}')

    def _analyze_performance(self, verbose):
        """성능 분석"""
        self.stdout.write('\n📊 성능 분석')
        self.stdout.write('-' * 50)
        
        # 성능 메트릭 수집
        perf_summary = performance_monitor.get_performance_summary()
        
        # 요청 성능
        req_perf = perf_summary['request_performance']
        self.stdout.write(f'🌐 요청 성능:')
        self.stdout.write(f'   - 평균 응답시간: {req_perf["avg_time"]:.3f}초')
        self.stdout.write(f'   - 최대 응답시간: {req_perf["max_time"]:.3f}초')
        self.stdout.write(f'   - 총 요청 수: {req_perf["total_requests"]}')
        
        # 쿼리 성능
        query_perf = perf_summary['query_performance']
        if query_perf['total_queries'] > 0:
            self.stdout.write(f'🗄️ 쿼리 성능:')
            self.stdout.write(f'   - 요청당 평균 쿼리: {query_perf["avg_queries_per_request"]:.1f}')
            self.stdout.write(f'   - 최대 쿼리 수: {query_perf["max_queries"]}')
            self.stdout.write(f'   - 총 쿼리 수: {query_perf["total_queries"]}')
        
        # 캐시 성능
        cache_perf = perf_summary['cache_performance']
        self.stdout.write(f'💾 캐시 성능:')
        self.stdout.write(f'   - 적중률: {cache_perf["hit_rate"]:.1%}')
        self.stdout.write(f'   - 히트: {cache_perf["total_hits"]}')
        self.stdout.write(f'   - 미스: {cache_perf["total_misses"]}')
        
        # 성능 등급 평가
        self._evaluate_performance(req_perf, cache_perf)

    def _evaluate_performance(self, req_perf, cache_perf):
        """성능 등급 평가"""
        avg_time = req_perf['avg_time']
        cache_hit_rate = cache_perf['hit_rate']
        
        # 성능 점수 계산
        time_score = 100 if avg_time < 0.1 else max(0, 100 - (avg_time - 0.1) * 200)
        cache_score = cache_hit_rate * 100
        
        overall_score = (time_score + cache_score) / 2
        
        if overall_score >= 90:
            grade = '🏆 우수'
            color = self.style.SUCCESS
        elif overall_score >= 70:
            grade = '👍 양호'
            color = self.style.WARNING
        elif overall_score >= 50:
            grade = '⚠️ 보통'
            color = self.style.WARNING
        else:
            grade = '🚨 개선 필요'
            color = self.style.ERROR
        
        self.stdout.write(f'\n📊 전체 성능 등급: ', ending='')
        self.stdout.write(color(f'{grade} ({overall_score:.1f}점)'))

    def _warmup_cache(self, dry_run, verbose):
        """캐시 워밍업"""
        self.stdout.write('\n🔥 캐시 워밍업')
        self.stdout.write('-' * 50)
        
        if dry_run:
            self.stdout.write('계획된 작업:')
            self.stdout.write('  - 자주 사용되는 데이터 캐시 로드')
            self.stdout.write('  - 통계 데이터 캐시 생성')
            return
        
        try:
            warm_up_cache()
            self.stdout.write('✅ 캐시 워밍업 완료')
            
            # 워밍업 결과 확인
            cache_status = get_cache_status()
            if cache_status['status'] == 'healthy':
                self.stdout.write('✅ 캐시 시스템 정상 작동 확인')
            
        except Exception as e:
            self.stdout.write(f'❌ 캐시 워밍업 실패: {str(e)}')