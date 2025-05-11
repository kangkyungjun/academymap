from django.urls import path
from .views import AcademyListAPIView

urlpatterns = [
    path('academies/', AcademyListAPIView.as_view(), name='academy_list'),
]
