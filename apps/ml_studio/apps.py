"""
IntelliHub AI — ML Studio App Configuration
=============================================
Django application config for the Machine Learning Studio module.
"""

from django.apps import AppConfig


class MlStudioConfig(AppConfig):
    """Configuration class for the ML Studio application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ml_studio'
    verbose_name = 'ML Studio'
