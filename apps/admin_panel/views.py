"""
IntelliHub AI — Admin Panel Views
====================================
Platform administration dashboard (admin-role only).
"""

import logging
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from apps.accounts.models import User
from apps.datasets.models import Dataset
from apps.ml_studio.models import MLModel, Prediction
from apps.reports.models import Report
from apps.scraper.models import ScrapeJob

logger = logging.getLogger(__name__)


def admin_required(view_func):
    """Decorator: restrict to admin-role users only."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'admin':
            messages.error(request, "Admin access required.")
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


@admin_required
def admin_dashboard(request):
    """Admin dashboard with platform-wide metrics."""
    try:
        total_users = User.objects.count()
        total_datasets = Dataset.objects.count()
        total_models = MLModel.objects.count()
        total_reports = Report.objects.count()
        total_predictions = Prediction.objects.count()
        total_scrape_jobs = ScrapeJob.objects.count()

        users_by_role = list(User.objects.values('role').annotate(count=Count('id')).order_by('-count'))
        recent_users = User.objects.order_by('-date_joined')[:10]
        datasets_by_type = list(Dataset.objects.values('file_type').annotate(count=Count('id')))
        storage_used = Dataset.objects.aggregate(total=Sum('file_size'))['total'] or 0

        context = {
            'total_users': total_users,
            'total_datasets': total_datasets,
            'total_models': total_models,
            'total_reports': total_reports,
            'total_predictions': total_predictions,
            'total_scrape_jobs': total_scrape_jobs,
            'users_by_role': users_by_role,
            'recent_users': recent_users,
            'datasets_by_type': datasets_by_type,
            'storage_used': storage_used,
        }
        return render(request, 'admin_panel/dashboard.html', context)
    except Exception as e:
        logger.exception(f"Error in admin_dashboard: {e}")
        messages.error(request, "Admin dashboard error.")
        return redirect('dashboard:home')


@admin_required
def admin_users(request):
    """User management page."""
    try:
        search = request.GET.get('q', '')
        users = User.objects.all().order_by('-date_joined')
        if search:
            users = users.filter(username__icontains=search) | users.filter(email__icontains=search)
        paginator = Paginator(users, 25)
        page = request.GET.get('page')
        users_page = paginator.get_page(page)
        return render(request, 'admin_panel/users.html', {'users': users_page, 'search': search})
    except Exception as e:
        logger.exception(f"Error in admin_users: {e}")
        messages.error(request, "Could not load users.")
        return redirect('admin_panel:dashboard')


@admin_required
def admin_user_detail(request, user_id):
    """View a specific user's details."""
    try:
        target_user = get_object_or_404(User, pk=user_id)
        context = {
            'target_user': target_user,
            'datasets_count': Dataset.objects.filter(user=target_user).count(),
            'models_count': MLModel.objects.filter(user=target_user).count(),
            'reports_count': Report.objects.filter(user=target_user).count(),
        }
        return render(request, 'admin_panel/user_detail.html', context)
    except Exception as e:
        logger.exception(f"Error in admin_user_detail: {e}")
        messages.error(request, "Could not load user details.")
        return redirect('admin_panel:users')
