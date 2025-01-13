from django.shortcuts import render

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, F, Count
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.core.paginator import Paginator
import pandas as pd

from main.models import Data

from .models import Data  # Data 모델 import

from django.core.cache import cache
from django.utils.timezone import now
from django.db import models

# Create your views here.

def main(request):

    return render(request, 'main/main.html')


def search(request):
    if request.method == 'POST':
        searched = request.POST['searched']
        data = Data.objects.filter(상호명__contains=searched)
        context = {'searched': searched, 'data': data}
        return render(request, 'main/academy.html', context)
    else:
        return render(request, 'main/academy.html')

def academy(request, pk):
    academy = get_object_or_404(Data, pk=pk)
    context = {'academy': academy}
    return render(request, 'main/academy.html', context)


def academy_list(request):
    # 시도명 목록 (초기화)
    시도명_list = Data.objects.values_list('시도명', flat=True).distinct()

    # 선택된 값 가져오기
    시도명 = request.GET.get('시도명', '')
    시군구명 = request.GET.get('시군구명', '')
    행정동명 = request.GET.get('행정동명', '')
    과목 = request.GET.get('과목', '')

    # 과목 필드 매핑
    과목_mapping = {
        '종합': '과목_종합',
        '수학': '과목_수학',
        '영어': '과목_영어',
        '과학': '과목_과학',
        '외국어': '과목_외국어',
        '예체능': '과목_예체능',
        '컴퓨터': '과목_컴퓨터',
        '논술': '과목_논술',
        '기타': '과목_기타',
        '독서실 / 스터디카페': '과목_독서실스터디카페',
    }

    # 필터링 조건
    queryset = Data.objects.all()
    if 시도명:
        queryset = queryset.filter(시도명=시도명)
    if 시군구명:
        queryset = queryset.filter(시군구명=시군구명)
    if 행정동명:
        queryset = queryset.filter(행정동명=행정동명)
    if 과목 and 과목 in 과목_mapping:
        filter_field = {과목_mapping[과목]: True}
        queryset = queryset.filter(**filter_field)

    # Paginator 적용 (페이지당 30개씩)
    paginator = Paginator(queryset, 30)
    page = request.GET.get('page')  # 현재 페이지 번호

    try:
        academylist = paginator.page(page)
    except PageNotAnInteger:
        academylist = paginator.page(1)  # 페이지 번호가 없으면 1페이지
    except EmptyPage:
        academylist = paginator.page(paginator.num_pages)  # 페이지 범위를 벗어나면 마지막 페이지

    context = {
        '시도명_list': 시도명_list,
        '시도명_selected': 시도명,
        '시군구명_selected': 시군구명,
        '행정동명_selected': 행정동명,
        '과목_selected': 과목,
        'academylist': academylist,
        '과목_list': ['종합', '수학', '영어', '과학', '외국어', '예체능', '컴퓨터', '논술', '기타', '독서실/스터디카페'],
    }
    return render(request, 'main/academy_list.html', context)

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
    return render(request, 'main/map.html')

# 동적으로 학원 데이터를 필터링하여 제공하는 API
def filtered_academies(request):
    import json
    body = json.loads(request.body)

    # 지도 영역 좌표
    sw_lat = body.get('swLat')
    sw_lng = body.get('swLng')
    ne_lat = body.get('neLat')
    ne_lng = body.get('neLng')

    # 과목 필터
    category = body.get('category', '')

    과목_mapping = {
        '종합': '과목_종합',
        '수학': '과목_수학',
        '영어': '과목_영어',
        '과학': '과목_과학',
        '외국어': '과목_외국어',
        '예체능': '과목_예체능',
        '컴퓨터': '과목_컴퓨터',
        '논술': '과목_논술',
        '기타': '과목_기타',
        '독서실/스터디카페': '과목_독서실스터디카페',
    }

    queryset = Data.objects.filter(
        위도__gte=sw_lat,
        위도__lte=ne_lat,
        경도__gte=sw_lng,
        경도__lte=ne_lng,
    )

    if category and category != '전체' and category in 과목_mapping:
        filter_field = {과목_mapping[category]: True}
        queryset = queryset.filter(**filter_field)

    data = list(queryset.values('id', '상호명', '위도', '경도', '도로명주소', '전화번호'))
    return JsonResponse(data, safe=False)



def clean_value(value):
    if pd.isna(value) or value == '-':
        return None
    return value

# Boolean 값 변환 함수
def convert_to_boolean(value):
    if str(value).strip().lower() in ['true', '1', 'yes', 'o', 'y', '예']:
        return True
    return False

def data_update(request):
    n_data = pd.read_excel('n_data.xlsx')

    for i in range(len(n_data)):
        row = n_data.iloc[i]

        data, created = Data.objects.update_or_create(
            상가업소번호=clean_value(row['상가업소번호']),
            defaults={
                '상호명': clean_value(row['상호명']),
                '상권업종대분류코드': clean_value(row['상권업종대분류코드']),
                '상권업종대분류명': clean_value(row['상권업종대분류명']),
                '상권업종중분류명': clean_value(row['상권업종중분류명']),
                '상권업종소분류명': clean_value(row['상권업종소분류명']),
                '시도명': clean_value(row['시도명']),
                '시군구명': clean_value(row['시군구명']),
                '행정동명': clean_value(row['행정동명']),
                '법정동명': clean_value(row['법정동명']),
                '지번주소': clean_value(row['지번주소']),
                '도로명주소': clean_value(row['도로명주소']),
                '경도': clean_value(row['경도']),
                '위도': clean_value(row['위도']),
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
        )

    return render(request, 'main/data_update.html')

