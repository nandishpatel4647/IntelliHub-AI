"""
IntelliHub AI — API Serializers
==================================
DRF serializers for all API endpoints.
"""

from rest_framework import serializers
from apps.accounts.models import User
from apps.datasets.models import Dataset
from apps.ml_studio.models import MLModel, Prediction


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'institution', 'date_joined']
        read_only_fields = ['id', 'username', 'date_joined']


class DatasetSerializer(serializers.ModelSerializer):
    """Serializer for dataset listing and detail."""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Dataset
        fields = [
            'id', 'name', 'description', 'file_type', 'file_size',
            'num_rows', 'num_columns', 'column_names', 'quality_score',
            'is_favorite', 'created_at', 'username',
        ]
        read_only_fields = ['id', 'file_size', 'num_rows', 'num_columns', 'column_names', 'quality_score', 'created_at', 'username']


class DatasetUploadSerializer(serializers.Serializer):
    """Serializer for dataset upload."""
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    file = serializers.FileField()


class MLModelSerializer(serializers.ModelSerializer):
    """Serializer for ML models."""
    dataset_name = serializers.CharField(source='dataset.name', read_only=True)

    class Meta:
        model = MLModel
        fields = [
            'id', 'name', 'model_type', 'target_column', 'feature_columns',
            'metrics', 'test_size', 'dataset_name', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class PredictionSerializer(serializers.ModelSerializer):
    """Serializer for predictions."""
    class Meta:
        model = Prediction
        fields = ['id', 'model', 'input_data', 'predicted_value', 'confidence', 'created_at']
        read_only_fields = ['id', 'predicted_value', 'confidence', 'created_at']


class PredictionCreateSerializer(serializers.Serializer):
    """Serializer for creating predictions."""
    model_id = serializers.IntegerField()
    input_data = serializers.DictField()
