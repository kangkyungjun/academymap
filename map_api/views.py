from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Academy
from .serializers import AcademySerializer
from django.db.models import Count, Avg
from django.db import models

class AcademyListView(APIView):
    def get(self, request):
        # 모든 학원 데이터를 가져옴
        academies = Academy.objects.all()
        
        # 지도 영역 bounds 필터링 지원
        sw_lat = request.GET.get('sw_lat')
        sw_lng = request.GET.get('sw_lng') 
        ne_lat = request.GET.get('ne_lat')
        ne_lng = request.GET.get('ne_lng')
        
        if sw_lat and sw_lng and ne_lat and ne_lng:
            try:
                sw_lat = float(sw_lat)
                sw_lng = float(sw_lng)
                ne_lat = float(ne_lat)
                ne_lng = float(ne_lng)
                
                # 디버깅: 전체 학원 수 확인
                total_count = Academy.objects.filter(위도__isnull=False, 경도__isnull=False).count()
                print(f"📊 전체 학원 수: {total_count}")
                
                # 지도 영역 내의 학원만 필터링
                academies = academies.filter(
                    위도__gte=sw_lat,
                    위도__lte=ne_lat,
                    경도__gte=sw_lng,
                    경도__lte=ne_lng,
                    위도__isnull=False,
                    경도__isnull=False
                )
                
                bounds_count = academies.count()
                print(f"🗺️ 지도 영역 필터링: ({sw_lat}, {sw_lng}) ~ ({ne_lat}, {ne_lng}) - {bounds_count}개 발견")
                
                # 디버깅: 좌표 범위 내 전체 데이터 확인 (필터 없이)
                debug_academies = Academy.objects.filter(
                    위도__gte=sw_lat,
                    위도__lte=ne_lat,
                    경도__gte=sw_lng,
                    경도__lte=ne_lng,
                    위도__isnull=False,
                    경도__isnull=False
                )
                debug_count = debug_academies.count()
                print(f"🔍 디버그 - 해당 영역 전체 학원: {debug_count}개")
                
                if debug_count > 0:
                    # 몇 개 샘플 좌표 출력
                    samples = debug_academies[:3]
                    for academy in samples:
                        print(f"🏫 샘플: {academy.상호명} - ({academy.위도}, {academy.경도})")
                        
            except ValueError:
                print("❌ 지도 영역 좌표 변환 실패")
        
        # 기본 필터링 파라미터 지원
        category = request.GET.get('category', '전체')
        min_price = request.GET.get('priceMin')
        max_price = request.GET.get('priceMax')
        age_groups = request.GET.getlist('ageGroups[]')
        shuttle = request.GET.get('shuttleFilter') == 'true'
        
        # 카테고리 필터링
        if category and category != '전체':
            field_name = f'과목_{category}'
            if hasattr(Academy, field_name):
                academies = academies.filter(**{field_name: True})
        
        # 수강료 필터링
        if min_price and max_price:
            try:
                academies = academies.filter(수강료_평균__gte=float(min_price), 수강료_평균__lte=float(max_price))
            except ValueError:
                pass
        
        # 연령 필터링
        for age_group in age_groups:
            field_name = f'대상_{age_group}'
            if hasattr(Academy, field_name):
                academies = academies.filter(**{field_name: True})
        
        # 셔틀버스 필터링
        if shuttle:
            academies = academies.filter(셔틀버스__isnull=False).exclude(셔틀버스='')
        
        # 페이지네이션 지원
        limit = request.GET.get('limit', '50')
        offset = request.GET.get('offset', '0')
        
        try:
            limit = int(limit)
            offset = int(offset)
            total_count = academies.count()
            academies = academies[offset:offset + limit]
            
            serializer = AcademySerializer(academies, many=True)
            
            return Response({
                'results': serializer.data,
                'count': total_count,
                'next': offset + limit < total_count,
                'previous': offset > 0
            }, status=status.HTTP_200_OK)
        except ValueError:
            serializer = AcademySerializer(academies, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

class FilteredAcademyView(APIView):
    def post(self, request):
        # 필터링 파라미터를 받음
        category = request.data.get('category', '전체')
        min_price = request.data.get('priceMin', None)
        max_price = request.data.get('priceMax', None)
        age_groups = request.data.get('ageGroups', [])
        shuttle = request.data.get('shuttleFilter', False)

        # 필터링 조건 설정
        academies = Academy.objects.all()

        # 카테고리 필터링
        if category != '전체':
            field_name = f'과목_{category}'
            academies = academies.filter(**{field_name: True})

        # 수강료 필터링
        if min_price and max_price:
            academies = academies.filter(수강료_평균__gte=min_price, 수강료_평균__lte=max_price)

        # 연령 필터링
        for age_group in age_groups:
            field_name = f'대상_{age_group}'
            academies = academies.filter(**{field_name: True})

        # 셔틀버스 필터링
        if shuttle:
            academies = academies.filter(셔틀버스__isnull=False).exclude(셔틀버스='')

        serializer = AcademySerializer(academies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ClusterView(APIView):
    def get(self, request):
        """줌 레벨 13 이하에서 동별 클러스터 데이터 제공"""
        # 지도 영역 bounds 파라미터
        sw_lat = request.GET.get('sw_lat')
        sw_lng = request.GET.get('sw_lng') 
        ne_lat = request.GET.get('ne_lat')
        ne_lng = request.GET.get('ne_lng')
        
        academies = Academy.objects.filter(위도__isnull=False, 경도__isnull=False)
        
        # bounds 필터링
        if sw_lat and sw_lng and ne_lat and ne_lng:
            try:
                sw_lat = float(sw_lat)
                sw_lng = float(sw_lng)
                ne_lat = float(ne_lat)
                ne_lng = float(ne_lng)
                
                academies = academies.filter(
                    위도__gte=sw_lat,
                    위도__lte=ne_lat,
                    경도__gte=sw_lng,
                    경도__lte=ne_lng
                )
                print(f"🗺️ 클러스터 영역 필터링: ({sw_lat}, {sw_lng}) ~ ({ne_lat}, {ne_lng})")
            except ValueError:
                print("❌ 클러스터 영역 좌표 변환 실패")
        
        # 기본 필터링 파라미터 지원
        category = request.GET.get('category', '전체')
        min_price = request.GET.get('priceMin')
        max_price = request.GET.get('priceMax')
        age_groups = request.GET.getlist('ageGroups[]')
        shuttle = request.GET.get('shuttleFilter') == 'true'
        
        # 카테고리 필터링
        if category and category != '전체':
            field_name = f'과목_{category}'
            if hasattr(Academy, field_name):
                academies = academies.filter(**{field_name: True})
        
        # 수강료 필터링
        if min_price and max_price:
            try:
                academies = academies.filter(수강료_평균__gte=float(min_price), 수강료_평균__lte=float(max_price))
            except ValueError:
                pass
        
        # 연령 필터링
        for age_group in age_groups:
            field_name = f'대상_{age_group}'
            if hasattr(Academy, field_name):
                academies = academies.filter(**{field_name: True})
        
        # 셔틀버스 필터링
        if shuttle:
            academies = academies.filter(셔틀버스__isnull=False).exclude(셔틀버스='')
        
        # 동별로 그룹화하여 학원 수 집계
        clusters = academies.values('행정동명', '시군구명').annotate(
            count=Count('id'),
            avg_lat=Avg('위도'),
            avg_lng=Avg('경도')
        ).filter(count__gt=0, 행정동명__isnull=False).order_by('-count')
        
        # 클러스터 데이터 구성
        cluster_data = []
        for cluster in clusters:
            if cluster['avg_lat'] and cluster['avg_lng']:
                cluster_data.append({
                    'name': f"{cluster['시군구명']} {cluster['행정동명']}",
                    'count': cluster['count'],
                    'lat': float(cluster['avg_lat']),
                    'lng': float(cluster['avg_lng']),
                    'district': cluster['시군구명'],
                    'dong': cluster['행정동명']
                })
        
        print(f"🏘️ 클러스터 데이터: {len(cluster_data)}개 동")
        
        return Response({
            'clusters': cluster_data,
            'total_academies': academies.count()
        }, status=status.HTTP_200_OK)
