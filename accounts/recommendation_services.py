import logging
import math
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, Count, Avg, F, Value
from django.db.models.functions import Coalesce
from django.contrib.auth import get_user_model
from django.core.cache import cache

from main.models import Data as Academy
from .recommendation_models import (
    UserPreferenceProfile, RecommendationHistory, 
    UserBehaviorLog, LocationBasedRecommendation
)
from .review_models import Review

User = get_user_model()
logger = logging.getLogger(__name__)


class RecommendationEngine:
    """추천 엔진 메인 클래스"""
    
    def __init__(self):
        self.cache_timeout = 3600  # 1시간 캐시
        self.max_recommendations = 20
        self.min_score_threshold = 30.0
    
    def get_recommendations_for_user(
        self, 
        user: User, 
        location: Optional[Tuple[float, float]] = None,
        limit: int = 10,
        recommendation_type: str = 'comprehensive'
    ) -> List[Dict[str, Any]]:
        """사용자별 맞춤 추천"""
        
        # 사용자 선호도 프로필 조회/생성
        profile, created = UserPreferenceProfile.objects.get_or_create(
            user=user,
            defaults={
                'distance_weight': 4,
                'price_weight': 3,
                'rating_weight': 5,
                'facility_weight': 3,
                'teacher_weight': 4,
            }
        )
        
        if created:
            logger.info(f"새로운 선호도 프로필 생성: {user.username}")
        
        # 캐시 키 생성
        cache_key = self._generate_cache_key(
            user_id=user.id,
            location=location,
            recommendation_type=recommendation_type
        )
        
        # 캐시된 결과 확인
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"캐시된 추천 결과 반환: {user.username}")
            return cached_result[:limit]
        
        # 추천 계산
        recommendations = self._calculate_recommendations(
            profile, location, recommendation_type
        )
        
        # 결과 제한 및 필터링
        filtered_recommendations = [
            rec for rec in recommendations 
            if rec['score'] >= self.min_score_threshold
        ][:self.max_recommendations]
        
        # 캐시 저장
        cache.set(cache_key, filtered_recommendations, self.cache_timeout)
        
        # 추천 기록 저장
        self._save_recommendation_history(
            user, filtered_recommendations[:limit], recommendation_type, location
        )
        
        return filtered_recommendations[:limit]
    
    def get_location_based_recommendations(
        self,
        latitude: float,
        longitude: float,
        radius: float = 5.0,
        subjects: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """위치 기반 추천"""
        
        # 캐시 키 생성
        cache_key = f"location_rec_{latitude:.4f}_{longitude:.4f}_{radius}_{hash(str(subjects))}"
        
        # 캐시된 결과 확인
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result[:limit]
        
        # 반경 내 학원 조회
        nearby_academies = self._get_nearby_academies(
            latitude, longitude, radius, subjects
        )
        
        # 점수 계산 (거리 기반)
        recommendations = []
        for academy in nearby_academies:
            distance = self._calculate_distance(
                latitude, longitude,
                float(academy.위도), float(academy.경도)
            )
            
            # 기본 점수 계산
            distance_score = max(0, (radius - distance) / radius * 100)
            rating_score = self._get_academy_rating_score(academy)
            
            total_score = (distance_score * 0.6 + rating_score * 0.4)
            
            if total_score >= self.min_score_threshold:
                recommendations.append({
                    'academy_id': academy.id,
                    'academy_name': academy.상호명,
                    'academy_data': self._serialize_academy(academy),
                    'score': round(total_score, 2),
                    'distance': round(distance, 2),
                    'score_details': {
                        'distance_score': round(distance_score, 2),
                        'rating_score': round(rating_score, 2),
                        'total_score': round(total_score, 2)
                    }
                })
        
        # 점수순 정렬
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        # 캐시 저장
        cache.set(cache_key, recommendations, self.cache_timeout)
        
        return recommendations[:limit]
    
    def get_similar_academies(
        self, 
        academy_id: int, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """유사한 학원 추천"""
        
        try:
            target_academy = Academy.objects.get(id=academy_id)
        except Academy.DoesNotExist:
            return []
        
        # 캐시 키 생성
        cache_key = f"similar_academies_{academy_id}_{limit}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # 유사도 기준 (과목, 위치, 가격대 등)
        similar_academies = Academy.objects.exclude(id=academy_id).filter(
            Q(**{f'과목_{subject}': True for subject in self._get_academy_subjects(target_academy)})
        )
        
        # 위치 기반 필터링 (반경 10km)
        if target_academy.위도 and target_academy.경도:
            similar_academies = self._filter_by_distance(
                similar_academies,
                float(target_academy.위도),
                float(target_academy.경도),
                10.0
            )
        
        # 유사도 점수 계산
        recommendations = []
        target_subjects = set(self._get_academy_subjects(target_academy))
        
        for academy in similar_academies[:20]:  # 성능을 위해 20개로 제한
            similarity_score = self._calculate_similarity_score(
                target_academy, academy, target_subjects
            )
            
            if similarity_score >= 50:  # 50% 이상 유사도
                recommendations.append({
                    'academy_id': academy.id,
                    'academy_name': academy.상호명,
                    'academy_data': self._serialize_academy(academy),
                    'similarity_score': round(similarity_score, 2),
                    'score_details': {
                        'subject_similarity': self._calculate_subject_similarity(target_academy, academy),
                        'location_proximity': self._calculate_location_proximity(target_academy, academy),
                        'rating_similarity': self._calculate_rating_similarity(target_academy, academy)
                    }
                })
        
        # 유사도 점수순 정렬
        recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        # 캐시 저장
        cache.set(cache_key, recommendations, self.cache_timeout)
        
        return recommendations[:limit]
    
    def update_user_preference_from_behavior(self, user: User):
        """사용자 행동 기반 선호도 업데이트"""
        
        profile, created = UserPreferenceProfile.objects.get_or_create(
            user=user
        )
        
        if not profile.auto_update_enabled:
            return
        
        # 최근 30일간의 행동 로그 분석
        recent_logs = UserBehaviorLog.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).select_related('academy')
        
        if not recent_logs.exists():
            return
        
        # 관심있는 학원들의 특성 분석
        interested_academies = recent_logs.filter(
            action_type__in=['bookmark', 'view', 'contact']
        ).values_list('academy', flat=True).distinct()
        
        if interested_academies:
            academies = Academy.objects.filter(id__in=interested_academies)
            
            # 선호 과목 업데이트
            subject_preferences = self._analyze_subject_preferences(academies)
            if subject_preferences:
                profile.preferred_subjects = subject_preferences
            
            # 선호 위치 범위 업데이트 (평균 거리 계산)
            avg_distance = self._calculate_average_preferred_distance(user, academies)
            if avg_distance and avg_distance < profile.max_distance:
                profile.max_distance = min(avg_distance * 1.5, 10.0)  # 1.5배 버퍼, 최대 10km
            
            # 가격 선호도 업데이트
            avg_price = self._analyze_price_preferences(academies)
            if avg_price:
                profile.max_price_range = int(avg_price * 1.2)  # 20% 버퍼
            
            profile.last_updated = timezone.now()
            profile.save()
            
            logger.info(f"사용자 선호도 프로필 업데이트: {user.username}")
    
    def record_user_behavior(
        self,
        user: User,
        action_type: str,
        academy: Optional[Academy] = None,
        action_data: Optional[Dict] = None,
        location: Optional[Tuple[float, float]] = None
    ):
        """사용자 행동 기록"""
        
        log_data = {
            'user': user,
            'action_type': action_type,
            'academy': academy,
            'action_data': action_data or {},
        }
        
        if location:
            log_data['user_latitude'] = location[0]
            log_data['user_longitude'] = location[1]
        
        UserBehaviorLog.objects.create(**log_data)
        
        # 비동기로 선호도 프로필 업데이트 (실제로는 Celery 등 사용)
        if action_type in ['bookmark', 'view', 'contact']:
            self.update_user_preference_from_behavior(user)
    
    def _calculate_recommendations(
        self,
        profile: UserPreferenceProfile,
        location: Optional[Tuple[float, float]],
        recommendation_type: str
    ) -> List[Dict[str, Any]]:
        """추천 점수 계산"""
        
        # 기본 학원 쿼리셋
        queryset = Academy.objects.all()
        
        # 선호 과목 필터링
        if profile.preferred_subjects:
            subject_filters = Q()
            for subject in profile.preferred_subjects:
                field_name = f'과목_{subject}'
                if hasattr(Academy, field_name):
                    subject_filters |= Q(**{field_name: True})
            if subject_filters:
                queryset = queryset.filter(subject_filters)
        
        # 위치 기반 필터링
        user_location = location or (profile.base_latitude, profile.base_longitude)
        if user_location[0] and user_location[1] and profile.max_distance:
            queryset = self._filter_by_distance(
                queryset, user_location[0], user_location[1], profile.max_distance
            )
        
        # 각 학원별 점수 계산
        recommendations = []
        for academy in queryset[:100]:  # 성능을 위해 100개로 제한
            score_data = profile.calculate_academy_score(academy, user_location)
            
            if score_data['total_score'] >= self.min_score_threshold:
                recommendations.append({
                    'academy_id': academy.id,
                    'academy_name': academy.상호명,
                    'academy_data': self._serialize_academy(academy),
                    'score': score_data['total_score'],
                    'score_details': score_data['details'],
                    'recommendation_reason': self._generate_recommendation_reason(score_data)
                })
        
        # 점수순 정렬
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations
    
    def _get_nearby_academies(
        self,
        latitude: float,
        longitude: float,
        radius: float,
        subjects: Optional[List[str]] = None
    ) -> List[Academy]:
        """반경 내 학원 조회"""
        
        queryset = Academy.objects.filter(
            위도__isnull=False,
            경도__isnull=False
        )
        
        # 과목 필터링
        if subjects:
            subject_filters = Q()
            for subject in subjects:
                field_name = f'과목_{subject}'
                if hasattr(Academy, field_name):
                    subject_filters |= Q(**{field_name: True})
            if subject_filters:
                queryset = queryset.filter(subject_filters)
        
        # 대략적인 경계박스로 1차 필터링 (성능 최적화)
        lat_range = radius / 111.0  # 위도 1도 ≈ 111km
        lng_range = radius / (111.0 * math.cos(math.radians(latitude)))
        
        queryset = queryset.filter(
            위도__gte=latitude - lat_range,
            위도__lte=latitude + lat_range,
            경도__gte=longitude - lng_range,
            경도__lte=longitude + lng_range
        )
        
        # 정확한 거리 계산으로 2차 필터링
        nearby_academies = []
        for academy in queryset:
            distance = self._calculate_distance(
                latitude, longitude,
                float(academy.위도), float(academy.경도)
            )
            if distance <= radius:
                nearby_academies.append(academy)
        
        return nearby_academies
    
    def _filter_by_distance(
        self,
        queryset,
        latitude: float,
        longitude: float,
        max_distance: float
    ):
        """거리 기반 쿼리셋 필터링"""
        
        # 대략적인 경계박스로 필터링
        lat_range = max_distance / 111.0
        lng_range = max_distance / (111.0 * math.cos(math.radians(latitude)))
        
        return queryset.filter(
            위도__isnull=False,
            경도__isnull=False,
            위도__gte=latitude - lat_range,
            위도__lte=latitude + lat_range,
            경도__gte=longitude - lng_range,
            경도__lte=longitude + lng_range
        )
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Haversine 거리 계산"""
        R = 6371  # 지구 반지름 (km)
        
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _get_academy_rating_score(self, academy: Academy) -> float:
        """학원 평점 점수 계산"""
        reviews = Review.objects.filter(academy=academy, is_hidden=False)
        if reviews.exists():
            avg_rating = reviews.aggregate(Avg('overall_rating'))['overall_rating__avg']
            return (avg_rating / 5) * 100 if avg_rating else 50
        return 50  # 리뷰가 없으면 중간 점수
    
    def _get_academy_subjects(self, academy: Academy) -> List[str]:
        """학원의 과목 목록 반환"""
        subjects = []
        subject_fields = [
            '수학', '영어', '국어', '과학', '사회', '예체능', '논술', '외국어'
        ]
        
        for subject in subject_fields:
            field_name = f'과목_{subject}'
            if hasattr(academy, field_name) and getattr(academy, field_name):
                subjects.append(subject)
        
        return subjects
    
    def _calculate_similarity_score(
        self,
        target_academy: Academy,
        compare_academy: Academy,
        target_subjects: set
    ) -> float:
        """학원 간 유사도 점수 계산"""
        
        # 과목 유사도 (40%)
        compare_subjects = set(self._get_academy_subjects(compare_academy))
        subject_similarity = len(target_subjects & compare_subjects) / max(len(target_subjects | compare_subjects), 1) * 100
        
        # 위치 근접도 (30%)
        location_proximity = 0
        if (target_academy.위도 and target_academy.경도 and 
            compare_academy.위도 and compare_academy.경도):
            distance = self._calculate_distance(
                float(target_academy.위도), float(target_academy.경도),
                float(compare_academy.위도), float(compare_academy.경도)
            )
            location_proximity = max(0, (10 - distance) / 10 * 100)  # 10km 기준
        
        # 평점 유사도 (30%)
        target_rating = self._get_academy_rating_score(target_academy)
        compare_rating = self._get_academy_rating_score(compare_academy)
        rating_similarity = 100 - abs(target_rating - compare_rating)
        
        return (subject_similarity * 0.4 + location_proximity * 0.3 + rating_similarity * 0.3)
    
    def _calculate_subject_similarity(self, academy1: Academy, academy2: Academy) -> float:
        """과목 유사도 계산"""
        subjects1 = set(self._get_academy_subjects(academy1))
        subjects2 = set(self._get_academy_subjects(academy2))
        
        if not subjects1 and not subjects2:
            return 100.0
        if not subjects1 or not subjects2:
            return 0.0
        
        intersection = len(subjects1 & subjects2)
        union = len(subjects1 | subjects2)
        
        return (intersection / union) * 100 if union > 0 else 0.0
    
    def _calculate_location_proximity(self, academy1: Academy, academy2: Academy) -> float:
        """위치 근접도 계산"""
        if not all([academy1.위도, academy1.경도, academy2.위도, academy2.경도]):
            return 50.0  # 위치 정보가 없으면 중간 점수
        
        distance = self._calculate_distance(
            float(academy1.위도), float(academy1.경도),
            float(academy2.위도), float(academy2.경도)
        )
        
        # 10km 기준으로 근접도 계산
        return max(0, (10 - distance) / 10 * 100)
    
    def _calculate_rating_similarity(self, academy1: Academy, academy2: Academy) -> float:
        """평점 유사도 계산"""
        rating1 = self._get_academy_rating_score(academy1)
        rating2 = self._get_academy_rating_score(academy2)
        
        return 100 - abs(rating1 - rating2)
    
    def _serialize_academy(self, academy: Academy) -> Dict[str, Any]:
        """학원 데이터 직렬화"""
        return {
            'id': academy.id,
            'name': academy.상호명,
            'address': getattr(academy, '도로명주소', ''),
            'latitude': float(academy.위도) if academy.위도 else None,
            'longitude': float(academy.경도) if academy.경도 else None,
            'subjects': self._get_academy_subjects(academy),
            'phone': getattr(academy, '전화번호', ''),
            'shuttle': getattr(academy, '셔틀', False),
        }
    
    def _generate_recommendation_reason(self, score_data: Dict) -> str:
        """추천 이유 생성"""
        reasons = []
        details = score_data.get('details', {})
        
        if 'distance' in details:
            distance = details['distance']['actual']
            reasons.append(f"거리 {distance:.1f}km로 접근성이 좋음")
        
        if 'rating' in details:
            rating = details['rating']['actual']
            review_count = details['rating']['review_count']
            reasons.append(f"평점 {rating:.1f}점 (리뷰 {review_count}개)")
        
        if 'subject_match' in details:
            reasons.append("관심 과목과 일치")
        
        return " • ".join(reasons) if reasons else "종합적으로 적합한 학원"
    
    def _analyze_subject_preferences(self, academies) -> List[str]:
        """관심 학원들의 과목 분석"""
        subject_counts = {}
        
        for academy in academies:
            subjects = self._get_academy_subjects(academy)
            for subject in subjects:
                subject_counts[subject] = subject_counts.get(subject, 0) + 1
        
        # 빈도수 기준 상위 과목들 반환
        return sorted(subject_counts.keys(), key=lambda x: subject_counts[x], reverse=True)[:5]
    
    def _calculate_average_preferred_distance(self, user: User, academies) -> Optional[float]:
        """선호 거리 계산"""
        profile = user.preference_profile
        if not profile.base_latitude or not profile.base_longitude:
            return None
        
        distances = []
        for academy in academies:
            if academy.위도 and academy.경도:
                distance = self._calculate_distance(
                    profile.base_latitude, profile.base_longitude,
                    float(academy.위도), float(academy.경도)
                )
                distances.append(distance)
        
        return sum(distances) / len(distances) if distances else None
    
    def _analyze_price_preferences(self, academies) -> Optional[float]:
        """가격 선호도 분석"""
        prices = []
        
        for academy in academies:
            if hasattr(academy, '수강료') and academy.수강료:
                try:
                    price = float(academy.수강료.replace(',', '').replace('원', ''))
                    prices.append(price)
                except (ValueError, AttributeError):
                    pass
        
        return sum(prices) / len(prices) if prices else None
    
    def _generate_cache_key(self, **kwargs) -> str:
        """캐시 키 생성"""
        key_string = "_".join([f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None])
        return f"recommendation_{hashlib.md5(key_string.encode()).hexdigest()}"
    
    def _save_recommendation_history(
        self,
        user: User,
        recommendations: List[Dict],
        recommendation_type: str,
        location: Optional[Tuple[float, float]]
    ):
        """추천 기록 저장"""
        
        history_objects = []
        for rec in recommendations:
            try:
                academy = Academy.objects.get(id=rec['academy_id'])
                history_objects.append(
                    RecommendationHistory(
                        user=user,
                        academy=academy,
                        recommendation_score=rec['score'],
                        recommendation_reason=rec.get('recommendation_reason', ''),
                        score_details=rec.get('score_details', {}),
                        recommendation_type=recommendation_type,
                        search_location={
                            'latitude': location[0] if location else None,
                            'longitude': location[1] if location else None
                        }
                    )
                )
            except Academy.DoesNotExist:
                continue
        
        if history_objects:
            RecommendationHistory.objects.bulk_create(history_objects)


# 전역 인스턴스
recommendation_engine = RecommendationEngine()