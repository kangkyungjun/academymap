from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.db.models.functions import Round

from .review_models import Review, ReviewImage, ReviewHelpful, ReviewReport
from .review_serializers import (
    ReviewSerializer, ReviewListSerializer, ReviewCreateSerializer,
    ReviewHelpfulSerializer, ReviewReportSerializer, AcademyReviewStatsSerializer,
    ReviewFilterSerializer, ReviewImageSerializer
)
from main.models import Data as Academy


class ReviewPagination(PageNumberPagination):
    """리뷰 페이지네이션"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def review_list_create(request):
    """리뷰 목록 조회 및 생성"""
    
    if request.method == 'GET':
        # 리뷰 목록 조회
        reviews = Review.objects.filter(is_hidden=False).select_related('academy', 'user')
        
        # 필터링
        filter_serializer = ReviewFilterSerializer(data=request.query_params)
        if filter_serializer.is_valid():
            filters = filter_serializer.validated_data
            
            # 학원별 필터링
            if filters.get('academy_id'):
                reviews = reviews.filter(academy_id=filters['academy_id'])
            
            # 평점 필터링
            if filters.get('rating'):
                reviews = reviews.filter(overall_rating=filters['rating'])
            
            # 학년별 필터링
            if filters.get('grade'):
                grade = filters['grade']
                if grade == '초등':
                    reviews = reviews.filter(
                        Q(grade_when_attended__contains='초등') |
                        Q(grade_when_attended__in=['초등 저학년', '초등 고학년'])
                    )
                elif grade == '중등':
                    reviews = reviews.filter(grade_when_attended__in=['중1', '중2', '중3'])
                elif grade == '고등':
                    reviews = reviews.filter(grade_when_attended__in=['고1', '고2', '고3', '재수생'])
                else:
                    reviews = reviews.filter(grade_when_attended=grade)
            
            # 인증된 리뷰만 필터링
            if filters.get('verified_only'):
                reviews = reviews.filter(is_verified=True)
            
            # 정렬
            order_by = filters.get('order_by', '-created_at')
            reviews = reviews.order_by(order_by)
        else:
            reviews = reviews.order_by('-created_at')
        
        # 페이지네이션
        paginator = ReviewPagination()
        page = paginator.paginate_queryset(reviews, request)
        
        if page is not None:
            serializer = ReviewListSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ReviewListSerializer(reviews, many=True, context={'request': request})
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # 리뷰 생성
        serializer = ReviewCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            review = serializer.save()
            response_serializer = ReviewSerializer(review, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def review_detail(request, pk):
    """리뷰 상세 조회, 수정, 삭제"""
    
    review = get_object_or_404(Review, pk=pk)
    
    # 삭제나 수정 시 작성자 확인
    if request.method in ['PUT', 'DELETE'] and review.user != request.user:
        return Response(
            {'error': '본인이 작성한 리뷰만 수정/삭제할 수 있습니다.'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        serializer = ReviewSerializer(review, context={'request': request})
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = ReviewSerializer(
            review, 
            data=request.data, 
            context={'request': request},
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        review.delete()
        return Response({'message': '리뷰가 삭제되었습니다.'}, 
                       status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def review_helpful(request, pk):
    """리뷰 유용성 평가"""
    
    review = get_object_or_404(Review, pk=pk)
    
    # 본인이 작성한 리뷰는 평가할 수 없음
    if review.user == request.user:
        return Response(
            {'error': '본인이 작성한 리뷰는 평가할 수 없습니다.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = ReviewHelpfulSerializer(
        data=request.data, 
        context={'request': request, 'review': review}
    )
    if serializer.is_valid():
        helpful = serializer.save()
        return Response({
            'message': '평가가 등록되었습니다.',
            'is_helpful': helpful.is_helpful
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def review_report(request, pk):
    """리뷰 신고"""
    
    review = get_object_or_404(Review, pk=pk)
    
    # 본인이 작성한 리뷰는 신고할 수 없음
    if review.user == request.user:
        return Response(
            {'error': '본인이 작성한 리뷰는 신고할 수 없습니다.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = ReviewReportSerializer(
        data=request.data, 
        context={'request': request, 'review': review}
    )
    if serializer.is_valid():
        report = serializer.save()
        return Response({
            'message': '신고가 접수되었습니다.',
            'report_id': report.id
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def academy_review_stats(request, academy_id):
    """학원별 리뷰 통계"""
    
    academy = get_object_or_404(Academy, pk=academy_id)
    reviews = Review.objects.filter(academy=academy, is_hidden=False)
    
    if not reviews.exists():
        return Response({
            'total_reviews': 0,
            'average_overall_rating': 0,
            'average_teaching_rating': 0,
            'average_facility_rating': 0,
            'average_management_rating': 0,
            'average_cost_rating': 0,
            'rating_distribution': {str(i): 0 for i in range(1, 6)},
            'recommend_percentage': 0,
            'verified_review_count': 0
        })
    
    # 기본 통계
    stats = reviews.aggregate(
        total_reviews=Count('id'),
        average_overall_rating=Round(Avg('overall_rating'), 2),
        average_teaching_rating=Round(Avg('teaching_rating'), 2),
        average_facility_rating=Round(Avg('facility_rating'), 2),
        average_management_rating=Round(Avg('management_rating'), 2),
        average_cost_rating=Round(Avg('cost_rating'), 2),
        verified_review_count=Count('id', filter=Q(is_verified=True))
    )
    
    # 평점 분포
    rating_distribution = {}
    for i in range(1, 6):
        count = reviews.filter(overall_rating=i).count()
        rating_distribution[str(i)] = count
    
    # 추천 비율
    total_reviews = stats['total_reviews']
    recommend_count = reviews.filter(would_recommend=True).count()
    recommend_percentage = (recommend_count / total_reviews * 100) if total_reviews > 0 else 0
    
    stats.update({
        'rating_distribution': rating_distribution,
        'recommend_percentage': round(recommend_percentage, 2)
    })
    
    serializer = AcademyReviewStatsSerializer(stats)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_reviews(request):
    """내가 작성한 리뷰 목록"""
    
    reviews = Review.objects.filter(user=request.user).select_related('academy')
    
    # 정렬
    order_by = request.query_params.get('order_by', '-created_at')
    reviews = reviews.order_by(order_by)
    
    # 페이지네이션
    paginator = ReviewPagination()
    page = paginator.paginate_queryset(reviews, request)
    
    if page is not None:
        serializer = ReviewListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    
    serializer = ReviewListSerializer(reviews, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def review_image_upload(request, pk):
    """리뷰 이미지 업로드"""
    
    review = get_object_or_404(Review, pk=pk)
    
    # 작성자 확인
    if review.user != request.user:
        return Response(
            {'error': '본인이 작성한 리뷰에만 이미지를 추가할 수 있습니다.'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # 이미지 수 제한 (최대 5개)
    if review.images.count() >= 5:
        return Response(
            {'error': '리뷰당 최대 5개의 이미지만 업로드할 수 있습니다.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = ReviewImageSerializer(data=request.data)
    if serializer.is_valid():
        image = serializer.save(review=review)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def review_image_delete(request, pk, image_id):
    """리뷰 이미지 삭제"""
    
    review = get_object_or_404(Review, pk=pk)
    image = get_object_or_404(ReviewImage, pk=image_id, review=review)
    
    # 작성자 확인
    if review.user != request.user:
        return Response(
            {'error': '본인이 작성한 리뷰의 이미지만 삭제할 수 있습니다.'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    image.delete()
    return Response({'message': '이미지가 삭제되었습니다.'}, 
                   status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def review_summary(request):
    """전체 리뷰 요약 통계"""
    
    total_reviews = Review.objects.filter(is_hidden=False).count()
    total_academies_with_reviews = Review.objects.filter(is_hidden=False).values('academy').distinct().count()
    
    if total_reviews == 0:
        return Response({
            'total_reviews': 0,
            'total_academies_with_reviews': 0,
            'average_rating': 0,
            'top_rated_academies': [],
            'recent_reviews': []
        })
    
    # 전체 평균 평점
    average_rating = Review.objects.filter(is_hidden=False).aggregate(
        avg_rating=Round(Avg('overall_rating'), 2)
    )['avg_rating']
    
    # 평점 높은 학원 Top 10
    top_rated_academies = []
    academy_ratings = Review.objects.filter(is_hidden=False).values('academy', 'academy__상호명').annotate(
        avg_rating=Round(Avg('overall_rating'), 2),
        review_count=Count('id')
    ).filter(review_count__gte=3).order_by('-avg_rating')[:10]
    
    for academy_rating in academy_ratings:
        top_rated_academies.append({
            'academy_id': academy_rating['academy'],
            'academy_name': academy_rating['academy__상호명'],
            'average_rating': academy_rating['avg_rating'],
            'review_count': academy_rating['review_count']
        })
    
    # 최근 리뷰 5개
    recent_reviews = Review.objects.filter(is_hidden=False).select_related('academy', 'user').order_by('-created_at')[:5]
    recent_serializer = ReviewListSerializer(recent_reviews, many=True, context={'request': request})
    
    return Response({
        'total_reviews': total_reviews,
        'total_academies_with_reviews': total_academies_with_reviews,
        'average_rating': average_rating,
        'top_rated_academies': top_rated_academies,
        'recent_reviews': recent_serializer.data
    })