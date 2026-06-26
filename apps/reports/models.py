"""
IntelliHub AI — Report Models
=================================
Auto-generated PDF analysis reports.
"""

from django.db import models


class Report(models.Model):
    """An auto-generated PDF analysis report."""
    REPORT_TYPE_CHOICES = [
        ('dataset_summary', 'Dataset Summary'),
        ('full_analysis', 'Full Analysis'),
        ('ml_report', 'ML Report'),
        ('custom', 'Custom'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reports')
    dataset = models.ForeignKey('datasets.Dataset', on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, default='dataset_summary')
    report_file = models.FileField(upload_to='reports/')
    sections = models.JSONField(default=list)
    page_count = models.IntegerField(default=0)
    file_size = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'intellihub_reports'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_report_type_display()})"
