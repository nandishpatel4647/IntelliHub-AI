"""IntelliHub AI — EDA URL Configuration."""

from django.urls import path
from . import views

app_name = 'eda'

urlpatterns = [
    path('', views.eda_home, name='home'),
    path('<int:dataset_pk>/', views.eda_dashboard, name='dashboard'),
    path('<int:dataset_pk>/chart/', views.generate_chart, name='generate_chart'),
]
