"""
IntelliHub AI — Dataset Manager URL Configuration
===================================================
Maps URL patterns to dataset views.
"""

from django.urls import path

from . import views

app_name = 'datasets'

urlpatterns = [
    path('', views.dataset_list, name='list'),
    path('upload/', views.upload_dataset, name='upload'),
    path('<int:pk>/', views.dataset_detail, name='detail'),
    path('<int:pk>/delete/', views.dataset_delete, name='delete'),
    path('<int:pk>/favorite/', views.dataset_toggle_favorite, name='toggle_favorite'),
]
