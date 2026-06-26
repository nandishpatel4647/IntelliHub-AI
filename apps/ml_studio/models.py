"""
IntelliHub AI — ML Studio Models
==================================
Data models for machine learning model training, storage,
and prediction tracking.
"""

from django.conf import settings
from django.db import models


class MLModel(models.Model):
    """
    Represents a trained machine-learning model.

    Stores the model artefact (pickled), training configuration,
    evaluation metrics, and links back to the source dataset.
    """

    MODEL_TYPES = [
        ('linear_regression', 'Linear Regression'),
        ('multiple_regression', 'Multiple Regression'),
        ('polynomial_regression', 'Polynomial Regression'),
        ('ridge', 'Ridge Regression'),
        ('lasso', 'Lasso Regression'),
        ('logistic_regression', 'Logistic Regression'),
        ('decision_tree', 'Decision Tree'),
        ('random_forest', 'Random Forest'),
        ('knn', 'K-Nearest Neighbors'),
        ('svm', 'Support Vector Machine'),
        ('naive_bayes', 'Naive Bayes'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ml_models',
        help_text='Owner of this ML model.',
    )
    dataset = models.ForeignKey(
        'datasets.Dataset',
        on_delete=models.CASCADE,
        related_name='ml_models',
        help_text='Source dataset used for training.',
    )
    name = models.CharField(
        max_length=255,
        help_text='Human-readable model name.',
    )
    model_type = models.CharField(
        max_length=30,
        choices=MODEL_TYPES,
        help_text='Algorithm used for training.',
    )
    target_column = models.CharField(
        max_length=255,
        help_text='Name of the target / label column.',
    )
    feature_columns = models.JSONField(
        default=list,
        help_text='List of feature column names used for training.',
    )
    model_file = models.FileField(
        upload_to='models/',
        blank=True,
        help_text='Serialised model artefact (pickle).',
    )
    metrics = models.JSONField(
        default=dict,
        help_text=(
            'Evaluation metrics dict — e.g. accuracy, f1, precision, '
            'recall, r2, mae, rmse, confusion_matrix.'
        ),
    )
    test_size = models.FloatField(
        default=0.2,
        help_text='Fraction of data reserved for testing (0–1).',
    )
    hyperparameters = models.JSONField(
        default=dict,
        help_text='Model-specific hyperparameters used during training.',
    )
    is_favorite = models.BooleanField(
        default=False,
        help_text='Whether the user has starred this model.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'intellihub_ml_models'
        ordering = ['-created_at']
        verbose_name = 'ML Model'
        verbose_name_plural = 'ML Models'

    def __str__(self):
        """Return 'model_name (model_type)'."""
        return f"{self.name} ({self.get_model_type_display()})"


class Prediction(models.Model):
    """
    Stores individual predictions made with a trained MLModel.

    Records the raw input data, predicted value, and optional
    confidence score for auditing and history display.
    """

    model = models.ForeignKey(
        MLModel,
        on_delete=models.CASCADE,
        related_name='predictions',
        help_text='The ML model that produced this prediction.',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='predictions',
        help_text='User who requested this prediction.',
    )
    input_data = models.JSONField(
        help_text='Feature values supplied for prediction.',
    )
    predicted_value = models.JSONField(
        help_text='Model output (scalar or probability array).',
    )
    confidence = models.FloatField(
        null=True,
        blank=True,
        help_text='Prediction confidence / probability (classification only).',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'intellihub_predictions'
        ordering = ['-created_at']
        verbose_name = 'Prediction'
        verbose_name_plural = 'Predictions'

    def __str__(self):
        """Return a short summary of the prediction."""
        return f"Prediction #{self.pk} — {self.model.name}"
