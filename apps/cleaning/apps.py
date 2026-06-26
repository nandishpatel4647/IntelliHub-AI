from django.apps import AppConfig


class CleaningConfig(AppConfig):
    """Configuration for the AI Data Cleaning module."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cleaning'
    verbose_name = 'AI Data Cleaning'
