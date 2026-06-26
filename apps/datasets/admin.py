"""
IntelliHub AI — Dataset Manager Admin Configuration
=====================================================
Registers Dataset and DatasetVersion with the Django admin site.
"""

from django.contrib import admin

from .models import Dataset, DatasetVersion


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    """Admin interface for the Dataset model."""

    list_display = (
        'name',
        'user',
        'file_type',
        'num_rows',
        'num_columns',
        'quality_score',
        'is_favorite',
        'created_at',
    )
    list_filter = ('file_type', 'is_favorite', 'is_public', 'created_at')
    search_fields = ('name', 'description', 'user__username')
    readonly_fields = (
        'file_size',
        'num_rows',
        'num_columns',
        'column_names',
        'column_types',
        'missing_values',
        'duplicate_rows',
        'memory_usage',
        'quality_score',
        'created_at',
        'updated_at',
    )
    raw_id_fields = ('user',)
    date_hierarchy = 'created_at'


@admin.register(DatasetVersion)
class DatasetVersionAdmin(admin.ModelAdmin):
    """Admin interface for the DatasetVersion model."""

    list_display = ('dataset', 'version_number', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('dataset__name', 'notes')
    raw_id_fields = ('dataset',)
