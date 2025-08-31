from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
import json
import csv
import io

from .comparison_models import AcademyComparison, ComparisonTemplate, ComparisonHistory
from .comparison_serializers import (
    AcademyComparisonSerializer, ComparisonListSerializer, 
    ComparisonTemplateSerializer, ComparisonHistorySerializer,
    QuickComparisonSerializer, ComparisonExportSerializer,
    ComparisonAcademySerializer
)
from main.models import Data as Academy


class ComparisonPagination(PageNumberPagination):
    """비교 페이지네이션"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def comparison_list_create(request):
    """비교 목록 조회 및 생성"""
    
    if request.method == 'GET':
        # 비교 목록 조회
        comparisons = AcademyComparison.objects.filter(user=request.user)
        
        # 정렬
        order_by = request.query_params.get('order_by', '-updated_at')
        comparisons = comparisons.order_by(order_by)
        
        # 페이지네이션
        paginator = ComparisonPagination()
        page = paginator.paginate_queryset(comparisons, request)
        
        if page is not None:
            serializer = ComparisonListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ComparisonListSerializer(comparisons, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # 비교 생성
        serializer = AcademyComparisonSerializer(
            data=request.data, 
            context={'request': request}
        )
        if serializer.is_valid():
            comparison = serializer.save()
            response_serializer = AcademyComparisonSerializer(
                comparison, 
                context={'request': request}
            )
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def comparison_detail(request, pk):
    """비교 상세 조회, 수정, 삭제"""
    
    comparison = get_object_or_404(AcademyComparison, pk=pk, user=request.user)
    
    if request.method == 'GET':
        # 조회 기록 생성
        ComparisonHistory.objects.create(
            user=request.user,
            comparison=comparison,
            action='viewed'
        )
        
        serializer = AcademyComparisonSerializer(
            comparison, 
            context={'request': request}
        )
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = AcademyComparisonSerializer(
            comparison,
            data=request.data,
            context={'request': request},
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        comparison.delete()
        return Response({'message': '비교가 삭제되었습니다.'}, 
                       status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def quick_comparison(request):
    """빠른 비교 (저장하지 않음)"""
    
    serializer = QuickComparisonSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    academy_ids = serializer.validated_data['academy_ids']
    base_latitude = serializer.validated_data.get('base_latitude')
    base_longitude = serializer.validated_data.get('base_longitude')
    weights = serializer.validated_data.get('weights', {})
    
    # 학원들 가져오기
    academies = Academy.objects.filter(id__in=academy_ids)
    
    # 임시 비교 객체 생성 (저장하지 않고 계산만 수행)
    temp_comparison = AcademyComparison(
        user=request.user,
        name="임시 비교",
        tuition_weight=weights.get('tuition', 3),
        rating_weight=weights.get('rating', 4),
        distance_weight=weights.get('distance', 3),
        quality_weight=weights.get('quality', 5),
        base_latitude=base_latitude,
        base_longitude=base_longitude
    )
    
    # 수동으로 비교 결과 계산
    from django.db.models import Avg
    from .review_models import Review
    import math
    
    results = []
    
    for academy in academies:
        score = 0
        details = {}
        
        # 평점 점수 (리뷰 기반)
        reviews = Review.objects.filter(academy=academy, is_hidden=False)
        if reviews.exists():
            avg_rating = reviews.aggregate(Avg('overall_rating'))['overall_rating__avg'] or 0
            rating_score = (avg_rating / 5) * 100 * (temp_comparison.rating_weight / 5)
            score += rating_score
            details['rating_score'] = round(rating_score, 2)
            details['average_rating'] = round(avg_rating, 2)
        else:
            details['rating_score'] = 0
            details['average_rating'] = 0
        
        # 거리 점수 (기준 위치 기반)
        if base_latitude and base_longitude and academy.위도 and academy.경도:
            # 하버사인 공식으로 거리 계산
            lat1, lon1 = math.radians(base_latitude), math.radians(base_longitude)
            lat2, lon2 = math.radians(academy.위도), math.radians(academy.경도)
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = (math.sin(dlat/2)**2 + 
                 math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2)
            distance = 2 * math.asin(math.sqrt(a)) * 6371  # km
            
            # 거리가 가까울수록 높은 점수 (5km 이내가 만점)
            distance_score = max(0, (5 - min(distance, 5)) / 5) * 100 * (temp_comparison.distance_weight / 5)
            score += distance_score
            details['distance_score'] = round(distance_score, 2)
            details['distance_km'] = round(distance, 2)
        else:
            details['distance_score'] = 0
            details['distance_km'] = None
        
        # 수강료 점수 (낮을수록 높은 점수)
        if academy.수강료_평균:
            try:
                tuition = float(academy.수강료_평균.replace(',', '').replace('원', ''))
                # 10만원 이하가 만점, 50만원 이상이 0점으로 가정
                tuition_score = max(0, (500000 - min(tuition, 500000)) / 400000) * 100 * (temp_comparison.tuition_weight / 5)
                score += tuition_score
                details['tuition_score'] = round(tuition_score, 2)
                details['tuition_amount'] = tuition
            except (ValueError, TypeError):
                details['tuition_score'] = 0
                details['tuition_amount'] = None
        else:
            details['tuition_score'] = 0
            details['tuition_amount'] = None
        
        # 교육품질 점수 (리뷰의 세부 평점 기반)
        if reviews.exists():
            quality_avg = reviews.aggregate(
                teaching=Avg('teaching_rating'),
                facility=Avg('facility_rating'),
                management=Avg('management_rating')
            )
            quality_score_val = (
                (quality_avg['teaching'] or 0) +
                (quality_avg['facility'] or 0) +
                (quality_avg['management'] or 0)
            ) / 3
            quality_score = (quality_score_val / 5) * 100 * (temp_comparison.quality_weight / 5)
            score += quality_score
            details['quality_score'] = round(quality_score, 2)
            details['quality_breakdown'] = {
                'teaching': round(quality_avg['teaching'] or 0, 2),
                'facility': round(quality_avg['facility'] or 0, 2),
                'management': round(quality_avg['management'] or 0, 2)
            }
        else:
            details['quality_score'] = 0
            details['quality_breakdown'] = {
                'teaching': 0,
                'facility': 0,
                'management': 0
            }
        
        # academy 객체를 시리얼라이저에서 사용할 수 있도록 변환
        academy_serializer = ComparisonAcademySerializer(academy)
        
        results.append({
            'academy': academy_serializer.data,
            'total_score': round(score, 2),
            'details': details
        })
    
    # 점수 순으로 정렬
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    return Response({
        'comparison_results': results,
        'weights': {
            'tuition': temp_comparison.tuition_weight,
            'rating': temp_comparison.rating_weight,
            'distance': temp_comparison.distance_weight,
            'quality': temp_comparison.quality_weight
        },
        'base_location': {
            'latitude': base_latitude,
            'longitude': base_longitude
        }
    })


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def comparison_template_list_create(request):
    """비교 템플릿 목록 조회 및 생성"""
    
    if request.method == 'GET':
        templates = ComparisonTemplate.objects.filter(user=request.user)
        serializer = ComparisonTemplateSerializer(templates, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = ComparisonTemplateSerializer(
            data=request.data, 
            context={'request': request}
        )
        if serializer.is_valid():
            template = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def comparison_template_detail(request, pk):
    """비교 템플릿 상세 조회, 수정, 삭제"""
    
    template = get_object_or_404(ComparisonTemplate, pk=pk, user=request.user)
    
    if request.method == 'GET':
        serializer = ComparisonTemplateSerializer(template)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = ComparisonTemplateSerializer(
            template,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        template.delete()
        return Response({'message': '템플릿이 삭제되었습니다.'}, 
                       status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_comparison_from_template(request, template_id):
    """템플릿으로부터 비교 생성"""
    
    template = get_object_or_404(ComparisonTemplate, pk=template_id, user=request.user)
    
    # 요청 데이터에서 학원 ID와 기본 정보 가져오기
    academy_ids = request.data.get('academy_ids', [])
    name = request.data.get('name', f"{template.name} 비교")
    description = request.data.get('description', '')
    base_latitude = request.data.get('base_latitude')
    base_longitude = request.data.get('base_longitude')
    base_address = request.data.get('base_address', '')
    
    if not academy_ids or len(academy_ids) < 2:
        return Response(
            {'error': '최소 2개 이상의 학원을 선택해야 합니다.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 템플릿 설정으로 비교 생성
    comparison_data = {
        'name': name,
        'description': description,
        'academy_ids': academy_ids,
        'compare_tuition': template.compare_tuition,
        'compare_rating': template.compare_rating,
        'compare_distance': template.compare_distance,
        'compare_subjects': template.compare_subjects,
        'compare_facilities': template.compare_facilities,
        'tuition_weight': template.tuition_weight,
        'rating_weight': template.rating_weight,
        'distance_weight': template.distance_weight,
        'quality_weight': template.quality_weight,
        'base_latitude': base_latitude,
        'base_longitude': base_longitude,
        'base_address': base_address
    }
    
    serializer = AcademyComparisonSerializer(
        data=comparison_data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        comparison = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def comparison_history(request):
    """비교 기록 조회"""
    
    history = ComparisonHistory.objects.filter(user=request.user)
    
    # 필터링
    action = request.query_params.get('action')
    if action:
        history = history.filter(action=action)
    
    # 정렬
    history = history.order_by('-created_at')
    
    # 페이지네이션
    paginator = ComparisonPagination()
    page = paginator.paginate_queryset(history, request)
    
    if page is not None:
        serializer = ComparisonHistorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    serializer = ComparisonHistorySerializer(history, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def share_comparison(request, pk):
    """비교 공유"""
    
    comparison = get_object_or_404(AcademyComparison, pk=pk, user=request.user)
    
    # 공개 상태로 변경
    comparison.is_public = True
    comparison.save()
    
    # 공유 기록 생성
    ComparisonHistory.objects.create(
        user=request.user,
        comparison=comparison,
        action='shared'
    )
    
    # 공유 URL 생성 (프론트엔드에서 사용)
    share_url = f"/comparisons/shared/{comparison.id}"
    
    return Response({
        'message': '비교가 공유되었습니다.',
        'share_url': share_url,
        'is_public': comparison.is_public
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def shared_comparison_detail(request, pk):
    """공유된 비교 조회"""
    
    comparison = get_object_or_404(
        AcademyComparison, 
        pk=pk, 
        is_public=True
    )
    
    serializer = AcademyComparisonSerializer(comparison, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def export_comparison(request, pk):
    """비교 결과 내보내기"""
    
    comparison = get_object_or_404(AcademyComparison, pk=pk, user=request.user)
    
    export_serializer = ComparisonExportSerializer(data=request.data)
    if not export_serializer.is_valid():
        return Response(export_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    export_format = export_serializer.validated_data['format']
    include_details = export_serializer.validated_data['include_details']
    include_scores = export_serializer.validated_data['include_scores']
    
    # 내보내기 기록 생성
    ComparisonHistory.objects.create(
        user=request.user,
        comparison=comparison,
        action='exported',
        details={'format': export_format}
    )
    
    # 데이터 준비
    comparison_serializer = AcademyComparisonSerializer(
        comparison, 
        context={'request': request}
    )
    data = comparison_serializer.data
    
    if export_format == 'json':
        response_data = {
            'comparison': {
                'name': data['name'],
                'description': data['description'],
                'created_at': data['created_at']
            },
            'academies': data['academies']
        }
        
        if include_scores:
            response_data['results'] = data['comparison_results']
        
        return Response(response_data)
    
    elif export_format == 'csv':
        # CSV 형태로 내보내기
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="comparison_{comparison.id}.csv"'
        
        writer = csv.writer(response)
        
        # 헤더
        headers = ['학원명', '주소', '평점', '수강료']
        if include_scores:
            headers.extend(['종합점수', '평점점수', '거리점수', '수강료점수', '품질점수'])
        writer.writerow(headers)
        
        # 데이터
        for result in data['comparison_results']:
            academy = result['academy']
            row = [
                academy['상호명'],
                academy['도로명주소'],
                academy.get('별점', ''),
                academy.get('수강료_평균', '')
            ]
            
            if include_scores:
                row.extend([
                    result['total_score'],
                    result['details'].get('rating_score', 0),
                    result['details'].get('distance_score', 0),
                    result['details'].get('tuition_score', 0),
                    result['details'].get('quality_score', 0)
                ])
            
            writer.writerow(row)
        
        return response
    
    return Response({'error': '지원하지 않는 형식입니다.'}, 
                   status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def comparison_stats(request):
    """사용자 비교 통계"""
    
    user = request.user
    
    # 전체 비교 수
    total_comparisons = AcademyComparison.objects.filter(user=user).count()
    
    # 공개 비교 수
    public_comparisons = AcademyComparison.objects.filter(
        user=user, 
        is_public=True
    ).count()
    
    # 최근 30일 비교 활동
    from django.utils import timezone
    from datetime import timedelta
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_activity = ComparisonHistory.objects.filter(
        user=user,
        created_at__gte=thirty_days_ago
    ).count()
    
    # 가장 많이 비교된 학원들
    from django.db.models import Count
    popular_academies = Academy.objects.filter(
        comparisons__user=user
    ).annotate(
        comparison_count=Count('comparisons')
    ).order_by('-comparison_count')[:5]
    
    popular_academies_data = []
    for academy in popular_academies:
        popular_academies_data.append({
            'academy_id': academy.id,
            'academy_name': academy.상호명,
            'comparison_count': academy.comparison_count
        })
    
    # 템플릿 수
    template_count = ComparisonTemplate.objects.filter(user=user).count()
    
    return Response({
        'total_comparisons': total_comparisons,
        'public_comparisons': public_comparisons,
        'recent_activity': recent_activity,
        'popular_academies': popular_academies_data,
        'template_count': template_count
    })