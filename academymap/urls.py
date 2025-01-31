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

    path('', main.views.map, name='map'),
    path('api/filtered_academies', main.views.filtered_academies, name='filtered_academies'),

    # 학원 관리 페이지 관련 URL 추가
    path('manage/', main.views.manage, name='manage'),
    path('manage/add/', main.views.add_academy, name='add_academy'),
    path('manage/modify/<int:pk>/', main.views.modify_academy, name='modify_academy'),
    path('manage/delete/<int:pk>/', main.views.delete_academy, name='delete_academy'),

    # 전체 데이터 업로드 시 사용
    path('data_update', main.views.data_update, name='data_update'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)