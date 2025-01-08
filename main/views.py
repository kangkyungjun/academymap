from django.shortcuts import render

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, F, Count
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

import pandas as pd

from main.models import Data

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
    학원_종류 = request.GET.get('학원_종류', '')

    # 필터링 조건
    queryset = Data.objects.all()
    if 시도명:
        queryset = queryset.filter(시도명=시도명)
    if 시군구명:
        queryset = queryset.filter(시군구명=시군구명)
    if 행정동명:
        queryset = queryset.filter(행정동명=행정동명)
    if 학원_종류:
        queryset = queryset.filter(학원_종류=학원_종류)

    context = {
        '시도명_list': 시도명_list,
        '시도명_selected': 시도명,
        '시군구명_selected': 시군구명,
        '행정동명_selected': 행정동명,
        '학원_종류_selected': 학원_종류,
        'academylist': queryset,  # 필터링된 결과
        '학원_종류_list': ['종합','수학','영어','과학','외국어','컴퓨터','예체능','기타','독서실 / 스터디카페'],
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
    academies = Data.objects.all()
    context = {'academies':academies}
    return render(request, 'main/map.html', context)


def data_update(request):
    n_data = pd.read_excel('n_data.xlsx')

    for i in range(len(n_data)):
        # 상가업소번호 추출
        shop_id = n_data.iloc[i, 0]
            # 새로운 데이터 저장
        row = n_data.iloc[i]
        data = Data(
            상가업소번호=row['상가업소번호'],
            상호명=row['상호명'],
            상권업종대분류코드=row['상권업종대분류코드'],
            상권업종대분류명=row['상권업종대분류명'],
            상권업종중분류명=row['상권업종중분류명'],
            상권업종소분류명=row['상권업종소분류명'],
            시도명=row['시도명'],
            시군구명=row['시군구명'],
            행정동명=row['행정동명'],
            법정동명=row['법정동명'],
            지번주소=row['지번주소'],
            도로명주소=row['도로명주소'],
            경도=row['경도'],
            위도=row['위도'] ,
            학원_종류 = row['학원_종류'],
            원장님 = row['원장님'],
            레벨테스트 = row['레벨테스트'],
            강사 = row['강사'],
            별점 = row['별점'],
            전화번호 = row['전화번호'],
            셔틀버스 = row['셔틀버스'],
            수강료 = row['수강료']
        )
        data.save()
            # for index, row in n_data.iterrows():
            #     data = Data(
            #         상가업소번호=row['상가업소번호'],
            #         상호명=row['상호명'],
            #         상권업종대분류코드=row['상권업종대분류코드'],
            #         상권업종대분류명=row['상권업종대분류명'],
            #         상권업종중분류명=row['상권업종중분류명'],
            #         상권업종소분류명=row['상권업종소분류명'],
            #         표준산업분류명=row['표준산업분류명'],
            #         시도명=row['시도명'],
            #         시군구명=row['시군구명'],
            #         행정동명=row['행정동명'],
            #         법정동명=row['법정동명'],
            #         지번주소=row['지번주소'],
            #         건물명=row['건물명'],
            #         도로명주소=row['도로명주소'],
            #         구우편번호=row['구우편번호'],
            #         층정보=row['층정보'],
            #         경도=row['경도'],
            #         위도=row['위도']
            #     )
            #     data.save()
    return render(request, 'main/data_update.html')