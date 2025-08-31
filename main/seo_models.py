"""
SEO 최적화를 위한 모델들
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import Data as Academy

User = get_user_model()


class SEOMetadata(models.Model):
    """SEO 메타데이터"""
    
    PAGE_TYPE_CHOICES = [
        ('homepage', '홈페이지'),
        ('search', '검색 페이지'),
        ('academy_detail', '학원 상세'),
        ('region', '지역 페이지'),
        ('subject', '과목 페이지'),
        ('custom', '사용자 정의'),
    ]
    
    page_type = models.CharField(
        max_length=20,
        choices=PAGE_TYPE_CHOICES,
        verbose_name="페이지 유형"
    )
    path = models.CharField(max_length=255, unique=True, verbose_name="경로")
    title = models.CharField(max_length=60, verbose_name="제목")
    description = models.CharField(max_length=160, verbose_name="설명")
    keywords = models.TextField(verbose_name="키워드")
    
    # Open Graph
    og_title = models.CharField(max_length=60, blank=True, verbose_name="OG 제목")
    og_description = models.CharField(max_length=160, blank=True, verbose_name="OG 설명")
    og_image = models.URLField(blank=True, verbose_name="OG 이미지")
    
    # Twitter Card
    twitter_title = models.CharField(max_length=60, blank=True, verbose_name="트위터 제목")
    twitter_description = models.CharField(max_length=160, blank=True, verbose_name="트위터 설명")
    twitter_image = models.URLField(blank=True, verbose_name="트위터 이미지")
    
    # 구조화된 데이터
    schema_type = models.CharField(max_length=50, blank=True, verbose_name="스키마 타입")
    schema_data = models.JSONField(default=dict, verbose_name="스키마 데이터")
    
    # 설정
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    priority = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name="우선순위"
    )
    changefreq = models.CharField(
        max_length=10,
        choices=[
            ('always', '항상'),
            ('hourly', '시간별'),
            ('daily', '일별'),
            ('weekly', '주별'),
            ('monthly', '월별'),
            ('yearly', '연별'),
            ('never', '없음'),
        ],
        default='weekly',
        verbose_name="변경 빈도"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', 'path']
        verbose_name = "SEO 메타데이터"
        verbose_name_plural = "SEO 메타데이터들"
        indexes = [
            models.Index(fields=['page_type', 'is_active']),
            models.Index(fields=['path']),
        ]
    
    def __str__(self):
        return f"{self.get_page_type_display()} - {self.path}"


class AcademySEO(models.Model):
    """학원별 SEO 최적화"""
    
    academy = models.OneToOneField(
        Academy,
        on_delete=models.CASCADE,
        related_name='seo_data',
        verbose_name="학원"
    )
    
    # SEO 최적화된 제목과 설명
    seo_title = models.CharField(max_length=60, verbose_name="SEO 제목")
    seo_description = models.CharField(max_length=160, verbose_name="SEO 설명")
    seo_keywords = models.TextField(verbose_name="SEO 키워드")
    
    # URL 슬러그 (한글 지원)
    slug = models.SlugField(max_length=200, unique=True, verbose_name="URL 슬러그")
    
    # 지역 SEO
    local_keywords = models.TextField(verbose_name="지역 키워드")
    business_hours = models.JSONField(default=dict, verbose_name="운영시간")
    
    # 리뷰 및 평점 (구조화된 데이터용)
    review_count = models.IntegerField(default=0, verbose_name="리뷰 수")
    average_rating = models.FloatField(default=0.0, verbose_name="평균 평점")
    
    # 소셜 미디어
    facebook_url = models.URLField(blank=True, verbose_name="페이스북 URL")
    instagram_url = models.URLField(blank=True, verbose_name="인스타그램 URL")
    blog_url = models.URLField(blank=True, verbose_name="블로그 URL")
    
    # 최적화 점수
    seo_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="SEO 점수"
    )
    
    last_optimized = models.DateTimeField(auto_now=True, verbose_name="마지막 최적화")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-seo_score', 'academy__상호명']
        verbose_name = "학원 SEO"
        verbose_name_plural = "학원 SEO들"
        indexes = [
            models.Index(fields=['seo_score']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return f"{self.academy.상호명} - SEO ({self.seo_score}점)"


class SearchKeyword(models.Model):
    """검색 키워드 분석"""
    
    keyword = models.CharField(max_length=100, verbose_name="키워드")
    search_count = models.IntegerField(default=0, verbose_name="검색 횟수")
    click_count = models.IntegerField(default=0, verbose_name="클릭 횟수")
    
    # 키워드 분류
    category = models.CharField(
        max_length=20,
        choices=[
            ('region', '지역'),
            ('subject', '과목'),
            ('age', '연령대'),
            ('brand', '브랜드'),
            ('general', '일반'),
        ],
        default='general',
        verbose_name="카테고리"
    )
    
    # 관련 지역
    region_sido = models.CharField(max_length=50, blank=True, verbose_name="시도")
    region_sigungu = models.CharField(max_length=50, blank=True, verbose_name="시군구")
    
    # 통계
    ctr = models.FloatField(default=0.0, verbose_name="클릭률 (%)")
    impression_count = models.IntegerField(default=0, verbose_name="노출 횟수")
    
    # 트렌드
    trend_score = models.FloatField(default=0.0, verbose_name="트렌드 점수")
    is_trending = models.BooleanField(default=False, verbose_name="트렌딩 키워드")
    
    date = models.DateField(default=timezone.now, verbose_name="날짜")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['keyword', 'date']
        ordering = ['-search_count', '-trend_score']
        verbose_name = "검색 키워드"
        verbose_name_plural = "검색 키워드들"
        indexes = [
            models.Index(fields=['keyword', 'date']),
            models.Index(fields=['category', 'region_sido']),
            models.Index(fields=['-search_count']),
        ]
    
    def save(self, *args, **kwargs):
        # CTR 계산
        if self.impression_count > 0:
            self.ctr = (self.click_count / self.impression_count) * 100
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.keyword} ({self.search_count}회)"


class SitemapEntry(models.Model):
    """사이트맵 엔트리"""
    
    url = models.CharField(max_length=255, unique=True, verbose_name="URL")
    lastmod = models.DateTimeField(default=timezone.now, verbose_name="마지막 수정")
    changefreq = models.CharField(
        max_length=10,
        choices=[
            ('always', '항상'),
            ('hourly', '시간별'),
            ('daily', '일별'),
            ('weekly', '주별'),
            ('monthly', '월별'),
            ('yearly', '연별'),
            ('never', '없음'),
        ],
        default='weekly',
        verbose_name="변경 빈도"
    )
    priority = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name="우선순위"
    )
    
    # 분류
    page_type = models.CharField(
        max_length=20,
        choices=[
            ('homepage', '홈페이지'),
            ('academy', '학원'),
            ('search', '검색'),
            ('region', '지역'),
            ('category', '카테고리'),
        ],
        verbose_name="페이지 유형"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-priority', 'url']
        verbose_name = "사이트맵 엔트리"
        verbose_name_plural = "사이트맵 엔트리들"
        indexes = [
            models.Index(fields=['page_type', 'is_active']),
            models.Index(fields=['-priority']),
        ]
    
    def __str__(self):
        return self.url


class RobotsRule(models.Model):
    """Robots.txt 규칙"""
    
    user_agent = models.CharField(max_length=100, default='*', verbose_name="사용자 에이전트")
    rule_type = models.CharField(
        max_length=10,
        choices=[
            ('allow', '허용'),
            ('disallow', '차단'),
        ],
        verbose_name="규칙 유형"
    )
    path = models.CharField(max_length=255, verbose_name="경로")
    
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    order = models.IntegerField(default=0, verbose_name="순서")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'user_agent']
        verbose_name = "Robots 규칙"
        verbose_name_plural = "Robots 규칙들"
    
    def __str__(self):
        return f"{self.user_agent} - {self.get_rule_type_display()}: {self.path}"


class SEOAudit(models.Model):
    """SEO 감사 결과"""
    
    url = models.CharField(max_length=255, verbose_name="URL")
    audit_date = models.DateTimeField(auto_now_add=True, verbose_name="감사일")
    
    # 점수
    overall_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="전체 점수"
    )
    
    # 세부 점수
    title_score = models.IntegerField(default=0, verbose_name="제목 점수")
    description_score = models.IntegerField(default=0, verbose_name="설명 점수")
    keywords_score = models.IntegerField(default=0, verbose_name="키워드 점수")
    content_score = models.IntegerField(default=0, verbose_name="콘텐츠 점수")
    performance_score = models.IntegerField(default=0, verbose_name="성능 점수")
    
    # 이슈
    issues = models.JSONField(default=list, verbose_name="발견된 이슈")
    recommendations = models.JSONField(default=list, verbose_name="개선 권장사항")
    
    # 메타 정보
    load_time = models.FloatField(default=0.0, verbose_name="로드 시간 (초)")
    page_size = models.IntegerField(default=0, verbose_name="페이지 크기 (KB)")
    
    class Meta:
        ordering = ['-audit_date']
        verbose_name = "SEO 감사"
        verbose_name_plural = "SEO 감사들"
        indexes = [
            models.Index(fields=['url', '-audit_date']),
            models.Index(fields=['-overall_score']),
        ]
    
    def __str__(self):
        return f"{self.url} - {self.overall_score}점 ({self.audit_date.date()})"