"""
IntelliHub AI — Scraper Models
=================================
Web scraping job tracking.
"""

from django.db import models


class ScrapeJob(models.Model):
    """A web scraping job."""
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('running', 'Running'),
        ('done', 'Done'), ('failed', 'Failed'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='scrape_jobs')
    url = models.URLField()
    job_name = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    result_file = models.FileField(upload_to='scrapes/', blank=True)
    rows_scraped = models.IntegerField(default=0)
    columns_scraped = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'intellihub_scrape_jobs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.job_name} ({self.status})"
