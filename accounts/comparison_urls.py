from django.urls import path
from . import comparison_views

urlpatterns = [
    # 비교 관리
    path('comparisons/', comparison_views.comparison_list_create, name='comparison-list-create'),
    path('comparisons/<int:pk>/', comparison_views.comparison_detail, name='comparison-detail'),
    path('comparisons/quick/', comparison_views.quick_comparison, name='quick-comparison'),
    path('comparisons/stats/', comparison_views.comparison_stats, name='comparison-stats'),
    
    # 비교 공유
    path('comparisons/<int:pk>/share/', comparison_views.share_comparison, name='share-comparison'),
    path('comparisons/shared/<int:pk>/', comparison_views.shared_comparison_detail, name='shared-comparison-detail'),
    
    # 비교 내보내기
    path('comparisons/<int:pk>/export/', comparison_views.export_comparison, name='export-comparison'),
    
    # 비교 템플릿
    path('comparison-templates/', comparison_views.comparison_template_list_create, name='comparison-template-list-create'),
    path('comparison-templates/<int:pk>/', comparison_views.comparison_template_detail, name='comparison-template-detail'),
    path('comparison-templates/<int:template_id>/create-comparison/', comparison_views.create_comparison_from_template, name='create-comparison-from-template'),
    
    # 비교 기록
    path('comparison-history/', comparison_views.comparison_history, name='comparison-history'),
]