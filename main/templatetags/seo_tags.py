"""
SEO 최적화 템플릿 태그
"""

from django import template
from django.utils.safestring import mark_safe
from django.conf import settings
import json

try:
    from ..seo_services import SEOMetadataService
except ImportError:
    SEOMetadataService = None

register = template.Library()


@register.simple_tag(takes_context=True)
def seo_meta_tags(context, academy=None):
    """SEO 메타 태그 렌더링"""
    request = context.get('request')
    if not request:
        return ''
    
    try:
        # 경로별 메타데이터 조회
        path = request.path
        metadata = None
        
        if SEOMetadataService:
            if academy:
                # 학원 상세 페이지
                metadata = SEOMetadataService.create_academy_metadata(academy)
            else:
                # 일반 페이지
                metadata = SEOMetadataService.get_metadata(path)
        
        # 기본 메타데이터
        if not metadata:
            metadata = {
                'title': 'AcademyMap - 전국 학원 정보',
                'description': '전국 학원 정보를 한 곳에서 확인하세요. 지역별, 과목별 학원 검색과 수강료 비교.',
                'keywords': '학원, 교육, 수강료, 위치, 학원 검색'
            }
        
        # HTML 메타 태그 생성
        tags = []
        
        # 기본 메타 태그
        tags.append(f'<title>{metadata.get("title", "")}</title>')
        tags.append(f'<meta name="description" content="{metadata.get("description", "")}">')
        tags.append(f'<meta name="keywords" content="{metadata.get("keywords", "")}">')
        
        # Open Graph 태그
        og_title = metadata.get('og_title', metadata.get('title', ''))
        og_description = metadata.get('og_description', metadata.get('description', ''))
        og_image = metadata.get('og_image', f'{settings.SITE_URL}/static/images/og-image.jpg')
        
        tags.extend([
            f'<meta property="og:title" content="{og_title}">',
            f'<meta property="og:description" content="{og_description}">',
            f'<meta property="og:image" content="{og_image}">',
            f'<meta property="og:url" content="{request.build_absolute_uri()}">',
            '<meta property="og:type" content="website">',
            '<meta property="og:site_name" content="AcademyMap">',
        ])
        
        # Twitter Card 태그
        twitter_title = metadata.get('twitter_title', metadata.get('title', ''))
        twitter_description = metadata.get('twitter_description', metadata.get('description', ''))
        twitter_image = metadata.get('twitter_image', og_image)
        
        tags.extend([
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:title" content="{twitter_title}">',
            f'<meta name="twitter:description" content="{twitter_description}">',
            f'<meta name="twitter:image" content="{twitter_image}">',
        ])
        
        # 기타 메타 태그
        tags.extend([
            '<meta name="robots" content="index, follow">',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '<meta charset="UTF-8">',
            f'<link rel="canonical" href="{request.build_absolute_uri()}">',
        ])
        
        return mark_safe('\n'.join(tags))
        
    except Exception as e:
        # 오류 시 기본 태그만 반환
        return mark_safe(f'''
            <title>AcademyMap - 전국 학원 정보</title>
            <meta name="description" content="전국 학원 정보를 한 곳에서 확인하세요.">
            <meta name="keywords" content="학원, 교육, 수강료">
        ''')


@register.simple_tag(takes_context=True)
def structured_data(context, academy=None):
    """구조화된 데이터 (JSON-LD) 렌더링"""
    request = context.get('request')
    if not request:
        return ''
    
    try:
        schema_data = None
        
        if academy and SEOMetadataService:
            # 학원 상세 페이지 구조화된 데이터
            metadata = SEOMetadataService.create_academy_metadata(academy)
            schema_data = metadata.get('schema_data')
        
        if not schema_data:
            # 기본 웹사이트 구조화된 데이터
            schema_data = {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": "AcademyMap",
                "url": settings.SITE_URL,
                "description": "전국 학원 정보 검색 서비스",
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": f"{settings.SITE_URL}/search?q={{search_term_string}}",
                    "query-input": "required name=search_term_string"
                }
            }
        
        json_ld = json.dumps(schema_data, ensure_ascii=False, indent=2)
        return mark_safe(f'<script type="application/ld+json">\n{json_ld}\n</script>')
        
    except Exception as e:
        return ''


@register.simple_tag
def breadcrumb_schema(items):
    """빵부스러기 구조화된 데이터"""
    try:
        if not items:
            return ''
        
        list_items = []
        for i, item in enumerate(items, 1):
            list_items.append({
                "@type": "ListItem",
                "position": i,
                "name": item['name'],
                "item": item.get('url', '')
            })
        
        schema_data = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": list_items
        }
        
        json_ld = json.dumps(schema_data, ensure_ascii=False, indent=2)
        return mark_safe(f'<script type="application/ld+json">\n{json_ld}\n</script>')
        
    except Exception:
        return ''


@register.simple_tag
def local_business_schema(academy):
    """지역 비즈니스 구조화된 데이터"""
    try:
        if not academy:
            return ''
        
        schema_data = {
            "@context": "https://schema.org",
            "@type": "EducationalOrganization",
            "name": academy.상호명,
            "address": {
                "@type": "PostalAddress",
                "streetAddress": academy.도로명주소 or academy.지번주소,
                "addressLocality": academy.시군구명,
                "addressRegion": academy.시도명,
                "addressCountry": "KR"
            },
            "url": f"{settings.SITE_URL}/academy/{academy.id}",
        }
        
        # 전화번호 추가
        if academy.전화번호:
            schema_data["telephone"] = academy.전화번호
        
        # 좌표 추가
        if academy.경도 and academy.위도:
            schema_data["geo"] = {
                "@type": "GeoCoordinates",
                "latitude": academy.위도,
                "longitude": academy.경도
            }
        
        # 평점 추가
        if academy.별점 and academy.별점 > 0:
            schema_data["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": academy.별점,
                "bestRating": 5
            }
        
        json_ld = json.dumps(schema_data, ensure_ascii=False, indent=2)
        return mark_safe(f'<script type="application/ld+json">\n{json_ld}\n</script>')
        
    except Exception:
        return ''


@register.simple_tag
def faq_schema(faq_list):
    """FAQ 구조화된 데이터"""
    try:
        if not faq_list:
            return ''
        
        main_entities = []
        for faq in faq_list:
            main_entities.append({
                "@type": "Question",
                "name": faq.get('question', ''),
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": faq.get('answer', '')
                }
            })
        
        schema_data = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": main_entities
        }
        
        json_ld = json.dumps(schema_data, ensure_ascii=False, indent=2)
        return mark_safe(f'<script type="application/ld+json">\n{json_ld}\n</script>')
        
    except Exception:
        return ''


@register.filter
def truncate_seo_title(title, length=60):
    """SEO 제목 길이 제한"""
    if len(title) <= length:
        return title
    return title[:length-3] + '...'


@register.filter
def truncate_seo_description(description, length=160):
    """SEO 설명 길이 제한"""
    if len(description) <= length:
        return description
    return description[:length-3] + '...'


@register.inclusion_tag('seo/meta_tags.html', takes_context=True)
def render_meta_tags(context, academy=None):
    """메타 태그 템플릿 렌더링"""
    request = context.get('request')
    metadata = {}
    
    if request and SEOMetadataService:
        if academy:
            metadata = SEOMetadataService.create_academy_metadata(academy)
        else:
            metadata = SEOMetadataService.get_metadata(request.path) or {}
    
    return {
        'metadata': metadata,
        'request': request,
        'academy': academy,
    }