"""
언어 선택 및 다국어 지원을 위한 뷰
Language selection and multilingual support views
"""

from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.utils import translation
from django.utils.translation import gettext as _
from django.conf import settings
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

def language_selector(request):
    """
    언어 선택 페이지
    Language selection page
    """
    current_language = translation.get_language()
    available_languages = settings.LANGUAGES
    
    context = {
        'current_language': current_language,
        'available_languages': available_languages,
        'redirect_to': request.GET.get('next', '/')
    }
    
    return render(request, 'main/language_selector.html', context)

@require_POST
def set_language(request):
    """
    언어 설정 뷰 (Django 기본 set_language 뷰와 유사)
    Language setting view (similar to Django's default set_language view)
    """
    next_url = request.POST.get('next', '/')
    language = request.POST.get('language')
    
    if language and language in dict(settings.LANGUAGES):
        # 세션에 언어 설정 저장
        request.session[translation.LANGUAGE_SESSION_KEY] = language
        
        # 언어 활성화
        translation.activate(language)
        
        # 쿠키에도 저장 (선택사항)
        response = redirect(next_url)
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME, 
            language,
            max_age=settings.LANGUAGE_COOKIE_AGE,
            path=settings.LANGUAGE_COOKIE_PATH,
            domain=settings.LANGUAGE_COOKIE_DOMAIN,
        )
        
        return response
    
    return redirect(next_url)

def get_language_info(request):
    """
    현재 언어 정보를 JSON으로 반환
    Returns current language information as JSON
    """
    current_language = translation.get_language()
    
    language_info = {
        'code': current_language,
        'name': dict(settings.LANGUAGES).get(current_language, current_language),
        'available_languages': [
            {
                'code': code,
                'name': name,
                'is_current': code == current_language
            }
            for code, name in settings.LANGUAGES
        ]
    }
    
    return JsonResponse(language_info)

@csrf_exempt
def detect_language(request):
    """
    사용자의 선호 언어 감지
    Detect user's preferred language
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            accept_language = data.get('accept_language', '')
            
            # Accept-Language 헤더 파싱
            preferred_languages = []
            if accept_language:
                for lang_entry in accept_language.split(','):
                    lang_parts = lang_entry.strip().split(';')
                    lang_code = lang_parts[0].strip()
                    
                    # 우선순위 파싱 (q 값)
                    priority = 1.0
                    if len(lang_parts) > 1:
                        q_part = lang_parts[1].strip()
                        if q_part.startswith('q='):
                            try:
                                priority = float(q_part[2:])
                            except ValueError:
                                priority = 1.0
                    
                    preferred_languages.append((lang_code, priority))
            
            # 우선순위순으로 정렬
            preferred_languages.sort(key=lambda x: x[1], reverse=True)
            
            # 지원되는 언어 중에서 최적 선택
            available_codes = [code for code, _ in settings.LANGUAGES]
            detected_language = settings.LANGUAGE_CODE  # 기본값
            
            for lang_code, _ in preferred_languages:
                # 정확한 매칭
                if lang_code in available_codes:
                    detected_language = lang_code
                    break
                
                # 부분 매칭 (예: en-US -> en)
                primary_lang = lang_code.split('-')[0]
                if primary_lang in available_codes:
                    detected_language = primary_lang
                    break
            
            return JsonResponse({
                'detected_language': detected_language,
                'confidence': 'high' if detected_language != settings.LANGUAGE_CODE else 'low',
                'available_languages': available_codes
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'POST method required'}, status=405)

def localized_content(request, content_type='general'):
    """
    언어별 로컬라이즈된 콘텐츠 반환
    Returns localized content by language
    """
    current_language = translation.get_language()
    
    # 언어별 콘텐츠 매핑
    content_mapping = {
        'ko': {
            'welcome_message': '학원 검색의 새로운 기준, AcademyMap에 오신 것을 환영합니다!',
            'search_placeholder': '학원명이나 지역을 검색해보세요',
            'popular_subjects': ['수학', '영어', '과학', '예체능'],
            'age_groups': ['유아', '초등', '중등', '고등'],
            'features': [
                '실시간 학원 정보',
                '상세한 수강료 비교',
                '학부모 후기 및 평점',
                '셔틀버스 정보'
            ]
        },
        'en': {
            'welcome_message': 'Welcome to AcademyMap - The new standard for academy search!',
            'search_placeholder': 'Search by academy name or location',
            'popular_subjects': ['Math', 'English', 'Science', 'Arts & Sports'],
            'age_groups': ['Preschool', 'Elementary', 'Middle School', 'High School'],
            'features': [
                'Real-time academy information',
                'Detailed tuition comparison',
                'Parent reviews and ratings',
                'Shuttle bus information'
            ]
        },
        'zh-hans': {
            'welcome_message': '欢迎来到AcademyMap - 学院搜索的新标准！',
            'search_placeholder': '按学院名称或地区搜索',
            'popular_subjects': ['数学', '英语', '科学', '艺术体育'],
            'age_groups': ['学前', '小学', '初中', '高中'],
            'features': [
                '实时学院信息',
                '详细学费比较',
                '家长评价和评分',
                '班车信息'
            ]
        }
    }
    
    content = content_mapping.get(current_language, content_mapping['ko'])
    
    return JsonResponse({
        'language': current_language,
        'content': content,
        'content_type': content_type
    })

def language_stats(request):
    """
    언어 사용 통계 (관리자용)
    Language usage statistics (for administrators)
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # 실제 구현에서는 데이터베이스에서 통계를 가져와야 함
    # In actual implementation, statistics should be fetched from database
    stats = {
        'total_users': 1000,  # 예시 데이터
        'language_distribution': {
            'ko': {'users': 850, 'percentage': 85.0},
            'en': {'users': 120, 'percentage': 12.0},
            'zh-hans': {'users': 30, 'percentage': 3.0}
        },
        'recent_activity': {
            'daily_language_switches': 45,
            'most_popular_language': 'ko',
            'growing_language': 'zh-hans'
        }
    }
    
    return JsonResponse(stats)

