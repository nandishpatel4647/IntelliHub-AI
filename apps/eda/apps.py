from django.apps import AppConfig


class EdaConfig(AppConfig):
    """Configuration for the EDA & Visualization module."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.eda'
    verbose_name = 'EDA & Visualization'
