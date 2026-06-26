"""IntelliHub AI — DL Studio URL Configuration."""

from django.urls import path
from . import views

app_name = 'dl_studio'

urlpatterns = [
    path('', views.dl_studio_home, name='home'),
    path('train/', views.train_dl_model, name='train'),
    path('<int:pk>/', views.dl_model_detail, name='detail'),
]
