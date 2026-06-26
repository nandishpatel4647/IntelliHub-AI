"""
IntelliHub AI — API Center Views
====================================
DRF ViewSets with JWT authentication.
"""

import pickle
import logging
import pandas as pd
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rest_framework import viewsets, permissions, status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response
from apps.datasets.models import Dataset
from apps.ml_studio.models import MLModel, Prediction
from apps.accounts.models import User
from .serializers import (
    DatasetSerializer, MLModelSerializer, PredictionSerializer,
    PredictionCreateSerializer, UserSerializer,
)

logger = logging.getLogger(__name__)


class DatasetViewSet(viewsets.ModelViewSet):
    """API ViewSet for datasets — CRUD operations."""
    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter datasets to current user, support search."""
        qs = Dataset.objects.filter(user=self.request.user).select_related('user')
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

    def perform_create(self, serializer):
        """Auto-profile uploaded dataset."""
        serializer.save(user=self.request.user)


class MLModelViewSet(viewsets.ReadOnlyModelViewSet):
    """API ViewSet for ML models — read only."""
    serializer_class = MLModelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MLModel.objects.filter(user=self.request.user).select_related('dataset')


class PredictionViewSet(viewsets.ModelViewSet):
    """API ViewSet for predictions."""
    serializer_class = PredictionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Prediction.objects.filter(user=self.request.user).select_related('model')

    def create(self, request, *args, **kwargs):
        """Create a prediction using a trained model."""
        try:
            ser = PredictionCreateSerializer(data=request.data)
            ser.is_valid(raise_exception=True)

            model_id = ser.validated_data['model_id']
            input_data = ser.validated_data['input_data']

            ml_model = MLModel.objects.get(pk=model_id, user=request.user)

            if not ml_model.model_file:
                return Response({'error': 'No model file found'}, status=status.HTTP_400_BAD_REQUEST)

            with open(ml_model.model_file.path, 'rb') as f:
                model_bundle = pickle.load(f)

            model = model_bundle.get('model')
            scaler = model_bundle.get('scaler')
            encoders = model_bundle.get('label_encoders', {})

            features = ml_model.feature_columns
            input_values = []
            for feat in features:
                val = input_data.get(feat, 0)
                if feat in encoders:
                    try:
                        val = encoders[feat].transform([str(val)])[0]
                    except ValueError:
                        val = 0
                input_values.append(float(val))

            import numpy as np
            X = np.array([input_values])
            if scaler:
                X = scaler.transform(X)

            prediction_val = model.predict(X)
            result = prediction_val[0]
            if hasattr(result, 'tolist'):
                result = result.tolist()

            confidence = None
            if hasattr(model, 'predict_proba'):
                proba = model.predict_proba(X)
                confidence = float(max(proba[0]))

            pred = Prediction.objects.create(
                model=ml_model, user=request.user,
                input_data=input_data, predicted_value=result,
                confidence=confidence,
            )

            return Response(PredictionSerializer(pred).data, status=status.HTTP_201_CREATED)
        except MLModel.DoesNotExist:
            return Response({'error': 'Model not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"Prediction error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfileView(RetrieveUpdateAPIView):
    """API view for user profile — get/update current user."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@login_required
def api_docs_view(request):
    """Render API documentation page."""
    return render(request, 'api_center/docs.html', {
        'base_url': request.build_absolute_uri('/api/'),
    })
