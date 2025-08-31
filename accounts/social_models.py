from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from main.models import Data as Academy

User = get_user_model()


class SocialPlatform(models.Model):
    """소셜 미디어 플랫폼"""
    
    name = models.CharField(max_length=50, unique=True, verbose_name="플랫폼명")
    display_name = models.CharField(max_length=100, verbose_name="표시명")
    icon = models.CharField(max_length=50, blank=True, verbose_name="아이콘")
    color = models.CharField(max_length=7, default='#000000', verbose_name="브랜드 색상")
    share_url_template = models.URLField(
        max_length=500, 
        verbose_name="공유 URL 템플릿",
        help_text="변수: {url}, {title}, {description}, {hashtags}"
    )
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    order = models.IntegerField(default=0, verbose_name="정렬 순서")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "소셜 플랫폼"
        verbose_name_plural = "소셜 플랫폼들"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.display_name


class ShareableContent(models.Model):
    """공유 가능한 콘텐츠"""
    
    CONTENT_TYPES = [
        ('academy', '학원 정보'),
        ('comparison', '학원 비교'),
        ('review', '리뷰'),
        ('list', '학원 목록'),
        ('search_result', '검색 결과'),
    ]
    
    content_type = models.CharField(
        max_length=20, 
        choices=CONTENT_TYPES,
        verbose_name="콘텐츠 유형"
    )
    title = models.CharField(max_length=200, verbose_name="제목")
    description = models.TextField(verbose_name="설명")
    url = models.URLField(verbose_name="대상 URL")
    image_url = models.URLField(blank=True, verbose_name="이미지 URL")
    
    # 메타데이터
    metadata = models.JSONField(default=dict, blank=True, verbose_name="메타데이터")
    hashtags = models.CharField(max_length=500, blank=True, verbose_name="해시태그")
    
    # SEO 메타태그
    og_title = models.CharField(max_length=200, blank=True, verbose_name="OG 제목")
    og_description = models.TextField(blank=True, verbose_name="OG 설명")
    og_image = models.URLField(blank=True, verbose_name="OG 이미지")
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name="생성자"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "공유 콘텐츠"
        verbose_name_plural = "공유 콘텐츠들"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_content_type_display()}: {self.title}"


class SocialShare(models.Model):
    """소셜 미디어 공유 기록"""
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='social_shares',
        verbose_name="사용자"
    )
    platform = models.ForeignKey(
        SocialPlatform,
        on_delete=models.CASCADE,
        verbose_name="플랫폼"
    )
    content = models.ForeignKey(
        ShareableContent,
        on_delete=models.CASCADE,
        verbose_name="공유 콘텐츠"
    )
    
    # 공유 정보
    shared_url = models.URLField(verbose_name="실제 공유된 URL")
    custom_message = models.TextField(blank=True, verbose_name="사용자 메시지")
    
    # 통계
    clicks = models.IntegerField(default=0, verbose_name="클릭 수")
    engagement_score = models.FloatField(default=0.0, verbose_name="참여도 점수")
    
    shared_at = models.DateTimeField(auto_now_add=True, verbose_name="공유 시간")
    
    class Meta:
        verbose_name = "소셜 공유"
        verbose_name_plural = "소셜 공유 기록"
        ordering = ['-shared_at']
        unique_together = ['user', 'platform', 'content', 'shared_at']
    
    def __str__(self):
        return f"{self.user.username} → {self.platform.display_name}: {self.content.title[:50]}"


class AcademyShare(models.Model):
    """학원 공유 (특화된 공유 모델)"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='academy_shares',
        verbose_name="공유한 사용자"
    )
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name='shares',
        verbose_name="공유된 학원"
    )
    platform = models.ForeignKey(
        SocialPlatform,
        on_delete=models.CASCADE,
        verbose_name="플랫폼"
    )
    
    # 공유 내용 커스터마이징
    custom_title = models.CharField(max_length=200, blank=True, verbose_name="사용자 정의 제목")
    custom_description = models.TextField(blank=True, verbose_name="사용자 정의 설명")
    selected_subjects = models.JSONField(default=list, blank=True, verbose_name="선택된 과목")
    include_rating = models.BooleanField(default=True, verbose_name="평점 포함")
    include_price = models.BooleanField(default=False, verbose_name="가격 포함")
    include_location = models.BooleanField(default=True, verbose_name="위치 포함")
    
    # 추천 컨텍스트
    recommendation_reason = models.TextField(blank=True, verbose_name="추천 이유")
    target_age_group = models.CharField(max_length=50, blank=True, verbose_name="대상 연령대")
    
    shared_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "학원 공유"
        verbose_name_plural = "학원 공유들"
        ordering = ['-shared_at']
    
    def __str__(self):
        return f"{self.user.username} → {self.academy.상호명} ({self.platform.display_name})"
    
    def get_share_title(self):
        """공유 제목 생성"""
        if self.custom_title:
            return self.custom_title
        
        title_parts = [self.academy.상호명]
        
        if self.selected_subjects:
            subjects = ", ".join(self.selected_subjects[:3])
            title_parts.append(f"[{subjects}]")
        
        if self.include_rating and hasattr(self.academy, 'rating') and self.academy.rating:
            title_parts.append(f"⭐{self.academy.rating}")
        
        return " ".join(title_parts)
    
    def get_share_description(self):
        """공유 설명 생성"""
        if self.custom_description:
            return self.custom_description
        
        desc_parts = []
        
        if self.include_location:
            location = self.academy.도로명주소 or self.academy.지번주소
            if location:
                desc_parts.append(f"📍 {location}")
        
        if self.recommendation_reason:
            desc_parts.append(f"💡 {self.recommendation_reason}")
        
        if self.target_age_group:
            desc_parts.append(f"👥 {self.target_age_group} 대상")
        
        if self.include_price and hasattr(self.academy, 'price_info'):
            desc_parts.append(f"💰 {self.academy.price_info}")
        
        return "\n".join(desc_parts)
    
    def get_hashtags(self):
        """해시태그 생성"""
        hashtags = ['#학원추천', '#교육', '#AcademyMap']
        
        if self.selected_subjects:
            for subject in self.selected_subjects[:3]:
                hashtags.append(f"#{subject}")
        
        if self.target_age_group:
            hashtags.append(f"#{self.target_age_group}")
        
        # 지역 해시태그
        if self.academy.시군구명:
            region = self.academy.시군구명.replace(" ", "")
            hashtags.append(f"#{region}학원")
        
        return " ".join(hashtags[:10])  # 최대 10개


class ShareAnalytics(models.Model):
    """공유 분석 데이터"""
    
    date = models.DateField(verbose_name="날짜")
    platform = models.ForeignKey(
        SocialPlatform,
        on_delete=models.CASCADE,
        verbose_name="플랫폼"
    )
    
    # 일별 통계
    total_shares = models.IntegerField(default=0, verbose_name="총 공유 수")
    unique_users = models.IntegerField(default=0, verbose_name="순 사용자 수")
    total_clicks = models.IntegerField(default=0, verbose_name="총 클릭 수")
    
    # 콘텐츠 유형별 통계
    academy_shares = models.IntegerField(default=0, verbose_name="학원 공유 수")
    comparison_shares = models.IntegerField(default=0, verbose_name="비교 공유 수")
    review_shares = models.IntegerField(default=0, verbose_name="리뷰 공유 수")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "공유 분석"
        verbose_name_plural = "공유 분석 데이터"
        unique_together = ['date', 'platform']
        ordering = ['-date', 'platform']
    
    def __str__(self):
        return f"{self.date} - {self.platform.display_name}: {self.total_shares}건"


class PopularContent(models.Model):
    """인기 공유 콘텐츠"""
    
    content = models.ForeignKey(
        ShareableContent,
        on_delete=models.CASCADE,
        verbose_name="콘텐츠"
    )
    
    # 인기도 지표
    total_shares = models.IntegerField(default=0, verbose_name="총 공유 수")
    weekly_shares = models.IntegerField(default=0, verbose_name="주간 공유 수")
    monthly_shares = models.IntegerField(default=0, verbose_name="월간 공유 수")
    
    average_engagement = models.FloatField(default=0.0, verbose_name="평균 참여도")
    viral_score = models.FloatField(default=0.0, verbose_name="바이럴 점수")
    
    last_calculated = models.DateTimeField(auto_now=True, verbose_name="마지막 계산")
    
    class Meta:
        verbose_name = "인기 콘텐츠"
        verbose_name_plural = "인기 콘텐츠들"
        ordering = ['-viral_score', '-total_shares']
    
    def __str__(self):
        return f"{self.content.title} (바이럴 점수: {self.viral_score:.2f})"
    
    def calculate_viral_score(self):
        """바이럴 점수 계산"""
        # 가중 점수 계산
        score = (
            self.total_shares * 0.3 +
            self.weekly_shares * 0.4 +
            self.monthly_shares * 0.2 +
            self.average_engagement * 0.1
        )
        
        self.viral_score = score
        self.save(update_fields=['viral_score'])
        return score