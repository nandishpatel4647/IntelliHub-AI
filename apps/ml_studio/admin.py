"""
IntelliHub AI — ML Studio Admin Configuration
================================================
Register MLModel and Prediction for the Django admin site.
"""

from django.contrib import admin

from .models import MLModel, Prediction


@admin.register(MLModel)
class MLModelAdmin(admin.ModelAdmin):
    """Admin interface for trained ML models."""

    list_display = (
        'name', 'model_type', 'user', 'dataset',
        'is_favorite', 'created_at',
    )
    list_filter = ('model_type', 'is_favorite', 'created_at')
    search_fields = ('name', 'user__username', 'dataset__name')
    readonly_fields = ('metrics', 'feature_columns', 'hyperparameters', 'created_at')
    raw_id_fields = ('user', 'dataset')


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    """Admin interface for prediction history records."""

    list_display = ('id', 'model', 'user', 'confidence', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('model__name', 'user__username')
    readonly_fields = ('input_data', 'predicted_value', 'created_at')
    raw_id_fields = ('model', 'user')
