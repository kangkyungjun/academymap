"""
학원 운영자 대시보드 뷰
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.forms.models import model_to_dict
import json

try:
    from .models import Data as Academy
    from .operator_models import (
        AcademyOwner, OperatorDashboardSettings, AcademyInquiry, 
        AcademyPromotion, RevenueTracking
    )
    from .operator_services import OperatorDashboardService, OperatorPermissionService
    from .academy_enhancements import AcademyDetailInfo, AcademyStatistics
except ImportError:
    # Handle import errors during setup
    pass


@login_required
def operator_dashboard(request):
    """운영자 대시보드 메인 페이지"""
    try:
        # 사용자가 관리하는 학원 목록
        managed_academies = OperatorPermissionService.get_user_academies(request.user)
        
        if not managed_academies:
            # 학원 등록 또는 관리자 승인 대기 상태
            return render(request, 'main/operator/no_academy.html', {
                'user': request.user,
                'has_pending_requests': AcademyOwner.objects.filter(
                    user=request.user, 
                    is_verified=False
                ).exists()
            })
        
        # 기본 선택된 학원 (첫 번째 학원 또는 요청된 학원)
        selected_academy_id = request.GET.get('academy_id')
        if selected_academy_id:
            try:
                selected_academy = Academy.objects.get(
                    id=selected_academy_id,
                    id__in=[a.id for a in managed_academies]
                )
            except Academy.DoesNotExist:
                selected_academy = managed_academies[0]
        else:
            selected_academy = managed_academies[0]
        
        # 대시보드 데이터 수집
        overview = OperatorDashboardService.get_academy_overview(selected_academy, request.user)
        visitor_analytics = OperatorDashboardService.get_visitor_analytics(selected_academy, days=7)
        inquiry_summary = OperatorDashboardService.get_inquiry_summary(selected_academy)
        promotion_performance = OperatorDashboardService.get_promotion_performance(selected_academy)
        
        # 사용자 권한 확인
        permissions = OperatorPermissionService.get_user_permissions(request.user, selected_academy)
        
        context = {
            'managed_academies': managed_academies,
            'selected_academy': selected_academy,
            'overview': overview,
            'visitor_analytics': visitor_analytics,
            'inquiry_summary': inquiry_summary,
            'promotion_performance': promotion_performance,
            'permissions': permissions,
            'current_time': timezone.now(),
        }
        
        return render(request, 'main/operator/dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f'대시보드 로드 중 오류가 발생했습니다: {str(e)}')
        return render(request, 'main/operator/error.html', {'error': str(e)})


@login_required
def academy_analytics(request, academy_id):
    """학원 상세 분석 페이지"""
    try:
        academy = get_object_or_404(Academy, id=academy_id)
        
        # 권한 확인
        if not OperatorPermissionService.can_manage_academy(request.user, academy):
            return HttpResponseForbidden("이 학원을 관리할 권한이 없습니다.")
        
        permissions = OperatorPermissionService.get_user_permissions(request.user, academy)
        if not permissions['can_view_analytics']:
            return HttpResponseForbidden("분석 데이터를 볼 권한이 없습니다.")
        
        # 분석 기간 설정
        days = int(request.GET.get('days', 30))
        if days not in [7, 14, 30, 90]:
            days = 30
        
        # 분석 데이터 수집
        visitor_analytics = OperatorDashboardService.get_visitor_analytics(academy, days)
        competitor_insights = OperatorDashboardService.get_competitor_insights(academy)
        weekly_report = OperatorDashboardService.generate_weekly_report(academy)
        
        context = {
            'academy': academy,
            'visitor_analytics': visitor_analytics,
            'competitor_insights': competitor_insights,
            'weekly_report': weekly_report,
            'selected_period': days,
            'permissions': permissions,
        }
        
        return render(request, 'main/operator/analytics.html', context)
        
    except Exception as e:
        messages.error(request, f'분석 데이터 로드 중 오류: {str(e)}')
        return redirect('operator_dashboard')


@login_required
def inquiry_management(request, academy_id):
    """문의 관리 페이지"""
    try:
        academy = get_object_or_404(Academy, id=academy_id)
        
        # 권한 확인
        if not OperatorPermissionService.can_manage_academy(request.user, academy):
            return HttpResponseForbidden("이 학원을 관리할 권한이 없습니다.")
        
        # 필터링 옵션
        status_filter = request.GET.get('status', 'all')
        type_filter = request.GET.get('type', 'all')
        search_query = request.GET.get('search', '')
        
        # 문의 목록 조회
        inquiries = AcademyInquiry.objects.filter(academy=academy)
        
        if status_filter != 'all':
            inquiries = inquiries.filter(status=status_filter)
        
        if type_filter != 'all':
            inquiries = inquiries.filter(inquiry_type=type_filter)
        
        if search_query:
            inquiries = inquiries.filter(
                Q(subject__icontains=search_query) |
                Q(content__icontains=search_query) |
                Q(inquirer_name__icontains=search_query)
            )
        
        inquiries = inquiries.order_by('-created_at')
        
        # 페이지네이션
        paginator = Paginator(inquiries, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # 문의 현황 요약
        inquiry_summary = OperatorDashboardService.get_inquiry_summary(academy)
        
        context = {
            'academy': academy,
            'inquiries': page_obj,
            'inquiry_summary': inquiry_summary,
            'status_filter': status_filter,
            'type_filter': type_filter,
            'search_query': search_query,
            'inquiry_types': AcademyInquiry.INQUIRY_TYPE_CHOICES,
            'status_choices': AcademyInquiry.STATUS_CHOICES,
        }
        
        return render(request, 'main/operator/inquiries.html', context)
        
    except Exception as e:
        messages.error(request, f'문의 관리 페이지 로드 중 오류: {str(e)}')
        return redirect('operator_dashboard')


@login_required
@require_http_methods(["POST"])
def respond_to_inquiry(request, inquiry_id):
    """문의 응답 처리"""
    try:
        inquiry = get_object_or_404(AcademyInquiry, id=inquiry_id)
        
        # 권한 확인
        if not OperatorPermissionService.can_manage_academy(request.user, inquiry.academy):
            return JsonResponse({'error': '권한이 없습니다.'}, status=403)
        
        permissions = OperatorPermissionService.get_user_permissions(request.user, inquiry.academy)
        if not permissions['can_respond_reviews']:
            return JsonResponse({'error': '문의 응답 권한이 없습니다.'}, status=403)
        
        response_content = request.POST.get('response', '').strip()
        if not response_content:
            return JsonResponse({'error': '응답 내용을 입력해주세요.'}, status=400)
        
        # 응답 저장
        inquiry.response = response_content
        inquiry.responded_by = request.user
        inquiry.responded_at = timezone.now()
        inquiry.status = 'answered'
        inquiry.save()
        
        return JsonResponse({
            'success': True,
            'message': '응답이 저장되었습니다.',
            'inquiry': {
                'id': inquiry.id,
                'status': inquiry.status,
                'response': inquiry.response,
                'responded_at': inquiry.responded_at.isoformat() if inquiry.responded_at else None,
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': f'응답 처리 중 오류: {str(e)}'}, status=500)


@login_required
def promotion_management(request, academy_id):
    """프로모션 관리 페이지"""
    try:
        academy = get_object_or_404(Academy, id=academy_id)
        
        # 권한 확인
        if not OperatorPermissionService.can_manage_academy(request.user, academy):
            return HttpResponseForbidden("이 학원을 관리할 권한이 없습니다.")
        
        permissions = OperatorPermissionService.get_user_permissions(request.user, academy)
        if not permissions['can_manage_content']:
            return HttpResponseForbidden("콘텐츠 관리 권한이 없습니다.")
        
        # 프로모션 목록
        promotions = AcademyPromotion.objects.filter(academy=academy).order_by('-created_at')
        
        # 프로모션 성과
        promotion_performance = OperatorDashboardService.get_promotion_performance(academy)
        
        context = {
            'academy': academy,
            'promotions': promotions,
            'promotion_performance': promotion_performance,
            'promotion_types': AcademyPromotion.PROMOTION_TYPE_CHOICES,
            'permissions': permissions,
        }
        
        return render(request, 'main/operator/promotions.html', context)
        
    except Exception as e:
        messages.error(request, f'프로모션 관리 페이지 로드 중 오류: {str(e)}')
        return redirect('operator_dashboard')


@login_required
@require_http_methods(["POST"])
def create_promotion(request, academy_id):
    """프로모션 생성"""
    try:
        academy = get_object_or_404(Academy, id=academy_id)
        
        # 권한 확인
        if not OperatorPermissionService.can_manage_academy(request.user, academy):
            return JsonResponse({'error': '권한이 없습니다.'}, status=403)
        
        permissions = OperatorPermissionService.get_user_permissions(request.user, academy)
        if not permissions['can_manage_content']:
            return JsonResponse({'error': '콘텐츠 관리 권한이 없습니다.'}, status=403)
        
        # 프로모션 데이터 검증
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        promotion_type = request.POST.get('promotion_type', '')
        start_date = request.POST.get('start_date', '')
        end_date = request.POST.get('end_date', '')
        
        if not all([title, description, promotion_type, start_date, end_date]):
            return JsonResponse({'error': '필수 정보를 모두 입력해주세요.'}, status=400)
        
        # 프로모션 생성
        promotion = AcademyPromotion.objects.create(
            academy=academy,
            title=title,
            description=description,
            promotion_type=promotion_type,
            start_date=start_date,
            end_date=end_date,
            discount_rate=request.POST.get('discount_rate') or None,
            discount_amount=request.POST.get('discount_amount') or None,
            max_participants=request.POST.get('max_participants') or None,
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': '프로모션이 생성되었습니다.',
            'promotion_id': promotion.id
        })
        
    except Exception as e:
        return JsonResponse({'error': f'프로모션 생성 중 오류: {str(e)}'}, status=500)


@login_required
def academy_info_edit(request, academy_id):
    """학원 정보 수정 페이지"""
    try:
        academy = get_object_or_404(Academy, id=academy_id)
        
        # 권한 확인
        if not OperatorPermissionService.can_manage_academy(request.user, academy):
            return HttpResponseForbidden("이 학원을 관리할 권한이 없습니다.")
        
        permissions = OperatorPermissionService.get_user_permissions(request.user, academy)
        if not permissions['can_edit_info']:
            return HttpResponseForbidden("정보 수정 권한이 없습니다.")
        
        # 상세 정보 가져오기 또는 생성
        detail_info, created = AcademyDetailInfo.objects.get_or_create(academy=academy)
        
        if request.method == 'POST':
            try:
                # 기본 정보 업데이트
                academy.전화번호 = request.POST.get('phone', academy.전화번호)
                academy.영업시간 = request.POST.get('operating_hours', academy.영업시간)
                academy.소개글 = request.POST.get('description', academy.소개글)
                academy.save()
                
                # 상세 정보 업데이트
                detail_info.total_classrooms = request.POST.get('total_classrooms') or None
                detail_info.total_teachers = request.POST.get('total_teachers') or None
                detail_info.max_students_per_class = request.POST.get('max_students_per_class') or None
                detail_info.website_url = request.POST.get('website_url', detail_info.website_url)
                
                # 시설 정보 업데이트 (체크박스)
                facilities = []
                for facility_code, facility_name in AcademyDetailInfo.FACILITY_CHOICES:
                    if request.POST.get(f'facility_{facility_code}'):
                        facilities.append(facility_code)
                detail_info.facilities = facilities
                
                detail_info.save()
                
                messages.success(request, '학원 정보가 성공적으로 업데이트되었습니다.')
                return redirect('academy_info_edit', academy_id=academy_id)
                
            except Exception as e:
                messages.error(request, f'정보 업데이트 중 오류가 발생했습니다: {str(e)}')
        
        context = {
            'academy': academy,
            'detail_info': detail_info,
            'permissions': permissions,
            'facility_choices': AcademyDetailInfo.FACILITY_CHOICES,
            'current_facilities': detail_info.facilities or [],
        }
        
        return render(request, 'main/operator/edit_info.html', context)
        
    except Exception as e:
        messages.error(request, f'정보 수정 페이지 로드 중 오류: {str(e)}')
        return redirect('operator_dashboard')


@login_required
def api_academy_stats(request, academy_id):
    """학원 통계 API (차트 데이터용)"""
    try:
        academy = get_object_or_404(Academy, id=academy_id)
        
        # 권한 확인
        if not OperatorPermissionService.can_manage_academy(request.user, academy):
            return JsonResponse({'error': '권한이 없습니다.'}, status=403)
        
        permissions = OperatorPermissionService.get_user_permissions(request.user, academy)
        if not permissions['can_view_analytics']:
            return JsonResponse({'error': '분석 조회 권한이 없습니다.'}, status=403)
        
        days = int(request.GET.get('days', 30))
        analytics = OperatorDashboardService.get_visitor_analytics(academy, days)
        
        return JsonResponse({
            'success': True,
            'data': analytics
        })
        
    except Exception as e:
        return JsonResponse({'error': f'통계 조회 중 오류: {str(e)}'}, status=500)