from rest_framework import serializers
from .review_models import Review, ReviewImage, ReviewHelpful, ReviewReport
from main.models import Data as Academy
from api.serializers import AcademySerializer


class ReviewImageSerializer(serializers.ModelSerializer):
    """리뷰 이미지 시리얼라이저"""
    
    class Meta:
        model = ReviewImage
        fields = ['id', 'image', 'caption', 'order']


class ReviewSerializer(serializers.ModelSerializer):
    """리뷰 시리얼라이저"""
    academy = AcademySerializer(read_only=True)
    academy_id = serializers.IntegerField(write_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    author_name = serializers.SerializerMethodField()
    average_detailed_rating = serializers.ReadOnlyField()
    helpful_ratio = serializers.ReadOnlyField()
    user_helpful_vote = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = [
            'id', 'academy', 'academy_id', 'overall_rating', 'teaching_rating',
            'facility_rating', 'management_rating', 'cost_rating', 'title',
            'content', 'attendance_period', 'grade_when_attended', 'subjects_taken',
            'pros', 'cons', 'would_recommend', 'is_anonymous', 'is_verified',
            'helpful_count', 'not_helpful_count', 'created_at', 'updated_at',
            'images', 'author_name', 'average_detailed_rating', 'helpful_ratio',
            'user_helpful_vote'
        ]
        read_only_fields = [
            'id', 'is_verified', 'helpful_count', 'not_helpful_count', 
            'created_at', 'updated_at'
        ]
    
    def get_author_name(self, obj):
        """작성자 이름 (익명 처리)"""
        if obj.is_anonymous:
            return "익명"
        return obj.user.nickname or obj.user.username
    
    def get_user_helpful_vote(self, obj):
        """현재 사용자의 유용성 투표"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        try:
            vote = ReviewHelpful.objects.get(user=request.user, review=obj)
            return vote.is_helpful
        except ReviewHelpful.DoesNotExist:
            return None
    
    def validate_academy_id(self, value):
        """학원 ID 유효성 검증"""
        try:
            Academy.objects.get(id=value)
            return value
        except Academy.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 학원입니다.")
    
    def validate(self, attrs):
        """전체 유효성 검증"""
        user = self.context['request'].user
        academy_id = attrs.get('academy_id')
        
        # 이미 리뷰를 작성한 학원인지 확인 (수정 시 제외)
        if self.instance is None:  # 새로 생성하는 경우
            if Review.objects.filter(user=user, academy_id=academy_id).exists():
                raise serializers.ValidationError("이미 이 학원에 대한 리뷰를 작성하셨습니다.")
        
        return attrs
    
    def create(self, validated_data):
        """리뷰 생성"""
        academy_id = validated_data.pop('academy_id')
        academy = Academy.objects.get(id=academy_id)
        user = self.context['request'].user
        
        review = Review.objects.create(
            user=user,
            academy=academy,
            **validated_data
        )
        
        return review


class ReviewListSerializer(serializers.ModelSerializer):
    """리뷰 목록 시리얼라이저 (간단한 정보)"""
    academy_name = serializers.CharField(source='academy.상호명', read_only=True)
    author_name = serializers.SerializerMethodField()
    average_detailed_rating = serializers.ReadOnlyField()
    image_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = [
            'id', 'academy_id', 'academy_name', 'overall_rating', 'title',
            'content', 'attendance_period', 'grade_when_attended', 'would_recommend',
            'is_anonymous', 'is_verified', 'helpful_count', 'not_helpful_count',
            'created_at', 'author_name', 'average_detailed_rating', 'image_count'
        ]
    
    def get_author_name(self, obj):
        """작성자 이름 (익명 처리)"""
        if obj.is_anonymous:
            return "익명"
        return obj.user.nickname or obj.user.username
    
    def get_image_count(self, obj):
        """리뷰 이미지 수"""
        return obj.images.count()


class ReviewCreateSerializer(serializers.ModelSerializer):
    """리뷰 생성 시리얼라이저"""
    academy_id = serializers.IntegerField()
    
    class Meta:
        model = Review
        fields = [
            'academy_id', 'overall_rating', 'teaching_rating', 'facility_rating',
            'management_rating', 'cost_rating', 'title', 'content',
            'attendance_period', 'grade_when_attended', 'subjects_taken',
            'pros', 'cons', 'would_recommend', 'is_anonymous'
        ]
    
    def validate_academy_id(self, value):
        """학원 ID 유효성 검증"""
        try:
            Academy.objects.get(id=value)
            return value
        except Academy.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 학원입니다.")
    
    def validate(self, attrs):
        """전체 유효성 검증"""
        user = self.context['request'].user
        academy_id = attrs.get('academy_id')
        
        # 이미 리뷰를 작성한 학원인지 확인
        if Review.objects.filter(user=user, academy_id=academy_id).exists():
            raise serializers.ValidationError("이미 이 학원에 대한 리뷰를 작성하셨습니다.")
        
        return attrs
    
    def create(self, validated_data):
        """리뷰 생성"""
        academy_id = validated_data.pop('academy_id')
        academy = Academy.objects.get(id=academy_id)
        user = self.context['request'].user
        
        review = Review.objects.create(
            user=user,
            academy=academy,
            **validated_data
        )
        
        return review


class ReviewHelpfulSerializer(serializers.ModelSerializer):
    """리뷰 유용성 평가 시리얼라이저"""
    
    class Meta:
        model = ReviewHelpful
        fields = ['is_helpful']
    
    def create(self, validated_data):
        """유용성 평가 생성/수정"""
        user = self.context['request'].user
        review = self.context['review']
        
        # 기존 평가가 있으면 업데이트, 없으면 생성
        helpful, created = ReviewHelpful.objects.update_or_create(
            user=user,
            review=review,
            defaults=validated_data
        )
        
        # 리뷰의 유용성 카운트 업데이트
        self.update_review_helpful_count(review)
        
        return helpful
    
    def update_review_helpful_count(self, review):
        """리뷰의 유용성 카운트 업데이트"""
        helpful_count = ReviewHelpful.objects.filter(
            review=review, 
            is_helpful=True
        ).count()
        not_helpful_count = ReviewHelpful.objects.filter(
            review=review, 
            is_helpful=False
        ).count()
        
        review.helpful_count = helpful_count
        review.not_helpful_count = not_helpful_count
        review.save(update_fields=['helpful_count', 'not_helpful_count'])


class ReviewReportSerializer(serializers.ModelSerializer):
    """리뷰 신고 시리얼라이저"""
    
    class Meta:
        model = ReviewReport
        fields = ['reason', 'description']
    
    def create(self, validated_data):
        """리뷰 신고 생성"""
        user = self.context['request'].user
        review = self.context['review']
        
        # 이미 신고한 리뷰인지 확인
        if ReviewReport.objects.filter(user=user, review=review).exists():
            raise serializers.ValidationError("이미 신고한 리뷰입니다.")
        
        report = ReviewReport.objects.create(
            user=user,
            review=review,
            **validated_data
        )
        
        return report


class AcademyReviewStatsSerializer(serializers.Serializer):
    """학원 리뷰 통계 시리얼라이저"""
    total_reviews = serializers.IntegerField()
    average_overall_rating = serializers.FloatField()
    average_teaching_rating = serializers.FloatField()
    average_facility_rating = serializers.FloatField()
    average_management_rating = serializers.FloatField()
    average_cost_rating = serializers.FloatField()
    rating_distribution = serializers.DictField()
    recommend_percentage = serializers.FloatField()
    verified_review_count = serializers.IntegerField()


class ReviewFilterSerializer(serializers.Serializer):
    """리뷰 필터링 시리얼라이저"""
    academy_id = serializers.IntegerField(required=False)
    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    grade = serializers.ChoiceField(
        choices=[
            ('유아', '유아'),
            ('초등', '초등'),
            ('중등', '중등'),
            ('고등', '고등'),
            ('일반인', '일반인'),
        ],
        required=False
    )
    verified_only = serializers.BooleanField(required=False, default=False)
    order_by = serializers.ChoiceField(
        choices=[
            ('-created_at', '최신순'),
            ('created_at', '오래된순'),
            ('-overall_rating', '평점 높은순'),
            ('overall_rating', '평점 낮은순'),
            ('-helpful_count', '도움됨 많은순'),
        ],
        required=False,
        default='-created_at'
    )