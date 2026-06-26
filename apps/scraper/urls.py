from django.urls import path
from . import views

app_name = 'scraper'

urlpatterns = [
    path('', views.scraper_home, name='home'),
    path('start/', views.start_scrape, name='start'),
    path('<int:pk>/', views.scrape_detail, name='detail'),
    path('<int:pk>/download/', views.download_scrape, name='download'),
    path('<int:pk>/delete/', views.delete_scrape, name='delete'),
]
