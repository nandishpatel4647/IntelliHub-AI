"""
IntelliHub AI — ML Studio URL Configuration
==============================================
Maps URL patterns to ML Studio views.
"""

from django.urls import path

from . import views

app_name = 'ml_studio'

urlpatterns = [
    path('', views.ml_studio_home, name='home'),
    path('train/', views.train_model, name='train'),
    path('<int:pk>/', views.model_detail, name='detail'),
    path('<int:pk>/predict/', views.predict_view, name='predict'),
    path('<int:pk>/delete/', views.delete_model, name='delete'),
    path('compare/', views.compare_models, name='compare'),
]
