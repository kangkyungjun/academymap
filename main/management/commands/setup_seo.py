"""
SEO 초기 설정 명령어
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

try:
    from main.seo_models import SEOMetadata, RobotsRule, SitemapEntry
    from main.seo_services import SitemapService, AcademySEOService
    from main.models import Data as Academy
except ImportError:
    pass


class Command(BaseCommand):
    help = 'SEO 초기 설정 및 데이터 생성'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--generate-sitemap',
            action='store_true',
            help='사이트맵 생성',
        )
        parser.add_argument(
            '--optimize-academies',
            action='store_true',
            help='학원 SEO 최적화',
        )
        parser.add_argument(
            '--setup-metadata',
            action='store_true',
            help='기본 메타데이터 설정',
        )
        parser.add_argument(
            '--setup-robots',
            action='store_true',
            help='robots.txt 규칙 설정',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='모든 SEO 설정 실행',
        )
    
    def handle(self, *args, **options):
        try:
            if options['all']:
                self.setup_metadata()
                self.setup_robots()
                self.generate_sitemap()
                self.optimize_academies()
            else:
                if options['setup_metadata']:
                    self.setup_metadata()
                if options['setup_robots']:
                    self.setup_robots()
                if options['generate_sitemap']:
                    self.generate_sitemap()
                if options['optimize_academies']:
                    self.optimize_academies()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'SEO 설정 중 오류가 발생했습니다: {e}')
            )
    
    def setup_metadata(self):
        """기본 메타데이터 설정"""
        self.stdout.write('기본 메타데이터를 설정하는 중...')
        
        try:
            # 홈페이지 메타데이터
            homepage_meta, created = SEOMetadata.objects.get_or_create(
                path='/',
                defaults={
                    'page_type': 'homepage',
                    'title': 'AcademyMap - 전국 학원 정보 검색',
                    'description': '전국 학원 정보를 한 곳에서 확인하세요. 지역별, 과목별 학원 검색과 수강료 비교 서비스.',
                    'keywords': '학원, 교육, 수강료, 학원 검색, 학원 찾기, 교육기관, 지역별 학원, 과목별 학원',
                    'og_title': 'AcademyMap - 전국 학원 정보',
                    'og_description': '전국 학원 정보를 검색하고 비교하세요.',
                    'og_image': 'https://academymap.co.kr/static/images/og-home.jpg',
                    'priority': 1.0,
                    'changefreq': 'daily'
                }
            )
            
            # 검색 페이지 메타데이터
            search_meta, created = SEOMetadata.objects.get_or_create(
                path='/search',
                defaults={
                    'page_type': 'search',
                    'title': '학원 검색 - AcademyMap',
                    'description': '지역별, 과목별 학원 검색으로 원하는 학원을 찾아보세요. 수강료 비교와 리뷰 확인이 가능합니다.',
                    'keywords': '학원 검색, 지역별 학원, 과목별 학원, 수강료 비교, 학원 리뷰',
                    'priority': 0.9,
                    'changefreq': 'weekly'
                }
            )
            
            # 학원 관리 페이지 메타데이터
            manage_meta, created = SEOMetadata.objects.get_or_create(
                path='/manage',
                defaults={
                    'page_type': 'custom',
                    'title': '학원 관리 - AcademyMap',
                    'description': '학원 정보를 등록하고 관리하세요.',
                    'keywords': '학원 등록, 학원 관리, 학원 정보 수정',
                    'priority': 0.3,
                    'changefreq': 'monthly'
                }
            )
            
            self.stdout.write(
                self.style.SUCCESS('✅ 기본 메타데이터 설정 완료')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 메타데이터 설정 실패: {e}')
            )
    
    def setup_robots(self):
        """robots.txt 규칙 설정"""
        self.stdout.write('robots.txt 규칙을 설정하는 중...')
        
        try:
            # 기존 규칙 삭제
            RobotsRule.objects.all().delete()
            
            # 새 규칙 생성
            robots_rules = [
                # 모든 봇 허용
                {'user_agent': '*', 'rule_type': 'allow', 'path': '/', 'order': 1},
                
                # 관리자 페이지 차단
                {'user_agent': '*', 'rule_type': 'disallow', 'path': '/admin/', 'order': 2},
                {'user_agent': '*', 'rule_type': 'disallow', 'path': '/manage/', 'order': 3},
                
                # API 차단
                {'user_agent': '*', 'rule_type': 'disallow', 'path': '/api/', 'order': 4},
                {'user_agent': '*', 'rule_type': 'disallow', 'path': '/map_api/', 'order': 5},
                
                # 개인정보 관련 차단
                {'user_agent': '*', 'rule_type': 'disallow', 'path': '/auth/', 'order': 6},
                {'user_agent': '*', 'rule_type': 'disallow', 'path': '/accounts/', 'order': 7},
                
                # 임시 파일 차단
                {'user_agent': '*', 'rule_type': 'disallow', 'path': '/media/temp/', 'order': 8},
                {'user_agent': '*', 'rule_type': 'disallow', 'path': '/static/temp/', 'order': 9},
            ]
            
            for rule_data in robots_rules:
                RobotsRule.objects.create(**rule_data)
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ robots.txt 규칙 {len(robots_rules)}개 생성 완료')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ robots.txt 설정 실패: {e}')
            )
    
    def generate_sitemap(self):
        """사이트맵 생성"""
        self.stdout.write('사이트맵을 생성하는 중...')
        
        try:
            entries_count = SitemapService.generate_sitemap_entries()
            self.stdout.write(
                self.style.SUCCESS(f'✅ 사이트맵 {entries_count}개 엔트리 생성 완료')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 사이트맵 생성 실패: {e}')
            )
    
    def optimize_academies(self):
        """학원 SEO 최적화"""
        self.stdout.write('학원 SEO를 최적화하는 중...')
        
        try:
            academies = Academy.objects.all()[:100]  # 상위 100개 학원만 최적화
            optimized_count = 0
            
            for academy in academies:
                try:
                    if AcademySEOService.optimize_academy_seo(academy):
                        optimized_count += 1
                        if optimized_count % 10 == 0:
                            self.stdout.write(f'  - {optimized_count}개 학원 최적화 완료...')
                except Exception as e:
                    self.stdout.write(f'  - {academy.상호명} 최적화 실패: {e}')
                    continue
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ {optimized_count}개 학원 SEO 최적화 완료')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 학원 SEO 최적화 실패: {e}')
            )