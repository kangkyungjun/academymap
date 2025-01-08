from django.db import models

# Create your models here.

class Data(models.Model):
    상가업소번호 = models.CharField(max_length=255)
    상호명 = models.CharField(max_length=255)
    상권업종대분류코드 = models.CharField(max_length=255)
    상권업종대분류명 = models.CharField(max_length=255)
    상권업종중분류명 = models.CharField(max_length=255)
    상권업종소분류명 = models.CharField(max_length=255)
    시도명 = models.CharField(max_length=255)
    시군구명 = models.CharField(max_length=255)
    행정동명 = models.CharField(max_length=255)
    법정동명 = models.CharField(max_length=255)
    지번주소 = models.CharField(max_length=255)
    도로명주소 = models.CharField(max_length=255)
    경도 = models.CharField(max_length=255)
    위도 = models.CharField(max_length=255)
    원장님= models.CharField(max_length=255)
    레벨테스트= models.CharField(max_length=255)
    강사= models.CharField(max_length=255)
    별점= models.CharField(max_length=255)
    전화번호= models.CharField(max_length=255)
    셔틀버스= models.CharField(max_length=255)
    수강료= models.CharField(max_length=255)
    학원_종류 = models.CharField(max_length=255, choices=[
        ('종합', '종합'),
        ('수학', '수학'),
        ('영어', '영어'),
        ('과학', '과학'),
        ('외국어', '외국어'),
        ('컴퓨터', '컴퓨터'),
        ('예체능', '예체능'),
        ('기타', '기타'),
        ('독서실 / 스터디카페', '독서실 / 스터디카페'),
    ])

    def __str__(self):
        return self.상호명