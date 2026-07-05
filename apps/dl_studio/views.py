"""
IntelliHub AI — Deep Learning Studio Views
=============================================
Neural network builder with TensorFlow/Keras (graceful fallback to sklearn).
"""

import json
import logging
import pickle
import pandas as pd
import numpy as np
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.metrics import accuracy_score, mean_squared_error, r2_score, f1_score
from apps.datasets.models import Dataset
from .models import DLModel

logger = logging.getLogger(__name__)

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False


@login_required
def dl_studio_home(request):
    """Deep Learning Studio home — list models and training form."""
    try:
        datasets = Dataset.objects.filter(user=request.user).select_related('user')
        dl_models = DLModel.objects.filter(user=request.user).select_related('dataset')
        context = {
            'datasets': datasets,
            'dl_models': dl_models,
            'total_dl_models': dl_models.count(),
            'tf_available': TF_AVAILABLE,
        }
        return render(request, 'dl_studio/home.html', context)
    except Exception as e:
        logger.exception(f"Error in dl_studio_home: {e}")
        messages.error(request, "Could not load Deep Learning Studio.")
        return redirect('dashboard:home')


def _train_with_sklearn(X_train, X_test, y_train, y_test, architecture, epochs,
                        batch_size, learning_rate, is_classification, n_classes):
    """Fallback training using sklearn MLPClassifier/MLPRegressor."""
    hidden_layer_sizes = tuple(
        layer.get('units', 64)
        for layer in architecture
        if layer.get('type', 'dense') != 'dropout'
    )
    if not hidden_layer_sizes:
        hidden_layer_sizes = (128, 64)

    if is_classification:
        model = MLPClassifier(
            hidden_layer_sizes=hidden_layer_sizes,
            activation='relu',
            solver='adam',
            learning_rate_init=learning_rate,
            max_iter=epochs,
            batch_size=min(batch_size, len(X_train)),
            random_state=42,
            early_stopping=True,
            validation_fraction=0.2,
            verbose=False,
        )
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = round(accuracy_score(y_test, y_pred), 4)
        f1 = round(f1_score(y_test, y_pred, average='weighted', zero_division=0), 4)

        # Build training history from loss_curve_
        loss_curve = [round(float(v), 4) for v in model.loss_curve_]
        val_scores = [round(float(v), 4) for v in model.validation_scores_] if hasattr(model, 'validation_scores_') and model.validation_scores_ else []

        training_history = {
            'loss': loss_curve,
            'accuracy': val_scores if val_scores else [round(acc, 4)] * len(loss_curve),
        }
        eval_metrics = {'loss': round(float(loss_curve[-1]) if loss_curve else 0, 4), 'accuracy': acc, 'f1_score': f1}
    else:
        model = MLPRegressor(
            hidden_layer_sizes=hidden_layer_sizes,
            activation='relu',
            solver='adam',
            learning_rate_init=learning_rate,
            max_iter=epochs,
            batch_size=min(batch_size, len(X_train)),
            random_state=42,
            early_stopping=True,
            validation_fraction=0.2,
            verbose=False,
        )
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        mse = round(mean_squared_error(y_test, y_pred), 4)
        r2 = round(r2_score(y_test, y_pred), 4)

        loss_curve = [round(float(v), 4) for v in model.loss_curve_]
        training_history = {
            'loss': loss_curve,
            'mae': [round(mse**0.5, 4)] * len(loss_curve),
        }
        eval_metrics = {'loss': mse, 'mae': round(mse**0.5, 4), 'r2_score': r2}

    return model, training_history, eval_metrics


def _train_with_tensorflow(X_train, X_test, y_train, y_test, architecture, epochs,
                           batch_size, learning_rate, is_classification, n_classes):
    """Train using TensorFlow/Keras."""
    model = Sequential()
    model.add(Dense(architecture[0].get('units', 128),
                    activation=architecture[0].get('activation', 'relu'),
                    input_shape=(X_train.shape[1],)))

    for layer_cfg in architecture[1:]:
        layer_type = layer_cfg.get('type', 'dense')
        if layer_type == 'dropout':
            model.add(Dropout(layer_cfg.get('rate', 0.2)))
        else:
            model.add(Dense(layer_cfg.get('units', 64),
                            activation=layer_cfg.get('activation', 'relu')))

    if is_classification:
        if n_classes == 2:
            model.add(Dense(1, activation='sigmoid'))
            loss = 'binary_crossentropy'
            metric_list = ['accuracy']
        else:
            model.add(Dense(n_classes, activation='softmax'))
            loss = 'categorical_crossentropy'
            metric_list = ['accuracy']
    else:
        model.add(Dense(1, activation='linear'))
        loss = 'mse'
        metric_list = ['mae']

    model.compile(optimizer=Adam(learning_rate=learning_rate), loss=loss, metrics=metric_list)

    history = model.fit(
        X_train, y_train,
        validation_split=0.2,
        epochs=epochs,
        batch_size=batch_size,
        verbose=0,
    )

    training_history = {k: [float(v) for v in vals] for k, vals in history.history.items()}
    eval_results = model.evaluate(X_test, y_test, verbose=0)
    eval_metrics = {name: round(float(val), 4) for name, val in
                    zip(['loss'] + metric_list, [eval_results] if isinstance(eval_results, float) else eval_results)}

    return model, training_history, eval_metrics


