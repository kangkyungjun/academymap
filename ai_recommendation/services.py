import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import NMF, PCA
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
import logging
import json
from datetime import timedelta
from typing import List, Dict, Tuple, Optional
import re

from .models import (
    UserPreference, UserBehavior, AcademyVector, RecommendationModel,
    Recommendation, RecommendationLog, AcademySimilarity
)
from main.models import Data as Academy

logger = logging.getLogger(__name__)


class PreferenceAnalyzer:
    """사용자 선호도 분석기"""
    
    def __init__(self):
        self.subject_weights = {
            '수학': ['수학', '산수', 'math'],
            '영어': ['영어', 'english', '회화'],
            '국어': ['국어', '논술', '작문'],
            '과학': ['과학', '물리', '화학', '생물'],
            '예술': ['미술', '음악', '피아노', '바이올린'],
            '체육': ['체육', '태권도', '수영', '축구'],
            '기타': ['컴퓨터', 'IT', '코딩', '프로그래밍']
        }
    
    def extract_user_preferences(self, user):
        """사용자 행동에서 선호도 추출"""
        try:
            # 최근 30일간 행동 데이터
            recent_behaviors = UserBehavior.objects.filter(
                user=user,
                timestamp__gte=timezone.now() - timedelta(days=30)
            ).select_related('academy')
            
            preferences = {
                'subject': self._analyze_subject_preference(recent_behaviors),
                'location': self._analyze_location_preference(recent_behaviors),
                'price': self._analyze_price_preference(recent_behaviors),
                'teaching_method': self._analyze_teaching_method_preference(recent_behaviors),
            }
            
            # 기존 선호도와 병합
            self._merge_with_existing_preferences(user, preferences)
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error extracting user preferences: {e}")
            return {}
    
    def _analyze_subject_preference(self, behaviors):
        """과목 선호도 분석"""
        subject_scores = {}
        
        for behavior in behaviors:
            if not behavior.academy:
                continue
                
            academy = behavior.academy
            
            # 과목 필드들 검사
            for subject, keywords in self.subject_weights.items():
                score = 0
                
                # 학원 과목 필드 검사
                for field_name in ['과목_유아', '과목_초등', '과목_중등', '과목_고등', '과목_성인']:
                    field_value = getattr(academy, field_name, '') or ''
                    if any(keyword in field_value for keyword in keywords):
                        score += self._get_behavior_weight(behavior.action)
                
                # 검색어에서 과목 추출
                if behavior.search_query:
                    if any(keyword in behavior.search_query for keyword in keywords):
                        score += self._get_behavior_weight(behavior.action) * 0.8
                
                if score > 0:
                    subject_scores[subject] = subject_scores.get(subject, 0) + score
        
        # 정규화
        if subject_scores:
            max_score = max(subject_scores.values())
            subject_scores = {k: v/max_score for k, v in subject_scores.items()}
        
        return subject_scores
    
    def _analyze_location_preference(self, behaviors):
        """위치 선호도 분석"""
        location_scores = {}
        
        for behavior in behaviors:
            if not behavior.academy:
                continue
                
            academy = behavior.academy
            
            # 지역 정보
            regions = [
                academy.시도명,
                academy.시군구명,
                academy.도로명주소,
            ]
            
            for region in regions:
                if region:
                    region_clean = re.sub(r'[^\w가-힣]', '', str(region))
                    if region_clean:
                        weight = self._get_behavior_weight(behavior.action)
                        location_scores[region_clean] = location_scores.get(region_clean, 0) + weight
        
        return location_scores
    
    def _analyze_price_preference(self, behaviors):
        """가격 선호도 분석"""
        price_behaviors = []
        
        for behavior in behaviors:
            if not behavior.academy:
                continue
                
            academy = behavior.academy
            
            # 수강료 정보가 있는 경우
            if hasattr(academy, '수강료') and academy.수강료:
                try:
                    fee = float(re.sub(r'[^\d.]', '', str(academy.수강료)))
                    if fee > 0:
                        weight = self._get_behavior_weight(behavior.action)
                        price_behaviors.append({'price': fee, 'weight': weight})
                except (ValueError, TypeError):
                    continue
        
        if not price_behaviors:
            return {'low': 0.3, 'medium': 0.4, 'high': 0.3}  # 기본값
        
        # 가격대별 선호도 계산
        prices = [b['price'] for b in price_behaviors]
        weights = [b['weight'] for b in price_behaviors]
        
        if len(prices) > 0:
            p25, p75 = np.percentile(prices, [25, 75])
            
            low_score = sum(w for p, w in zip(prices, weights) if p <= p25)
            medium_score = sum(w for p, w in zip(prices, weights) if p25 < p <= p75)
            high_score = sum(w for p, w in zip(prices, weights) if p > p75)
            
            total = low_score + medium_score + high_score
            if total > 0:
                return {
                    'low': low_score / total,
                    'medium': medium_score / total,
                    'high': high_score / total
                }
        
        return {'low': 0.3, 'medium': 0.4, 'high': 0.3}
    
    def _analyze_teaching_method_preference(self, behaviors):
        """교육방식 선호도 분석"""
        method_keywords = {
            'group': ['그룹', '집단', '단체', '클래스'],
            'individual': ['개별', '1:1', '개인', '맞춤'],
            'online': ['온라인', '화상', '비대면', '원격'],
            'offline': ['오프라인', '대면', '방문', '현장']
        }
        
        method_scores = {}
        
        for behavior in behaviors:
            if behavior.search_query:
                query = behavior.search_query.lower()
                weight = self._get_behavior_weight(behavior.action)
                
                for method, keywords in method_keywords.items():
                    if any(keyword in query for keyword in keywords):
                        method_scores[method] = method_scores.get(method, 0) + weight
        
        # 정규화
        if method_scores:
            total = sum(method_scores.values())
            method_scores = {k: v/total for k, v in method_scores.items()}
        
        return method_scores
    
    def _get_behavior_weight(self, action):
        """행동별 가중치 반환"""
        weights = {
            'view': 1.0,
            'search': 0.8,
            'filter': 0.9,
            'contact': 3.0,
            'bookmark': 2.0,
            'click': 1.2,
            'share': 1.5,
            'review': 2.5,
        }
        return weights.get(action, 1.0)
    
    def _merge_with_existing_preferences(self, user, new_preferences):
        """기존 선호도와 새로운 선호도 병합"""
        try:
            for pref_type, pref_data in new_preferences.items():
                if not pref_data:
                    continue
                    
                preference, created = UserPreference.objects.get_or_create(
                    user=user,
                    preference_type=pref_type,
                    defaults={
                        'preference_value': json.dumps(pref_data, ensure_ascii=False),
                        'weight': 1.0
                    }
                )
                
                if not created:
                    # 기존 데이터와 병합 (가중평균)
                    existing_data = preference.get_preference_data()
                    if isinstance(existing_data, dict) and isinstance(pref_data, dict):
                        merged_data = {}
                        all_keys = set(existing_data.keys()) | set(pref_data.keys())
                        
                        for key in all_keys:
                            old_val = existing_data.get(key, 0)
                            new_val = pref_data.get(key, 0)
                            # 기존 70%, 새로운 30% 가중치 적용
                            merged_data[key] = old_val * 0.7 + new_val * 0.3
                        
                        preference.preference_value = json.dumps(merged_data, ensure_ascii=False)
                        preference.save()
                        
        except Exception as e:
            logger.error(f"Error merging preferences: {e}")


