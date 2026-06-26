from django.contrib import admin
from .models import DLModel


@admin.register(DLModel)
class DLModelAdmin(admin.ModelAdmin):
    """Admin for DLModel."""
    list_display = ('name', 'user', 'model_type', 'dataset', 'epochs', 'created_at')
    list_filter = ('model_type', 'created_at')
