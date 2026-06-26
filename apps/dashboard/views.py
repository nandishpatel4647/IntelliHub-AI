"""
IntelliHub AI — Dashboard Views
==================================
Central hub with aggregated metrics from all modules.
"""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg
from apps.datasets.models import Dataset
from apps.ml_studio.models import MLModel, Prediction
from apps.reports.models import Report

logger = logging.getLogger(__name__)


@login_required
def dashboard_home(request):
    """Main dashboard with aggregated metrics from all modules."""
    try:
        user = request.user

        # Aggregate metrics
        total_datasets = Dataset.objects.filter(user=user).count()
        total_models = MLModel.objects.filter(user=user).count()
        total_predictions = Prediction.objects.filter(user=user).count()
        total_reports = Report.objects.filter(user=user).count()

        avg_quality = Dataset.objects.filter(user=user).aggregate(
            avg=Avg('quality_score')
        )['avg'] or 0

        # Recent items
        recent_datasets = Dataset.objects.filter(user=user).order_by('-created_at')[:5]
        recent_models = MLModel.objects.filter(user=user).select_related('dataset').order_by('-created_at')[:5]

        context = {
            'total_datasets': total_datasets,
            'total_models': total_models,
            'total_predictions': total_predictions,
            'total_reports': total_reports,
            'avg_quality': round(avg_quality, 1),
            'recent_datasets': recent_datasets,
            'recent_models': recent_models,
        }
        return render(request, 'dashboard/home.html', context)
    except Exception as e:
        logger.exception(f"Error in dashboard_home: {e}")
        messages.error(request, "Dashboard could not load.")
        return render(request, 'dashboard/home.html', {
            'total_datasets': 0, 'total_models': 0,
            'total_predictions': 0, 'total_reports': 0,
            'avg_quality': 0, 'recent_datasets': [], 'recent_models': [],
        })
