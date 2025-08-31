"""
학원 상세 정보 페이지 개선을 위한 추가 모델들과 서비스
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import Data as Academy
import json
from typing import Dict, List, Any

User = get_user_model()


class AcademyDetailInfo(models.Model):
    """학원 상세 정보 확장"""
    
    academy = models.OneToOneField(
        Academy,
        on_delete=models.CASCADE,
        related_name='detail_info',
        verbose_name="학원"
    )
    
    # 시설 정보
    FACILITY_CHOICES = [
        ('parking', '주차장'),
        ('elevator', '엘리베이터'),
        ('wheelchair', '휠체어 접근'),
        ('cafe', '카페테리아'),
        ('library', '자습실'),
        ('computer_room', '컴퓨터실'),
        ('science_lab', '실험실'),
        ('auditorium', '강당'),
        ('sports', '체육시설'),
        ('air_conditioning', '냉난방'),
    ]
    
    facilities = models.JSONField(default=list, blank=True, verbose_name="시설 정보")
    total_classrooms = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name="총 강의실 수"
    )
    max_students_per_class = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name="반별 최대 학생 수"
    )
    
    # 강사 정보
    total_teachers = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name="총 강사 수"
    )
    teacher_student_ratio = models.FloatField(
        null=True, 
        blank=True, 
        verbose_name="강사:학생 비율"
    )
    
    # 운영 정보
    established_year = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name="설립년도",
        validators=[MinValueValidator(1900), MaxValueValidator(2025)]
    )
    website_url = models.URLField(blank=True, verbose_name="홈페이지")
    social_media = models.JSONField(default=dict, blank=True, verbose_name="소셜미디어")
    
    # 교육 프로그램
    programs = models.JSONField(default=list, blank=True, verbose_name="교육 프로그램")
    special_programs = models.TextField(blank=True, verbose_name="특별 프로그램")
    
    # 시간표 정보
    class_schedule = models.JSONField(default=dict, blank=True, verbose_name="시간표")
    
    # 비용 정보 (상세)
    registration_fee = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name="등록비"
    )
    material_fee = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name="교재비"
    )
    has_scholarship = models.BooleanField(default=False, verbose_name="장학금 제도")
    
    # 기타 정보
    parking_info = models.TextField(blank=True, verbose_name="주차 정보")
    transportation_info = models.TextField(blank=True, verbose_name="교통 정보")
    notice = models.TextField(blank=True, verbose_name="공지사항")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "학원 상세정보"
        verbose_name_plural = "학원 상세정보들"
    
    def __str__(self):
        return f"{self.academy.상호명} 상세정보"
    
    def get_facilities_display(self):
        """시설 정보 표시용"""
        facility_dict = dict(self.FACILITY_CHOICES)
        return [facility_dict.get(f, f) for f in self.facilities]


class AcademyGallery(models.Model):
    """학원 갤러리 (추가 이미지들)"""
    
    CATEGORY_CHOICES = [
        ('exterior', '외관'),
        ('interior', '내부'),
        ('classroom', '강의실'),
        ('facility', '시설'),
        ('activity', '활동사진'),
        ('certificate', '인증서'),
        ('event', '행사'),
    ]
    
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='gallery',
        verbose_name="학원"
    )
    
    image_url = models.URLField(max_length=500, verbose_name="이미지 URL")
    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES, 
        default='interior',
        verbose_name="카테고리"
    )
    title = models.CharField(max_length=100, blank=True, verbose_name="제목")
    description = models.TextField(blank=True, verbose_name="설명")
    order = models.IntegerField(default=0, verbose_name="정렬순서")
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "학원 갤러리"
        verbose_name_plural = "학원 갤러리들"
        ordering = ['academy', 'category', 'order']
    
    def __str__(self):
        return f"{self.academy.상호명} - {self.get_category_display()}"


class AcademyStatistics(models.Model):
    """학원 통계 정보"""
    
    academy = models.OneToOneField(
        Academy,
        on_delete=models.CASCADE,
        related_name='statistics',
        verbose_name="학원"
    )
    
    # 조회수
    view_count = models.IntegerField(default=0, verbose_name="조회수")
    monthly_views = models.IntegerField(default=0, verbose_name="월간 조회수")
    
    # 즐겨찾기
    bookmark_count = models.IntegerField(default=0, verbose_name="즐겨찾기 수")
    
    # 공유
    share_count = models.IntegerField(default=0, verbose_name="공유 수")
    
    # 리뷰 관련
    review_count = models.IntegerField(default=0, verbose_name="리뷰 수")
    average_rating = models.FloatField(default=0.0, verbose_name="평균 평점")
    
    # 순위 정보
    local_rank = models.IntegerField(null=True, blank=True, verbose_name="지역 순위")
    category_rank = models.IntegerField(null=True, blank=True, verbose_name="카테고리 순위")
    
    # 인기도 지수
    popularity_score = models.FloatField(default=0.0, verbose_name="인기도 점수")
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "학원 통계"
        verbose_name_plural = "학원 통계들"
    
    def __str__(self):
        return f"{self.academy.상호명} 통계"
    
    def calculate_popularity_score(self):
        """인기도 점수 계산"""
        score = (
            self.view_count * 0.3 +
            self.bookmark_count * 0.4 +
            self.review_count * 0.2 +
            self.average_rating * 0.1
        )
        self.popularity_score = score
        self.save(update_fields=['popularity_score'])
        return score


class AcademyViewHistory(models.Model):
    """학원 조회 기록"""
    
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='view_history',
        verbose_name="학원"
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="사용자"
    )
    
    # 방문자 정보 (비회원용)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # 방문 정보
    viewed_at = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=40, blank=True, null=True)
    referrer = models.URLField(blank=True)
    
    # 체류 시간 (초)
    duration = models.IntegerField(null=True, blank=True, verbose_name="체류시간(초)")
    
    class Meta:
        verbose_name = "조회 기록"
        verbose_name_plural = "조회 기록들"
        ordering = ['-viewed_at']
    
    def __str__(self):
        user_info = self.user.username if self.user else f"익명({self.ip_address})"
        return f"{self.academy.상호명} - {user_info}"


class AcademyFAQ(models.Model):
    """학원 자주 묻는 질문"""
    
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='faqs',
        verbose_name="학원"
    )
    
    question = models.CharField(max_length=200, verbose_name="질문")
    answer = models.TextField(verbose_name="답변")
    order = models.IntegerField(default=0, verbose_name="순서")
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "자주 묻는 질문"
        verbose_name_plural = "자주 묻는 질문들"
        ordering = ['academy', 'order']
    
    def __str__(self):
        return f"{self.academy.상호명} - {self.question[:30]}"


class AcademyNews(models.Model):
    """학원 소식/공지사항"""
    
    NEWS_TYPES = [
        ('notice', '공지사항'),
        ('event', '이벤트'),
        ('news', '소식'),
        ('achievement', '수상/성과'),
    ]
    
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='news',
        verbose_name="학원"
    )
    
    title = models.CharField(max_length=200, verbose_name="제목")
    content = models.TextField(verbose_name="내용")
    news_type = models.CharField(
        max_length=20,
        choices=NEWS_TYPES,
        default='notice',
        verbose_name="유형"
    )
    
    # 중요도
    is_important = models.BooleanField(default=False, verbose_name="중요")
    is_pinned = models.BooleanField(default=False, verbose_name="상단고정")
    
    # 게시 기간
    publish_date = models.DateTimeField(default=timezone.now, verbose_name="게시일")
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="종료일")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "학원 소식"
        verbose_name_plural = "학원 소식들"
        ordering = ['-is_pinned', '-is_important', '-publish_date']
    
    def __str__(self):
        return f"{self.academy.상호명} - {self.title}"
    
    def is_active(self):
        """게시 상태 확인"""
        now = timezone.now()
        return (
            self.publish_date <= now and 
            (self.end_date is None or self.end_date >= now)
        )


class AcademyComparison(models.Model):
    """학원 비교 데이터"""
    
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='main_comparisons',
        verbose_name="학원"
    )
    
    # 비교 대상 학원들 (같은 지역, 같은 과목)
    comparison_data = models.JSONField(default=dict, verbose_name="비교 데이터")
    
    # 강점
    strengths = models.JSONField(default=list, verbose_name="강점")
    
    # 약점
    weaknesses = models.JSONField(default=list, verbose_name="개선점")
    
    # 경쟁 학원 수
    competitor_count = models.IntegerField(default=0, verbose_name="경쟁 학원 수")
    
    # 가격 경쟁력 (백분율)
    price_competitiveness = models.FloatField(default=0.0, verbose_name="가격 경쟁력")
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "학원 비교"
        verbose_name_plural = "학원 비교들"
    
    def __str__(self):
        return f"{self.academy.상호명} 비교분석"


# 서비스 클래스들
class AcademyEnhancementService:
    """학원 정보 개선 서비스"""
    
    @staticmethod
    def get_enhanced_academy_data(academy: Academy, user=None) -> Dict:
        """학원의 향상된 정보 조회"""
        
        # 기본 정보
        data = {
            'academy': academy,
            'detail_info': getattr(academy, 'detail_info', None),
            'statistics': getattr(academy, 'statistics', None),
        }
        
        # 갤러리 정보
        gallery = academy.gallery.all().order_by('category', 'order')
        data['gallery'] = {
            category: list(gallery.filter(category=category))
            for category, _ in AcademyGallery.CATEGORY_CHOICES
        }
        
        # FAQ
        data['faqs'] = academy.faqs.filter(is_active=True).order_by('order')
        
        # 최근 소식
        data['recent_news'] = academy.news.filter(
            publish_date__lte=timezone.now()
        ).filter(
            models.Q(end_date__gte=timezone.now()) | models.Q(end_date__isnull=True)
        )[:5]
        
        # 비교 정보
        data['comparison'] = getattr(academy, 'comparisons', None)
        
        # 사용자별 정보 (로그인한 경우)
        if user and user.is_authenticated:
            # 즐겨찾기 여부
            data['is_bookmarked'] = academy.bookmarked_by.filter(user=user).exists()
            
            # 사용자 리뷰 여부
            data['user_review'] = academy.reviews.filter(user=user).first()
        
        return data
    
    @staticmethod
    def record_academy_view(academy: Academy, request) -> AcademyViewHistory:
        """학원 조회 기록"""
        
        # IP 주소 추출
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        # 조회 기록 생성
        # Ensure session exists
        if not hasattr(request, 'session') or not request.session.session_key:
            request.session.save()
            
        view_history = AcademyViewHistory.objects.create(
            academy=academy,
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            session_id=request.session.session_key or '',
            referrer=request.META.get('HTTP_REFERER', '')
        )
        
        # 통계 업데이트
        stats, created = AcademyStatistics.objects.get_or_create(academy=academy)
        stats.view_count += 1
        stats.save(update_fields=['view_count'])
        
        return view_history
    
    @staticmethod
    def calculate_academy_score(academy: Academy) -> Dict:
        """학원 종합 점수 계산"""
        
        stats = getattr(academy, 'statistics', None)
        if not stats:
            return {'total_score': 0, 'breakdown': {}}
        
        # 점수 구성 요소
        scores = {
            'rating': min(stats.average_rating * 20, 100),  # 평점 (5점 만점을 100점으로)
            'popularity': min(stats.popularity_score * 10, 100),  # 인기도
            'review_count': min(stats.review_count * 2, 100),  # 리뷰 수
            'facilities': 0,  # 시설 점수 (detail_info가 있을 때 계산)
        }
        
        # 시설 점수 계산
        detail_info = getattr(academy, 'detail_info', None)
        if detail_info and detail_info.facilities:
            facility_score = len(detail_info.facilities) * 10
            scores['facilities'] = min(facility_score, 100)
        
        # 가중 평균으로 총점 계산
        weights = {
            'rating': 0.4,
            'popularity': 0.3,
            'review_count': 0.2,
            'facilities': 0.1
        }
        
        total_score = sum(scores[key] * weights[key] for key in scores)
        
        return {
            'total_score': round(total_score, 1),
            'breakdown': scores,
            'grade': AcademyEnhancementService._get_grade(total_score)
        }
    
    @staticmethod
    def _get_grade(score: float) -> str:
        """점수에 따른 등급 반환"""
        if score >= 90:
            return 'A+'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B+'
        elif score >= 60:
            return 'B'
        elif score >= 50:
            return 'C+'
        elif score >= 40:
            return 'C'
        else:
            return 'D'
    
    @staticmethod
    def get_similar_academies(academy: Academy, limit: int = 5) -> List[Academy]:
        """유사한 학원 추천"""
        
        # 같은 지역, 같은 과목의 학원들
        similar_filter = models.Q(시군구명=academy.시군구명)
        
        # 과목 필터 추가
        subject_fields = [
            '과목_수학', '과목_영어', '과목_과학', '과목_외국어',
            '과목_예체능', '과목_컴퓨터', '과목_논술', '과목_기타'
        ]
        
        subject_q = models.Q()
        for field in subject_fields:
            if getattr(academy, field, False):
                subject_q |= models.Q(**{field: True})
        
        if subject_q:
            similar_filter &= subject_q
        
        # 자기 자신 제외하고 평점 순으로 정렬
        similar_academies = Academy.objects.filter(similar_filter)\
            .exclude(id=academy.id)\
            .order_by('-별점')[:limit]
        
        return list(similar_academies)
    
    @staticmethod
    def update_academy_statistics(academy: Academy):
        """학원 통계 정보 업데이트"""
        
        stats, created = AcademyStatistics.objects.get_or_create(academy=academy)
        
        # 리뷰 관련 통계
        from accounts.review_models import Review
        reviews = Review.objects.filter(academy=academy)
        stats.review_count = reviews.count()
        if reviews.exists():
            stats.average_rating = reviews.aggregate(
                avg_rating=models.Avg('overall_rating')
            )['avg_rating'] or 0.0
        
        # 즐겨찾기 수
        stats.bookmark_count = academy.bookmarked_by.count()
        
        # 공유 수
        try:
            from accounts.social_models import SocialShare, ShareableContent
            share_content = ShareableContent.objects.filter(
                metadata__academy_id=academy.id
            )
            stats.share_count = SocialShare.objects.filter(
                content__in=share_content
            ).count()
        except:
            pass
        
        # 인기도 점수 재계산
        stats.calculate_popularity_score()
        
        return stats