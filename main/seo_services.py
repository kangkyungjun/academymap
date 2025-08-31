"""
SEO 최적화 서비스
"""

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q, F
from django.template.loader import render_to_string
from typing import Dict, List, Any, Optional
import re
import json
from datetime import datetime, timedelta
from urllib.parse import urljoin

try:
    from .seo_models import (
        SEOMetadata, AcademySEO, SearchKeyword, 
        SitemapEntry, RobotsRule, SEOAudit
    )
    from .models import Data as Academy
except ImportError:
    pass


class SEOMetadataService:
    """SEO 메타데이터 관리 서비스"""
    
    @staticmethod
    def get_metadata(path: str) -> Optional[Dict[str, Any]]:
        """경로에 해당하는 SEO 메타데이터 조회"""
        try:
            seo_meta = SEOMetadata.objects.filter(
                path=path, is_active=True
            ).first()
            
            if seo_meta:
                return {
                    'title': seo_meta.title,
                    'description': seo_meta.description,
                    'keywords': seo_meta.keywords,
                    'og_title': seo_meta.og_title or seo_meta.title,
                    'og_description': seo_meta.og_description or seo_meta.description,
                    'og_image': seo_meta.og_image,
                    'twitter_title': seo_meta.twitter_title or seo_meta.title,
                    'twitter_description': seo_meta.twitter_description or seo_meta.description,
                    'twitter_image': seo_meta.twitter_image,
                    'schema_type': seo_meta.schema_type,
                    'schema_data': seo_meta.schema_data,
                }
            
            return None
        except Exception:
            return None
    
    @staticmethod
    def create_academy_metadata(academy: Academy) -> Dict[str, Any]:
        """학원 상세 페이지용 동적 메타데이터 생성"""
        try:
            # 기본 정보
            name = academy.상호명
            region = f"{academy.시도명} {academy.시군구명}"
            subjects = []
            
            # 과목 정보 수집
            subject_fields = [
                '과목_수학', '과목_영어', '과목_과학', '과목_외국어',
                '과목_논술', '과목_예체능', '과목_컴퓨터', '과목_기타'
            ]
            for field in subject_fields:
                if getattr(academy, field, False):
                    subject_name = field.replace('과목_', '')
                    subjects.append(subject_name)
            
            # 대상 연령 수집
            targets = []
            if academy.대상_초등: targets.append('초등')
            if academy.대상_중등: targets.append('중등')
            if academy.대상_고등: targets.append('고등')
            
            # SEO 제목 생성
            title_parts = [name]
            if subjects:
                title_parts.append(f"{', '.join(subjects[:2])}")
            title_parts.append(region)
            title = f"{' | '.join(title_parts)} - AcademyMap"
            
            # SEO 설명 생성
            description_parts = [f"{region}의 {name}"]
            if subjects:
                description_parts.append(f"{', '.join(subjects[:3])} 전문")
            if targets:
                description_parts.append(f"{', '.join(targets)} 대상")
            if academy.수강료_평균:
                description_parts.append(f"평균 수강료 {academy.수강료_평균:,}원")
            
            description = f"{' '.join(description_parts)}. 위치, 수강료, 리뷰 정보를 확인하세요."
            
            # 키워드 생성
            keywords = [name, region, academy.시도명, academy.시군구명]
            keywords.extend(subjects)
            keywords.extend(targets)
            keywords.extend(['학원', '교육', '수강료', '리뷰'])
            
            # 구조화된 데이터 (Local Business Schema)
            schema_data = {
                "@context": "https://schema.org",
                "@type": "EducationalOrganization",
                "name": name,
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": academy.도로명주소 or academy.지번주소,
                    "addressLocality": academy.시군구명,
                    "addressRegion": academy.시도명,
                    "addressCountry": "KR"
                },
                "telephone": academy.전화번호,
                "url": f"{settings.SITE_URL}/academy/{academy.id}",
                "description": description,
            }
            
            # 평점 정보 추가
            if academy.별점 and academy.별점 > 0:
                schema_data["aggregateRating"] = {
                    "@type": "AggregateRating",
                    "ratingValue": academy.별점,
                    "bestRating": 5
                }
            
            # 좌표 정보 추가
            if academy.경도 and academy.위도:
                schema_data["geo"] = {
                    "@type": "GeoCoordinates",
                    "latitude": academy.위도,
                    "longitude": academy.경도
                }
            
            return {
                'title': title[:60],  # 60자 제한
                'description': description[:160],  # 160자 제한
                'keywords': ', '.join(keywords[:20]),  # 상위 20개 키워드
                'schema_data': schema_data,
                'og_title': title[:60],
                'og_description': description[:160],
                'twitter_title': title[:60],
                'twitter_description': description[:160],
            }
            
        except Exception as e:
            return {
                'title': f"{academy.상호명} - AcademyMap",
                'description': f"{academy.상호명}의 정보를 확인하세요.",
                'keywords': f"{academy.상호명}, 학원, {academy.시도명}",
            }
    
    @staticmethod
    def create_search_metadata(
        region: str = None, 
        subjects: List[str] = None, 
        targets: List[str] = None
    ) -> Dict[str, Any]:
        """검색 페이지용 동적 메타데이터 생성"""
        try:
            title_parts = ['학원 찾기']
            description_parts = []
            keywords = ['학원 검색', '학원 찾기', '교육']
            
            if region:
                title_parts.append(region)
                description_parts.append(f"{region} 지역")
                keywords.extend([region, f"{region} 학원"])
            
            if subjects:
                subject_text = ', '.join(subjects[:3])
                title_parts.append(subject_text)
                description_parts.append(f"{subject_text} 전문")
                keywords.extend(subjects)
            
            if targets:
                target_text = ', '.join(targets)
                title_parts.append(f"{target_text} 대상")
                description_parts.append(f"{target_text} 대상")
                keywords.extend([f"{t} 학원" for t in targets])
            
            title = f"{' '.join(title_parts)} - AcademyMap"
            
            if description_parts:
                description = f"{' '.join(description_parts)} 학원을 찾아보세요. 위치, 수강료, 리뷰 비교 가능."
            else:
                description = "전국 학원 정보를 한 곳에서 확인하세요. 지역별, 과목별 검색과 수강료 비교."
            
            return {
                'title': title[:60],
                'description': description[:160],
                'keywords': ', '.join(keywords[:15]),
            }
            
        except Exception:
            return {
                'title': "학원 검색 - AcademyMap",
                'description': "전국 학원 정보를 검색하고 비교하세요.",
                'keywords': "학원 검색, 학원 찾기, 교육",
            }


