"""
번역 유틸리티 모듈
Translation utility module for AcademyMap
"""

from django.utils.translation import gettext_lazy as _, get_language, activate
from django.conf import settings
import json
import os

# 주요 용어 번역 사전
TRANSLATION_DICT = {
    'ko': {
        # 기본 용어
        'academy': '학원',
        'search': '검색',
        'filter': '필터',
        'location': '위치',
        'price': '가격',
        'subject': '과목',
        'age_group': '대상',
        'rating': '평점',
        'review': '후기',
        'contact': '문의',
        'address': '주소',
        'phone': '전화번호',
        'website': '웹사이트',
        'description': '설명',
        'fee': '수강료',
        'schedule': '수업시간',
        'teacher': '강사',
        'facility': '시설',
        'parking': '주차',
        'shuttle': '셔틀',
        'registration': '등록',
        'enrollment': '수강신청',
        'curriculum': '커리큘럼',
        'achievement': '성과',
        'certificate': '자격증',
        'experience': '경력',
        'recommendation': '추천',
        'popular': '인기',
        'nearby': '주변',
        'recent': '최근',
        'new': '신규',
        'updated': '업데이트',
        'closed': '휴원',
        'open': '개원',
        # 과목별
        'math': '수학',
        'korean': '국어',
        'english': '영어',
        'science': '과학',
        'social_studies': '사회',
        'art': '미술',
        'music': '음악',
        'physical_education': '체육',
        'computer': '컴퓨터',
        'coding': '코딩',
        'programming': '프로그래밍',
        'piano': '피아노',
        'violin': '바이올린',
        'guitar': '기타',
        'dance': '댄스',
        'ballet': '발레',
        'taekwondo': '태권도',
        'swimming': '수영',
        'tennis': '테니스',
        'badminton': '배드민턴',
        'soccer': '축구',
        'basketball': '농구',
        # 연령대
        'preschool': '유아',
        'elementary': '초등',
        'middle_school': '중등',
        'high_school': '고등',
        'adult': '성인',
        'senior': '시니어',
    },
    'en': {
        # 기본 용어
        'academy': 'Academy',
        'search': 'Search',
        'filter': 'Filter',
        'location': 'Location',
        'price': 'Price',
        'subject': 'Subject',
        'age_group': 'Age Group',
        'rating': 'Rating',
        'review': 'Review',
        'contact': 'Contact',
        'address': 'Address',
        'phone': 'Phone',
        'website': 'Website',
        'description': 'Description',
        'fee': 'Fee',
        'schedule': 'Schedule',
        'teacher': 'Teacher',
        'facility': 'Facility',
        'parking': 'Parking',
        'shuttle': 'Shuttle',
        'registration': 'Registration',
        'enrollment': 'Enrollment',
        'curriculum': 'Curriculum',
        'achievement': 'Achievement',
        'certificate': 'Certificate',
        'experience': 'Experience',
        'recommendation': 'Recommendation',
        'popular': 'Popular',
        'nearby': 'Nearby',
        'recent': 'Recent',
        'new': 'New',
        'updated': 'Updated',
        'closed': 'Closed',
        'open': 'Open',
        # 과목별
        'math': 'Math',
        'korean': 'Korean',
        'english': 'English',
        'science': 'Science',
        'social_studies': 'Social Studies',
        'art': 'Art',
        'music': 'Music',
        'physical_education': 'Physical Education',
        'computer': 'Computer',
        'coding': 'Coding',
        'programming': 'Programming',
        'piano': 'Piano',
        'violin': 'Violin',
        'guitar': 'Guitar',
        'dance': 'Dance',
        'ballet': 'Ballet',
        'taekwondo': 'Taekwondo',
        'swimming': 'Swimming',
        'tennis': 'Tennis',
        'badminton': 'Badminton',
        'soccer': 'Soccer',
        'basketball': 'Basketball',
        # 연령대
        'preschool': 'Preschool',
        'elementary': 'Elementary',
        'middle_school': 'Middle School',
        'high_school': 'High School',
        'adult': 'Adult',
        'senior': 'Senior',
    },
    'zh-hans': {
        # 기본 용어
        'academy': '学院',
        'search': '搜索',
        'filter': '筛选',
        'location': '位置',
        'price': '价格',
        'subject': '科目',
        'age_group': '年龄组',
        'rating': '评分',
        'review': '评价',
        'contact': '联系',
        'address': '地址',
        'phone': '电话',
        'website': '网站',
        'description': '描述',
        'fee': '费用',
        'schedule': '时间表',
        'teacher': '老师',
        'facility': '设施',
        'parking': '停车',
        'shuttle': '班车',
        'registration': '注册',
        'enrollment': '报名',
        'curriculum': '课程',
        'achievement': '成就',
        'certificate': '证书',
        'experience': '经验',
        'recommendation': '推荐',
        'popular': '热门',
        'nearby': '附近',
        'recent': '最近',
        'new': '新的',
        'updated': '更新',
        'closed': '关闭',
        'open': '开放',
        # 과목별
        'math': '数学',
        'korean': '韩语',
        'english': '英语',
        'science': '科学',
        'social_studies': '社会',
        'art': '美术',
        'music': '音乐',
        'physical_education': '体育',
        'computer': '计算机',
        'coding': '编程',
        'programming': '程序设计',
        'piano': '钢琴',
        'violin': '小提琴',
        'guitar': '吉他',
        'dance': '舞蹈',
        'ballet': '芭蕾',
        'taekwondo': '跆拳道',
        'swimming': '游泳',
        'tennis': '网球',
        'badminton': '羽毛球',
        'soccer': '足球',
        'basketball': '篮球',
        # 연령대
        'preschool': '学前',
        'elementary': '小学',
        'middle_school': '中学',
        'high_school': '高中',
        'adult': '成人',
        'senior': '老年',
    }
}

