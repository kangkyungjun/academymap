from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import json

from main.models import Data as Academy


class UserPreference(models.Model):
    """사용자 선호도 모델"""
    PREFERENCE_TYPE_CHOICES = [
        ('subject', '과목'),
        ('location', '위치'),
        ('price', '가격'),
        ('teaching_method', '교육방식'),
        ('facility', '시설'),
        ('schedule', '일정'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='preferences')
    preference_type = models.CharField(max_length=20, choices=PREFERENCE_TYPE_CHOICES)
    preference_value = models.CharField(max_length=200)  # JSON 형태로 저장
    weight = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        verbose_name='가중치'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_preferences'
        unique_together = ['user', 'preference_type']
        indexes = [
            models.Index(fields=['user', 'preference_type']),
            models.Index(fields=['preference_type', 'weight']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_preference_type_display()}: {self.preference_value}"
    
    def get_preference_data(self):
        """선호도 데이터 파싱"""
        try:
            return json.loads(self.preference_value)
        except (json.JSONDecodeError, TypeError):
            return self.preference_value


class UserBehavior(models.Model):
    """사용자 행동 분석 모델"""
    ACTION_CHOICES = [
        ('view', '조회'),
        ('search', '검색'),
        ('filter', '필터링'),
        ('contact', '문의'),
        ('bookmark', '즐겨찾기'),
        ('click', '클릭'),
        ('share', '공유'),
        ('review', '리뷰'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='behaviors')
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, related_name='user_behaviors', null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # 행동 상세 정보
    search_query = models.CharField(max_length=500, blank=True)  # 검색어
    filter_criteria = models.JSONField(default=dict, blank=True)  # 필터 조건
    session_id = models.CharField(max_length=100, blank=True)  # 세션 ID
    
    # 컨텍스트 정보
    page_url = models.URLField(blank=True)
    referrer = models.URLField(blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    # 시간 정보
    duration = models.PositiveIntegerField(default=0, verbose_name='체류시간(초)')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_behaviors'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'action', 'timestamp']),
            models.Index(fields=['academy', 'action']),
            models.Index(fields=['session_id', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        academy_name = self.academy.상호명 if self.academy else '전체'
        return f"{self.user.username} - {self.get_action_display()}: {academy_name}"


class AcademyVector(models.Model):
    """학원 특성 벡터 모델"""
    academy = models.OneToOneField(Academy, on_delete=models.CASCADE, related_name='vector')
    
    # 특성 벡터 (정규화된 값들)
    subject_vector = models.JSONField(default=dict)  # 과목별 특성
    location_vector = models.JSONField(default=dict)  # 위치 특성
    price_vector = models.JSONField(default=dict)  # 가격대 특성
    quality_vector = models.JSONField(default=dict)  # 품질 특성
    facility_vector = models.JSONField(default=dict)  # 시설 특성
    
    # 통계 기반 특성
    popularity_score = models.FloatField(default=0.0, verbose_name='인기도')
    rating_score = models.FloatField(default=0.0, verbose_name='평점')
    engagement_score = models.FloatField(default=0.0, verbose_name='참여도')
    
    # 텍스트 임베딩 (AI 모델 기반)
    description_embedding = models.JSONField(default=list, blank=True)  # 설명 임베딩
    keyword_embedding = models.JSONField(default=list, blank=True)  # 키워드 임베딩
    
    # 메타데이터
    vector_version = models.CharField(max_length=20, default='1.0')
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'academy_vectors'
        indexes = [
            models.Index(fields=['popularity_score']),
            models.Index(fields=['rating_score']),
            models.Index(fields=['engagement_score']),
            models.Index(fields=['last_updated']),
        ]
    
    def __str__(self):
        return f"{self.academy.상호명} 벡터"
    
    def update_popularity_score(self):
        """인기도 점수 업데이트"""
        behaviors = UserBehavior.objects.filter(
            academy=self.academy,
            timestamp__gte=timezone.now() - timezone.timedelta(days=30)
        )
        
        # 행동별 가중치
        action_weights = {
            'view': 1.0,
            'search': 0.8,
            'click': 1.2,
            'contact': 3.0,
            'bookmark': 2.0,
            'share': 1.5,
            'review': 2.5,
        }
        
        total_score = sum(
            action_weights.get(behavior.action, 1.0) 
            for behavior in behaviors
        )
        
        self.popularity_score = min(total_score / 100.0, 5.0)  # 0-5 범위로 정규화
        self.save()


class RecommendationModel(models.Model):
    """추천 모델 메타데이터"""
    MODEL_TYPE_CHOICES = [
        ('collaborative', '협업 필터링'),
        ('content_based', '콘텐츠 기반'),
        ('hybrid', '하이브리드'),
        ('deep_learning', '딥러닝'),
        ('matrix_factorization', '행렬 분해'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    model_type = models.CharField(max_length=30, choices=MODEL_TYPE_CHOICES)
    version = models.CharField(max_length=20)
    
    # 모델 파라미터
    parameters = models.JSONField(default=dict)
    hyperparameters = models.JSONField(default=dict)
    
    # 성능 지표
    accuracy = models.FloatField(null=True, blank=True)
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)
    f1_score = models.FloatField(null=True, blank=True)
    
    # 상태
    is_active = models.BooleanField(default=False)
    is_trained = models.BooleanField(default=False)
    
    # 시간 정보
    created_at = models.DateTimeField(auto_now_add=True)
    trained_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'recommendation_models'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'is_trained']),
            models.Index(fields=['model_type', 'version']),
        ]
    
    def __str__(self):
        return f"{self.name} v{self.version} ({self.get_model_type_display()})"


class Recommendation(models.Model):
    """추천 결과 모델"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recommendations')
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, related_name='recommendations')
    model = models.ForeignKey(RecommendationModel, on_delete=models.CASCADE)
    
    # 추천 점수
    confidence_score = models.FloatField(verbose_name='신뢰도')  # 0.0 - 1.0
    relevance_score = models.FloatField(verbose_name='관련성')  # 0.0 - 1.0
    final_score = models.FloatField(verbose_name='최종점수')  # 가중 평균
    
    # 추천 이유
    reason_type = models.CharField(max_length=50, blank=True)  # 'similar_users', 'content_match' 등
    reason_details = models.JSONField(default=dict, blank=True)  # 상세 이유
    explanation = models.TextField(blank=True)  # 사용자용 설명
    
    # 추천 컨텍스트
    context = models.JSONField(default=dict, blank=True)  # 추천 시점의 컨텍스트 정보
    session_id = models.CharField(max_length=100, blank=True)
    
    # 사용자 반응
    is_clicked = models.BooleanField(default=False)
    is_contacted = models.BooleanField(default=False)
    feedback_score = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # 시간 정보
    recommended_at = models.DateTimeField(auto_now_add=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'recommendations'
        unique_together = ['user', 'academy', 'model', 'session_id']
        ordering = ['-final_score', '-recommended_at']
        indexes = [
            models.Index(fields=['user', 'final_score']),
            models.Index(fields=['academy', 'final_score']),
            models.Index(fields=['model', 'recommended_at']),
            models.Index(fields=['session_id', 'final_score']),
            models.Index(fields=['is_clicked', 'is_contacted']),
        ]
    
    def __str__(self):
        return f"{self.user.username}에게 {self.academy.상호명} 추천 ({self.final_score:.2f})"
    
    def mark_as_clicked(self):
        """클릭으로 표시"""
        self.is_clicked = True
        self.clicked_at = timezone.now()
        self.save()
    
    def add_feedback(self, score, comment=''):
        """사용자 피드백 추가"""
        self.feedback_score = score
        if comment:
            context = self.context or {}
            context['feedback_comment'] = comment
            self.context = context
        self.save()


class RecommendationLog(models.Model):
    """추천 시스템 로그"""
    LOG_TYPE_CHOICES = [
        ('request', '추천 요청'),
        ('generation', '추천 생성'),
        ('serving', '추천 제공'),
        ('feedback', '피드백'),
        ('error', '오류'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        related_name='recommendation_logs'
    )
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES)
    
    # 로그 상세 정보
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    
    # 성능 지표
    processing_time = models.FloatField(null=True, blank=True, verbose_name='처리시간(초)')
    recommendation_count = models.PositiveIntegerField(null=True, blank=True)
    
    # 메타데이터
    session_id = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    # 시간 정보
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'recommendation_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'log_type', 'timestamp']),
            models.Index(fields=['log_type', 'timestamp']),
            models.Index(fields=['session_id']),
        ]
    
    def __str__(self):
        user_name = self.user.username if self.user else 'Anonymous'
        return f"{user_name} - {self.get_log_type_display()}: {self.message[:50]}"


class AcademySimilarity(models.Model):
    """학원 간 유사도 매트릭스"""
    academy1 = models.ForeignKey(Academy, on_delete=models.CASCADE, related_name='similarities_as_first')
    academy2 = models.ForeignKey(Academy, on_delete=models.CASCADE, related_name='similarities_as_second')
    
    # 유사도 점수들
    content_similarity = models.FloatField(default=0.0, verbose_name='콘텐츠 유사도')
    location_similarity = models.FloatField(default=0.0, verbose_name='위치 유사도')
    user_similarity = models.FloatField(default=0.0, verbose_name='사용자 기반 유사도')
    overall_similarity = models.FloatField(default=0.0, verbose_name='전체 유사도')
    
    # 계산 정보
    calculation_method = models.CharField(max_length=50, default='cosine')
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'academy_similarities'
        unique_together = ['academy1', 'academy2']
        indexes = [
            models.Index(fields=['academy1', 'overall_similarity']),
            models.Index(fields=['academy2', 'overall_similarity']),
            models.Index(fields=['overall_similarity']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(academy1__lt=models.F('academy2')),
                name='academy_similarity_order_constraint'
            )
        ]
    
    def __str__(self):
        return f"{self.academy1.상호명} ↔ {self.academy2.상호명} ({self.overall_similarity:.3f})"
    
    def save(self, *args, **kwargs):
        # academy1이 academy2보다 ID가 작도록 보장
        if self.academy1.id > self.academy2.id:
            self.academy1, self.academy2 = self.academy2, self.academy1
        super().save(*args, **kwargs)