class AcademySEOService:
    """학원 SEO 관리 서비스"""
    
    @staticmethod
    def optimize_academy_seo(academy: Academy) -> Optional['AcademySEO']:
        """학원 SEO 데이터 최적화"""
        try:
            academy_seo, created = AcademySEO.objects.get_or_create(
                academy=academy,
                defaults={
                    'seo_title': '',
                    'seo_description': '',
                    'seo_keywords': '',
                    'slug': f"academy-{academy.id}",
                }
            )
            
            # 메타데이터 생성
            metadata = SEOMetadataService.create_academy_metadata(academy)
            
            # SEO 데이터 업데이트
            academy_seo.seo_title = metadata['title']
            academy_seo.seo_description = metadata['description']
            academy_seo.seo_keywords = metadata['keywords']
            
            # 슬러그 생성 (한글 지원)
            slug_base = re.sub(r'[^\w\s-]', '', academy.상호명)
            slug_base = re.sub(r'[-\s]+', '-', slug_base).strip('-')
            academy_seo.slug = f"{slug_base}-{academy.id}".lower()
            
            # 지역 키워드 생성
            local_keywords = []
            if academy.시도명:
                local_keywords.append(academy.시도명)
                local_keywords.append(f"{academy.시도명} 학원")
            if academy.시군구명:
                local_keywords.append(academy.시군구명)
                local_keywords.append(f"{academy.시군구명} 학원")
            if academy.시도명 and academy.시군구명:
                local_keywords.append(f"{academy.시도명} {academy.시군구명} 학원")
            
            academy_seo.local_keywords = ', '.join(filter(None, local_keywords))
            
            # 운영시간 (기본값)
            academy_seo.business_hours = {
                "monday": "09:00-22:00",
                "tuesday": "09:00-22:00", 
                "wednesday": "09:00-22:00",
                "thursday": "09:00-22:00",
                "friday": "09:00-22:00",
                "saturday": "09:00-18:00",
                "sunday": "휴무"
            }
            
            # SEO 점수 계산
            academy_seo.seo_score = AcademySEOService.calculate_seo_score(academy, academy_seo)
            
            academy_seo.save()
            return academy_seo
            
        except Exception as e:
            print(f"Academy SEO optimization error: {e}")
            return None
    
    @staticmethod
    def calculate_seo_score(academy: Academy, academy_seo: 'AcademySEO') -> int:
        """SEO 점수 계산 (0-100)"""
        score = 0
        
        # 기본 정보 완성도 (40점)
        if academy.상호명: score += 5
        if academy.도로명주소 or academy.지번주소: score += 5
        if academy.전화번호: score += 5
        if academy.경도 and academy.위도: score += 10
        if academy_seo.seo_title and len(academy_seo.seo_title) <= 60: score += 8
        if academy_seo.seo_description and len(academy_seo.seo_description) <= 160: score += 7
        
        # 콘텐츠 풍부도 (30점)
        subjects_count = sum([
            academy.과목_수학, academy.과목_영어, academy.과목_과학,
            academy.과목_외국어, academy.과목_논술, academy.과목_예체능,
            academy.과목_컴퓨터, academy.과목_기타
        ])
        score += min(subjects_count * 3, 15)  # 최대 15점
        
        targets_count = sum([academy.대상_초등, academy.대상_중등, academy.대상_고등])
        score += min(targets_count * 2, 6)  # 최대 6점
        
        if academy.수강료_평균: score += 5
        if academy.별점: score += 4
        
        # 키워드 최적화 (20점)
        if academy_seo.seo_keywords:
            keyword_count = len(academy_seo.seo_keywords.split(','))
            score += min(keyword_count, 10)  # 최대 10점
        
        if academy_seo.local_keywords:
            local_keyword_count = len(academy_seo.local_keywords.split(','))
            score += min(local_keyword_count, 10)  # 최대 10점
        
        # 소셜 미디어 및 추가 정보 (10점)
        if academy_seo.facebook_url: score += 2
        if academy_seo.instagram_url: score += 2
        if academy_seo.blog_url: score += 2
        if academy_seo.review_count > 0: score += 2
        if academy_seo.average_rating > 0: score += 2
        
        return min(score, 100)  # 최대 100점


