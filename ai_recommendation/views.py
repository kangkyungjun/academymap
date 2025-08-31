from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import logging
from datetime import timedelta

from .models import (
    UserPreference, UserBehavior, AcademyVector, 
    Recommendation, RecommendationLog, AcademySimilarity
)
from .services import RecommendationEngine, PreferenceAnalyzer, VectorBuilder, SimilarityCalculator
from .serializers import (
    UserPreferenceSerializer, UserBehaviorSerializer,
    RecommendationSerializer, AcademyRecommendationSerializer
)
from main.models import Data as Academy

logger = logging.getLogger(__name__)


class UserPreferenceViewSet(viewsets.ModelViewSet):
    """사용자 선호도 관리"""
    serializer_class = UserPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserPreference.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def update_preferences(self, request):
        """선호도 일괄 업데이트"""
        try:
            preferences_data = request.data.get('preferences', {})
            
            for pref_type, pref_value in preferences_data.items():
                weight = pref_value.get('weight', 1.0) if isinstance(pref_value, dict) else 1.0
                value = pref_value.get('value', pref_value) if isinstance(pref_value, dict) else pref_value
                
                preference, created = UserPreference.objects.update_or_create(
                    user=request.user,
                    preference_type=pref_type,
                    defaults={
                        'preference_value': json.dumps(value, ensure_ascii=False),
                        'weight': weight
                    }
                )
            
            # 선호도 업데이트 후 캐시 무효화
            cache_key = f"recommendations_{request.user.id}_*"
            cache.delete_many(cache.get(cache_key, []))
            
            return Response({'message': '선호도가 업데이트되었습니다.'})
            
        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            return Response(
                {'error': '선호도 업데이트 중 오류가 발생했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def analyze_from_behavior(self, request):
        """행동 패턴에서 선호도 자동 분석"""
        try:
            analyzer = PreferenceAnalyzer()
            preferences = analyzer.extract_user_preferences(request.user)
            
            return Response({
                'preferences': preferences,
                'message': '행동 패턴 분석이 완료되었습니다.'
            })
            
        except Exception as e:
            logger.error(f"Error analyzing preferences: {e}")
            return Response(
                {'error': '선호도 분석 중 오류가 발생했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserBehaviorViewSet(viewsets.ReadOnlyModelViewSet):
    """사용자 행동 조회"""
    serializer_class = UserBehaviorSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserBehavior.objects.filter(user=self.request.user).order_by('-timestamp')
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """행동 통계"""
        try:
            behaviors = self.get_queryset().filter(
                timestamp__gte=timezone.now() - timedelta(days=30)
            )
            
            # 행동 유형별 통계
            action_stats = behaviors.values('action').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # 학원별 상호작용 통계
            academy_stats = behaviors.filter(
                academy__isnull=False
            ).values(
                'academy__상호명'
            ).annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            # 시간별 활동 패턴
            hourly_stats = {}
            for behavior in behaviors:
                hour = behavior.timestamp.hour
                hourly_stats[hour] = hourly_stats.get(hour, 0) + 1
            
            return Response({
                'action_statistics': list(action_stats),
                'top_academies': list(academy_stats),
                'hourly_pattern': hourly_stats,
                'total_behaviors': behaviors.count()
            })
            
        except Exception as e:
            logger.error(f"Error getting behavior statistics: {e}")
            return Response(
                {'error': '행동 통계 조회 중 오류가 발생했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class RecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    """추천 관리"""
    serializer_class = RecommendationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Recommendation.objects.filter(user=self.request.user).order_by('-final_score')
    
    @action(detail=False, methods=['get'])
    def personalized(self, request):
        """개인화 추천"""
        try:
            limit = min(int(request.query_params.get('limit', 10)), 50)
            session_id = request.query_params.get('session_id', '')
            
            # 추천 엔진 실행
            engine = RecommendationEngine()
            context = {
                'session_id': session_id,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': self.get_client_ip(request)
            }
            
            recommendations = engine.get_recommendations(
                user=request.user,
                limit=limit,
                context=context
            )
            
            # 응답 데이터 구성
            response_data = []
            for rec in recommendations:
                academy_data = AcademyRecommendationSerializer(rec['academy']).data
                academy_data.update({
                    'recommendation_score': rec['final_score'],
                    'confidence_score': rec.get('confidence_score', 0.5),
                    'reason_type': rec['reason_type'],
                    'explanation': rec.get('explanation', ''),
                    'reason_details': rec.get('reason_details', {})
                })
                response_data.append(academy_data)
            
            # 로그 기록
            RecommendationLog.objects.create(
                user=request.user,
                log_type='serving',
                message=f'Served {len(response_data)} personalized recommendations',
                recommendation_count=len(response_data),
                session_id=session_id,
                ip_address=context['ip_address'],
                user_agent=context['user_agent']
            )
            
            return Response({
                'recommendations': response_data,
                'total_count': len(response_data),
                'generated_at': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error generating personalized recommendations: {e}")
            return Response(
                {'error': '개인화 추천 생성 중 오류가 발생했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def similar_academies(self, request):
        """유사 학원 추천"""
        try:
            academy_id = request.query_params.get('academy_id')
            if not academy_id:
                return Response(
                    {'error': '학원 ID가 필요합니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            academy = get_object_or_404(Academy, id=academy_id)
            limit = min(int(request.query_params.get('limit', 5)), 20)
            
            # 유사 학원 조회
            similarities = AcademySimilarity.objects.filter(
                Q(academy1=academy) | Q(academy2=academy)
            ).select_related('academy1', 'academy2').order_by('-overall_similarity')[:limit]
            
            similar_academies = []
            for sim in similarities:
                similar_academy = sim.academy2 if sim.academy1 == academy else sim.academy1
                academy_data = AcademyRecommendationSerializer(similar_academy).data
                academy_data.update({
                    'similarity_score': sim.overall_similarity,
                    'content_similarity': sim.content_similarity,
                    'location_similarity': sim.location_similarity,
                    'user_similarity': sim.user_similarity
                })
                similar_academies.append(academy_data)
            
            return Response({
                'base_academy': AcademyRecommendationSerializer(academy).data,
                'similar_academies': similar_academies,
                'total_count': len(similar_academies)
            })
            
        except Exception as e:
            logger.error(f"Error getting similar academies: {e}")
            return Response(
                {'error': '유사 학원 조회 중 오류가 발생했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def feedback(self, request, pk=None):
        """추천 피드백"""
        try:
            recommendation = self.get_object()
            feedback_score = request.data.get('score')
            comment = request.data.get('comment', '')
            
            if feedback_score is not None:
                recommendation.add_feedback(feedback_score, comment)
                
                # 피드백 로그 기록
                RecommendationLog.objects.create(
                    user=request.user,
                    log_type='feedback',
                    message=f'Feedback received for recommendation {recommendation.id}',
                    data={
                        'recommendation_id': recommendation.id,
                        'academy_id': recommendation.academy_id,
                        'feedback_score': feedback_score,
                        'comment': comment
                    }
                )
                
                return Response({'message': '피드백이 등록되었습니다.'})
            
            return Response(
                {'error': '피드백 점수가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            return Response(
                {'error': '피드백 처리 중 오류가 발생했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def click(self, request, pk=None):
        """추천 클릭 추적"""
        try:
            recommendation = self.get_object()
            recommendation.mark_as_clicked()
            
            return Response({'message': '클릭이 기록되었습니다.'})
            
        except Exception as e:
            logger.error(f"Error tracking click: {e}")
            return Response({'message': '클릭 기록 실패'})
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class BehaviorTrackingView(APIView):
    """사용자 행동 추적 API"""
    
    def post(self, request):
        """행동 데이터 수집"""
        try:
            data = json.loads(request.body)
            
            # 필수 필드 검증
            required_fields = ['action']
            for field in required_fields:
                if field not in data:
                    return JsonResponse(
                        {'error': f'필수 필드 {field}가 누락되었습니다.'},
                        status=400
                    )
            
            # 사용자 인증 (토큰 또는 세션 기반)
            user = self.get_authenticated_user(request)
            if not user:
                # 비회원의 경우 세션 기반 추적
                user = None
            
            # 행동 데이터 저장
            behavior = UserBehavior.objects.create(
                user=user,
                academy_id=data.get('academy_id'),
                action=data.get('action'),
                search_query=data.get('search_query', ''),
                filter_criteria=data.get('filter_criteria', {}),
                session_id=data.get('session_id', ''),
                page_url=data.get('page_url', ''),
                referrer=data.get('referrer', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                ip_address=self.get_client_ip(request),
                duration=data.get('duration', 0)
            )
            
            return JsonResponse({
                'message': '행동이 기록되었습니다.',
                'behavior_id': behavior.id
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': '잘못된 JSON 데이터입니다.'}, status=400)
        except Exception as e:
            logger.error(f"Error tracking behavior: {e}")
            return JsonResponse({'error': '행동 추적 중 오류가 발생했습니다.'}, status=500)
    
    def get_authenticated_user(self, request):
        """인증된 사용자 반환"""
        try:
            from django.contrib.auth import get_user_model
            from rest_framework.authtoken.models import Token
            
            User = get_user_model()
            
            # Authorization 헤더에서 토큰 추출
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header and auth_header.startswith('Token '):
                token_key = auth_header[6:]
                try:
                    token = Token.objects.select_related('user').get(key=token_key)
                    return token.user
                except Token.DoesNotExist:
                    pass
            
            # 세션 기반 인증
            if request.user.is_authenticated:
                return request.user
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting authenticated user: {e}")
            return None
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RecommendationAnalyticsView(APIView):
    """추천 시스템 분석"""
    
    def get(self, request):
        """추천 시스템 전체 통계"""
        try:
            # 추천 통계
            total_recommendations = Recommendation.objects.count()
            clicked_recommendations = Recommendation.objects.filter(is_clicked=True).count()
            contacted_recommendations = Recommendation.objects.filter(is_contacted=True).count()
            
            click_rate = (clicked_recommendations / total_recommendations * 100) if total_recommendations > 0 else 0
            contact_rate = (contacted_recommendations / total_recommendations * 100) if total_recommendations > 0 else 0
            
            # 피드백 통계
            feedback_stats = Recommendation.objects.filter(
                feedback_score__isnull=False
            ).aggregate(
                avg_score=Avg('feedback_score'),
                total_feedback=Count('id')
            )
            
            # 사용자 행동 통계
            behavior_stats = UserBehavior.objects.values('action').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # 인기 학원 통계
            popular_academies = Recommendation.objects.values(
                'academy__상호명'
            ).annotate(
                recommendation_count=Count('id'),
                click_count=Count('id', filter=Q(is_clicked=True))
            ).order_by('-recommendation_count')[:10]
            
            return JsonResponse({
                'recommendation_stats': {
                    'total_recommendations': total_recommendations,
                    'click_rate': round(click_rate, 2),
                    'contact_rate': round(contact_rate, 2),
                    'avg_feedback_score': round(feedback_stats['avg_score'] or 0, 2),
                    'total_feedback': feedback_stats['total_feedback']
                },
                'behavior_stats': list(behavior_stats),
                'popular_academies': list(popular_academies)
            })
            
        except Exception as e:
            logger.error(f"Error getting system statistics: {e}")
            return JsonResponse({'error': '통계 조회 중 오류가 발생했습니다.'}, status=500)
    
    def post(self, request):
        """모델 성능 분석"""
        try:
            from .models import RecommendationModel
            
            models = RecommendationModel.objects.filter(is_active=True)
            model_stats = []
            
            for model in models:
                recommendations = Recommendation.objects.filter(model=model)
                
                total_count = recommendations.count()
                clicked_count = recommendations.filter(is_clicked=True).count()
                feedback_avg = recommendations.filter(
                    feedback_score__isnull=False
                ).aggregate(avg=Avg('feedback_score'))['avg'] or 0
                
                model_stats.append({
                    'model_name': model.name,
                    'model_type': model.get_model_type_display(),
                    'version': model.version,
                    'total_recommendations': total_count,
                    'click_rate': (clicked_count / total_count * 100) if total_count > 0 else 0,
                    'avg_feedback_score': round(feedback_avg, 2),
                    'accuracy': model.accuracy,
                    'precision': model.precision,
                    'recall': model.recall,
                    'f1_score': model.f1_score
                })
            
            return JsonResponse({'model_performance': model_stats})
            
        except Exception as e:
            logger.error(f"Error getting model performance: {e}")
            return JsonResponse({'error': '모델 성능 조회 중 오류가 발생했습니다.'}, status=500)


class RecommendationMaintenanceView(APIView):
    """추천 시스템 유지보수"""
    
    def post(self, request):
        """학원 벡터 재구성"""
        try:
            builder = VectorBuilder()
            builder.build_academy_vectors()
            
            return JsonResponse({'message': '학원 벡터 재구성이 완료되었습니다.'})
            
        except Exception as e:
            logger.error(f"Error rebuilding vectors: {e}")
            return JsonResponse({'error': '벡터 재구성 중 오류가 발생했습니다.'}, status=500)
    
    def put(self, request):
        """유사도 재계산"""
        try:
            calculator = SimilarityCalculator()
            calculator.calculate_all_similarities()
            
            return JsonResponse({'message': '유사도 재계산이 완료되었습니다.'})
            
        except Exception as e:
            logger.error(f"Error recalculating similarities: {e}")
            return JsonResponse({'error': '유사도 재계산 중 오류가 발생했습니다.'}, status=500)
    
    def delete(self, request):
        """추천 캐시 삭제"""
        try:
            cache.clear()
            
            return JsonResponse({'message': '캐시가 삭제되었습니다.'})
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return JsonResponse({'error': '캐시 삭제 중 오류가 발생했습니다.'}, status=500)