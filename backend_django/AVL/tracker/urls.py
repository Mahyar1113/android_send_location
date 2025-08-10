from django.urls import path
from . import views

urlpatterns = [
    path('api/receive_location/', views.receive_location, name='receive_location'),
    path('start_recording/', views.start_recording, name='start_recording'),
    path('stop_recording/', views.stop_recording, name='stop_recording'),
    path('', views.map_view, name='map_view'),
]