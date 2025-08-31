"""
데이터 분석 및 리포팅 REST API ViewSets
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q
from datetime import datetime, timedelta
import json
import csv
import io

try:
    from .analytics_models import (
        AnalyticsReport, UserAnalytics, AcademyAnalytics,
        RegionalAnalytics, MarketTrend, ConversionFunnel, CustomDashboard
    )
    from .analytics_serializers import (
        AnalyticsReportSerializer, AnalyticsReportCreateSerializer,
        UserAnalyticsSerializer, AcademyAnalyticsSerializer,
        RegionalAnalyticsSerializer, MarketTrendSerializer,
        ConversionFunnelSerializer, CustomDashboardSerializer,
        CustomDashboardCreateSerializer, AnalyticsSummarySerializer,
        AnalyticsChartDataSerializer, AnalyticsFilterSerializer,
        ExportDataSerializer
    )
    from .analytics_services import AnalyticsDataService, AnalyticsReportService
    from .models import Data as Academy
except ImportError:
    # 마이그레이션 중이거나 모델이 아직 생성되지 않은 경우
    pass


class AnalyticsReportViewSet(viewsets.ModelViewSet):
    """분석 리포트 ViewSet"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AnalyticsReportCreateSerializer
        return AnalyticsReportSerializer
    
    def get_queryset(self):
        """사용자별 리포트 필터링"""
        queryset = AnalyticsReport.objects.all()
        
        # 공개 리포트 또는 본인이 생성한 리포트만 조회
        queryset = queryset.filter(
            Q(is_public=True) | Q(generated_by=self.request.user)
        )
        
        # 필터 파라미터
        report_type = self.request.query_params.get('type')
        category = self.request.query_params.get('category')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        if category:
            queryset = queryset.filter(category=category)
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)
        
        return queryset.order_by('-generated_at')
    
    def perform_create(self, serializer):
        """리포트 생성 시 생성자 설정 및 자동 데이터 수집"""
        try:
            # 리포트 서비스를 통한 생성
            service = AnalyticsReportService()
            report = service.generate_report(
                report_type=serializer.validated_data['report_type'],
                category=serializer.validated_data['category'],
                start_date=serializer.validated_data['start_date'],
                end_date=serializer.validated_data['end_date'],
                title=serializer.validated_data['title'],
                generated_by=self.request.user,
                is_public=serializer.validated_data.get('is_public', False)
            )
            serializer.instance = report
        except Exception as e:
            raise serializer.ValidationError(f'리포트 생성 중 오류가 발생했습니다: {e}')
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """분석 요약 정보"""
        try:
            today = timezone.now().date()
            
            # 오늘의 사용자 분석
            user_analytics = UserAnalytics.objects.filter(date=today).first()
            
            # 학원 통계
            academy_count = Academy.objects.count()
            
            # 최근 7일간 조회수
            week_ago = today - timedelta(days=7)
            total_views = AcademyAnalytics.objects.filter(
                date__gte=week_ago
            ).aggregate(total=Sum('views'))['total'] or 0
            
            # 전환율
            conversion_data = ConversionFunnel.objects.filter(date=today).first()
            conversion_rate = conversion_data.overall_conversion if conversion_data else 0
            
            # 상위 지역
            top_regions = RegionalAnalytics.objects.filter(
                date=today
            ).order_by('-total_views')[:5]
            
            # 최근 리포트 수
            recent_reports = AnalyticsReport.objects.filter(
                generated_at__gte=today - timedelta(days=7)
            ).count()
            
            summary_data = {
                'total_users': user_analytics.total_users if user_analytics else 0,
                'total_sessions': user_analytics.total_sessions if user_analytics else 0,
                'total_academies': academy_count,
                'total_views': total_views,
                'conversion_rate': conversion_rate,
                'top_regions': [
                    {'name': f'{r.region_sido} {r.region_sigungu}', 'views': r.total_views}
                    for r in top_regions
                ],
                'trending_subjects': [],  # TODO: 인기 과목 분석 구현
                'recent_reports_count': recent_reports
            }
            
            serializer = AnalyticsSummarySerializer(summary_data)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'error': f'요약 정보 조회 중 오류가 발생했습니다: {e}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """사용자 분석 ViewSet"""
    serializer_class = UserAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = UserAnalytics.objects.all()
        
        # 날짜 필터링
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.order_by('-date')
    
    @action(detail=False, methods=['get'])
    def chart_data(self, request):
        """차트용 데이터"""
        try:
            # 최근 30일 데이터
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
            
            data = self.get_queryset().filter(
                date__range=(start_date, end_date)
            ).order_by('date')
            
            chart_data = {
                'labels': [item.date.strftime('%Y-%m-%d') for item in data],
                'datasets': [
                    {
                        'label': '총 사용자',
                        'data': [item.total_users for item in data],
                        'borderColor': '#007bff',
                        'backgroundColor': 'rgba(0, 123, 255, 0.1)'
                    },
                    {
                        'label': '신규 사용자',
                        'data': [item.new_users for item in data],
                        'borderColor': '#28a745',
                        'backgroundColor': 'rgba(40, 167, 69, 0.1)'
                    }
                ]
            }
            
            serializer = AnalyticsChartDataSerializer(chart_data)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'error': f'차트 데이터 조회 중 오류가 발생했습니다: {e}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AcademyAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """학원 분석 ViewSet"""
    serializer_class = AcademyAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = AcademyAnalytics.objects.all()
        
        # 필터링
        academy_id = self.request.query_params.get('academy_id')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if academy_id:
            queryset = queryset.filter(academy_id=academy_id)
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.order_by('-date')
    
    @action(detail=False, methods=['get'])
    def top_academies(self, request):
        """상위 학원 목록"""
        try:
            # 최근 7일간 조회수 기준
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=7)
            
            top_academies = AcademyAnalytics.objects.filter(
                date__range=(start_date, end_date)
            ).values(
                'academy__id', 'academy__상호명'
            ).annotate(
                total_views=Sum('views'),
                total_inquiries=Sum('inquiries')
            ).order_by('-total_views')[:10]
            
            return Response(list(top_academies))
            
        except Exception as e:
            return Response(
                {'error': f'상위 학원 조회 중 오류가 발생했습니다: {e}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RegionalAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """지역 분석 ViewSet"""
    serializer_class = RegionalAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = RegionalAnalytics.objects.all()
        
        # 필터링
        sido = self.request.query_params.get('sido')
        sigungu = self.request.query_params.get('sigungu')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if sido:
            queryset = queryset.filter(region_sido=sido)
        if sigungu:
            queryset = queryset.filter(region_sigungu=sigungu)
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.order_by('-date', 'region_sido', 'region_sigungu')
    
    @action(detail=False, methods=['get'])
    def map_data(self, request):
        """지도용 지역 데이터"""
        try:
            # 최신 날짜의 데이터만
            latest_date = RegionalAnalytics.objects.aggregate(
                max_date=models.Max('date')
            )['max_date']
            
            if not latest_date:
                return Response([])
            
            data = RegionalAnalytics.objects.filter(
                date=latest_date
            ).values(
                'region_sido', 'region_sigungu', 
                'total_academies', 'total_views', 'avg_rating'
            )
            
            return Response(list(data))
            
        except Exception as e:
            return Response(
                {'error': f'지도 데이터 조회 중 오류가 발생했습니다: {e}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MarketTrendViewSet(viewsets.ReadOnlyModelViewSet):
    """시장 트렌드 ViewSet"""
    serializer_class = MarketTrendSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = MarketTrend.objects.all()
        
        # 필터링
        trend_type = self.request.query_params.get('trend_type')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if trend_type:
            queryset = queryset.filter(trend_type=trend_type)
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.order_by('-date', 'trend_type')


class ConversionFunnelViewSet(viewsets.ReadOnlyModelViewSet):
    """전환 퍼널 ViewSet"""
    serializer_class = ConversionFunnelSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = ConversionFunnel.objects.all()
        
        # 날짜 필터링
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.order_by('-date')
    
    @action(detail=False, methods=['get'])
    def funnel_chart(self, request):
        """퍼널 차트 데이터"""
        try:
            # 최신 데이터
            latest = self.get_queryset().first()
            
            if not latest:
                return Response({'error': '퍼널 데이터가 없습니다.'}, status=404)
            
            funnel_data = {
                'labels': ['방문자', '검색', '학원 조회', '상세 조회', '문의'],
                'data': [
                    latest.stage_1_visitors,
                    latest.stage_2_search,
                    latest.stage_3_view,
                    latest.stage_4_detail,
                    latest.stage_5_inquiry
                ]
            }
            
            return Response(funnel_data)
            
        except Exception as e:
            return Response(
                {'error': f'퍼널 차트 데이터 조회 중 오류가 발생했습니다: {e}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomDashboardViewSet(viewsets.ModelViewSet):
    """사용자 정의 대시보드 ViewSet"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CustomDashboardCreateSerializer
        return CustomDashboardSerializer
    
    def get_queryset(self):
        """사용자별 대시보드 필터링"""
        return CustomDashboard.objects.filter(
            Q(user=self.request.user) | 
            Q(shared_with=self.request.user)
        ).order_by('-is_default', 'name')
    
    def perform_create(self, serializer):
        """대시보드 생성 시 사용자 설정"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """기본 대시보드 설정"""
        try:
            dashboard = self.get_object()
            
            # 기존 기본 대시보드 해제
            CustomDashboard.objects.filter(
                user=request.user, is_default=True
            ).update(is_default=False)
            
            # 새 기본 대시보드 설정
            dashboard.is_default = True
            dashboard.save()
            
            return Response({'message': '기본 대시보드가 설정되었습니다.'})
            
        except Exception as e:
            return Response(
                {'error': f'기본 대시보드 설정 중 오류가 발생했습니다: {e}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnalyticsDataViewSet(viewsets.ViewSet):
    """분석 데이터 관리 ViewSet"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def export(self, request):
        """데이터 내보내기"""
        serializer = ExportDataSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data_type = serializer.validated_data['data_type']
            start_date = serializer.validated_data['start_date']
            end_date = serializer.validated_data['end_date']
            format_type = serializer.validated_data.get('format', 'csv')
            
            # 데이터 조회
            if data_type == 'user_analytics':
                data = UserAnalytics.objects.filter(
                    date__range=(start_date, end_date)
                )
                fields = ['date', 'total_users', 'new_users', 'returning_users']
                
            elif data_type == 'academy_analytics':
                data = AcademyAnalytics.objects.filter(
                    date__range=(start_date, end_date)
                )
                fields = ['date', 'academy__상호명', 'views', 'inquiries']
                
            else:
                return Response(
                    {'error': '지원하지 않는 데이터 유형입니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # CSV 형식으로 내보내기
            if format_type == 'csv':
                output = io.StringIO()
                writer = csv.writer(output)
                
                # 헤더
                writer.writerow(fields)
                
                # 데이터
                for item in data:
                    row = []
                    for field in fields:
                        if '__' in field:
                            value = getattr(item, field.split('__')[0])
                            value = getattr(value, field.split('__')[1])
                        else:
                            value = getattr(item, field)
                        row.append(value)
                    writer.writerow(row)
                
                return Response({
                    'data': output.getvalue(),
                    'filename': f'{data_type}_{start_date}_{end_date}.csv'
                })
            
            return Response(
                {'error': '지원하지 않는 형식입니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            return Response(
                {'error': f'데이터 내보내기 중 오류가 발생했습니다: {e}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )