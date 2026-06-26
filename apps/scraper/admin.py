from django.contrib import admin
from .models import ScrapeJob


@admin.register(ScrapeJob)
class ScrapeJobAdmin(admin.ModelAdmin):
    list_display = ('job_name', 'user', 'url', 'status', 'rows_scraped', 'created_at')
    list_filter = ('status', 'created_at')
