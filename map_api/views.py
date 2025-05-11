from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Academy
from .serializers import AcademySerializer

class AcademyListView(APIView):
    def get(self, request):
        # 모든 학원 데이터를 가져옴
        academies = Academy.objects.all()
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
