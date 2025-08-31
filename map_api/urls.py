from django.urls import path
from .views import AcademyListView, FilteredAcademyView, ClusterView

urlpatterns = [
    path('academies/', AcademyListView.as_view(), name='academy_list'),
    path('filtered_academies/', FilteredAcademyView.as_view(), name='filtered_academies'),
    path('clusters/', ClusterView.as_view(), name='clusters'),
]
