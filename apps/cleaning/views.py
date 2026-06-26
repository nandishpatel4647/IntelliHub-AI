"""
IntelliHub AI — AI Data Cleaning Views
========================================
Smart cleaning engine with recommendations,
auto-clean, and manual per-column operations.
"""

import json
import logging
import pandas as pd
import numpy as np
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.datasets.models import Dataset
from .models import CleaningLog

logger = logging.getLogger(__name__)


def _load_dataframe(dataset):
    """Load a Dataset model instance into a Pandas DataFrame."""
    if dataset.file_type == 'csv':
        return pd.read_csv(dataset.file.path)
    elif dataset.file_type == 'excel':
        return pd.read_excel(dataset.file.path)
    return pd.read_json(dataset.file.path)


def _calculate_quality_score(df):
    """Score dataset quality from 0-100."""
    score = 100.0
    if len(df) == 0:
        return 0.0
    missing_pct = df.isnull().mean().mean() * 100
    score -= missing_pct * 0.5
    dup_pct = (df.duplicated().sum() / len(df)) * 100
    score -= dup_pct * 0.3
    if df.dtypes.nunique() >= 3:
        score += 5
    return max(0.0, min(100.0, round(score, 1)))


@login_required
def cleaning_home(request):
    """Cleaning dashboard — select a dataset and see recommendations."""
    try:
        datasets = Dataset.objects.filter(user=request.user).select_related('user')
        recent_logs = CleaningLog.objects.filter(
            user=request.user
        ).select_related('dataset').order_by('-created_at')[:10]
        context = {
            'datasets': datasets,
            'recent_logs': recent_logs,
        }
        return render(request, 'cleaning/home.html', context)
    except Exception as e:
        logger.exception(f"Error in cleaning_home: {e}")
        messages.error(request, "Something went wrong loading the cleaning dashboard.")
        return redirect('dashboard:home')


