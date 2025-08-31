from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from main.models import Data as Academy
from .recommendation_models import (
    UserPreferenceProfile, RecommendationHistory, UserBehaviorLog
)
from .recommendation_serializers import (
    UserPreferenceProfileSerializer, RecommendationRequestSerializer,
    LocationBasedRecommendationSerializer, SimilarAcademyRequestSerializer,
    RecommendationResultSerializer, RecommendationHistorySerializer,
    UserBehaviorLogSerializer, BehaviorTrackingSerializer,
    RecommendationFeedbackSerializer, PreferenceAnalysisSerializer,
    RecommendationStatsSerializer
)
from .recommendation_services import recommendation_engine

logger = logging.getLogger(__name__)


class UserPreferenceViewSet(viewsets.ModelViewSet):
    """사용자 선호도 프로필 ViewSet"""
    
    serializer_class = UserPreferenceProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """사용자 선호도 프로필 조회/생성"""
        profile, created = UserPreferenceProfile.objects.get_or_create(
            user=self.request.user
        )
        if created:
            logger.info(f"새로운 선호도 프로필 생성: {self.request.user.username}")
        return profile
    
    def list(self, request):
        """선호도 프로필 조회"""
        profile = self.get_object()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """선호도 프로필 업데이트"""
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            logger.info(f"선호도 프로필 업데이트: {request.user.username}")
            
            return Response({
                'message': '선호도 프로필이 업데이트되었습니다.',
                'data': serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def reset_to_default(self, request):
        """기본 설정으로 초기화"""
        profile = self.get_object()
        
        # 기본값으로 초기화
        profile.distance_weight = 4
        profile.price_weight = 3
        profile.rating_weight = 5
        profile.facility_weight = 3
        profile.teacher_weight = 4
        profile.max_distance = 5.0
        profile.max_price_range = 500000
        profile.min_rating = 3.0
        profile.preferred_subjects = []
        profile.preferred_academy_types = []
        profile.preferred_time_slots = []
        profile.learning_purposes = []
        profile.auto_update_enabled = True
        profile.save()
        
        serializer = self.get_serializer(profile)
        return Response({
            'message': '선호도 프로필이 기본값으로 초기화되었습니다.',
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def analysis(self, request):
        """선호도 분석"""
        user = request.user
        
        # 최근 30일간의 행동 로그 분석
        recent_logs = UserBehaviorLog.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).select_related('academy')
        
        # 가장 많이 본 과목들
        viewed_academies = recent_logs.filter(
            action_type='view',
            academy__isnull=False
        ).values_list('academy', flat=True)
        
        most_viewed_subjects = []
        if viewed_academies:
            academies = Academy.objects.filter(id__in=viewed_academies)
            subject_counts = {}
            
            for academy in academies:
                subjects = recommendation_engine._get_academy_subjects(academy)
                for subject in subjects:
                    subject_counts[subject] = subject_counts.get(subject, 0) + 1
            
            most_viewed_subjects = sorted(
                subject_counts.keys(), 
                key=lambda x: subject_counts[x], 
                reverse=True
            )[:5]
        
        # 평균 선호 거리 계산
        profile = self.get_object()
        avg_distance = None
        
        if (profile.base_latitude and profile.base_longitude and 
            recent_logs.filter(action_type__in=['view', 'bookmark']).exists()):
            
            distances = []
            for log in recent_logs.filter(action_type__in=['view', 'bookmark']):
                if log.academy and log.academy.위도 and log.academy.경도:
                    distance = recommendation_engine._calculate_distance(
                        profile.base_latitude, profile.base_longitude,
                        float(log.academy.위도), float(log.academy.경도)
                    )
                    distances.append(distance)
            
            if distances:
                avg_distance = sum(distances) / len(distances)
        
        # 선호 가격대 분석
        price_analysis = {'min': None, 'max': None, 'avg': None}
        
        bookmarked_academies = recent_logs.filter(
            action_type='bookmark',
            academy__isnull=False
        ).values_list('academy', flat=True)
        
        if bookmarked_academies:
            academies = Academy.objects.filter(id__in=bookmarked_academies)
            prices = []
            
            for academy in academies:
                if hasattr(academy, '수강료') and academy.수강료:
                    try:
                        price = float(academy.수강료.replace(',', '').replace('원', ''))
                        prices.append(price)
                    except (ValueError, AttributeError):
                        pass
            
            if prices:
                price_analysis = {
                    'min': min(prices),
                    'max': max(prices),
                    'avg': sum(prices) / len(prices)
                }
        
        # 활동 패턴
        activity_patterns = dict(
            recent_logs.values('action_type')
            .annotate(count=Count('id'))
            .values_list('action_type', 'count')
        )
        
        # 위치 선호도 (구/동별 분석)
        location_preferences = {}
        location_logs = recent_logs.filter(
            action_type__in=['view', 'bookmark'],
            academy__isnull=False
        )
        
        for log in location_logs:
            if hasattr(log.academy, '구') and log.academy.구:
                district = log.academy.구
                location_preferences[district] = location_preferences.get(district, 0) + 1
        
        # 추천 정확도 계산
        recommendations = RecommendationHistory.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=30)
        )
        
        recommendation_accuracy = 0
        if recommendations.exists():
            positive_actions = recommendations.filter(
                Q(user_clicked=True) | Q(user_bookmarked=True) | Q(user_contacted=True)
            ).count()
            recommendation_accuracy = (positive_actions / recommendations.count()) * 100
        
        analysis_data = {
            'most_viewed_subjects': most_viewed_subjects,
            'average_preferred_distance': avg_distance,
            'preferred_price_range': price_analysis,
            'activity_patterns': activity_patterns,
            'location_preferences': location_preferences,
            'recommendation_accuracy': round(recommendation_accuracy, 2)
        }
        
        serializer = PreferenceAnalysisSerializer(data=analysis_data)
        serializer.is_valid()
        return Response(serializer.data)


class RecommendationViewSet(viewsets.ViewSet):
    """추천 ViewSet"""
    
    permission_classes = [IsAuthenticated]
    
    def create(self, request):
        """맞춤 추천 요청"""
        serializer = RecommendationRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            
            # 위치 정보 처리
            location = None
            if data.get('latitude') and data.get('longitude'):
                location = (data['latitude'], data['longitude'])
            
            try:
                recommendations = recommendation_engine.get_recommendations_for_user(
                    user=request.user,
                    location=location,
                    limit=data['limit'],
                    recommendation_type=data['recommendation_type']
                )
                
                # 행동 로그 기록
                recommendation_engine.record_user_behavior(
                    user=request.user,
                    action_type='search',
                    action_data={
                        'recommendation_type': data['recommendation_type'],
                        'subjects': data.get('subjects', []),
                        'limit': data['limit']
                    },
                    location=location
                )
                
                return Response({
                    'message': f'{len(recommendations)}개의 추천 결과를 찾았습니다.',
                    'recommendations': recommendations,
                    'total_count': len(recommendations)
                })
                
            except Exception as e:
                logger.error(f"추천 생성 실패: {str(e)}")
                return Response({
                    'error': '추천을 생성하는 중 오류가 발생했습니다.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def location_based(self, request):
        """위치 기반 추천"""
        serializer = LocationBasedRecommendationSerializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            
            try:
                recommendations = recommendation_engine.get_location_based_recommendations(
                    latitude=data['latitude'],
                    longitude=data['longitude'],
                    radius=data['radius'],
                    subjects=data.get('subjects'),
                    limit=data['limit']
                )
                
                # 행동 로그 기록
                recommendation_engine.record_user_behavior(
                    user=request.user,
                    action_type='search',
                    action_data={
                        'search_type': 'location_based',
                        'radius': data['radius'],
                        'subjects': data.get('subjects', [])
                    },
                    location=(data['latitude'], data['longitude'])
                )
                
                return Response({
                    'message': f'{len(recommendations)}개의 추천 결과를 찾았습니다.',
                    'recommendations': recommendations,
                    'search_center': {
                        'latitude': data['latitude'],
                        'longitude': data['longitude'],
                        'radius': data['radius']
                    }
                })
                
            except Exception as e:
                logger.error(f"위치 기반 추천 실패: {str(e)}")
                return Response({
                    'error': '위치 기반 추천을 생성하는 중 오류가 발생했습니다.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def similar_academies(self, request):
        """유사 학원 추천"""
        serializer = SimilarAcademyRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            
            try:
                recommendations = recommendation_engine.get_similar_academies(
                    academy_id=data['academy_id'],
                    limit=data['limit']
                )
                
                # 기준 학원 정보 조회
                try:
                    base_academy = Academy.objects.get(id=data['academy_id'])
                    base_academy_name = base_academy.상호명
                except Academy.DoesNotExist:
                    return Response({
                        'error': '기준 학원을 찾을 수 없습니다.'
                    }, status=status.HTTP_404_NOT_FOUND)
                
                # 행동 로그 기록
                recommendation_engine.record_user_behavior(
                    user=request.user,
                    action_type='search',
                    academy=base_academy,
                    action_data={
                        'search_type': 'similar_academies',
                        'base_academy_id': data['academy_id']
                    }
                )
                
                return Response({
                    'message': f'{base_academy_name}과(와) 유사한 {len(recommendations)}개의 학원을 찾았습니다.',
                    'base_academy': {
                        'id': base_academy.id,
                        'name': base_academy_name
                    },
                    'recommendations': recommendations
                })
                
            except Exception as e:
                logger.error(f"유사 학원 추천 실패: {str(e)}")
                return Response({
                    'error': '유사 학원 추천을 생성하는 중 오류가 발생했습니다.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BehaviorTrackingViewSet(viewsets.ViewSet):
    """사용자 행동 추적 ViewSet"""
    
    permission_classes = [IsAuthenticated]
    
    def create(self, request):
        """행동 추적 기록"""
        serializer = BehaviorTrackingSerializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            
            # 학원 조회
            academy = None
            if data.get('academy_id'):
                try:
                    academy = Academy.objects.get(id=data['academy_id'])
                except Academy.DoesNotExist:
                    return Response({
                        'error': '학원을 찾을 수 없습니다.'
                    }, status=status.HTTP_404_NOT_FOUND)
            
            # 위치 정보 처리
            location = None
            if data.get('latitude') and data.get('longitude'):
                location = (data['latitude'], data['longitude'])
            
            # 행동 기록
            recommendation_engine.record_user_behavior(
                user=request.user,
                action_type=data['action_type'],
                academy=academy,
                action_data=data.get('action_data', {}),
                location=location
            )
            
            return Response({
                'message': '행동이 기록되었습니다.',
                'recorded_action': data['action_type']
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_track(self, request):
        """대량 행동 추적"""
        if not isinstance(request.data, list):
            return Response({
                'error': '배열 형태의 데이터가 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        recorded_count = 0
        errors = []
        
        for i, behavior_data in enumerate(request.data):
            serializer = BehaviorTrackingSerializer(data=behavior_data)
            
            if serializer.is_valid():
                data = serializer.validated_data
                
                # 학원 조회
                academy = None
                if data.get('academy_id'):
                    try:
                        academy = Academy.objects.get(id=data['academy_id'])
                    except Academy.DoesNotExist:
                        errors.append(f"인덱스 {i}: 학원을 찾을 수 없습니다.")
                        continue
                
                # 위치 정보 처리
                location = None
                if data.get('latitude') and data.get('longitude'):
                    location = (data['latitude'], data['longitude'])
                
                # 행동 기록
                recommendation_engine.record_user_behavior(
                    user=request.user,
                    action_type=data['action_type'],
                    academy=academy,
                    action_data=data.get('action_data', {}),
                    location=location
                )
                recorded_count += 1
            else:
                errors.append(f"인덱스 {i}: {serializer.errors}")
        
        return Response({
            'message': f'{recorded_count}개의 행동이 기록되었습니다.',
            'recorded_count': recorded_count,
            'errors': errors if errors else None
        })


class RecommendationHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """추천 기록 ViewSet"""
    
    serializer_class = RecommendationHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """사용자별 추천 기록 조회"""
        return RecommendationHistory.objects.filter(
            user=self.request.user
        ).select_related('academy').order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def feedback(self, request, pk=None):
        """추천에 대한 피드백 제공"""
        recommendation = get_object_or_404(
            RecommendationHistory,
            pk=pk,
            user=request.user
        )
        
        serializer = RecommendationFeedbackSerializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            
            # 피드백 업데이트
            recommendation.user_feedback = data['feedback']
            recommendation.user_clicked = data.get('clicked', recommendation.user_clicked)
            recommendation.user_bookmarked = data.get('bookmarked', recommendation.user_bookmarked)
            recommendation.user_contacted = data.get('contacted', recommendation.user_contacted)
            recommendation.user_enrolled = data.get('enrolled', recommendation.user_enrolled)
            recommendation.save()
            
            return Response({
                'message': '피드백이 기록되었습니다.',
                'feedback': data['feedback']
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """추천 통계"""
        user_recommendations = self.get_queryset()
        
        # 기본 통계
        total_count = user_recommendations.count()
        clicked_count = user_recommendations.filter(user_clicked=True).count()
        bookmarked_count = user_recommendations.filter(user_bookmarked=True).count()
        
        click_rate = (clicked_count / total_count * 100) if total_count > 0 else 0
        bookmark_rate = (bookmarked_count / total_count * 100) if total_count > 0 else 0
        
        # 추천 방식별 통계
        type_stats = dict(
            user_recommendations.values('recommendation_type')
            .annotate(count=Count('id'))
            .values_list('recommendation_type', 'count')
        )
        
        # 최근 7일간 일별 통계
        daily_stats = []
        for i in range(7):
            date = timezone.now().date() - timedelta(days=i)
            daily_count = user_recommendations.filter(
                created_at__date=date
            ).count()
            daily_stats.append({
                'date': date.isoformat(),
                'count': daily_count
            })
        
        # 가장 많이 추천된 학원들
        top_academies = (
            user_recommendations.values('academy__id', 'academy__상호명')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        
        top_recommended_academies = [
            {
                'academy_id': item['academy__id'],
                'academy_name': item['academy__상호명'],
                'recommendation_count': item['count']
            }
            for item in top_academies
        ]
        
        stats_data = {
            'total_recommendations': total_count,
            'clicked_recommendations': clicked_count,
            'bookmarked_recommendations': bookmarked_count,
            'click_through_rate': round(click_rate, 2),
            'bookmark_rate': round(bookmark_rate, 2),
            'recommendation_type_stats': type_stats,
            'daily_stats': daily_stats,
            'weekly_stats': [],  # 필요시 구현
            'top_recommended_academies': top_recommended_academies
        }
        
        serializer = RecommendationStatsSerializer(data=stats_data)
        serializer.is_valid()
        return Response(serializer.data)


class AdminRecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    """관리자용 추천 분석 ViewSet"""
    
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def system_stats(self, request):
        """전체 시스템 추천 통계"""
        # 전체 추천 통계
        all_recommendations = RecommendationHistory.objects.all()
        
        total_users = all_recommendations.values('user').distinct().count()
        total_recommendations = all_recommendations.count()
        avg_recommendations_per_user = total_recommendations / total_users if total_users > 0 else 0
        
        # 추천 성과
        clicked_recommendations = all_recommendations.filter(user_clicked=True).count()
        bookmarked_recommendations = all_recommendations.filter(user_bookmarked=True).count()
        
        overall_click_rate = (clicked_recommendations / total_recommendations * 100) if total_recommendations > 0 else 0
        overall_bookmark_rate = (bookmarked_recommendations / total_recommendations * 100) if total_recommendations > 0 else 0
        
        # 최근 30일간 트렌드
        recent_recommendations = all_recommendations.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        )
        
        # 인기 학원 (추천 횟수 기준)
        popular_academies = (
            all_recommendations.values('academy__id', 'academy__상호명')
            .annotate(
                recommendation_count=Count('id'),
                avg_score=Avg('recommendation_score')
            )
            .order_by('-recommendation_count')[:10]
        )
        
        return Response({
            'total_users_with_recommendations': total_users,
            'total_recommendations': total_recommendations,
            'average_recommendations_per_user': round(avg_recommendations_per_user, 2),
            'overall_click_through_rate': round(overall_click_rate, 2),
            'overall_bookmark_rate': round(overall_bookmark_rate, 2),
            'recent_30_days_count': recent_recommendations.count(),
            'popular_academies': [
                {
                    'academy_id': item['academy__id'],
                    'academy_name': item['academy__상호명'],
                    'recommendation_count': item['recommendation_count'],
                    'average_score': round(item['avg_score'], 2)
                }
                for item in popular_academies
            ]
        })