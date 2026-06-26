from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.report_list, name='list'),
    path('generate/', views.generate_report_view, name='generate'),
    path('<int:pk>/download/', views.report_download, name='download'),
    path('<int:pk>/delete/', views.report_delete, name='delete'),
]
