"""
IntelliHub AI — Cleaning Models
================================
Tracks data cleaning operations performed on datasets.
"""

from django.db import models


class CleaningLog(models.Model):
    """Records each cleaning operation performed on a dataset."""

    user = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='cleaning_logs'
    )
    dataset = models.ForeignKey(
        'datasets.Dataset', on_delete=models.CASCADE, related_name='cleaning_logs'
    )
    actions_applied = models.JSONField(default=list)
    rows_before = models.IntegerField(default=0)
    rows_after = models.IntegerField(default=0)
    quality_before = models.FloatField(default=0.0)
    quality_after = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'intellihub_cleaning_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"Cleaning on {self.dataset.name} at {self.created_at:%Y-%m-%d %H:%M}"