class VectorBuilder:
    """학원 특성 벡터 생성기"""
    
    def __init__(self):
        self.tfidf_vectorizer = None
        self.scaler = StandardScaler()
    
    def build_academy_vectors(self):
        """모든 학원의 특성 벡터 생성"""
        try:
            academies = Academy.objects.all()
            logger.info(f"Building vectors for {academies.count()} academies")
            
            # 기본 특성 데이터 수집
            academy_data = []
            for academy in academies:
                data = self._extract_academy_features(academy)
                academy_data.append(data)
            
            if not academy_data:
                return
            
            # 벡터 생성 및 저장
            for academy, data in zip(academies, academy_data):
                self._create_or_update_vector(academy, data)
            
            logger.info("Academy vectors building completed")
            
        except Exception as e:
            logger.error(f"Error building academy vectors: {e}")
    
    def _extract_academy_features(self, academy):
        """학원에서 특성 추출"""
        features = {
            'academy_id': academy.id,
            'subjects': self._extract_subjects(academy),
            'location': self._extract_location_features(academy),
            'price': self._extract_price_features(academy),
            'facilities': self._extract_facility_features(academy),
            'description': self._extract_text_features(academy),
        }
        return features
    
    def _extract_subjects(self, academy):
        """과목 특성 추출"""
        subjects = {}
        subject_fields = ['과목_유아', '과목_초등', '과목_중등', '과목_고등', '과목_성인']
        
        for field in subject_fields:
            value = getattr(academy, field, '') or ''
            if value and str(value).strip().lower() != 'nan':
                # 과목별 점수 계산
                age_group = field.replace('과목_', '')
                subjects[age_group] = len(str(value).split(','))
        
        return subjects
    
    def _extract_location_features(self, academy):
        """위치 특성 추출"""
        location = {
            'sido': academy.시도명 or '',
            'sigungu': academy.시군구명 or '',
            'latitude': float(academy.위도) if academy.위도 else 0.0,
            'longitude': float(academy.경도) if academy.경도 else 0.0,
        }
        
        # 지역 클러스터링 (대략적인 지역 구분)
        if location['latitude'] and location['longitude']:
            location['region_cluster'] = self._get_region_cluster(
                location['latitude'], 
                location['longitude']
            )
        
        return location
    
    def _extract_price_features(self, academy):
        """가격 특성 추출"""
        price_info = {
            'has_fee_info': False,
            'price_level': 'unknown',
            'fee_value': 0.0
        }
        
        if hasattr(academy, '수강료') and academy.수강료:
            fee_str = str(academy.수강료)
            if fee_str.lower() != 'nan':
                price_info['has_fee_info'] = True
                
                # 가격 추출 시도
                numbers = re.findall(r'[\d,]+', fee_str)
                if numbers:
                    try:
                        fee_value = float(numbers[0].replace(',', ''))
                        price_info['fee_value'] = fee_value
                        
                        # 가격 레벨 분류
                        if fee_value < 100000:
                            price_info['price_level'] = 'low'
                        elif fee_value < 300000:
                            price_info['price_level'] = 'medium'
                        else:
                            price_info['price_level'] = 'high'
                    except ValueError:
                        pass
        
        return price_info
    
    def _extract_facility_features(self, academy):
        """시설 특성 추출"""
        facilities = {
            'has_shuttle': False,
            'has_parking': False,
            'facility_score': 0
        }
        
        # 셔틀버스 정보
        if hasattr(academy, '셔틀버스') and academy.셔틀버스:
            shuttle_info = str(academy.셔틀버스).lower()
            if shuttle_info != 'nan' and any(word in shuttle_info for word in ['있음', '운행', 'o', 'yes']):
                facilities['has_shuttle'] = True
                facilities['facility_score'] += 1
        
        # 기타 시설 정보 (상호명이나 기타 필드에서 추출)
        facility_keywords = ['주차', 'parking', '카페', '휴게실', '도서관', 'library']
        academy_text = f"{academy.상호명} {getattr(academy, '기타정보', '')}"
        
        for keyword in facility_keywords:
            if keyword in academy_text.lower():
                facilities['facility_score'] += 0.5
        
        return facilities
    
    def _extract_text_features(self, academy):
        """텍스트 특성 추출"""
        text_fields = [
            academy.상호명,
            getattr(academy, '기타정보', ''),
            academy.도로명주소 or '',
        ]
        
        combined_text = ' '.join(str(field) for field in text_fields if field)
        return combined_text
    
    def _get_region_cluster(self, lat, lng):
        """위치 기반 지역 클러스터 반환"""
        # 간단한 위경도 기반 지역 구분
        if 37.4 <= lat <= 37.7 and 126.8 <= lng <= 127.2:
            return 'seoul'
        elif 37.2 <= lat <= 37.5 and 126.8 <= lng <= 127.0:
            return 'gyeonggi_south'
        elif 37.5 <= lat <= 37.8 and 126.7 <= lng <= 127.2:
            return 'gyeonggi_north'
        else:
            return 'other'
    
    def _create_or_update_vector(self, academy, features):
        """학원 벡터 생성 또는 업데이트"""
        try:
            vector, created = AcademyVector.objects.get_or_create(
                academy=academy,
                defaults={
                    'subject_vector': features['subjects'],
                    'location_vector': features['location'],
                    'price_vector': features['price'],
                    'facility_vector': features['facilities'],
                    'popularity_score': 0.0,
                    'rating_score': 0.0,
                    'engagement_score': 0.0,
                }
            )
            
            if not created:
                # 기존 벡터 업데이트
                vector.subject_vector = features['subjects']
                vector.location_vector = features['location']
                vector.price_vector = features['price']
                vector.facility_vector = features['facilities']
                vector.save()
            
            # 인기도 점수 업데이트
            vector.update_popularity_score()
            
        except Exception as e:
            logger.error(f"Error creating vector for academy {academy.id}: {e}")


