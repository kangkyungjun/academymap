import json
import pandas as pd
import math

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, F, Count, FloatField, Min, Max, Avg
from django.db.models.functions import Cast, Sqrt, Power
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.csrf import csrf_exempt

from .models import Data
from .forms import AcademyForm
from django.db.models import Q, FloatField


def calculate_distance(lat1, lng1, lat2, lng2):
    """
    두 지점 간의 거리를 계산 (Haversine formula)
    결과: km 단위
    """
    if not all([lat1, lng1, lat2, lng2]):
        return float('inf')

    R = 6371  # 지구 반지름 (km)

    lat1_rad = math.radians(float(lat1))
    lng1_rad = math.radians(float(lng1))
    lat2_rad = math.radians(float(lat2))
    lng2_rad = math.radians(float(lng2))

    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad

    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c



# Create your views here.

def main(request):

    return render(request, 'main/main.html')

def search(request):
    searched = request.GET.get('searched', '').strip()
    price_min = int(request.GET.get('price_min', '0'))
    price_max = int(request.GET.get('price_max', '2000000'))
    category = request.GET.get('category', '전체')
    age_groups = request.GET.getlist('ageGroups[]')
    shuttle = request.GET.get('shuttleFilter') == 'true'

    academies = Data.objects.all()

    if searched:
        search_terms = searched.split()
        search_filter = Q()
        category_mapping = {
            '수학': '과목_수학', '영어': '과목_영어', '과학': '과목_과학',
            '외국어': '과목_외국어', '예체능': '과목_예체능',
            '컴퓨터': '과목_컴퓨터', '논술': '과목_논술',
            '기타': '과목_기타', '독서실': '과목_독서실스터디카페',
            '스터디카페': '과목_독서실스터디카페', '종합': '과목_종합',
            '태권도': '과목_예체능', '피아노': '과목_예체능', '미술': '과목_예체능'
        }

        for term in search_terms:
            term_filter = (
                Q(상호명__icontains=term) |
                Q(도로명주소__icontains=term) |
                Q(시도명__icontains=term) |
                Q(시군구명__icontains=term) |
                Q(행정동명__icontains=term) |
                Q(법정동명__icontains=term)
            )
            if term in category_mapping:
                term_filter |= Q(**{category_mapping[term]: True})

            search_filter &= term_filter

        academies = academies.filter(search_filter)

    # 수강료 평균 필터링
    academies = academies.annotate(
        수강료_평균_float=Cast('수강료_평균', FloatField())
    ).filter(
        수강료_평균_float__gte=price_min,
        수강료_평균_float__lte=price_max
    )

    if category != '전체':
        academies = academies.filter(**{f'과목_{category}': True})

    if age_groups:
        age_filter = Q()
        for age in age_groups:
            age_filter |= Q(**{f'대상_{age}': True})
        academies = academies.filter(age_filter)

    # 셔틀버스는 true일 때만 필터링하고 false일 때는 모든 결과를 유지합니다.
    if shuttle:
        academies = academies.filter(Q(셔틀버스__iexact='true') | Q(셔틀버스__icontains='있음'))

    academies = academies.distinct()[:1000]

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'main/search_results_partial.html', {'academies': academies})

    context = {
        'searched': searched,
        'initial_results': academies,
        'min_price': price_min,
        'max_price': price_max,
        '과목_list': ['전체', '수학', '영어', '과학', '외국어', '예체능', '컴퓨터', '논술', '기타', '독서실스터디카페'],
        'target_age_groups': ['유아', '초등', '중등', '고등', '특목고', '일반', '기타'],
    }

    return render(request, 'main/search.html', context)



def academy(request, pk):
    academy = get_object_or_404(Data, pk=pk)

    # 현재 학원의 수강료_평균 (문자열을 float로 변환)
    try:
        current_tuition = float(academy.수강료_평균)
    except (TypeError, ValueError):
        current_tuition = 0

    # 과목 분류 우선순위 목록 (순서대로 첫 True인 필드 선택)
    subject_fields = [
        ('과목_종합', '종합'),
        ('과목_수학', '수학'),
        ('과목_영어', '영어'),
        ('과목_과학', '과학'),
        ('과목_외국어', '외국어'),
        ('과목_예체능', '예체능'),
        ('과목_컴퓨터', '컴퓨터'),
        ('과목_논술', '논술'),
        ('과목_기타', '기타'),
        ('과목_독서실스터디카페', '독서실/스터디카페'),
    ]
    subject_field = None
    subject_label = None
    for field, label in subject_fields:
        if getattr(academy, field):
            subject_field = field
            subject_label = label
            break

    # 동일 과목에 해당하는 학원들만 대상으로 평균 계산 (0, None, 'false' 값 제외)
    if subject_field:
        base_queryset = Data.objects.filter(**{subject_field: True})\
            .exclude(수강료_평균__iexact='false')\
            .annotate(tuition=Cast('수강료_평균', FloatField()))\
            .filter(tuition__gt=0)
        district_avg = base_queryset.filter(시군구명=academy.시군구명)\
            .aggregate(avg=Avg('tuition'))['avg'] or 0
        province_avg = base_queryset.filter(시도명=academy.시도명)\
            .aggregate(avg=Avg('tuition'))['avg'] or 0
        overall_avg = base_queryset.aggregate(avg=Avg('tuition'))['avg'] or 0
    else:
        district_avg = province_avg = overall_avg = 0

    # 전국 통계 계산
    if overall_avg == 0 or current_tuition == 0:
        tuition_stat_nation = "수강료 정보가 없습니다."
        diff_nation_abs = 0
        percentage_nation = 0
    else:
        diff_nation = current_tuition - overall_avg
        diff_nation_abs = round(abs(diff_nation), 0)
        percentage_nation = round(((current_tuition / overall_avg) - 1) * 100, 1)
        if diff_nation > 0:
            tuition_stat_nation = f"전국 평균보다 {percentage_nation}%, {diff_nation_abs:,.0f}원 높습니다."
        elif diff_nation < 0:
            tuition_stat_nation = f"전국 평균보다 {abs(percentage_nation)}%, {diff_nation_abs:,.0f}원 낮습니다."
        else:
            tuition_stat_nation = "전국 평균과 동일합니다."

    # 시도(도) 통계 계산
    if province_avg == 0 or current_tuition == 0:
        tuition_stat_province = f"수강료 정보가 없습니다."
        diff_province_abs = 0
        percentage_province = 0
    else:
        diff_province = current_tuition - province_avg
        diff_province_abs = round(abs(diff_province), 0)
        percentage_province = round(((current_tuition / province_avg) - 1) * 100, 1)
        if diff_province > 0:
            tuition_stat_province = f"{academy.시도명} 평균보다 {percentage_province}%, {diff_province_abs:,.0f}원 높습니다."
        elif diff_province < 0:
            tuition_stat_province = f"{academy.시도명} 평균보다 {abs(percentage_province)}%, {diff_province_abs:,.0f}원 낮습니다."
        else:
            tuition_stat_province = f"{academy.시도명} 평균과 동일합니다."

    # 시군구 통계 계산
    if district_avg == 0 or current_tuition == 0:
        tuition_stat_district = f"수강료 정보가 없습니다."
        diff_district_abs = 0
        percentage_district = 0
    else:
        diff_district = current_tuition - district_avg
        diff_district_abs = round(abs(diff_district), 0)
        percentage_district = round(((current_tuition / district_avg) - 1) * 100, 1)
        if diff_district > 0:
            tuition_stat_district = f"{academy.시군구명} 평균보다 {percentage_district}%, {diff_district_abs:,.0f}원 높습니다."
        elif diff_district < 0:
            tuition_stat_district = f"{academy.시군구명} 평균보다 {abs(percentage_district)}%, {diff_district_abs:,.0f}원 낮습니다."
        else:
            tuition_stat_district = f"{academy.시군구명} 평균과 동일합니다."

    # 차트용 데이터 (여기서는 행정동, 법정동은 계산하지 않았으므로 0 처리)
    chart_labels = [
        "현재 학원",       # 현재 학원
        academy.법정동명,       # 법정동 평균 (여기서는 미계산 → 0)
        academy.행정동명,       # 행정동 평균 (미계산 → 0)
        academy.시군구명,       # 시군구 평균
        academy.시도명,         # 시도 평균
        "전국"                # 전국 평균
    ]
    chart_data = [current_tuition, 0, 0, district_avg, province_avg, overall_avg]
    is_tuition_empty = (overall_avg == 0)

    context = {
        'academy': academy,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'is_tuition_empty': is_tuition_empty,
        'tuition_stat_nation': tuition_stat_nation,
        'tuition_stat_province': tuition_stat_province,
        'tuition_stat_district': tuition_stat_district,
        'subject_label': subject_label,
        # 별도로 각 통계의 차이 및 비율 값도 context에 포함 (원할 경우)
        'diff_nation_abs': diff_nation_abs,
        'percentage_nation': percentage_nation,
        'diff_province_abs': diff_province_abs,
        'percentage_province': percentage_province,
        'diff_district_abs': diff_district_abs,
        'percentage_district': percentage_district,
    }
    return render(request, 'main/academy.html', context)


