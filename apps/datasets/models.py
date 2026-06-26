"""
IntelliHub AI — Dataset Manager Models
========================================
Core data models for dataset storage, profiling metadata,
and version history tracking.
"""

from django.conf import settings
from django.db import models


class Dataset(models.Model):
    """
    Represents an uploaded dataset with auto-profiled metadata.

    Stores the uploaded file alongside computed statistics such as
    row/column counts, data types, missing values, duplicates, memory
    usage, and an overall quality score.
    """

    FILE_TYPE_CHOICES = [
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('json', 'JSON'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='datasets',
        help_text='Owner of this dataset.',
    )
    name = models.CharField(
        max_length=255,
        help_text='Human-readable dataset name.',
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text='Optional description or notes about this dataset.',
    )
    file = models.FileField(
        upload_to='datasets/%Y/%m/',
        help_text='The uploaded data file.',
    )
    file_type = models.CharField(
        max_length=10,
        choices=FILE_TYPE_CHOICES,
        help_text='Detected file format.',
    )
    file_size = models.BigIntegerField(
        default=0,
        help_text='File size in bytes.',
    )
    num_rows = models.IntegerField(
        default=0,
        help_text='Total number of rows in the dataset.',
    )
    num_columns = models.IntegerField(
        default=0,
        help_text='Total number of columns in the dataset.',
    )
    column_names = models.JSONField(
        default=list,
        help_text='Ordered list of column names.',
    )
    column_types = models.JSONField(
        default=dict,
        help_text='Mapping of column name → detected dtype string.',
    )
    missing_values = models.JSONField(
        default=dict,
        help_text='Mapping of column name → count of missing values.',
    )
    duplicate_rows = models.IntegerField(
        default=0,
        help_text='Number of fully duplicated rows.',
    )
    memory_usage = models.FloatField(
        default=0.0,
        help_text='Approximate in-memory size in megabytes.',
    )
    quality_score = models.FloatField(
        default=0.0,
        help_text='Computed data quality score (0–100).',
    )
    is_favorite = models.BooleanField(
        default=False,
        help_text='Whether the user has starred this dataset.',
    )
    is_public = models.BooleanField(
        default=False,
        help_text='Whether this dataset is visible to other users.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'intellihub_datasets'
        ordering = ['-created_at']
        verbose_name = 'Dataset'
        verbose_name_plural = 'Datasets'

    def __str__(self):
        """Return a human-readable label: 'dataset_name (username)'."""
        return f"{self.name} ({self.user.username})"


class DatasetVersion(models.Model):
    """
    Tracks historical snapshots of a dataset.

    Each version stores a separate file copy and optional notes
    describing what changed.
    """

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name='versions',
        help_text='Parent dataset this version belongs to.',
    )
    version_number = models.IntegerField(
        default=1,
        help_text='Incrementing version identifier.',
    )
    file = models.FileField(
        upload_to='dataset_versions/',
        help_text='Snapshot file for this version.',
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text='Change notes describing this version.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'intellihub_dataset_versions'
        ordering = ['-version_number']
        verbose_name = 'Dataset Version'
        verbose_name_plural = 'Dataset Versions'

    def __str__(self):
        """Return 'DatasetName v<N>'."""
        return f"{self.dataset.name} v{self.version_number}"
