from rest_framework import serializers
from main.models import Data  # 기존 main 앱의 Data 모델을 가져옴

class AcademySerializer(serializers.ModelSerializer):
    class Meta:
        model = Data
        fields = '__all__'
