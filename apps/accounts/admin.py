"""
IntelliHub AI — Accounts Admin Configuration
===============================================
Custom admin registration for the User model with
role, quota, and activity columns.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin view for IntelliHub User model.

    Extends Django's built-in UserAdmin to expose role-based fields,
    dataset quotas, and profile metadata in the admin interface.
    """

    list_display = (
        'username',
        'email',
        'role',
        'dataset_quota',
        'is_active',
        'date_joined',
    )
    list_filter = (
        'role',
        'is_active',
        'is_staff',
        'is_email_verified',
        'date_joined',
    )
    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
        'institution',
    )
    ordering = ('-date_joined',)

    # Extend the default UserAdmin fieldsets with IntelliHub-specific fields
    fieldsets = BaseUserAdmin.fieldsets + (
        ('IntelliHub Profile', {
            'fields': (
                'role',
                'profile_photo',
                'bio',
                'institution',
                'github_url',
                'linkedin_url',
                'is_email_verified',
                'dataset_quota',
            ),
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('IntelliHub Profile', {
            'fields': (
                'email',
                'role',
                'institution',
                'dataset_quota',
            ),
        }),
    )
