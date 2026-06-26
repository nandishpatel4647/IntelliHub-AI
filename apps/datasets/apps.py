"""
IntelliHub AI — Dataset Manager App Configuration
====================================================
Registers the Dataset Manager module with Django.
"""

from django.apps import AppConfig


class DatasetConfig(AppConfig):
    """Django application configuration for the Dataset Manager module."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.datasets'
    verbose_name = 'Dataset Manager'
