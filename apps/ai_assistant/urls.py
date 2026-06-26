from django.urls import path
from . import views

app_name = 'ai_assistant'

urlpatterns = [
    path('', views.chat_home, name='home'),
    path('<int:session_pk>/', views.chat_session_view, name='session'),
    path('send/', views.send_message, name='send_message'),
    path('new/', views.new_session, name='new_session'),
    path('<int:session_pk>/delete/', views.delete_session, name='delete_session'),
]
