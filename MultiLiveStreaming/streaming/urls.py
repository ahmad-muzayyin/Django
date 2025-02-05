from django.urls import path
from . import views  
from .views import logout_view, video_list

urlpatterns = [
    # path('', views.index, name='index'),
    path('add-video/', views.add_video, name='add_video'),
    path('live-list/', views.live_list, name='live_list'),
    path('stop-live/<int:live_id>/', views.stop_live, name='stop_live'),
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', logout_view, name='logout'),
    path('daftar-video/', views.daftar_video, name='daftar_video'),
    path('edit_video/<int:id>/', views.edit_video, name='edit_video'),
    path('delete_video/<int:id>/', views.delete_video, name='delete_video'),
    path('start_live/<int:id>/', views.start_live, name='start_live'),
    path('start_live_streaming/<int:id>/', views.start_live_streaming, name='start_live_streaming'),
    path('edit_schedule/<int:id>/', views.edit_schedule, name='edit_schedule'),
    path('videos/', video_list, name='video_list'),
]
