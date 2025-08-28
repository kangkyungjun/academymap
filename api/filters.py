"""
Django Filter 클래스들 - 고급 필터링을 위한 커스텀 필터 구현
"""
import django_filters
from django.db.models import Q
from main.models import Data


class AcademyFilter(django_filters.FilterSet):
    """학원 검색을 위한 고급 필터 클래스"""
    
    # 텍스트 검색
    search = django_filters.CharFilter(method='filter_search', label='검색어')
    
    # 과목 필터 (다중 선택 가능)
    subjects = django_filters.MultipleChoiceFilter(
        method='filter_subjects',
        choices=[
            ('종합', '종합'),
            ('수학', '수학'),
            ('영어', '영어'),
            ('과학', '과학'),
            ('외국어', '외국어'),
            ('예체능', '예체능'),
            ('컴퓨터', '컴퓨터'),
            ('논술', '논술'),
            ('기타', '기타'),
            ('독서실스터디카페', '독서실/스터디카페'),
        ],
        label='과목'
    )
    
    # 연령대 필터 (다중 선택 가능)
    target_ages = django_filters.MultipleChoiceFilter(
        method='filter_target_ages',
        choices=[
            ('유아', '유아'),
            ('초등', '초등'),
            ('중등', '중등'),
            ('고등', '고등'),
            ('특목고', '특목고'),
            ('일반', '일반'),
            ('기타', '기타'),
        ],
        label='대상 연령'
    )
    
    # 지역 필터
    region = django_filters.CharFilter(method='filter_region', label='지역')
    sido = django_filters.CharFilter(field_name='시도명', lookup_expr='icontains', label='시도')
    sigungu = django_filters.CharFilter(field_name='시군구명', lookup_expr='icontains', label='시군구')
    
    # 평점 필터
    rating_min = django_filters.NumberFilter(field_name='별점', lookup_expr='gte', label='최소 평점')
    rating_max = django_filters.NumberFilter(field_name='별점', lookup_expr='lte', label='최대 평점')
    
    # 셔틀버스 필터
    has_shuttle = django_filters.BooleanFilter(method='filter_shuttle', label='셔틀버스 운영')
    
    # 인증 필터
    has_certification = django_filters.BooleanFilter(method='filter_certification', label='인증 보유')
    
    # 위치 기반 필터
    lat = django_filters.NumberFilter(method='filter_location', label='위도')
    lon = django_filters.NumberFilter(method='filter_location', label='경도')
    radius = django_filters.NumberFilter(method='filter_location', label='검색 반경(km)')
    
    class Meta:
        model = Data
        fields = []
    
    def filter_search(self, queryset, name, value):
        """통합 검색 필터"""
        if not value:
            return queryset
            
        # 검색어를 공백으로 분리하여 각각 검색
        search_terms = value.split()
        for term in search_terms:
            queryset = queryset.filter(
                Q(상호명__icontains=term) |
                Q(도로명주소__icontains=term) |
                Q(시도명__icontains=term) |
                Q(시군구명__icontains=term) |
                Q(행정동명__icontains=term) |
                Q(법정동명__icontains=term)
            )
        return queryset
    
    def filter_subjects(self, queryset, name, value):
        """과목 필터 (OR 조건)"""
        if not value:
            return queryset
            
        subject_filter = Q()
        for subject in value:
            subject_filter |= Q(**{f'과목_{subject}': True})
        return queryset.filter(subject_filter)
    
    def filter_target_ages(self, queryset, name, value):
        """연령대 필터 (OR 조건)"""
        if not value:
            return queryset
            
        age_filter = Q()
        for age in value:
            age_filter |= Q(**{f'대상_{age}': True})
        return queryset.filter(age_filter)
    
    def filter_region(self, queryset, name, value):
        """지역 통합 검색"""
        if not value:
            return queryset
        return queryset.filter(
            Q(시도명__icontains=value) |
            Q(시군구명__icontains=value) |
            Q(행정동명__icontains=value)
        )
    
    def filter_shuttle(self, queryset, name, value):
        """셔틀버스 필터"""
        if value is None:
            return queryset
        if value:
            return queryset.exclude(셔틀버스__isnull=True).exclude(셔틀버스='')
        else:
            return queryset.filter(Q(셔틀버스__isnull=True) | Q(셔틀버스=''))
    
    def filter_certification(self, queryset, name, value):
        """인증 필터"""
        if value is None:
            return queryset
        if value:
            return queryset.filter(
                Q(인증_명문대=True) | Q(인증_경력=True)
            )
        else:
            return queryset.filter(인증_명문대=False, 인증_경력=False)
    
    def filter_location(self, queryset, name, value):
        """위치 기반 필터링은 뷰에서 처리"""
        # 이 메서드는 실제로 사용되지 않음
        # 위치 기반 필터링은 뷰의 get_queryset에서 처리
        return queryset


class PopularAcademyFilter(django_filters.FilterSet):
    """인기 학원 필터 (평점, 리뷰 수 기준)"""
    
    min_rating = django_filters.NumberFilter(field_name='별점', lookup_expr='gte')
    has_photo = django_filters.BooleanFilter(method='filter_has_photo')
    
    class Meta:
        model = Data
        fields = ['min_rating']
    
    def filter_has_photo(self, queryset, name, value):
        """사진이 있는 학원 필터"""
        if value is None:
            return queryset
        if value:
            return queryset.exclude(학원사진__isnull=True).exclude(학원사진='')
        else:
            return queryset.filter(Q(학원사진__isnull=True) | Q(학원사진=''))


class NearbyAcademyFilter(django_filters.FilterSet):
    """주변 학원 검색용 특화 필터"""
    
    subjects = django_filters.MultipleChoiceFilter(
        method='filter_subjects',
        choices=[
            ('종합', '종합'),
            ('수학', '수학'),
            ('영어', '영어'),
            ('과학', '과학'),
            ('외국어', '외국어'),
            ('예체능', '예체능'),
            ('컴퓨터', '컴퓨터'),
            ('논술', '논술'),
            ('기타', '기타'),
            ('독서실스터디카페', '독서실/스터디카페'),
        ]
    )
    
    target_ages = django_filters.MultipleChoiceFilter(
        method='filter_target_ages',
        choices=[
            ('유아', '유아'),
            ('초등', '초등'),
            ('중등', '중등'),
            ('고등', '고등'),
            ('특목고', '특목고'),
            ('일반', '일반'),
            ('기타', '기타'),
        ]
    )
    
    rating_min = django_filters.NumberFilter(field_name='별점', lookup_expr='gte')
    has_shuttle = django_filters.BooleanFilter(method='filter_shuttle')
    
    class Meta:
        model = Data
        fields = []
    
    def filter_subjects(self, queryset, name, value):
        if not value:
            return queryset
        subject_filter = Q()
        for subject in value:
            subject_filter |= Q(**{f'과목_{subject}': True})
        return queryset.filter(subject_filter)
    
    def filter_target_ages(self, queryset, name, value):
        if not value:
            return queryset
        age_filter = Q()
        for age in value:
            age_filter |= Q(**{f'대상_{age}': True})
        return queryset.filter(age_filter)
    
    def filter_shuttle(self, queryset, name, value):
        if value is None:
            return queryset
        if value:
            return queryset.exclude(셔틀버스__isnull=True).exclude(셔틀버스='')
        else:
            return queryset.filter(Q(셔틀버스__isnull=True) | Q(셔틀버스=''))