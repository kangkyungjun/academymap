from django.urls import path
from . import review_views

urlpatterns = [
    # 리뷰 관리
    path('reviews/', review_views.review_list_create, name='review-list-create'),
    path('reviews/<int:pk>/', review_views.review_detail, name='review-detail'),
    path('reviews/my/', review_views.my_reviews, name='my-reviews'),
    path('reviews/summary/', review_views.review_summary, name='review-summary'),
    
    # 리뷰 평가 및 신고
    path('reviews/<int:pk>/helpful/', review_views.review_helpful, name='review-helpful'),
    path('reviews/<int:pk>/report/', review_views.review_report, name='review-report'),
    
    # 리뷰 이미지
    path('reviews/<int:pk>/images/', review_views.review_image_upload, name='review-image-upload'),
    path('reviews/<int:pk>/images/<int:image_id>/', review_views.review_image_delete, name='review-image-delete'),
    
    # 학원별 리뷰 통계
    path('academies/<int:academy_id>/reviews/stats/', review_views.academy_review_stats, name='academy-review-stats'),
]