class SearchKeywordService:
    """검색 키워드 분석 서비스"""
    
    @staticmethod
    def track_search(keyword: str, region_sido: str = None, region_sigungu: str = None):
        """검색 키워드 추적"""
        try:
            today = timezone.now().date()
            
            search_keyword, created = SearchKeyword.objects.get_or_create(
                keyword=keyword,
                date=today,
                defaults={
                    'search_count': 0,
                    'click_count': 0,
                    'impression_count': 0,
                    'region_sido': region_sido or '',
                    'region_sigungu': region_sigungu or '',
                    'category': SearchKeywordService.categorize_keyword(keyword)
                }
            )
            
            search_keyword.search_count = F('search_count') + 1
            search_keyword.impression_count = F('impression_count') + 1
            search_keyword.save(update_fields=['search_count', 'impression_count'])
            
            return search_keyword
            
        except Exception as e:
            print(f"Search tracking error: {e}")
            return None
    
    @staticmethod
    def track_click(keyword: str):
        """클릭 추적"""
        try:
            today = timezone.now().date()
            
            search_keyword = SearchKeyword.objects.filter(
                keyword=keyword, date=today
            ).first()
            
            if search_keyword:
                search_keyword.click_count = F('click_count') + 1
                search_keyword.save(update_fields=['click_count'])
            
        except Exception as e:
            print(f"Click tracking error: {e}")
    
    @staticmethod
    def categorize_keyword(keyword: str) -> str:
        """키워드 분류"""
        keyword_lower = keyword.lower()
        
        # 지역 키워드
        regions = [
            '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
            '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주'
        ]
        for region in regions:
            if region in keyword:
                return 'region'
        
        # 과목 키워드
        subjects = ['수학', '영어', '국어', '과학', '사회', '논술', '예체능']
        for subject in subjects:
            if subject in keyword:
                return 'subject'
        
        # 연령대 키워드
        ages = ['초등', '중등', '고등', '유치원', '성인']
        for age in ages:
            if age in keyword:
                return 'age'
        
        # 브랜드 키워드 (주요 학원 브랜드)
        brands = ['대교', '재능', '웅진', '구몬', '눈높이', '청담', '윤선생']
        for brand in brands:
            if brand in keyword:
                return 'brand'
        
        return 'general'
    
    @staticmethod
    def get_trending_keywords(days: int = 7) -> List[Dict[str, Any]]:
        """트렌딩 키워드 조회"""
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            keywords = SearchKeyword.objects.filter(
                date__range=(start_date, end_date)
            ).values('keyword').annotate(
                total_searches=models.Sum('search_count'),
                total_clicks=models.Sum('click_count'),
                avg_ctr=models.Avg('ctr')
            ).order_by('-total_searches')[:20]
            
            return list(keywords)
            
        except Exception as e:
            print(f"Trending keywords error: {e}")
            return []


