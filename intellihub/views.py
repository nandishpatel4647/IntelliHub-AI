"""
IntelliHub AI — Custom Error Handlers
=======================================
Branded 404 and 500 error pages.
"""

from django.shortcuts import render


def handler404(request, exception):
    """Custom 404 — Page Not Found with IntelliHub branding."""
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    """Custom 500 — Server Error with IntelliHub branding."""
    return render(request, 'errors/500.html', status=500)
