"""
IntelliHub AI — User Model
============================
Custom User model extending AbstractUser with role-based access,
profile metadata, and dataset quota management.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model for IntelliHub AI platform.

    Extends Django's AbstractUser with role-based permissions,
    professional profile fields, and dataset quota tracking.
    """

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('data_scientist', 'Data Scientist'),
        ('student', 'Student'),
        ('researcher', 'Researcher'),
        ('company', 'Company'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='student',
        help_text='User role determines permissions and default quotas.',
    )
    profile_photo = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True,
        help_text='User profile photo (recommended: 256×256 px).',
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        default='',
        help_text='Short biography or description.',
    )
    institution = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text='University, company, or research institution.',
    )
    github_url = models.URLField(
        max_length=300,
        blank=True,
        default='',
        verbose_name='GitHub URL',
        help_text='Link to GitHub profile.',
    )
    linkedin_url = models.URLField(
        max_length=300,
        blank=True,
        default='',
        verbose_name='LinkedIn URL',
        help_text='Link to LinkedIn profile.',
    )
    is_email_verified = models.BooleanField(
        default=False,
        help_text='Whether the user has verified their email address.',
    )
    dataset_quota = models.IntegerField(
        default=5,
        help_text='Maximum number of datasets allowed. -1 means unlimited.',
    )

    class Meta:
        db_table = 'intellihub_users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        """Return display name: full name if available, otherwise username."""
        full_name = self.get_full_name()
        if full_name.strip():
            return f"{full_name} (@{self.username})"
        return self.username

    def get_dataset_count(self):
        """
        Return the number of datasets owned by this user.

        Uses the reverse relation from the Dataset model. Returns 0 if
        the datasets app is not installed or no datasets exist.
        """
        try:
            return self.datasets.count()
        except Exception:
            return 0

    def has_quota_remaining(self):
        """
        Check whether the user can upload more datasets.

        Returns:
            bool: True if dataset_quota is -1 (unlimited) or the user's
                  current dataset count is below their quota.
        """
        if self.dataset_quota == -1:
            return True
        return self.get_dataset_count() < self.dataset_quota