class SimilarityCalculator:
    """학원 간 유사도 계산기"""
    
    def calculate_all_similarities(self):
        """모든 학원 간 유사도 계산"""
        try:
            academies = list(Academy.objects.filter(academyvector__isnull=False))
            total_pairs = len(academies) * (len(academies) - 1) // 2
            
            logger.info(f"Calculating similarities for {len(academies)} academies ({total_pairs} pairs)")
            
            calculated = 0
            for i, academy1 in enumerate(academies):
                for academy2 in academies[i+1:]:
                    self._calculate_similarity_pair(academy1, academy2)
                    calculated += 1
                    
                    if calculated % 1000 == 0:
                        logger.info(f"Calculated {calculated}/{total_pairs} similarities")
            
            logger.info("Similarity calculation completed")
            
        except Exception as e:
            logger.error(f"Error calculating similarities: {e}")
    
    def _calculate_similarity_pair(self, academy1, academy2):
        """두 학원 간 유사도 계산"""
        try:
            vector1 = academy1.vector
            vector2 = academy2.vector
            
            # 콘텐츠 유사도 (과목, 시설 등)
            content_sim = self._calculate_content_similarity(vector1, vector2)
            
            # 위치 유사도
            location_sim = self._calculate_location_similarity(vector1, vector2)
            
            # 사용자 행동 기반 유사도
            user_sim = self._calculate_user_similarity(academy1, academy2)
            
            # 전체 유사도 (가중 평균)
            overall_sim = (
                content_sim * 0.4 +
                location_sim * 0.3 +
                user_sim * 0.3
            )
            
            # 결과 저장
            AcademySimilarity.objects.update_or_create(
                academy1=academy1,
                academy2=academy2,
                defaults={
                    'content_similarity': content_sim,
                    'location_similarity': location_sim,
                    'user_similarity': user_sim,
                    'overall_similarity': overall_sim,
                    'calculation_method': 'hybrid'
                }
            )
            
        except Exception as e:
            logger.error(f"Error calculating similarity for academies {academy1.id}, {academy2.id}: {e}")
    
    def _calculate_content_similarity(self, vector1, vector2):
        """콘텐츠 기반 유사도 계산"""
        try:
            similarity_scores = []
            
            # 과목 유사도
            subject_sim = self._cosine_similarity_dict(
                vector1.subject_vector, 
                vector2.subject_vector
            )
            similarity_scores.append(subject_sim)
            
            # 시설 유사도
            facility_sim = self._cosine_similarity_dict(
                vector1.facility_vector, 
                vector2.facility_vector
            )
            similarity_scores.append(facility_sim)
            
            # 가격대 유사도
            price_sim = self._calculate_price_similarity(
                vector1.price_vector,
                vector2.price_vector
            )
            similarity_scores.append(price_sim)
            
            return np.mean(similarity_scores) if similarity_scores else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating content similarity: {e}")
            return 0.0
    
    def _calculate_location_similarity(self, vector1, vector2):
        """위치 기반 유사도 계산"""
        try:
            loc1 = vector1.location_vector
            loc2 = vector2.location_vector
            
            # 위경도가 있는 경우 거리 기반 유사도
            if (loc1.get('latitude') and loc1.get('longitude') and 
                loc2.get('latitude') and loc2.get('longitude')):
                
                distance = self._haversine_distance(
                    loc1['latitude'], loc1['longitude'],
                    loc2['latitude'], loc2['longitude']
                )
                
                # 거리를 유사도로 변환 (가까울수록 높음)
                # 50km 이내는 높은 유사도, 그 이후는 급격히 감소
                if distance <= 5:  # 5km 이내
                    return 1.0
                elif distance <= 20:  # 20km 이내
                    return 1.0 - (distance - 5) / 15 * 0.5
                elif distance <= 50:  # 50km 이내
                    return 0.5 - (distance - 20) / 30 * 0.4
                else:
                    return 0.1
            
            # 행정구역 기반 유사도
            if loc1.get('sigungu') and loc2.get('sigungu'):
                if loc1['sigungu'] == loc2['sigungu']:
                    return 0.9
                elif loc1.get('sido') == loc2.get('sido'):
                    return 0.6
            
            return 0.1  # 기본 유사도
            
        except Exception as e:
            logger.error(f"Error calculating location similarity: {e}")
            return 0.0
    
    def _calculate_user_similarity(self, academy1, academy2):
        """사용자 행동 기반 유사도 계산"""
        try:
            # 공통 사용자 찾기
            users1 = set(UserBehavior.objects.filter(
                academy=academy1,
                action__in=['view', 'contact', 'bookmark']
            ).values_list('user_id', flat=True))
            
            users2 = set(UserBehavior.objects.filter(
                academy=academy2,
                action__in=['view', 'contact', 'bookmark']
            ).values_list('user_id', flat=True))
            
            if not users1 or not users2:
                return 0.0
            
            # Jaccard 유사도
            intersection = len(users1 & users2)
            union = len(users1 | users2)
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating user similarity: {e}")
            return 0.0
    
    def _cosine_similarity_dict(self, dict1, dict2):
        """딕셔너리 간 코사인 유사도 계산"""
        try:
            if not dict1 or not dict2:
                return 0.0
            
            all_keys = set(dict1.keys()) | set(dict2.keys())
            if not all_keys:
                return 0.0
            
            vec1 = np.array([dict1.get(key, 0) for key in all_keys])
            vec2 = np.array([dict2.get(key, 0) for key in all_keys])
            
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return np.dot(vec1, vec2) / (norm1 * norm2)
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def _calculate_price_similarity(self, price1, price2):
        """가격 유사도 계산"""
        try:
            if not price1 or not price2:
                return 0.0
            
            level1 = price1.get('price_level', 'unknown')
            level2 = price2.get('price_level', 'unknown')
            
            if level1 == level2:
                return 1.0
            elif level1 == 'unknown' or level2 == 'unknown':
                return 0.3
            else:
                # 인접한 가격대는 0.5, 멀리 떨어진 가격대는 0.1
                price_levels = ['low', 'medium', 'high']
                if level1 in price_levels and level2 in price_levels:
                    diff = abs(price_levels.index(level1) - price_levels.index(level2))
                    return 1.0 - diff * 0.4
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating price similarity: {e}")
            return 0.0
    
    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """Haversine 공식을 사용한 거리 계산 (km)"""
        try:
            R = 6371  # 지구 반지름 (km)
            
            lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
            c = 2 * np.arcsin(np.sqrt(a))
            
            return R * c
            
        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return float('inf')


