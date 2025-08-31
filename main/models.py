from django.db import models

# Create your models here.

from django.db import models


class Data(models.Model):
    상가업소번호 = models.CharField(max_length=255, null=True, blank=True)
    상호명 = models.CharField(max_length=255, null=True, blank=True)
    상권업종대분류코드 = models.CharField(max_length=255, null=True, blank=True)
    상권업종대분류명 = models.CharField(max_length=255, null=True, blank=True)
    상권업종중분류명 = models.CharField(max_length=255, null=True, blank=True)
    상권업종소분류명 = models.CharField(max_length=255, null=True, blank=True)
    시도명 = models.CharField(max_length=255, null=True, blank=True)
    시군구명 = models.CharField(max_length=255, null=True, blank=True)
    행정동명 = models.CharField(max_length=255, null=True, blank=True)
    법정동명 = models.CharField(max_length=255, null=True, blank=True)
    지번주소 = models.CharField(max_length=255, null=True, blank=True)
    도로명주소 = models.CharField(max_length=255, null=True, blank=True)
    경도 = models.FloatField(null=True, blank=True)
    위도 = models.FloatField(null=True, blank=True)

    # 추가 필드
    학원사진 = models.URLField(max_length=500, null=True, blank=True)
    대표원장 = models.CharField(max_length=255, null=True, blank=True)
    레벨테스트 = models.CharField(max_length=255, null=True, blank=True)
    강사 = models.CharField(max_length=255, null=True, blank=True)

    # 대상 학년
    대상_유아 = models.BooleanField(null=True, blank=True, default=False)
    대상_초등 = models.BooleanField(null=True, blank=True, default=False)
    대상_중등 = models.BooleanField(null=True, blank=True, default=False)
    대상_고등 = models.BooleanField(null=True, blank=True, default=False)
    대상_특목고 = models.BooleanField(null=True, blank=True, default=False)
    대상_일반 = models.BooleanField(null=True, blank=True, default=False)
    대상_기타 = models.BooleanField(null=True, blank=True, default=False)

    # 인증 정보
    인증_명문대 = models.BooleanField(null=True, blank=True, default=False)
    인증_경력 = models.BooleanField(null=True, blank=True, default=False)

    # 학원 소개글
    소개글 = models.TextField(null=True, blank=True)

    # 과목 분류
    과목_종합 = models.BooleanField(null=True, blank=True, default=False)
    과목_수학 = models.BooleanField(null=True, blank=True, default=False)
    과목_영어 = models.BooleanField(null=True, blank=True, default=False)
    과목_과학 = models.BooleanField(null=True, blank=True, default=False)
    과목_외국어 = models.BooleanField(null=True, blank=True, default=False)
    과목_예체능 = models.BooleanField(null=True, blank=True, default=False)
    과목_컴퓨터 = models.BooleanField(null=True, blank=True, default=False)
    과목_논술 = models.BooleanField(null=True, blank=True, default=False)
    과목_기타 = models.BooleanField(null=True, blank=True, default=False)
    과목_독서실스터디카페 = models.BooleanField(null=True, blank=True, default=False)

    # 기존 정보
    별점 = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    전화번호 = models.CharField(max_length=255, null=True, blank=True)
    영업시간 = models.CharField(max_length=255, null=True, blank=True)
    셔틀버스 = models.CharField(max_length=255, null=True, blank=True)
    수강료 = models.CharField(max_length=255, null=True, blank=True)
    수강료_평균 = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.상호명 or f"Academy {self.id}"
    
    class Meta:
        verbose_name = "학원"
        verbose_name_plural = "학원들"
        # 성능 최적화를 위한 데이터베이스 인덱스
        indexes = [
            models.Index(fields=['경도', '위도'], name='location_idx'),
            models.Index(fields=['상호명'], name='name_idx'),
            models.Index(fields=['시도명', '시군구명'], name='region_idx'),
            models.Index(fields=['별점'], name='rating_idx'),
            models.Index(fields=['과목_수학'], name='subject_math_idx'),
            models.Index(fields=['과목_영어'], name='subject_eng_idx'),
            models.Index(fields=['과목_종합'], name='subject_general_idx'),
        ]


# 운영자 관련 모델들 import
try:
    from .operator_models import *
    from .academy_enhancements import *
except ImportError:
    # 마이그레이션 중이거나 모델이 아직 없는 경우
    pass

# class Data(models.Model):
#     상가업소번호 = models.CharField(max_length=255)
#     상호명 = models.CharField(max_length=255)
#     상권업종대분류코드 = models.CharField(max_length=255)
#     상권업종대분류명 = models.CharField(max_length=255)
#     상권업종중분류명 = models.CharField(max_length=255)
#     상권업종소분류명 = models.CharField(max_length=255)
#     시도명 = models.CharField(max_length=255)
#     시군구명 = models.CharField(max_length=255)
#     행정동명 = models.CharField(max_length=255)
#     법정동명 = models.CharField(max_length=255)
#     지번주소 = models.CharField(max_length=255)
#     도로명주소 = models.CharField(max_length=255)
#     경도 = models.CharField(max_length=255)
#     위도 = models.CharField(max_length=255)
#     원장님= models.CharField(max_length=255)
#     레벨테스트= models.CharField(max_length=255)
#     강사= models.CharField(max_length=255)
#     별점= models.CharField(max_length=255)
#     전화번호= models.CharField(max_length=255)
#     셔틀버스= models.CharField(max_length=255)
#     수강료= models.CharField(max_length=255)
#     학원_종류 = models.CharField(max_length=255, choices=[
#         ('종합', '종합'),
#         ('수학', '수학'),
#         ('영어', '영어'),
#         ('과학', '과학'),
#         ('외국어', '외국어'),
#         ('컴퓨터', '컴퓨터'),
#         ('예체능', '예체능'),
#         ('기타', '기타'),
#         ('독서실 / 스터디카페', '독서실 / 스터디카페'),
#     ])
#
#     def __str__(self):
#         return self.상호명