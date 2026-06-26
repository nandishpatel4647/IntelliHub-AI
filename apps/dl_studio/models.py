"""
IntelliHub AI — Deep Learning Models
======================================
Stores neural network configurations and training results.
"""

from django.db import models


class DLModel(models.Model):
    """A trained deep learning (neural network) model."""

    MODEL_TYPE_CHOICES = [
        ('dense_nn', 'Dense Neural Network'),
        ('simple_cnn', 'Simple CNN'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='dl_models')
    dataset = models.ForeignKey('datasets.Dataset', on_delete=models.CASCADE, related_name='dl_models')
    name = models.CharField(max_length=255)
    model_type = models.CharField(max_length=20, choices=MODEL_TYPE_CHOICES, default='dense_nn')
    target_column = models.CharField(max_length=100)
    feature_columns = models.JSONField(default=list)
    architecture = models.JSONField(default=list)
    epochs = models.IntegerField(default=50)
    batch_size = models.IntegerField(default=32)
    learning_rate = models.FloatField(default=0.001)
    training_history = models.JSONField(default=dict)
    metrics = models.JSONField(default=dict)
    model_file = models.FileField(upload_to='dl_models/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'intellihub_dl_models'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_model_type_display()})"
