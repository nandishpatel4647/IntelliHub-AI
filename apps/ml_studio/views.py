"""
IntelliHub AI — ML Studio Views
==================================
Handles ML model training, evaluation, prediction, comparison,
and management for the Machine Learning Studio module.
"""

import json
import logging
import os
import pickle
import tempfile

import numpy as np
import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import (
    Lasso,
    LinearRegression,
    LogisticRegression,
    Ridge,
)
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from apps.datasets.models import Dataset

from .models import MLModel, Prediction

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────


def _read_dataframe(file_path, file_type):
    """
    Read an uploaded dataset file into a pandas DataFrame.

    Parameters
    ----------
    file_path : str
        Absolute filesystem path to the data file.
    file_type : str
        One of ``'csv'``, ``'excel'``, or ``'json'``.

    Returns
    -------
    pd.DataFrame
    """
    if file_type == 'csv':
        return pd.read_csv(file_path, low_memory=False)
    elif file_type == 'excel':
        return pd.read_excel(file_path, engine='openpyxl')
    elif file_type == 'json':
        return pd.read_json(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def is_classification(y):
    """
    Determine whether target *y* represents a classification problem.

    Returns ``True`` if *y* has 20 or fewer unique values **or** its
    dtype is ``object`` or ``category``.
    """
    if hasattr(y, 'dtype'):
        if y.dtype == 'object' or str(y.dtype) == 'category':
            return True
    unique_count = len(np.unique(y)) if hasattr(y, '__len__') else 0
    return unique_count <= 20


def _build_model(model_type, hyperparameters, classification):
    """
    Instantiate an sklearn estimator from *model_type* string.

    Parameters
    ----------
    model_type : str
        One of the keys in ``MLModel.MODEL_TYPES``.
    hyperparameters : dict
        User-supplied hyperparameter overrides.
    classification : bool
        Whether the task is classification (True) or regression (False).

    Returns
    -------
    sklearn estimator instance
    """
    hp = hyperparameters or {}

    if model_type in ('linear_regression', 'multiple_regression', 'polynomial_regression'):
        return LinearRegression()

    elif model_type == 'ridge':
        return Ridge(alpha=float(hp.get('alpha', 1.0)))

    elif model_type == 'lasso':
        return Lasso(alpha=float(hp.get('alpha', 1.0)))

    elif model_type == 'logistic_regression':
        return LogisticRegression(max_iter=1000)

    elif model_type == 'decision_tree':
        if classification:
            return DecisionTreeClassifier(
                max_depth=int(hp['max_depth']) if hp.get('max_depth') else None,
                random_state=42,
            )
        return DecisionTreeRegressor(
            max_depth=int(hp['max_depth']) if hp.get('max_depth') else None,
            random_state=42,
        )

    elif model_type == 'random_forest':
        n_estimators = int(hp.get('n_estimators', 100))
        if classification:
            return RandomForestClassifier(
                n_estimators=n_estimators, random_state=42,
            )
        return RandomForestRegressor(
            n_estimators=n_estimators, random_state=42,
        )

    elif model_type == 'knn':
        n_neighbors = int(hp.get('n_neighbors', 5))
        return KNeighborsClassifier(n_neighbors=n_neighbors)

    elif model_type == 'svm':
        kernel = hp.get('kernel', 'rbf')
        if classification:
            return SVC(kernel=kernel, probability=True)
        return SVR(kernel=kernel)

    elif model_type == 'naive_bayes':
        return GaussianNB()

    else:
        raise ValueError(f"Unknown model type: {model_type}")


def _compute_metrics(y_true, y_pred, classification, y_prob=None):
    """
    Compute evaluation metrics for predictions.

    Parameters
    ----------
    y_true : array-like
        True labels / values.
    y_pred : array-like
        Predicted labels / values.
    classification : bool
        Whether the task is classification.
    y_prob : array-like, optional
        Predicted probabilities (for ROC curve in binary classification).

    Returns
    -------
    dict
        Metrics dict suitable for JSON storage.
    """
    metrics = {}

    if classification:
        metrics['accuracy'] = round(float(accuracy_score(y_true, y_pred)), 4)
        metrics['precision'] = round(
            float(precision_score(y_true, y_pred, average='weighted', zero_division=0)), 4
        )
        metrics['recall'] = round(
            float(recall_score(y_true, y_pred, average='weighted', zero_division=0)), 4
        )
        metrics['f1'] = round(
            float(f1_score(y_true, y_pred, average='weighted', zero_division=0)), 4
        )

        cm = confusion_matrix(y_true, y_pred)
        metrics['confusion_matrix'] = cm.tolist()

        # ROC curve data for binary classification
        unique_classes = np.unique(y_true)
        if len(unique_classes) == 2 and y_prob is not None:
            try:
                if y_prob.ndim == 2:
                    prob_positive = y_prob[:, 1]
                else:
                    prob_positive = y_prob
                fpr, tpr, thresholds = roc_curve(y_true, prob_positive)
                metrics['roc_curve'] = {
                    'fpr': [round(float(v), 4) for v in fpr],
                    'tpr': [round(float(v), 4) for v in tpr],
                }
            except Exception:
                pass
    else:
        metrics['r2'] = round(float(r2_score(y_true, y_pred)), 4)
        metrics['mae'] = round(float(mean_absolute_error(y_true, y_pred)), 4)
        mse_val = float(mean_squared_error(y_true, y_pred))
        metrics['mse'] = round(mse_val, 4)
        metrics['rmse'] = round(float(np.sqrt(mse_val)), 4)

    return metrics


# ─── Views ────────────────────────────────────────────────────────


@login_required
def ml_studio_home(request):
    """
    Display the ML Studio dashboard with datasets, trained models,
    summary statistics, and the training form.
    """
    try:
        datasets = (
            Dataset.objects
            .filter(user=request.user)
            .select_related('user')
            .order_by('-created_at')
        )

        models_qs = (
            MLModel.objects
            .filter(user=request.user)
            .select_related('dataset', 'user')
            .order_by('-created_at')
        )

        total_models = models_qs.count()

        # Best model by accuracy (classification) or R² (regression)
        best_model = None
        best_score = -1.0
        for m in models_qs:
            score = m.metrics.get('accuracy', m.metrics.get('r2', 0)) or 0
            if float(score) > best_score:
                best_score = float(score)
                best_model = m

        # Average F1 across all classification models
        f1_scores = [
            float(m.metrics.get('f1', 0))
            for m in models_qs
            if m.metrics.get('f1') is not None
        ]
        avg_f1 = round(sum(f1_scores) / len(f1_scores), 4) if f1_scores else 0.0

        total_predictions = Prediction.objects.filter(user=request.user).count()

        # Prepare dataset columns as JSON for the training form
        datasets_columns = {}
        for ds in datasets:
            datasets_columns[ds.pk] = {
                'columns': ds.column_names or [],
                'column_types': ds.column_types or {},
            }

        context = {
            'datasets': datasets,
            'models': models_qs,
            'total_models': total_models,
            'best_model': best_model,
            'best_score': round(best_score, 4) if best_model else 0,
            'avg_f1': avg_f1,
            'total_predictions': total_predictions,
            'datasets_columns': json.dumps(datasets_columns),
        }
        return render(request, 'ml_studio/home.html', context)

    except Exception as e:
        logger.exception(f"Error loading ML Studio home: {e}")
        messages.error(request, "Something went wrong loading ML Studio.")
        return redirect('dashboard:home')


@login_required
def train_model(request):
    """
    Train a new ML model via AJAX POST.

    Expects a JSON body with ``dataset_id``, ``model_type``,
    ``target_column``, ``feature_columns``, ``test_size``, and
    optional ``hyperparameters``.

    Returns a :class:`JsonResponse` with training results and metrics.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required.'}, status=405)

    try:
        body = json.loads(request.body)
        dataset_id = body.get('dataset_id')
        model_type = body.get('model_type')
        target_column = body.get('target_column')
        feature_columns = body.get('feature_columns', [])
        test_size = float(body.get('test_size', 0.2))
        hyperparameters = body.get('hyperparameters', {})
        model_name = body.get('model_name', '').strip()

        # Validation
        if not dataset_id or not model_type or not target_column or not feature_columns:
            return JsonResponse({
                'error': 'Missing required fields: dataset_id, model_type, target_column, feature_columns.',
            }, status=400)

        # Load dataset
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)

        # Determine file type
        file_type = dataset.file_type
        df = _read_dataframe(dataset.file.path, file_type)

        # Validate columns exist
        if target_column not in df.columns:
            return JsonResponse({'error': f"Target column '{target_column}' not found in dataset."}, status=400)

        missing_features = [c for c in feature_columns if c not in df.columns]
        if missing_features:
            return JsonResponse({
                'error': f"Feature columns not found: {', '.join(missing_features)}",
            }, status=400)

        # Prepare target (y) and features (X)
        y = df[target_column].copy()
        X = df[feature_columns].copy()

        # Drop rows where target is NaN
        valid_mask = y.notna()
        X = X[valid_mask].reset_index(drop=True)
        y = y[valid_mask].reset_index(drop=True)

        if len(X) == 0:
            return JsonResponse({'error': 'No valid rows after removing NaN targets.'}, status=400)

        # Determine task type
        classification = is_classification(y)

        # Encode categorical target for classification
        target_encoder = None
        if classification and (y.dtype == 'object' or str(y.dtype) == 'category'):
            target_encoder = LabelEncoder()
            y = pd.Series(target_encoder.fit_transform(y.astype(str)))

        # Handle categorical features: LabelEncoder per column
        label_encoders = {}
        for col in X.columns:
            if X[col].dtype == 'object' or str(X[col].dtype) == 'category':
                le = LabelEncoder()
                X[col] = X[col].fillna('__missing__').astype(str)
                X[col] = le.fit_transform(X[col])
                label_encoders[col] = le
            else:
                # Fill numeric NaN with median
                median_val = X[col].median()
                X[col] = X[col].fillna(median_val)

        # Train / test split
        test_size_clamped = max(0.1, min(0.5, test_size))
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size_clamped, random_state=42,
        )

        # Feature scaling
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Build and train model
        estimator = _build_model(model_type, hyperparameters, classification)
        estimator.fit(X_train_scaled, y_train)

        # Predictions
        y_pred = estimator.predict(X_test_scaled)

        # Probabilities (for classification ROC)
        y_prob = None
        if classification and hasattr(estimator, 'predict_proba'):
            try:
                y_prob = estimator.predict_proba(X_test_scaled)
            except Exception:
                y_prob = None

        # Metrics
        metrics = _compute_metrics(y_test, y_pred, classification, y_prob)

        # Feature importance
        if hasattr(estimator, 'feature_importances_'):
            importances = estimator.feature_importances_.tolist()
            metrics['feature_importance'] = {
                'features': feature_columns,
                'importances': [round(float(v), 4) for v in importances],
            }
        elif hasattr(estimator, 'coef_'):
            coefs = np.atleast_1d(estimator.coef_)
            if coefs.ndim > 1:
                coefs = coefs[0]
            metrics['feature_importance'] = {
                'features': feature_columns,
                'importances': [round(float(abs(v)), 4) for v in coefs],
            }

        # Store actual vs predicted for charts
        metrics['y_test'] = [round(float(v), 4) for v in y_test.values[:200]]
        metrics['y_pred'] = [round(float(v), 4) for v in y_pred[:200]]

        # Serialise model pipeline (estimator + scaler + encoders)
        pipeline = {
            'estimator': estimator,
            'scaler': scaler,
            'label_encoders': label_encoders,
            'target_encoder': target_encoder,
            'feature_columns': feature_columns,
            'classification': classification,
        }
        model_bytes = pickle.dumps(pipeline)

        # Auto-generate name if not provided
        if not model_name:
            type_display = dict(MLModel.MODEL_TYPES).get(model_type, model_type)
            model_name = f"{type_display} — {dataset.name}"

        # Create DB record
        ml_model = MLModel(
            user=request.user,
            dataset=dataset,
            name=model_name,
            model_type=model_type,
            target_column=target_column,
            feature_columns=feature_columns,
            metrics=metrics,
            test_size=test_size_clamped,
            hyperparameters=hyperparameters,
        )
        ml_model.model_file.save(
            f"model_{ml_model.name[:30].replace(' ', '_')}.pkl",
            ContentFile(model_bytes),
            save=False,
        )
        ml_model.save()

        logger.info(
            "ML model trained: %s (pk=%s, type=%s) by user %s",
            ml_model.name, ml_model.pk, model_type, request.user.username,
        )

        return JsonResponse({
            'success': True,
            'model_id': ml_model.pk,
            'model_name': ml_model.name,
            'model_type': ml_model.get_model_type_display(),
            'metrics': metrics,
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)
    except Dataset.DoesNotExist:
        return JsonResponse({'error': 'Dataset not found.'}, status=404)
    except Exception as e:
        logger.exception(f"Error training ML model: {e}")
        return JsonResponse({'error': f'Training failed: {str(e)}'}, status=500)


@login_required
def model_detail(request, pk):
    """
    Display detailed information, charts, and prediction form for
    a single trained ML model.
    """
    try:
        ml_model = get_object_or_404(
            MLModel.objects.select_related('dataset', 'user'),
            pk=pk,
            user=request.user,
        )

        metrics = ml_model.metrics or {}
        classification = 'accuracy' in metrics

        # ── Plotly chart data ─────────────────────────────────
        charts = {}

        # Confusion matrix heatmap (classification)
        if classification and 'confusion_matrix' in metrics:
            cm = metrics['confusion_matrix']
            charts['confusion_matrix'] = {
                'z': cm,
                'type': 'heatmap',
                'colorscale': [
                    [0, '#0A0A0F'],
                    [0.5, '#7C3AED'],
                    [1, '#06B6D4'],
                ],
            }

        # ROC curve (binary classification)
        if classification and 'roc_curve' in metrics:
            roc_data = metrics['roc_curve']
            charts['roc_curve'] = {
                'fpr': roc_data['fpr'],
                'tpr': roc_data['tpr'],
            }

        # Predicted vs Actual scatter (regression)
        if not classification and 'y_test' in metrics and 'y_pred' in metrics:
            charts['predicted_vs_actual'] = {
                'y_test': metrics['y_test'],
                'y_pred': metrics['y_pred'],
            }
            # Residuals
            residuals = [
                round(float(a - p), 4)
                for a, p in zip(metrics['y_test'], metrics['y_pred'])
            ]
            charts['residuals'] = {
                'y_pred': metrics['y_pred'],
                'residuals': residuals,
            }

        # Feature importance
        if 'feature_importance' in metrics:
            charts['feature_importance'] = metrics['feature_importance']

        # Predictions history
        predictions = (
            Prediction.objects
            .filter(model=ml_model, user=request.user)
            .order_by('-created_at')[:20]
        )

        context = {
            'model': ml_model,
            'charts': json.dumps(charts),
            'classification': classification,
            'predictions': predictions,
            'feature_columns': ml_model.feature_columns,
        }
        return render(request, 'ml_studio/detail.html', context)

    except Exception as e:
        logger.exception(f"Error loading model detail (pk={pk}): {e}")
        messages.error(request, "Something went wrong loading the model.")
        return redirect('ml_studio:home')


@login_required
def predict_view(request, pk):
    """
    Make a prediction with a trained model via AJAX POST.

    Expects JSON body with ``input_data`` — a dict mapping feature
    names to input values.

    Returns predicted value and optional confidence.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required.'}, status=405)

    try:
        ml_model = get_object_or_404(MLModel, pk=pk, user=request.user)

        if not ml_model.model_file:
            return JsonResponse({'error': 'No model file found.'}, status=400)

        body = json.loads(request.body)
        input_data = body.get('input_data', {})

        if not input_data:
            return JsonResponse({'error': 'No input data provided.'}, status=400)

        # Load pipeline
        with ml_model.model_file.open('rb') as f:
            pipeline = pickle.loads(f.read())

        estimator = pipeline['estimator']
        scaler = pipeline['scaler']
        label_encoders = pipeline.get('label_encoders', {})
        target_encoder = pipeline.get('target_encoder')
        feature_cols = pipeline.get('feature_columns', ml_model.feature_columns)
        classification = pipeline.get('classification', True)

        # Build feature vector in correct order
        feature_values = []
        for col in feature_cols:
            raw_val = input_data.get(col, 0)
            if col in label_encoders:
                try:
                    encoded_val = label_encoders[col].transform([str(raw_val)])[0]
                except ValueError:
                    encoded_val = 0
                feature_values.append(encoded_val)
            else:
                try:
                    feature_values.append(float(raw_val))
                except (ValueError, TypeError):
                    feature_values.append(0.0)

        X_input = np.array(feature_values).reshape(1, -1)
        X_scaled = scaler.transform(X_input)

        # Predict
        prediction_raw = estimator.predict(X_scaled)[0]

        # Decode target if needed
        if target_encoder is not None:
            try:
                predicted_value = target_encoder.inverse_transform([int(prediction_raw)])[0]
            except (ValueError, IndexError):
                predicted_value = prediction_raw
        else:
            predicted_value = prediction_raw

        # Convert numpy types to Python native
        if isinstance(predicted_value, (np.integer,)):
            predicted_value = int(predicted_value)
        elif isinstance(predicted_value, (np.floating,)):
            predicted_value = round(float(predicted_value), 4)

        # Confidence
        confidence = None
        if classification and hasattr(estimator, 'predict_proba'):
            try:
                proba = estimator.predict_proba(X_scaled)[0]
                confidence = round(float(max(proba)), 4)
            except Exception:
                confidence = None

        # Save prediction record
        Prediction.objects.create(
            model=ml_model,
            user=request.user,
            input_data=input_data,
            predicted_value=predicted_value,
            confidence=confidence,
        )

        return JsonResponse({
            'success': True,
            'predicted_value': predicted_value,
            'confidence': confidence,
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)
    except Exception as e:
        logger.exception(f"Error making prediction (model pk={pk}): {e}")
        return JsonResponse({'error': f'Prediction failed: {str(e)}'}, status=500)


@login_required
def delete_model(request, pk):
    """
    Delete a trained ML model and its serialised artefact from disk.
    POST only.
    """
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('ml_studio:home')

    try:
        ml_model = get_object_or_404(MLModel, pk=pk, user=request.user)
        model_name = ml_model.name

        # Remove physical file
        if ml_model.model_file:
            try:
                file_path = ml_model.model_file.path
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as file_err:
                logger.warning("Could not delete model file for pk=%s: %s", pk, file_err)

        ml_model.delete()

        messages.success(request, f"Model '{model_name}' has been deleted.")
        return redirect('ml_studio:home')

    except Exception as e:
        logger.exception(f"Error deleting model (pk={pk}): {e}")
        messages.error(request, "Something went wrong while deleting the model.")
        return redirect('ml_studio:home')


@login_required
def compare_models(request):
    """
    Compare multiple ML models side by side.

    Accepts model IDs via ``?ids=1,2,3`` GET parameter.
    Returns JSON when requested via AJAX, otherwise renders a template.
    """
    try:
        ids_param = request.GET.get('ids', '')
        if not ids_param:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'No model IDs provided.'}, status=400)
            messages.warning(request, "No models selected for comparison.")
            return redirect('ml_studio:home')

        model_ids = [int(x.strip()) for x in ids_param.split(',') if x.strip().isdigit()]

        if not model_ids:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'No valid model IDs provided.'}, status=400)
            messages.warning(request, "No valid model IDs provided.")
            return redirect('ml_studio:home')

        models_qs = (
            MLModel.objects
            .filter(pk__in=model_ids, user=request.user)
            .select_related('dataset')
            .order_by('-created_at')
        )

        comparison = []
        for m in models_qs:
            metrics = m.metrics or {}
            comparison.append({
                'id': m.pk,
                'name': m.name,
                'model_type': m.get_model_type_display(),
                'dataset': m.dataset.name,
                'accuracy': metrics.get('accuracy'),
                'r2': metrics.get('r2'),
                'f1': metrics.get('f1'),
                'precision': metrics.get('precision'),
                'recall': metrics.get('recall'),
                'mae': metrics.get('mae'),
                'rmse': metrics.get('rmse'),
                'created_at': m.created_at.strftime('%Y-%m-%d %H:%M'),
            })

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'models': comparison})

        context = {
            'models': models_qs,
            'comparison': json.dumps(comparison),
        }
        return render(request, 'ml_studio/compare.html', context)

    except Exception as e:
        logger.exception(f"Error comparing models: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Comparison failed.'}, status=500)
        messages.error(request, "Something went wrong comparing models.")
        return redirect('ml_studio:home')
