"""IntelliHub AI — Cleaning URL Configuration."""

from django.urls import path
from . import views

app_name = 'cleaning'

urlpatterns = [
    path('', views.cleaning_home, name='home'),
    path('<int:dataset_pk>/recommendations/', views.get_cleaning_recommendations, name='recommendations'),
    path('<int:dataset_pk>/auto-clean/', views.auto_clean, name='auto_clean'),
    path('<int:dataset_pk>/manual-clean/', views.manual_clean, name='manual_clean'),
]
