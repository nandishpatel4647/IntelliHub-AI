"""
IntelliHub AI — Root URL Configuration
========================================
Maps all app modules to their URL namespaces.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    # Root redirect → dashboard (or login if not authenticated)
    path('', lambda request: redirect('dashboard:home')),

    # App modules (in navigation order)
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
    path('datasets/', include('apps.datasets.urls', namespace='datasets')),
    path('cleaning/', include('apps.cleaning.urls', namespace='cleaning')),
    path('eda/', include('apps.eda.urls', namespace='eda')),
    path('ml-studio/', include('apps.ml_studio.urls', namespace='ml_studio')),
    path('dl-studio/', include('apps.dl_studio.urls', namespace='dl_studio')),
    path('ai-assistant/', include('apps.ai_assistant.urls', namespace='ai_assistant')),
    path('scraper/', include('apps.scraper.urls', namespace='scraper')),
    path('api/', include('apps.api_center.urls', namespace='api_center')),
    path('reports/', include('apps.reports.urls', namespace='reports')),
    path('admin-panel/', include('apps.admin_panel.urls', namespace='admin_panel')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers
handler404 = 'intellihub.views.handler404'
handler500 = 'intellihub.views.handler500'
