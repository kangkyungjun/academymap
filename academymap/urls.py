"""
URL configuration for academymap project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
import main.views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('main', main.views.main, name='main'),
    path('academy/<int:pk>', main.views.academy, name='academy'),
    path('academy_list', main.views.academy_list, name='academy_list'),
    path('search', main.views.search, name='search'),
    path('get_regions', main.views.get_regions, name='get_regions'),

    path('map', main.views.map, name='map'),
    path('api/filtered_academies', main.views.filtered_academies, name='filtered_academies'),


    path('data_update', main.views.data_update, name='data_update'),
]
