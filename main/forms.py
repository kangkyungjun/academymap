from django import forms
from .models import Data

class AcademyForm(forms.ModelForm):
    class Meta:
        model = Data
        fields = [
            '상호명', '대표원장', '전화번호', '도로명주소', '시도명', '시군구명', '행정동명',
            '과목_종합', '과목_수학', '과목_영어', '과목_과학', '과목_외국어',
            '과목_예체능', '과목_컴퓨터', '과목_논술', '과목_기타', '과목_독서실스터디카페',
            '대상_유아', '대상_초등', '대상_중등', '대상_고등', '대상_특목고', '대상_일반', '대상_기타',
            '수강료', '수강료_평균', '별점', '학원사진'
        ]
        widgets = {
            '학원사진': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }