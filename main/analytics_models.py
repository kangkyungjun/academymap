"""
데이터 분석 및 리포팅을 위한 모델들
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import Data as Academy
from decimal import Decimal
import json
from typing import Dict, List, Any

User = get_user_model()


class AnalyticsReport(models.Model):
    """분석 리포트"""
    
    REPORT_TYPE_CHOICES = [
        ('daily', '일일 리포트'),
        ('weekly', '주간 리포트'),
        ('monthly', '월간 리포트'),
        ('quarterly', '분기 리포트'),
        ('yearly', '연간 리포트'),
        ('custom', '사용자 정의'),
    ]
    
    REPORT_CATEGORY_CHOICES = [
        ('traffic', '트래픽 분석'),
        ('user_behavior', '사용자 행동'),
        ('academy_performance', '학원 성과'),
        ('regional_analysis', '지역 분석'),
        ('market_trends', '시장 트렌드'),
        ('conversion', '전환 분석'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="리포트 제목")
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        verbose_name="리포트 유형"
    )
    category = models.CharField(
        max_length=30,
        choices=REPORT_CATEGORY_CHOICES,
        verbose_name="분석 카테고리"
    )
    
    # 분석 기간
    start_date = models.DateField(verbose_name="시작일")
    end_date = models.DateField(verbose_name="종료일")
    
    # 리포트 데이터
    data = models.JSONField(default=dict, verbose_name="분석 데이터")
    summary = models.TextField(verbose_name="요약")
    insights = models.JSONField(default=list, verbose_name="인사이트")
    recommendations = models.JSONField(default=list, verbose_name="추천사항")
    
    # 메타데이터
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="생성자"
    )
    is_public = models.BooleanField(default=False, verbose_name="공개 여부")
    
    class Meta:
        ordering = ['-generated_at']
        verbose_name = "분석 리포트"
        verbose_name_plural = "분석 리포트들"
        indexes = [
            models.Index(fields=['report_type', 'category']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.start_date} ~ {self.end_date})"


class UserAnalytics(models.Model):
    """사용자 분석 데이터"""
    
    # 기간별 집계
    date = models.DateField(verbose_name="날짜")
    
    # 사용자 통계
    total_users = models.IntegerField(default=0, verbose_name="총 사용자 수")
    new_users = models.IntegerField(default=0, verbose_name="신규 사용자 수")
    returning_users = models.IntegerField(default=0, verbose_name="재방문 사용자 수")
    
    # 세션 통계
    total_sessions = models.IntegerField(default=0, verbose_name="총 세션 수")
    avg_session_duration = models.FloatField(default=0.0, verbose_name="평균 세션 시간(초)")
    bounce_rate = models.FloatField(default=0.0, verbose_name="이탈률(%)")
    
    # 페이지 뷰
    total_pageviews = models.IntegerField(default=0, verbose_name="총 페이지 뷰")
    unique_pageviews = models.IntegerField(default=0, verbose_name="순 페이지 뷰")
    avg_pages_per_session = models.FloatField(default=0.0, verbose_name="세션당 페이지 수")
    
    # 트래픽 소스
    organic_traffic = models.IntegerField(default=0, verbose_name="자연 검색 트래픽")
    direct_traffic = models.IntegerField(default=0, verbose_name="직접 방문 트래픽")
    referral_traffic = models.IntegerField(default=0, verbose_name="추천 사이트 트래픽")
    social_traffic = models.IntegerField(default=0, verbose_name="소셜 미디어 트래픽")
    
    # 디바이스 정보
    desktop_users = models.IntegerField(default=0, verbose_name="데스크톱 사용자")
    mobile_users = models.IntegerField(default=0, verbose_name="모바일 사용자")
    tablet_users = models.IntegerField(default=0, verbose_name="태블릿 사용자")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['date']
        ordering = ['-date']
        verbose_name = "사용자 분석"
        verbose_name_plural = "사용자 분석들"
        indexes = [
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"사용자 분석 - {self.date}"


class AcademyAnalytics(models.Model):
    """학원별 분석 데이터"""
    
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='analytics_data',
        verbose_name="학원"
    )
    date = models.DateField(verbose_name="날짜")
    
    # 조회 통계
    views = models.IntegerField(default=0, verbose_name="조회수")
    unique_views = models.IntegerField(default=0, verbose_name="순 조회수")
    avg_view_duration = models.FloatField(default=0.0, verbose_name="평균 조회 시간(초)")
    
    # 참여 통계
    bookmarks = models.IntegerField(default=0, verbose_name="북마크 수")
    shares = models.IntegerField(default=0, verbose_name="공유 수")
    inquiries = models.IntegerField(default=0, verbose_name="문의 수")
    
    # 전환 통계
    conversion_rate = models.FloatField(default=0.0, verbose_name="전환율(%)")
    inquiry_conversion = models.FloatField(default=0.0, verbose_name="문의 전환율(%)")
    
    # 검색 키워드 (상위 10개)
    top_keywords = models.JSONField(default=list, verbose_name="상위 검색 키워드")
    
    # 추천 점수 변화
    recommendation_score = models.FloatField(default=0.0, verbose_name="추천 점수")
    popularity_rank = models.IntegerField(null=True, blank=True, verbose_name="인기 순위")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['academy', 'date']
        ordering = ['-date']
        verbose_name = "학원 분석"
        verbose_name_plural = "학원 분석들"
        indexes = [
            models.Index(fields=['academy', 'date']),
            models.Index(fields=['date', 'views']),
        ]
    
    def __str__(self):
        return f"{self.academy.상호명} - {self.date}"


class RegionalAnalytics(models.Model):
    """지역별 분석 데이터"""
    
    # 지역 정보
    region_sido = models.CharField(max_length=50, verbose_name="시도")
    region_sigungu = models.CharField(max_length=50, verbose_name="시군구")
    date = models.DateField(verbose_name="날짜")
    
    # 학원 통계
    total_academies = models.IntegerField(default=0, verbose_name="총 학원 수")
    active_academies = models.IntegerField(default=0, verbose_name="활성 학원 수")
    
    # 사용자 관심도
    total_views = models.IntegerField(default=0, verbose_name="총 조회수")
    unique_visitors = models.IntegerField(default=0, verbose_name="순 방문자 수")
    avg_rating = models.FloatField(default=0.0, verbose_name="평균 평점")
    
    # 수강료 통계
    avg_tuition = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="평균 수강료"
    )
    tuition_range_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="최저 수강료"
    )
    tuition_range_max = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="최고 수강료"
    )
    
    # 과목별 분포
    subject_distribution = models.JSONField(default=dict, verbose_name="과목별 분포")
    
    # 경쟁 지수
    competition_index = models.FloatField(default=0.0, verbose_name="경쟁 지수")
    market_saturation = models.FloatField(default=0.0, verbose_name="시장 포화도")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['region_sido', 'region_sigungu', 'date']
        ordering = ['-date', 'region_sido', 'region_sigungu']
        verbose_name = "지역 분석"
        verbose_name_plural = "지역 분석들"
        indexes = [
            models.Index(fields=['region_sido', 'region_sigungu']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.region_sido} {self.region_sigungu} - {self.date}"


class MarketTrend(models.Model):
    """시장 트렌드 분석"""
    
    TREND_TYPE_CHOICES = [
        ('subject_popularity', '과목별 인기도'),
        ('price_trend', '수강료 트렌드'),
        ('regional_growth', '지역별 성장률'),
        ('user_preference', '사용자 선호도'),
        ('seasonal_trend', '계절별 트렌드'),
    ]
    
    trend_type = models.CharField(
        max_length=30,
        choices=TREND_TYPE_CHOICES,
        verbose_name="트렌드 유형"
    )
    date = models.DateField(verbose_name="날짜")
    
    # 트렌드 데이터
    trend_data = models.JSONField(default=dict, verbose_name="트렌드 데이터")
    trend_score = models.FloatField(default=0.0, verbose_name="트렌드 점수")
    
    # 변화율
    change_rate = models.FloatField(default=0.0, verbose_name="변화율(%)")
    change_direction = models.CharField(
        max_length=20,
        choices=[
            ('up', '상승'),
            ('down', '하락'),
            ('stable', '안정'),
        ],
        default='stable',
        verbose_name="변화 방향"
    )
    
    # 예측 데이터
    prediction_data = models.JSONField(default=dict, verbose_name="예측 데이터")
    confidence_level = models.FloatField(default=0.0, verbose_name="신뢰도")
    
    description = models.TextField(blank=True, verbose_name="트렌드 설명")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['trend_type', 'date']
        ordering = ['-date', 'trend_type']
        verbose_name = "시장 트렌드"
        verbose_name_plural = "시장 트렌드들"
        indexes = [
            models.Index(fields=['trend_type', 'date']),
            models.Index(fields=['date', 'trend_score']),
        ]
    
    def __str__(self):
        return f"{self.get_trend_type_display()} - {self.date}"


class ConversionFunnel(models.Model):
    """전환 퍼널 분석"""
    
    date = models.DateField(verbose_name="날짜")
    
    # 퍼널 단계별 통계
    stage_1_visitors = models.IntegerField(default=0, verbose_name="1단계: 방문자")
    stage_2_search = models.IntegerField(default=0, verbose_name="2단계: 검색")
    stage_3_view = models.IntegerField(default=0, verbose_name="3단계: 학원 조회")
    stage_4_detail = models.IntegerField(default=0, verbose_name="4단계: 상세 조회")
    stage_5_inquiry = models.IntegerField(default=0, verbose_name="5단계: 문의")
    
    # 전환율
    search_conversion = models.FloatField(default=0.0, verbose_name="검색 전환율(%)")
    view_conversion = models.FloatField(default=0.0, verbose_name="조회 전환율(%)")
    detail_conversion = models.FloatField(default=0.0, verbose_name="상세 전환율(%)")
    inquiry_conversion = models.FloatField(default=0.0, verbose_name="문의 전환율(%)")
    
    # 이탈률
    stage_1_drop = models.FloatField(default=0.0, verbose_name="1단계 이탈률(%)")
    stage_2_drop = models.FloatField(default=0.0, verbose_name="2단계 이탈률(%)")
    stage_3_drop = models.FloatField(default=0.0, verbose_name="3단계 이탈률(%)")
    stage_4_drop = models.FloatField(default=0.0, verbose_name="4단계 이탈률(%)")
    
    # 전체 전환율
    overall_conversion = models.FloatField(default=0.0, verbose_name="전체 전환율(%)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['date']
        ordering = ['-date']
        verbose_name = "전환 퍼널"
        verbose_name_plural = "전환 퍼널들"
        indexes = [
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"전환 퍼널 - {self.date}"


class CustomDashboard(models.Model):
    """사용자 정의 대시보드"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='custom_dashboards',
        verbose_name="사용자"
    )
    
    name = models.CharField(max_length=100, verbose_name="대시보드 이름")
    description = models.TextField(blank=True, verbose_name="설명")
    
    # 대시보드 설정
    layout_config = models.JSONField(default=dict, verbose_name="레이아웃 설정")
    widget_config = models.JSONField(default=list, verbose_name="위젯 설정")
    filter_config = models.JSONField(default=dict, verbose_name="필터 설정")
    
    # 공유 설정
    is_shared = models.BooleanField(default=False, verbose_name="공유 여부")
    shared_with = models.ManyToManyField(
        User,
        blank=True,
        related_name='shared_dashboards',
        verbose_name="공유 대상"
    )
    
    is_default = models.BooleanField(default=False, verbose_name="기본 대시보드")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['user', '-is_default', 'name']
        verbose_name = "사용자 정의 대시보드"
        verbose_name_plural = "사용자 정의 대시보드들"
        indexes = [
            models.Index(fields=['user', 'is_default']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"