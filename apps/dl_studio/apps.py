from django.apps import AppConfig


class DlStudioConfig(AppConfig):
    """Configuration for the Deep Learning Studio module."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dl_studio'
    verbose_name = 'Deep Learning Studio'