def get_regions(request):
    level = request.GET.get('level')
    parent_value = request.GET.get('parent_value')

    if level == "시군구명":
        regions = Data.objects.filter(시도명=parent_value).values_list('시군구명', flat=True).distinct()
    elif level == "행정동명":
        regions = Data.objects.filter(시군구명=parent_value).values_list('행정동명', flat=True).distinct()
    else:
        regions = Data.objects.values_list('시도명', flat=True).distinct()

    return JsonResponse({'regions': list(regions)})


def map(request):
    price_range = Data.objects.aggregate(
       min_price=Min(Cast('수강료_평균', FloatField())),
       max_price=Max(Cast('수강료_평균', FloatField()))
    )
    # 모델에 정의된 대상 학년 옵션 (모두 True/False 필드이므로, 필터링 옵션으로 고정된 목록 사용)
    target_age_groups = ['유아', '초등', '중등', '고등', '특목고', '일반', '기타']
    context = {
       'min_price': price_range['min_price'] or 0,
       'max_price': price_range['max_price'] or 100,
       'target_age_groups': target_age_groups,
    }
    return render(request, 'main/map.html', context)



def map2(request):
    subject_list = ['전체', '수학', '영어', '과학', '외국어', '예체능', '컴퓨터', '논술', '기타', '독서실스터디카페']
    selected_subjects = request.GET.getlist('subjects')

    # 전체 버튼 처리
    if '전체' in selected_subjects or not selected_subjects:
        academies = Data.objects.all()
        selected_subjects = ['전체']
    else:
        subject_mapping = {
            '수학': '과목_수학',
            '영어': '과목_영어',
            '과학': '과목_과학',
            '외국어': '과목_외국어',
            '예체능': '과목_예체능',
            '컴퓨터': '과목_컴퓨터',
            '논술': '과목_논술',
            '기타': '과목_기타',
            '독서실스터디카페': '과목_독서실스터디카페'
        }
        filter_query = Q()
        for subject in selected_subjects:
            if subject in subject_mapping:
                filter_query |= Q(**{subject_mapping[subject]: True})
        academies = Data.objects.filter(filter_query)

    context = {
        'subject_list': subject_list,
        'selected_subjects': selected_subjects,
        'academies': academies,
    }

    return render(request, 'main/map2.html', context)