class SitemapService:
    """사이트맵 관리 서비스"""
    
    @staticmethod
    def generate_sitemap_entries():
        """사이트맵 엔트리 자동 생성"""
        try:
            # 기존 엔트리 삭제
            SitemapEntry.objects.all().delete()
            
            entries = []
            
            # 홈페이지
            entries.append(SitemapEntry(
                url='/',
                priority=1.0,
                changefreq='daily',
                page_type='homepage'
            ))
            
            # 학원 상세 페이지들
            academies = Academy.objects.filter(
                경도__isnull=False, 위도__isnull=False
            )[:1000]  # 상위 1000개만
            
            for academy in academies:
                entries.append(SitemapEntry(
                    url=f'/academy/{academy.id}',
                    priority=0.8,
                    changefreq='weekly',
                    page_type='academy',
                    lastmod=academy.updated_at if hasattr(academy, 'updated_at') else timezone.now()
                ))
            
            # 지역별 검색 페이지
            regions = Academy.objects.values('시도명', '시군구명').distinct()[:100]
            for region in regions:
                if region['시도명'] and region['시군구명']:
                    entries.append(SitemapEntry(
                        url=f'/search?region={region["시도명"]}+{region["시군구명"]}',
                        priority=0.6,
                        changefreq='weekly',
                        page_type='region'
                    ))
            
            # 과목별 검색 페이지
            subjects = ['수학', '영어', '국어', '과학', '사회', '논술']
            for subject in subjects:
                entries.append(SitemapEntry(
                    url=f'/search?subject={subject}',
                    priority=0.5,
                    changefreq='monthly',
                    page_type='category'
                ))
            
            # 벌크 생성
            SitemapEntry.objects.bulk_create(entries)
            
            return len(entries)
            
        except Exception as e:
            print(f"Sitemap generation error: {e}")
            return 0
    
    @staticmethod
    def generate_sitemap_xml() -> str:
        """XML 사이트맵 생성"""
        try:
            entries = SitemapEntry.objects.filter(is_active=True).order_by('-priority')
            
            sitemap_data = {
                'entries': [
                    {
                        'url': urljoin(settings.SITE_URL, entry.url),
                        'lastmod': entry.lastmod.isoformat(),
                        'changefreq': entry.changefreq,
                        'priority': entry.priority
                    }
                    for entry in entries
                ]
            }
            
            return render_to_string('seo/sitemap.xml', sitemap_data)
            
        except Exception as e:
            print(f"XML sitemap generation error: {e}")
            return ""


class RobotsService:
    """Robots.txt 관리 서비스"""
    
    @staticmethod
    def generate_robots_txt() -> str:
        """robots.txt 생성"""
        try:
            rules = RobotsRule.objects.filter(is_active=True).order_by('order')
            
            robots_content = []
            current_user_agent = None
            
            for rule in rules:
                if rule.user_agent != current_user_agent:
                    robots_content.append(f"User-agent: {rule.user_agent}")
                    current_user_agent = rule.user_agent
                
                action = "Allow" if rule.rule_type == 'allow' else "Disallow"
                robots_content.append(f"{action}: {rule.path}")
            
            # 사이트맵 추가
            robots_content.append("")
            robots_content.append(f"Sitemap: {settings.SITE_URL}/sitemap.xml")
            
            return "\n".join(robots_content)
            
        except Exception as e:
            print(f"Robots.txt generation error: {e}")
            return "User-agent: *\nDisallow:"


class SEOAuditService:
    """SEO 감사 서비스"""
    
    @staticmethod
    def audit_page(url: str) -> Optional['SEOAudit']:
        """페이지 SEO 감사"""
        try:
            # 기본 점수 계산 로직 (실제로는 더 복잡한 분석 필요)
            audit = SEOAudit.objects.create(
                url=url,
                overall_score=0,
                title_score=0,
                description_score=0,
                keywords_score=0,
                content_score=0,
                performance_score=0,
                issues=[],
                recommendations=[]
            )
            
            # 간단한 점수 계산 (실제 구현에서는 HTML 파싱, 성능 측정 등 필요)
            scores = SEOAuditService.calculate_audit_scores(url)
            
            audit.title_score = scores.get('title', 0)
            audit.description_score = scores.get('description', 0)
            audit.keywords_score = scores.get('keywords', 0)
            audit.content_score = scores.get('content', 0)
            audit.performance_score = scores.get('performance', 0)
            
            audit.overall_score = sum([
                audit.title_score, audit.description_score, 
                audit.keywords_score, audit.content_score, 
                audit.performance_score
            ]) // 5
            
            audit.save()
            return audit
            
        except Exception as e:
            print(f"SEO audit error: {e}")
            return None
    
    @staticmethod
    def calculate_audit_scores(url: str) -> Dict[str, int]:
        """감사 점수 계산 (임시 구현)"""
        # 실제 구현에서는 HTML 파싱, 성능 측정, 콘텐츠 분석 등이 필요
        return {
            'title': 80,
            'description': 75,
            'keywords': 70,
            'content': 85,
            'performance': 90
        }