from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from main.models import Data  # 기존 main 앱의 모델 사용
from .serializers import AcademySerializer

class AcademyListAPIView(APIView):
    def get(self, request):
        category = request.GET.get('category', '전체')
        price_min = request.GET.get('priceMin', None)
        price_max = request.GET.get('priceMax', None)
        age_groups = request.GET.getlist('ageGroups', [])
        shuttle_filter = request.GET.get('shuttleFilter', None)

        queryset = Data.objects.all()

        # 카테고리 필터
        if category and category != '전체':
            queryset = queryset.filter(**{f'과목_{category}': True})

        # 가격 필터
        if price_min:
            queryset = queryset.filter(수강료__gte=price_min)
        if price_max:
            queryset = queryset.filter(수강료__lte=price_max)

        # 연령 필터
        if age_groups:
            age_filter = {}
            for age in age_groups:
                age_filter[f'대상_{age}'] = True
            queryset = queryset.filter(**age_filter)

        # 셔틀 필터
        if shuttle_filter == 'true':
            queryset = queryset.filter(셔틀버스=True)

        serializer = AcademySerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