@login_required
def get_cleaning_recommendations(request, dataset_pk):
    """Analyze dataset and return cleaning recommendations as JSON."""
    try:
        dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)
        df = _load_dataframe(dataset)
        recommendations = []

        for col in df.columns:
            missing_count = int(df[col].isnull().sum())
            if missing_count > 0:
                if df[col].dtype in ['int64', 'float64']:
                    skewness = abs(df[col].dropna().skew()) if len(df[col].dropna()) > 2 else 0
                    strategy = 'median' if skewness > 1 else 'mean'
                    fill_val = round(getattr(df[col], strategy)(), 2)
                    rec_text = f"Fill with {strategy} ({fill_val})"
                else:
                    mode_series = df[col].mode()
                    mode_val = mode_series.iloc[0] if not mode_series.empty else 'Unknown'
                    strategy = 'mode'
                    rec_text = f"Fill with most frequent value ('{mode_val}')"

                ratio = missing_count / len(df)
                severity = 'high' if ratio > 0.3 else 'medium' if ratio > 0.1 else 'low'
                recommendations.append({
                    'column': col,
                    'issue': 'missing_values',
                    'count': missing_count,
                    'pct': round(ratio * 100, 1),
                    'strategy': strategy,
                    'recommendation': rec_text,
                    'severity': severity,
                })

            if df[col].dtype in ['int64', 'float64']:
                clean_col = df[col].dropna()
                if len(clean_col) > 4:
                    q1 = clean_col.quantile(0.25)
                    q3 = clean_col.quantile(0.75)
                    iqr = q3 - q1
                    outliers = int(((clean_col < q1 - 1.5 * iqr) | (clean_col > q3 + 1.5 * iqr)).sum())
                    if outliers > 0:
                        recommendations.append({
                            'column': col,
                            'issue': 'outliers',
                            'count': outliers,
                            'pct': round(outliers / len(df) * 100, 1),
                            'strategy': 'cap_iqr',
                            'recommendation': f"Cap {outliers} outliers using IQR bounds",
                            'severity': 'medium',
                        })

        dup_count = int(df.duplicated().sum())
        if dup_count > 0:
            recommendations.append({
                'column': 'ALL ROWS',
                'issue': 'duplicates',
                'count': dup_count,
                'pct': round(dup_count / len(df) * 100, 1),
                'strategy': 'drop_duplicates',
                'recommendation': f"Remove {dup_count} duplicate rows",
                'severity': 'high' if dup_count / len(df) > 0.1 else 'low',
            })

        return JsonResponse({'recommendations': recommendations, 'total_rows': len(df)})
    except Dataset.DoesNotExist:
        return JsonResponse({'error': 'Dataset not found'}, status=404)
    except Exception as e:
        logger.exception(f"Error getting cleaning recommendations: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def auto_clean(request, dataset_pk):
    """Apply all recommended cleaning in one click."""
    try:
        dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)
        df = _load_dataframe(dataset)
        original_rows = len(df)
        quality_before = dataset.quality_score
        actions = []

        # 1. Remove duplicates
        before_dup = len(df)
        df = df.drop_duplicates()
        removed = before_dup - len(df)
        if removed > 0:
            actions.append(f"Removed {removed} duplicate rows")

        # 2. Handle missing values
        for col in df.columns:
            missing = df[col].isnull().sum()
            if missing > 0:
                if df[col].dtype in ['int64', 'float64']:
                    fill_val = df[col].median()
                    df[col] = df[col].fillna(fill_val)
                    actions.append(f"Filled '{col}' nulls with median ({round(fill_val, 2)})")
                else:
                    mode_series = df[col].mode()
                    fill_val = mode_series.iloc[0] if not mode_series.empty else 'Unknown'
                    df[col] = df[col].fillna(fill_val)
                    actions.append(f"Filled '{col}' nulls with '{fill_val}'")

        # 3. Cap outliers
        for col in df.select_dtypes(include=['int64', 'float64']).columns:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            outlier_count = int(((df[col] < lower) | (df[col] > upper)).sum())
            if outlier_count > 0:
                df[col] = df[col].clip(lower, upper)
                actions.append(f"Capped {outlier_count} outliers in '{col}'")

        # Save cleaned data
        df.to_csv(dataset.file.path, index=False)
        new_quality = _calculate_quality_score(df)

        # Update dataset metadata
        dataset.num_rows = len(df)
        dataset.missing_values = {col: int(df[col].isnull().sum()) for col in df.columns}
        dataset.duplicate_rows = 0
        dataset.quality_score = new_quality
        dataset.save()

        # Create cleaning log
        CleaningLog.objects.create(
            user=request.user,
            dataset=dataset,
            actions_applied=actions,
            rows_before=original_rows,
            rows_after=len(df),
            quality_before=quality_before,
            quality_after=new_quality,
        )

        return JsonResponse({
            'success': True,
            'actions': actions,
            'before': {'rows': original_rows},
            'after': {'rows': len(df)},
            'quality_before': quality_before,
            'quality_after': new_quality,
        })
    except Exception as e:
        logger.exception(f"Error in auto_clean: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def manual_clean(request, dataset_pk):
    """Apply a single cleaning action on a specific column."""
    try:
        dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)
        df = _load_dataframe(dataset)
        body = json.loads(request.body)
        column = body.get('column')
        action = body.get('action')
        custom_value = body.get('value')

        if column not in df.columns and action != 'drop_duplicates':
            return JsonResponse({'error': f"Column '{column}' not found"}, status=400)

        original_rows = len(df)
        action_text = ''

        if action == 'fill_mean' and column:
            val = df[column].mean()
            df[column] = df[column].fillna(val)
            action_text = f"Filled '{column}' with mean ({round(val, 2)})"

        elif action == 'fill_median' and column:
            val = df[column].median()
            df[column] = df[column].fillna(val)
            action_text = f"Filled '{column}' with median ({round(val, 2)})"

        elif action == 'fill_mode' and column:
            mode_s = df[column].mode()
            val = mode_s.iloc[0] if not mode_s.empty else 'Unknown'
            df[column] = df[column].fillna(val)
            action_text = f"Filled '{column}' with mode ('{val}')"

        elif action == 'fill_custom' and column:
            df[column] = df[column].fillna(custom_value)
            action_text = f"Filled '{column}' with custom value '{custom_value}'"

        elif action == 'drop_column' and column:
            df = df.drop(columns=[column])
            action_text = f"Dropped column '{column}'"

        elif action == 'drop_nulls' and column:
            df = df.dropna(subset=[column])
            action_text = f"Dropped rows with nulls in '{column}'"

        elif action == 'cap_outliers' and column:
            q1 = df[column].quantile(0.25)
            q3 = df[column].quantile(0.75)
            iqr = q3 - q1
            df[column] = df[column].clip(q1 - 1.5 * iqr, q3 + 1.5 * iqr)
            action_text = f"Capped outliers in '{column}'"

        elif action == 'drop_duplicates':
            df = df.drop_duplicates()
            action_text = "Removed duplicate rows"

        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)

        # Save
        df.to_csv(dataset.file.path, index=False)
        new_quality = _calculate_quality_score(df)
        dataset.num_rows = len(df)
        dataset.num_columns = len(df.columns)
        dataset.column_names = list(df.columns)
        dataset.column_types = {col: str(dtype) for col, dtype in df.dtypes.items()}
        dataset.missing_values = {col: int(df[col].isnull().sum()) for col in df.columns}
        dataset.duplicate_rows = int(df.duplicated().sum())
        dataset.quality_score = new_quality
        dataset.save()

        CleaningLog.objects.create(
            user=request.user,
            dataset=dataset,
            actions_applied=[action_text],
            rows_before=original_rows,
            rows_after=len(df),
            quality_before=dataset.quality_score,
            quality_after=new_quality,
        )

        return JsonResponse({
            'success': True,
            'action_applied': action_text,
            'rows_affected': original_rows - len(df),
            'new_quality': new_quality,
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)
    except Exception as e:
        logger.exception(f"Error in manual_clean: {e}")
        return JsonResponse({'error': str(e)}, status=500)
