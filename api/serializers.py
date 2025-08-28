from rest_framework import serializers
from main.models import Data
import math

# 거리 계산 유틸리티 함수
def calculate_distance(lat1, lon1, lat2, lon2):
    """두 지점 간의 거리를 계산 (단위: km)"""
    if not all([lat1, lon1, lat2, lon2]):
        return None
    
    R = 6371  # 지구 반지름 (km)
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# 간단한 목록용 시리얼라이저
class AcademyListSerializer(serializers.ModelSerializer):
    """학원 목록용 간단한 시리얼라이저"""
    distance = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()
    target_ages = serializers.SerializerMethodField()
    
    class Meta:
        model = Data
        fields = [
            'id', '상호명', '도로명주소', '시도명', '시군구명', '행정동명',
            '경도', '위도', '별점', '수강료_평균', '학원사진',
            'distance', 'subjects', 'target_ages'
        ]
    
    def get_distance(self, obj):
        """요청자 위치로부터의 거리 계산"""
        request = self.context.get('request')
        if request and hasattr(request, 'user_lat') and hasattr(request, 'user_lon'):
            return calculate_distance(
                request.user_lat, request.user_lon,
                obj.위도, obj.경도
            )
        return None
    
    def get_subjects(self, obj):
        """활성화된 과목 목록 반환"""
        subjects = []
        subject_fields = {
            '과목_종합': '종합',
            '과목_수학': '수학',
            '과목_영어': '영어',
            '과목_과학': '과학',
            '과목_외국어': '외국어',
            '과목_예체능': '예체능',
            '과목_컴퓨터': '컴퓨터',
            '과목_논술': '논술',
            '과목_기타': '기타',
            '과목_독서실스터디카페': '독서실/스터디카페'
        }
        
        for field, name in subject_fields.items():
            if getattr(obj, field, False):
                subjects.append(name)
        return subjects
    
    def get_target_ages(self, obj):
        """대상 연령 목록 반환"""
        ages = []
        age_fields = {
            '대상_유아': '유아',
            '대상_초등': '초등',
            '대상_중등': '중등',
            '대상_고등': '고등',
            '대상_특목고': '특목고',
            '대상_일반': '일반',
            '대상_기타': '기타'
        }
        
        for field, name in age_fields.items():
            if getattr(obj, field, False):
                ages.append(name)
        return ages

# 상세 정보용 시리얼라이저
class AcademyDetailSerializer(serializers.ModelSerializer):
    """학원 상세 정보용 시리얼라이저"""
    distance = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()
    target_ages = serializers.SerializerMethodField()
    certifications = serializers.SerializerMethodField()
    
    class Meta:
        model = Data
        fields = '__all__'
        # 추가로 계산된 필드들
        extra_kwargs = {
            'distance': {'read_only': True},
            'subjects': {'read_only': True},
            'target_ages': {'read_only': True},
            'certifications': {'read_only': True},
        }
    
    def get_distance(self, obj):
        """요청자 위치로부터의 거리 계산"""
        request = self.context.get('request')
        if request and hasattr(request, 'user_lat') and hasattr(request, 'user_lon'):
            return calculate_distance(
                request.user_lat, request.user_lon,
                obj.위도, obj.경도
            )
        return None
    
    def get_subjects(self, obj):
        """활성화된 과목 목록 반환"""
        subjects = []
        subject_fields = {
            '과목_종합': '종합',
            '과목_수학': '수학',
            '과목_영어': '영어',
            '과목_과학': '과학',
            '과목_외국어': '외국어',
            '과목_예체능': '예체능',
            '과목_컴퓨터': '컴퓨터',
            '과목_논술': '논술',
            '과목_기타': '기타',
            '과목_독서실스터디카페': '독서실/스터디카페'
        }
        
        for field, name in subject_fields.items():
            if getattr(obj, field, False):
                subjects.append(name)
        return subjects
    
    def get_target_ages(self, obj):
        """대상 연령 목록 반환"""
        ages = []
        age_fields = {
            '대상_유아': '유아',
            '대상_초등': '초등',
            '대상_중등': '중등',
            '대상_고등': '고등',
            '대상_특목고': '특목고',
            '대상_일반': '일반',
            '대상_기타': '기타'
        }
        
        for field, name in age_fields.items():
            if getattr(obj, field, False):
                ages.append(name)
        return ages
    
    def get_certifications(self, obj):
        """인증 정보 반환"""
        certs = []
        if getattr(obj, '인증_명문대', False):
            certs.append('명문대 출신')
        if getattr(obj, '인증_경력', False):
            certs.append('경력 인증')
        return certs

# 검색/필터링용 시리얼라이저
class AcademySearchSerializer(serializers.Serializer):
    """검색 및 필터링 파라미터용 시리얼라이저"""
    query = serializers.CharField(required=False, help_text="검색어 (학원명, 주소)")
    category = serializers.CharField(required=False, help_text="과목 카테고리")
    price_min = serializers.IntegerField(required=False, help_text="최소 수강료")
    price_max = serializers.IntegerField(required=False, help_text="최대 수강료")
    age_groups = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="대상 연령대 목록"
    )
    shuttle = serializers.BooleanField(required=False, help_text="셔틀버스 여부")
    lat = serializers.FloatField(required=False, help_text="검색 기준 위도")
    lon = serializers.FloatField(required=False, help_text="검색 기준 경도")
    radius = serializers.FloatField(required=False, default=5.0, help_text="검색 반경 (km)")
    rating_min = serializers.FloatField(required=False, help_text="최소 평점")

# 하위 호환성을 위한 기존 시리얼라이저
class AcademySerializer(AcademyListSerializer):
    """기존 API 호환성을 위한 시리얼라이저"""
    pass