class RecommendationEngine:
    """추천 엔진"""
    
    def __init__(self):
        self.preference_analyzer = PreferenceAnalyzer()
        self.cache_timeout = 3600  # 1시간 캐시
    
    def get_recommendations(self, user, limit=10, context=None):
        """사용자 맞춤 추천 생성"""
        try:
            # 캐시 확인
            cache_key = f"recommendations_{user.id}_{limit}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            # 로그 기록
            log_start = timezone.now()
            session_id = context.get('session_id', '') if context else ''
            
            # 사용자 선호도 분석
            preferences = self.preference_analyzer.extract_user_preferences(user)
            
            # 추천 알고리즘 실행
            recommendations = []
            
            # 1. 콘텐츠 기반 추천
            content_recs = self._content_based_recommendations(user, preferences, limit//2)
            recommendations.extend(content_recs)
            
            # 2. 협업 필터링 추천
            collab_recs = self._collaborative_filtering_recommendations(user, limit//2)
            recommendations.extend(collab_recs)
            
            # 3. 인기도 기반 추천 (보완)
            if len(recommendations) < limit:
                popular_recs = self._popularity_based_recommendations(
                    user, limit - len(recommendations), exclude=[r['academy_id'] for r in recommendations]
                )
                recommendations.extend(popular_recs)
            
            # 최종 점수 계산 및 정렬
            final_recommendations = self._calculate_final_scores(recommendations, preferences)
            final_recommendations = final_recommendations[:limit]
            
            # 추천 결과 저장
            self._save_recommendations(user, final_recommendations, session_id)
            
            # 처리 시간 로그
            processing_time = (timezone.now() - log_start).total_seconds()
            RecommendationLog.objects.create(
                user=user,
                log_type='generation',
                message=f'Generated {len(final_recommendations)} recommendations',
                data={'preferences': preferences, 'context': context or {}},
                processing_time=processing_time,
                recommendation_count=len(final_recommendations),
                session_id=session_id
            )
            
            # 캐시 저장
            cache.set(cache_key, final_recommendations, self.cache_timeout)
            
            return final_recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations for user {user.id}: {e}")
            RecommendationLog.objects.create(
                user=user,
                log_type='error',
                message=f'Recommendation generation failed: {str(e)}',
                session_id=context.get('session_id', '') if context else ''
            )
            return []
    
    def _content_based_recommendations(self, user, preferences, limit):
        """콘텐츠 기반 추천"""
        recommendations = []
        
        try:
            # 사용자가 이미 상호작용한 학원들 제외
            interacted_academies = set(UserBehavior.objects.filter(user=user).values_list('academy_id', flat=True))
            
            # 학원 벡터 조회
            academy_vectors = AcademyVector.objects.select_related('academy').exclude(
                academy_id__in=interacted_academies
            )
            
            for vector in academy_vectors:
                score = self._calculate_content_score(vector, preferences)
                if score > 0:
                    recommendations.append({
                        'academy_id': vector.academy.id,
                        'academy': vector.academy,
                        'score': score,
                        'reason_type': 'content_match',
                        'reason_details': {'content_score': score}
                    })
            
            # 점수순 정렬
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error in content-based recommendations: {e}")
            return []
    
    def _collaborative_filtering_recommendations(self, user, limit):
        """협업 필터링 추천"""
        recommendations = []
        
        try:
            # 사용자와 유사한 사용자 찾기
            similar_users = self._find_similar_users(user)
            
            if not similar_users:
                return []
            
            # 유사한 사용자들이 관심을 보인 학원들 추천
            academy_scores = {}
            
            for similar_user_id, similarity_score in similar_users:
                user_behaviors = UserBehavior.objects.filter(
                    user_id=similar_user_id,
                    action__in=['contact', 'bookmark', 'view']
                ).select_related('academy')
                
                for behavior in user_behaviors:
                    if behavior.academy_id:
                        action_weight = {
                            'contact': 3.0,
                            'bookmark': 2.0,
                            'view': 1.0
                        }.get(behavior.action, 1.0)
                        
                        score = similarity_score * action_weight
                        academy_scores[behavior.academy_id] = academy_scores.get(behavior.academy_id, 0) + score
            
            # 사용자가 이미 상호작용한 학원 제외
            user_academies = set(UserBehavior.objects.filter(user=user).values_list('academy_id', flat=True))
            
            for academy_id, score in academy_scores.items():
                if academy_id not in user_academies:
                    try:
                        academy = Academy.objects.get(id=academy_id)
                        recommendations.append({
                            'academy_id': academy_id,
                            'academy': academy,
                            'score': score,
                            'reason_type': 'similar_users',
                            'reason_details': {'collaborative_score': score}
                        })
                    except Academy.DoesNotExist:
                        continue
            
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error in collaborative filtering: {e}")
            return []
    
    def _popularity_based_recommendations(self, user, limit, exclude=None):
        """인기도 기반 추천"""
        recommendations = []
        exclude = exclude or []
        
        try:
            # 사용자 상호작용 학원 제외
            user_academies = set(UserBehavior.objects.filter(user=user).values_list('academy_id', flat=True))
            exclude_set = set(exclude) | user_academies
            
            # 인기 학원들 조회
            popular_academies = AcademyVector.objects.select_related('academy').exclude(
                academy_id__in=exclude_set
            ).order_by('-popularity_score', '-rating_score')[:limit * 2]
            
            for vector in popular_academies:
                score = (vector.popularity_score * 0.7 + vector.rating_score * 0.3)
                if score > 0:
                    recommendations.append({
                        'academy_id': vector.academy.id,
                        'academy': vector.academy,
                        'score': score,
                        'reason_type': 'popularity',
                        'reason_details': {
                            'popularity_score': vector.popularity_score,
                            'rating_score': vector.rating_score
                        }
                    })
            
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error in popularity-based recommendations: {e}")
            return []
    
    def _calculate_content_score(self, academy_vector, user_preferences):
        """콘텐츠 기반 점수 계산"""
        total_score = 0.0
        
        try:
            # 과목 매칭 점수
            if 'subject' in user_preferences and user_preferences['subject']:
                subject_score = self._calculate_subject_match(
                    academy_vector.subject_vector, 
                    user_preferences['subject']
                )
                total_score += subject_score * 0.4
            
            # 위치 매칭 점수
            if 'location' in user_preferences and user_preferences['location']:
                location_score = self._calculate_location_match(
                    academy_vector.location_vector,
                    user_preferences['location']
                )
                total_score += location_score * 0.3
            
            # 가격 매칭 점수
            if 'price' in user_preferences and user_preferences['price']:
                price_score = self._calculate_price_match(
                    academy_vector.price_vector,
                    user_preferences['price']
                )
                total_score += price_score * 0.2
            
            # 기본 품질 점수
            quality_score = (
                academy_vector.popularity_score * 0.5 +
                academy_vector.rating_score * 0.3 +
                academy_vector.engagement_score * 0.2
            )
            total_score += quality_score * 0.1
            
            return total_score
            
        except Exception as e:
            logger.error(f"Error calculating content score: {e}")
            return 0.0
    
    def _calculate_subject_match(self, academy_subjects, user_subjects):
        """과목 매칭 점수 계산"""
        if not academy_subjects or not user_subjects:
            return 0.0
        
        total_score = 0.0
        for subject, user_weight in user_subjects.items():
            if subject in academy_subjects:
                academy_strength = academy_subjects[subject]
                total_score += user_weight * academy_strength
        
        return min(total_score, 1.0)
    
    def _calculate_location_match(self, academy_location, user_locations):
        """위치 매칭 점수 계산"""
        if not academy_location or not user_locations:
            return 0.0
        
        max_score = 0.0
        
        # 지역명 매칭
        academy_region = academy_location.get('sigungu', '')
        for region, weight in user_locations.items():
            if region in academy_region or academy_region in region:
                max_score = max(max_score, weight)
        
        return max_score
    
    def _calculate_price_match(self, academy_price, user_price_prefs):
        """가격 매칭 점수 계산"""
        if not academy_price or not user_price_prefs:
            return 0.0
        
        academy_level = academy_price.get('price_level', 'unknown')
        if academy_level == 'unknown':
            return 0.3  # 중립적 점수
        
        return user_price_prefs.get(academy_level, 0.0)
    
    def _find_similar_users(self, user, limit=50):
        """유사한 사용자 찾기"""
        try:
            # 사용자의 행동 패턴
            user_academies = set(UserBehavior.objects.filter(
                user=user, 
                action__in=['contact', 'bookmark', 'view']
            ).values_list('academy_id', flat=True))
            
            if not user_academies:
                return []
            
            # 다른 사용자들과의 유사도 계산
            similar_users = []
            other_users = UserBehavior.objects.filter(
                action__in=['contact', 'bookmark', 'view']
            ).exclude(user=user).values_list('user_id', flat=True).distinct()
            
            for other_user_id in other_users:
                other_academies = set(UserBehavior.objects.filter(
                    user_id=other_user_id,
                    action__in=['contact', 'bookmark', 'view']
                ).values_list('academy_id', flat=True))
                
                if other_academies:
                    # Jaccard 유사도
                    intersection = len(user_academies & other_academies)
                    union = len(user_academies | other_academies)
                    similarity = intersection / union if union > 0 else 0.0
                    
                    if similarity > 0.1:  # 최소 유사도 임계값
                        similar_users.append((other_user_id, similarity))
            
            # 유사도순 정렬
            similar_users.sort(key=lambda x: x[1], reverse=True)
            return similar_users[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar users: {e}")
            return []
    
    def _calculate_final_scores(self, recommendations, preferences):
        """최종 점수 계산 및 정렬"""
        try:
            for rec in recommendations:
                # 기본 점수에 다양성과 신선도 보정 적용
                diversity_bonus = self._calculate_diversity_bonus(rec)
                freshness_bonus = self._calculate_freshness_bonus(rec['academy'])
                
                final_score = (
                    rec['score'] * 0.8 +
                    diversity_bonus * 0.1 +
                    freshness_bonus * 0.1
                )
                
                rec['final_score'] = final_score
                rec['confidence_score'] = min(rec['score'], 1.0)
                rec['relevance_score'] = rec['score']
            
            # 최종 점수순 정렬
            recommendations.sort(key=lambda x: x['final_score'], reverse=True)
            return recommendations
            
        except Exception as e:
            logger.error(f"Error calculating final scores: {e}")
            return recommendations
    
    def _calculate_diversity_bonus(self, recommendation):
        """다양성 보너스 계산"""
        # 추천 이유가 다양할수록 보너스
        reason_diversity = {
            'content_match': 0.8,
            'similar_users': 0.9,
            'popularity': 0.5,
        }
        return reason_diversity.get(recommendation['reason_type'], 0.5)
    
    def _calculate_freshness_bonus(self, academy):
        """신선도 보너스 계산"""
        try:
            # 최근 업데이트된 학원에 보너스
            if hasattr(academy, 'updated_at') and academy.updated_at:
                days_since_update = (timezone.now() - academy.updated_at).days
                if days_since_update < 30:
                    return 1.0 - (days_since_update / 30) * 0.3
            return 0.7
        except:
            return 0.7
    
    def _save_recommendations(self, user, recommendations, session_id):
        """추천 결과 저장"""
        try:
            model = RecommendationModel.objects.filter(is_active=True).first()
            if not model:
                return
            
            for i, rec in enumerate(recommendations):
                Recommendation.objects.update_or_create(
                    user=user,
                    academy_id=rec['academy_id'],
                    model=model,
                    session_id=session_id,
                    defaults={
                        'confidence_score': rec.get('confidence_score', 0.5),
                        'relevance_score': rec.get('relevance_score', 0.5),
                        'final_score': rec['final_score'],
                        'reason_type': rec['reason_type'],
                        'reason_details': rec.get('reason_details', {}),
                        'explanation': self._generate_explanation(rec),
                        'context': {'rank': i + 1}
                    }
                )
                
        except Exception as e:
            logger.error(f"Error saving recommendations: {e}")
    
    def _generate_explanation(self, recommendation):
        """추천 이유 설명 생성"""
        reason_type = recommendation['reason_type']
        academy_name = recommendation['academy'].상호명
        
        explanations = {
            'content_match': f"회원님의 관심사와 잘 맞는 {academy_name}을 추천드립니다.",
            'similar_users': f"비슷한 관심사를 가진 다른 회원들이 많이 찾은 {academy_name}입니다.",
            'popularity': f"많은 회원들에게 인기가 높은 {academy_name}을 추천드립니다.",
        }
        
        return explanations.get(reason_type, f"{academy_name}을 추천드립니다.")