@csrf_exempt
def filtered_academies(request):
    body = json.loads(request.body)
    sw_lat = body.get('swLat')
    sw_lng = body.get('swLng')
    ne_lat = body.get('neLat')
    ne_lng = body.get('neLng')
    subjects = body.get('subjects', [])  # ✅ 수정됨
    filterMode = body.get('filterMode', 'OR')  # 기본값: OR 모드

    # 🔍 디버깅: Flutter에서 보내는 파라미터 확인 (print 문 제거 - BrokenPipe 오류 방지)
    # 필요시 로깅 사용
    # import logging
    # logger = logging.getLogger(__name__)
    # logger.debug(f"Flutter 요청 - 위치: SW({sw_lat}, {sw_lng}) NE({ne_lat}, {ne_lng})")

    # 🚀 수정: 전국 데이터 반환 (지역 제한 제거)
    queryset = Data.objects.all()

    # 필요시 한국 전체 범위로 제한 (위도: 33-39, 경도: 124-132)
    queryset = queryset.filter(
        위도__gte=33.0,
        위도__lte=39.0,
        경도__gte=124.0,
        경도__lte=132.0,
        위도__isnull=False,
        경도__isnull=False,
    )

    # ✅ 다중 과목 필터 적용 (OR/AND 모드 지원)

    subject_mapping = {
        '종합': '과목_종합',
        '수학': '과목_수학',
        '영어': '과목_영어',
        '과학': '과목_과학',
        '외국어': '과목_외국어',
        '예체능': '과목_예체능',
        '컴퓨터': '과목_컴퓨터',
        '논술': '과목_논술',
        '기타': '과목_기타',
        '독서실스터디카페': '과목_독서실스터디카페',
    }

    if subjects and '전체' not in subjects:
        if filterMode == 'AND':
            # AND 모드: 선택된 모든 과목을 동시에 제공하는 학원만 표시
            for subject in subjects:
                if subject in subject_mapping:
                    field_filter = {subject_mapping[subject]: True}
                    queryset = queryset.filter(**field_filter)
        else:
            # OR 모드: 선택된 과목 중 하나 이상을 제공하는 학원 표시
            subject_q = Q()
            for subject in subjects:
                if subject in subject_mapping:
                    subject_q |= Q(**{subject_mapping[subject]: True})
            queryset = queryset.filter(subject_q)

    # 가격 필터
    priceMin = body.get('priceMin')
    priceMax = body.get('priceMax')
    queryset = queryset.annotate(수강료평균_float=Cast('수강료_평균', FloatField()))

    if priceMin and float(priceMin) > 0:
        try:
            # null 값을 가진 학원도 포함 (가격 정보 없는 학원도 표시)
            queryset = queryset.filter(Q(수강료평균_float__gte=float(priceMin)) | Q(수강료평균_float__isnull=True))
        except ValueError:
            pass

    if priceMax:
        try:
            # null 값을 가진 학원도 포함 (가격 정보 없는 학원도 표시)
            queryset = queryset.filter(Q(수강료평균_float__lte=float(priceMax)) | Q(수강료평균_float__isnull=True))
        except ValueError:
            pass

    # 연령 필터
    ageGroups = body.get('ageGroups', [])
    if ageGroups:
        q_age = Q()
        for group in ageGroups:
            field = f"대상_{group}"
            if field in [f.name for f in Data._meta.fields]:
                q_age |= Q(**{field: True})
        queryset = queryset.filter(q_age)

    # 셔틀버스 필터
    shuttleFilter = body.get('shuttleFilter', False)
    if shuttleFilter:
        queryset = queryset.filter(Q(셔틀버스__icontains='있음') | Q(셔틀버스__iexact='true'))

    data = list(queryset.values(
        'id', '상호명', '위도', '경도', '도로명주소', '전화번호',
        '시군구명', '상권업종소분류명', '셔틀버스', '영업시간', '별점'
    ))

    # 📍 사용자 위치 기반 거리 계산 및 정렬
    user_lat = body.get('userLat')
    user_lng = body.get('userLng')

    if user_lat and user_lng:
        # 각 학원까지의 거리 계산
        for academy in data:
            academy_lat = academy.get('위도')
            academy_lng = academy.get('경도')

            if academy_lat and academy_lng:
                distance = calculate_distance(user_lat, user_lng, academy_lat, academy_lng)
                academy['distance'] = round(distance, 2)  # km, 소수점 2자리
            else:
                academy['distance'] = float('inf')  # 위치 정보 없는 경우 맨 뒤로

        # 거리순으로 정렬 (가까운 곳부터)
        data.sort(key=lambda x: x.get('distance', float('inf')))

        # 🚀 성능 최적화: 가까운 학원 상위 2000개만 반환
        data = data[:2000]

    # 🔍 디버깅: 반환되는 데이터 확인 (print 문 제거 - BrokenPipe 오류 방지)
    # 필요시 로깅 사용

    return JsonResponse(data, safe=False)
