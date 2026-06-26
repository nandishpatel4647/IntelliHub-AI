"""
IntelliHub AI — Accounts App Configuration
=============================================
Django application configuration for the user accounts module.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration class for the Accounts application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'User Accounts'