class LanguageMiddleware:
    """
    언어 감지 및 설정을 위한 커스텀 미들웨어
    Custom middleware for language detection and setting
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # 요청 전 처리
        self.process_request(request)
        
        response = self.get_response(request)
        
        # 응답 후 처리
        return self.process_response(request, response)
    
    def process_request(self, request):
        """
        요청 처리 전 언어 설정
        Set language before processing request
        """
        # URL에서 언어 코드 확인
        if hasattr(request, 'resolver_match') and request.resolver_match:
            if 'lang' in request.GET:
                lang_code = request.GET['lang']
                if lang_code in dict(settings.LANGUAGES):
                    translation.activate(lang_code)
                    request.LANGUAGE_CODE = lang_code
                    return
        
        # 세션에서 언어 확인
        if hasattr(request, 'session'):
            lang_code = request.session.get(translation.LANGUAGE_SESSION_KEY)
            if lang_code and lang_code in dict(settings.LANGUAGES):
                translation.activate(lang_code)
                request.LANGUAGE_CODE = lang_code
                return
        
        # 쿠키에서 언어 확인
        lang_code = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        if lang_code and lang_code in dict(settings.LANGUAGES):
            translation.activate(lang_code)
            request.LANGUAGE_CODE = lang_code
            return
        
        # Accept-Language 헤더에서 언어 확인
        if hasattr(request, 'META'):
            accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
            if accept_language:
                for lang_entry in accept_language.split(','):
                    lang_code = lang_entry.strip().split(';')[0].strip()
                    
                    # 정확한 매칭
                    if lang_code in dict(settings.LANGUAGES):
                        translation.activate(lang_code)
                        request.LANGUAGE_CODE = lang_code
                        return
                    
                    # 부분 매칭
                    primary_lang = lang_code.split('-')[0]
                    if primary_lang in dict(settings.LANGUAGES):
                        translation.activate(primary_lang)
                        request.LANGUAGE_CODE = primary_lang
                        return
        
        # 기본 언어 설정
        translation.activate(settings.LANGUAGE_CODE)
        request.LANGUAGE_CODE = settings.LANGUAGE_CODE
    
    def process_response(self, request, response):
        """
        응답 처리 후 언어 정보 추가
        Add language information after processing response
        """
        if hasattr(request, 'LANGUAGE_CODE'):
            response['Content-Language'] = request.LANGUAGE_CODE
        
        return response