@login_required
@require_POST
def train_dl_model(request):
    """Train a neural network model (TF/Keras or sklearn fallback)."""
    try:
        body = json.loads(request.body)
        dataset_id = body.get('dataset_id')
        model_name = body.get('name', 'DL Model')
        model_type = body.get('model_type', 'dense_nn')
        target_column = body.get('target_column')
        feature_columns = body.get('feature_columns', [])
        architecture = body.get('architecture', [{'units': 128, 'activation': 'relu'}, {'units': 64, 'activation': 'relu'}])
        epochs = int(body.get('epochs', 50))
        batch_size = int(body.get('batch_size', 32))
        learning_rate = float(body.get('learning_rate', 0.001))

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = pd.read_csv(dataset.file.path) if dataset.file_type == 'csv' else pd.read_excel(dataset.file.path)

        if not feature_columns:
            feature_columns = [c for c in df.columns if c != target_column]

        X = df[feature_columns].copy()
        y = df[target_column].copy()

        # Encode categoricals in X
        label_encoders = {}
        for col in X.select_dtypes(include=['object', 'category']).columns:
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))
            label_encoders[col] = le

        X = X.fillna(X.median(numeric_only=True))

        # Determine classification vs regression
        is_classification = y.dtype == 'object' or y.nunique() <= 20
        n_classes = 1
        if is_classification:
            le_target = LabelEncoder()
            y_encoded = le_target.fit_transform(y.astype(str))
            n_classes = len(set(y_encoded))
        else:
            y_encoded = y.fillna(y.median()).values.astype(float)

        X_train, X_test, y_train, y_test = train_test_split(
            X.values.astype(float), y_encoded, test_size=0.2, random_state=42
        )

        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)

        # Train with TF or sklearn fallback
        if TF_AVAILABLE:
            if is_classification and n_classes > 2:
                y_train_keras = keras.utils.to_categorical(y_train, n_classes)
                y_test_keras = keras.utils.to_categorical(y_test, n_classes)
            else:
                y_train_keras, y_test_keras = y_train, y_test

            trained_model, training_history, eval_metrics = _train_with_tensorflow(
                X_train, X_test, y_train_keras, y_test_keras,
                architecture, epochs, batch_size, learning_rate,
                is_classification, n_classes
            )
            engine = 'tensorflow'
        else:
            trained_model, training_history, eval_metrics = _train_with_sklearn(
                X_train, X_test, y_train, y_test,
                architecture, epochs, batch_size, learning_rate,
                is_classification, n_classes
            )
            engine = 'sklearn'

        # Save model
        import os
        model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'media', 'dl_models')
        os.makedirs(model_dir, exist_ok=True)
        model_filename = f"dl_{dataset.pk}_{model_type}_{DLModel.objects.count() + 1}"

        if engine == 'tensorflow':
            model_filename += '.h5'
            model_path = os.path.join(model_dir, model_filename)
            trained_model.save(model_path)
        else:
            model_filename += '.pkl'
            model_path = os.path.join(model_dir, model_filename)
            with open(model_path, 'wb') as f:
                pickle.dump(trained_model, f)

        dl_model = DLModel.objects.create(
            user=request.user,
            dataset=dataset,
            name=model_name,
            model_type=model_type,
            target_column=target_column,
            feature_columns=feature_columns,
            architecture=architecture,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
            training_history=training_history,
            metrics=eval_metrics,
            model_file=f"dl_models/{model_filename}",
        )

        return JsonResponse({
            'success': True,
            'model_id': dl_model.pk,
            'metrics': eval_metrics,
            'training_history': training_history,
            'engine': engine,
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.exception(f"Error training DL model: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def dl_model_detail(request, pk):
    """View DL model details with training curves."""
    try:
        dl_model = get_object_or_404(DLModel, pk=pk, user=request.user)
        context = {
            'model': dl_model,
            'training_history_json': json.dumps(dl_model.training_history),
            'metrics': dl_model.metrics,
        }
        return render(request, 'dl_studio/detail.html', context)
    except Exception as e:
        logger.exception(f"Error in dl_model_detail: {e}")
        messages.error(request, "Could not load model details.")
        return redirect('dl_studio:home')
