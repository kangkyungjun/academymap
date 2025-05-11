from django.urls import path
from .views import AcademyListView, FilteredAcademyView

urlpatterns = [
    path('academies/', AcademyListView.as_view(), name='academy_list'),
    path('filtered_academies/', FilteredAcademyView.as_view(), name='filtered_academies'),
]