def get_translated_term(key, language=None):
    """
    특정 용어의 번역을 반환
    Returns translation for a specific term
    
    Args:
        key (str): 번역할 키
        language (str): 언어 코드 (없으면 현재 언어 사용)
    
    Returns:
        str: 번역된 문자열
    """
    if language is None:
        language = get_language() or settings.LANGUAGE_CODE
    
    return TRANSLATION_DICT.get(language, {}).get(key, key)

def get_all_translations(key):
    """
    모든 언어의 번역을 반환
    Returns translations for all languages
    
    Args:
        key (str): 번역할 키
    
    Returns:
        dict: 언어별 번역 딕셔너리
    """
    translations = {}
    for lang_code, lang_dict in TRANSLATION_DICT.items():
        translations[lang_code] = lang_dict.get(key, key)
    return translations

def translate_academy_data(academy_data, target_language=None):
    """
    학원 데이터의 필드명을 번역
    Translates academy data field names
    
    Args:
        academy_data (dict): 학원 데이터
        target_language (str): 대상 언어
    
    Returns:
        dict: 번역된 학원 데이터
    """
    if target_language is None:
        target_language = get_language() or settings.LANGUAGE_CODE
    
    # 한국어인 경우 원본 데이터 반환
    if target_language == 'ko':
        return academy_data
    
    translated_data = {}
    
    # 필드명 매핑
    field_mapping = {
        'ko': {
            '상호명': 'name',
            '주소': 'address',
            '전화번호': 'phone',
            '수강료': 'fee',
            '평점': 'rating',
            '과목': 'subjects',
            '대상': 'age_groups',
        },
        'en': {
            'name': 'Academy Name',
            'address': 'Address',
            'phone': 'Phone Number',
            'fee': 'Tuition Fee',
            'rating': 'Rating',
            'subjects': 'Subjects',
            'age_groups': 'Age Groups',
        },
        'zh-hans': {
            'name': '学院名称',
            'address': '地址',
            'phone': '电话号码',
            'fee': '学费',
            'rating': '评分',
            'subjects': '科目',
            'age_groups': '年龄组',
        }
    }
    
    mapping = field_mapping.get(target_language, {})
    
    for key, value in academy_data.items():
        translated_key = mapping.get(key, key)
        translated_data[translated_key] = value
    
    return translated_data

def get_language_display_name(language_code):
    """
    언어 코드에 대한 표시명 반환
    Returns display name for language code
    """
    display_names = {
        'ko': '한국어',
        'en': 'English',
        'zh-hans': '中文'
    }
    return display_names.get(language_code, language_code)

def get_supported_languages():
    """
    지원되는 언어 목록 반환
    Returns list of supported languages
    """
    return list(TRANSLATION_DICT.keys())

def is_rtl_language(language_code):
    """
    RTL(Right-to-Left) 언어 여부 확인
    Checks if language is RTL (Right-to-Left)
    """
    rtl_languages = []  # 현재 지원 언어 중 RTL 없음
    return language_code in rtl_languages

def get_locale_data(language_code):
    """
    언어별 로케일 데이터 반환
    Returns locale data for language
    """
    locale_data = {
        'ko': {
            'date_format': 'Y년 m월 d일',
            'time_format': 'H:i',
            'currency_symbol': '₩',
            'decimal_separator': '.',
            'thousand_separator': ',',
            'number_format': '{:,}',
        },
        'en': {
            'date_format': 'F j, Y',
            'time_format': 'g:i A',
            'currency_symbol': '$',
            'decimal_separator': '.',
            'thousand_separator': ',',
            'number_format': '{:,}',
        },
        'zh-hans': {
            'date_format': 'Y年m月d日',
            'time_format': 'H:i',
            'currency_symbol': '¥',
            'decimal_separator': '.',
            'thousand_separator': ',',
            'number_format': '{:,}',
        }
    }
    return locale_data.get(language_code, locale_data['ko'])

class TranslationMiddleware:
    """
    번역 관련 미들웨어
    Translation middleware
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # 요청 처리 전 번역 설정
        language = self.get_language_from_request(request)
        if language:
            activate(language)
        
        response = self.get_response(request)
        
        # 응답 처리 후 정리
        return response
    
    def get_language_from_request(self, request):
        """
        요청에서 언어 코드 추출
        Extracts language code from request
        """
        # URL 파라미터에서 언어 확인
        if 'lang' in request.GET:
            lang = request.GET['lang']
            if lang in get_supported_languages():
                return lang
        
        # Accept-Language 헤더 확인
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        for lang_code in get_supported_languages():
            if lang_code in accept_language:
                return lang_code
        
        return settings.LANGUAGE_CODE