###### 기존 map 용 ######
# def filtered_academies(request):
#     body = json.loads(request.body)
#     sw_lat = body.get('swLat')
#     sw_lng = body.get('swLng')
#     ne_lat = body.get('neLat')
#     ne_lng = body.get('neLng')
#     category = body.get('category', '')
#
#     # 지도 범위 내의 학원들 필터링
#     queryset = Data.objects.filter(
#         위도__gte=sw_lat,
#         위도__lte=ne_lat,
#         경도__gte=sw_lng,
#         경도__lte=ne_lng,
#     )
#
#     # 과목(카테고리) 필터 적용
#     과목_mapping = {
#         '종합': '과목_종합',
#         '수학': '과목_수학',
#         '영어': '과목_영어',
#         '과학': '과목_과학',
#         '외국어': '과목_외국어',
#         '예체능': '과목_예체능',
#         '컴퓨터': '과목_컴퓨터',
#         '논술': '과목_논술',
#         '기타': '과목_기타',
#         '독서실/스터디카페': '과목_독서실스터디카페',
#     }
#     if category and category != '전체' and category in 과목_mapping:
#         filter_field = {과목_mapping[category]: True}
#         queryset = queryset.filter(**filter_field)
#
#     # 가격 범위 필터 적용 (수강료_평균을 float으로 캐스팅)
#     priceMin = body.get('priceMin', None)
#     priceMax = body.get('priceMax', None)
#     queryset = queryset.annotate(수강료평균_float=Cast('수강료_평균', FloatField()))
#     if priceMin:
#         try:
#             priceMin_val = float(priceMin)
#             queryset = queryset.filter(수강료평균_float__gte=priceMin_val)
#         except ValueError:
#             pass
#     if priceMax:
#         try:
#             priceMax_val = float(priceMax)
#             queryset = queryset.filter(수강료평균_float__lte=priceMax_val)
#         except ValueError:
#             pass
#
#     # 연령 필터 적용
#     ageGroups = body.get('ageGroups', [])
#     if ageGroups:
#         q_age = Q()
#         for group in ageGroups:
#             if group == '유아':
#                 q_age |= Q(대상_유아=True)
#             elif group == '초등':
#                 q_age |= Q(대상_초등=True)
#             elif group == '중등':
#                 q_age |= Q(대상_중등=True)
#             elif group == '고등':
#                 q_age |= Q(대상_고등=True)
#             elif group == '특목고':
#                 q_age |= Q(대상_특목고=True)
#             elif group == '일반':
#                 q_age |= Q(대상_일반=True)
#             elif group == '기타':
#                 q_age |= Q(대상_기타=True)
#         queryset = queryset.filter(q_age)
#
#     # 셔틀버스 필터 적용 (있음, True, true 등)
#     shuttleFilter = body.get('shuttleFilter', False)
#     if shuttleFilter:
#         queryset = queryset.filter(Q(셔틀버스__icontains='있음') | Q(셔틀버스__iexact='true'))
#
#     data = list(queryset.values(
#         'id',
#         '상호명',
#         '위도',
#         '경도',
#         '도로명주소',
#         '전화번호',
#         '시군구명',
#         '상권업종소분류명',
#         '셔틀버스',  # 🔥 반드시 추가되어야 하는 필드!
#         '영업시간',  # 🔥 반드시 추가되어야 하는 필드!
#         '별점',      # 🔥 필요하다면 추가
#     ))
#     return JsonResponse(data, safe=False)


def clean_value(value):
    if pd.isna(value) or value == '-':
        return None
    return value

# Boolean 값 변환 함수
def convert_to_boolean(value):
    if str(value).strip().lower() in ['true', '1', 'yes', 'o', 'y', '예']:
        return True
    return False


def manage(request):
    """ 학원 리스트 관리 페이지 (검색 및 페이지네이션 포함) """
    search_query = request.GET.get('search', '')
    queryset = Data.objects.all()

    if search_query:
        queryset = queryset.filter(상호명__icontains=search_query)

    # 페이지네이션 설정 (100개씩)
    paginator = Paginator(queryset, 100)
    page = request.GET.get('page')
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'main/manage.html', context)
def add_academy(request):
    """ 학원 정보 등록 페이지 """
    if request.method == 'POST':
        form = AcademyForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('manage')
    else:
        form = AcademyForm()
    return render(request, 'main/add_academy.html', {'form': form})

def modify_academy(request, pk):
    """ 기존 학원 정보 수정 페이지 """
    academy = get_object_or_404(Data, pk=pk)
    if request.method == 'POST':
        form = AcademyForm(request.POST, request.FILES, instance=academy)
        if form.is_valid():
            form.save()
            return redirect('manage')
    else:
        form = AcademyForm(instance=academy)
    return render(request, 'main/modify_academy.html', {'form': form, 'academy': academy})

def delete_academy(request, pk):
    """ 학원 정보 삭제 페이지 """
    academy = get_object_or_404(Data, pk=pk)
    if request.method == 'POST':
        academy.delete()
        return redirect('manage')
    return render(request, 'main/delete_academy.html', {'academy': academy})


def data_update(request):
    print("=== 데이터 업데이트 시작 ===")
    n_data = pd.read_excel('n_data.xlsx')
    print(f"Excel에서 읽은 총 레코드 수: {len(n_data)}")

    # 기존 데이터 백업을 위한 카운트
    existing_count = Data.objects.count()
    print(f"기존 DB 레코드 수: {existing_count}")

    success_count = 0
    error_count = 0

    for i in range(len(n_data)):
        try:
            row = n_data.iloc[i]

            # 고유 식별자 생성 (상호명 + 도로명주소 + 좌표 조합)
            상호명 = clean_value(row['상호명']) or f"학원_{i}"
            도로명주소 = clean_value(row['도로명주소']) or ""
            경도 = clean_value(row['경도']) or 0
            위도 = clean_value(row['위도']) or 0

            # 복합 고유 키 생성 (데이터 손실 방지)
            unique_key = f"{상호명}_{도로명주소}_{경도}_{위도}_{i}"

            # 상가업소번호 처리 (원본 데이터 보존)
            상가업소번호 = clean_value(row['상가업소번호'])
            if 상가업소번호 is None or str(상가업소번호).strip() == '':
                상가업소번호 = f"AUTO_ID_{i:08d}"

            # 공통 데이터 준비
            defaults_data = {
                '상가업소번호': 상가업소번호,
                '상호명': 상호명,
                '상권업종대분류코드': clean_value(row['상권업종대분류코드']),
                '상권업종대분류명': clean_value(row['상권업종대분류명']),
                '상권업종중분류명': clean_value(row['상권업종중분류명']),
                '상권업종소분류명': clean_value(row['상권업종소분류명']),
                '시도명': clean_value(row['시도명']),
                '시군구명': clean_value(row['시군구명']),
                '행정동명': clean_value(row['행정동명']),
                '법정동명': clean_value(row['법정동명']),
                '지번주소': clean_value(row['지번주소']),
                '도로명주소': 도로명주소,
                '경도': 경도,
                '위도': 위도,
                '학원사진': clean_value(row['학원사진']),
                '대표원장': clean_value(row['대표원장']),
                '레벨테스트': clean_value(row['레벨테스트']),
                '강사': clean_value(row['강사']),

                # Boolean 필드 변환
                '대상_유아': convert_to_boolean(row['대상_유아']),
                '대상_초등': convert_to_boolean(row['대상_초등']),
                '대상_중등': convert_to_boolean(row['대상_중등']),
                '대상_고등': convert_to_boolean(row['대상_고등']),
                '대상_특목고': convert_to_boolean(row['대상_특목고']),
                '대상_일반': convert_to_boolean(row['대상_일반']),
                '대상_기타': convert_to_boolean(row['대상_기타']),

                '인증_명문대': convert_to_boolean(row['인증_명문대']),
                '인증_경력': convert_to_boolean(row['인증_경력']),

                '소개글': clean_value(row['소개글']),

                '과목_종합': convert_to_boolean(row['과목_종합']),
                '과목_수학': convert_to_boolean(row['과목_수학']),
                '과목_영어': convert_to_boolean(row['과목_영어']),
                '과목_과학': convert_to_boolean(row['과목_과학']),
                '과목_외국어': convert_to_boolean(row['과목_외국어']),
                '과목_예체능': convert_to_boolean(row['과목_예체능']),
                '과목_컴퓨터': convert_to_boolean(row['과목_컴퓨터']),
                '과목_논술': convert_to_boolean(row['과목_논술']),
                '과목_기타': convert_to_boolean(row['과목_기타']),
                '과목_독서실스터디카페': convert_to_boolean(row['과목_독서실스터디카페']),

                '별점': clean_value(row['별점']),
                '전화번호': clean_value(row['전화번호']),
                '영업시간': clean_value(row['영업시간']),
                '셔틀버스': convert_to_boolean(row['셔틀버스']),
                '수강료': clean_value(row['수강료']),
                '수강료_평균': clean_value(row['수강료_평균']),
            }

            # 단순하게 새 레코드 생성 (모든 데이터 보존)
            # 중복 검사: 동일한 상호명, 도로명주소, 좌표를 가진 기존 레코드가 있는지 확인
            existing = Data.objects.filter(
                상호명=상호명,
                도로명주소=도로명주소,
                경도=경도,
                위도=위도
            ).first()

            if existing:
                # 기존 레코드 업데이트
                for key, value in defaults_data.items():
                    setattr(existing, key, value)
                existing.save()
                created = False
                data = existing
            else:
                # 새 레코드 생성
                data = Data.objects.create(**defaults_data)
                created = True

            if created:
                success_count += 1

            # 진행 상황 출력 (1000개마다)
            if i % 1000 == 0:
                print(f"진행 중... {i+1}/{len(n_data)} ({((i+1)/len(n_data)*100):.1f}%)")

        except Exception as e:
            error_count += 1
            print(f"에러 발생 (행 {i+1}): {e}")
            continue

    print(f"=== 데이터 업데이트 완료 ===")
    print(f"성공: {success_count}개")
    print(f"에러: {error_count}개")
    print(f"최종 DB 레코드 수: {Data.objects.count()}")

    return render(request, 'main/data_update.html', {
        'success_count': success_count,
        'error_count': error_count,
        'total_records': Data.objects.count()
    })

