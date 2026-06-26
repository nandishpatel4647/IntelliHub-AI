from django.contrib import admin
from .models import CleaningLog


@admin.register(CleaningLog)
class CleaningLogAdmin(admin.ModelAdmin):
    """Admin configuration for CleaningLog."""
    list_display = ('dataset', 'user', 'rows_before', 'rows_after', 'quality_before', 'quality_after', 'created_at')
    list_filter = ('created_at',)
    readonly_fields = ('actions_applied',)
