from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'dataset', 'report_type', 'created_at')
    list_filter = ('report_type', 'created_at')
