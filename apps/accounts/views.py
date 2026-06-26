"""
IntelliHub AI — Account Views
================================
Registration, login, logout, and profile management views.
All views use try/except with logging and Django messages.
"""

import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import LoginForm, ProfileForm, RegisterForm

logger = logging.getLogger(__name__)

# Mapping of role → default dataset quota
ROLE_QUOTA_MAP = {
    'student': 5,
    'researcher': -1,
    'data_scientist': 20,
    'company': -1,
    'admin': -1,
}


def register_view(request):
    """
    Handle new user registration.

    GET  → Render the registration form.
    POST → Validate, create user with role-based quota, log in, redirect.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    try:
        if request.method == 'POST':
            form = RegisterForm(request.POST, request.FILES)
            if form.is_valid():
                user = form.save(commit=False)
                user.dataset_quota = ROLE_QUOTA_MAP.get(user.role, 5)
                user.save()

                login(request, user)
                logger.info("New user registered: %s (role=%s)", user.username, user.role)
                messages.success(request, f'Welcome to IntelliHub, {user.first_name or user.username}!')
                return redirect('dashboard:home')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = RegisterForm()

        return render(request, 'accounts/register.html', {'form': form})

    except Exception as e:
        logger.exception("Error during registration: %s", e)
        messages.error(request, 'An unexpected error occurred during registration. Please try again.')
        return redirect('accounts:register')


def login_view(request):
    """
    Handle user login.

    GET  → Render the login form.
    POST → Authenticate credentials, respect ``next`` parameter, redirect.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    try:
        if request.method == 'POST':
            form = LoginForm(request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']
                user = authenticate(request, username=username, password=password)

                if user is not None:
                    login(request, user)
                    logger.info("User logged in: %s", user.username)
                    messages.success(request, f'Welcome back, {user.first_name or user.username}!')

                    next_url = request.GET.get('next') or request.POST.get('next', '')
                    if next_url:
                        return redirect(next_url)
                    return redirect('dashboard:home')
                else:
                    logger.warning("Failed login attempt for username: %s", username)
                    messages.error(request, 'Invalid username or password.')
            else:
                messages.error(request, 'Please fill in all required fields.')
        else:
            form = LoginForm()

        return render(request, 'accounts/login.html', {
            'form': form,
            'next': request.GET.get('next', ''),
        })

    except Exception as e:
        logger.exception("Error during login: %s", e)
        messages.error(request, 'An unexpected error occurred during login. Please try again.')
        return redirect('accounts:login')


@login_required
def logout_view(request):
    """
    Log the user out and redirect to the login page.
    """
    try:
        username = request.user.username
        logout(request)
        logger.info("User logged out: %s", username)
        messages.info(request, 'You have been logged out successfully.')
    except Exception as e:
        logger.exception("Error during logout: %s", e)
        messages.error(request, 'An error occurred during logout.')

    return redirect('accounts:login')


@login_required
def profile_view(request):
    """
    Display and update the authenticated user's profile.

    GET  → Pre-populated profile form with statistics.
    POST → Validate and save profile changes.

    Context includes:
        - form: ProfileForm instance
        - dataset_count: number of datasets owned
        - model_count: number of ML models owned
    """
    try:
        user = request.user

        if request.method == 'POST':
            form = ProfileForm(request.POST, request.FILES, instance=user)
            if form.is_valid():
                form.save()
                logger.info("Profile updated for user: %s", user.username)
                messages.success(request, 'Your profile has been updated successfully.')
                return redirect('accounts:profile')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = ProfileForm(instance=user)

        # Gather stats — gracefully handle missing reverse relations
        dataset_count = 0
        model_count = 0
        try:
            dataset_count = user.datasets.count()
        except Exception:
            dataset_count = 0
        try:
            model_count = user.ml_models.count()
        except Exception:
            model_count = 0

        return render(request, 'accounts/profile.html', {
            'form': form,
            'dataset_count': dataset_count,
            'model_count': model_count,
        })

    except Exception as e:
        logger.exception("Error loading profile for user %s: %s", request.user.username, e)
        messages.error(request, 'An unexpected error occurred while loading your profile.')
        return redirect('dashboard:home')
