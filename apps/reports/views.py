"""
IntelliHub AI — Report Generator Views
=========================================
Auto-generated PDF reports using ReportLab.
"""

import os
import logging
import pandas as pd
from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.http import FileResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from apps.datasets.models import Dataset
from apps.ml_studio.models import MLModel
from .models import Report

logger = logging.getLogger(__name__)


def _generate_pdf_report(dataset, title, sections, user):
    """Generate a professional PDF report using ReportLab."""
    report_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    os.makedirs(report_dir, exist_ok=True)
    filename = f"report_{dataset.pk}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(report_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=30*mm, bottomMargin=25*mm)
    styles = getSampleStyleSheet()
    elements = []

    # Custom styles
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=24, textColor=colors.HexColor('#2563EB'), spaceAfter=20)
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=16, textColor=colors.HexColor('#7C3AED'), spaceBefore=20, spaceAfter=10)
    body_style = styles['Normal']

    # Header
    elements.append(Paragraph("IntelliHub AI", ParagraphStyle('Brand', fontSize=12, textColor=colors.HexColor('#7C3AED'))))
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", body_style))
    elements.append(Paragraph(f"User: {user.get_full_name() or user.username}", body_style))
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#7C3AED')))
    elements.append(Spacer(1, 20))

    # Load data
    try:
        if dataset.file_type == 'csv':
            df = pd.read_csv(dataset.file.path)
        elif dataset.file_type == 'excel':
            df = pd.read_excel(dataset.file.path)
        else:
            df = pd.read_json(dataset.file.path)
    except Exception:
        df = pd.DataFrame()

    # Section 1: Dataset Overview
    if 'overview' in sections:
        elements.append(Paragraph("1. Dataset Overview", heading_style))
        overview_data = [
            ['Property', 'Value'],
            ['Name', dataset.name],
            ['File Type', dataset.file_type.upper()],
            ['Rows', str(dataset.num_rows)],
            ['Columns', str(dataset.num_columns)],
            ['Quality Score', f"{dataset.quality_score}/100"],
            ['Memory Usage', f"{dataset.memory_usage} MB"],
            ['Upload Date', dataset.created_at.strftime('%Y-%m-%d')],
        ]
        t = Table(overview_data, colWidths=[200, 280])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7C3AED')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))

    # Section 2: Column Analysis
    if 'columns' in sections and len(df) > 0:
        elements.append(Paragraph("2. Column Analysis", heading_style))
        col_data = [['Column', 'Type', 'Missing', 'Unique']]
        for col in df.columns[:20]:
            col_data.append([
                str(col)[:25], str(df[col].dtype),
                str(int(df[col].isnull().sum())),
                str(int(df[col].nunique())),
            ])
        t = Table(col_data, colWidths=[150, 100, 80, 80])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))

    # Section 3: Data Quality
    if 'quality' in sections:
        elements.append(Paragraph("3. Data Quality Assessment", heading_style))
        total_missing = sum(dataset.missing_values.values()) if dataset.missing_values else 0
        quality_data = [
            ['Metric', 'Value', 'Status'],
            ['Quality Score', f"{dataset.quality_score}/100", 'Excellent' if dataset.quality_score >= 80 else 'Good' if dataset.quality_score >= 60 else 'Needs Improvement'],
            ['Missing Values', str(total_missing), 'Clean' if total_missing == 0 else 'Action Needed'],
            ['Duplicate Rows', str(dataset.duplicate_rows), 'Clean' if dataset.duplicate_rows == 0 else 'Action Needed'],
        ]
        t = Table(quality_data, colWidths=[160, 160, 160])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10B981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))

    # Section 4: Statistical Summary
    if 'statistics' in sections and len(df) > 0:
        numeric_df = df.select_dtypes(include=['int64', 'float64'])
        if len(numeric_df.columns) > 0:
            elements.append(Paragraph("4. Statistical Summary", heading_style))
            desc = numeric_df.describe().round(2)
            stat_data = [['Statistic'] + list(desc.columns[:8])]
            for idx in desc.index:
                row = [idx] + [str(desc.loc[idx, col]) for col in desc.columns[:8]]
                stat_data.append(row)
            col_widths = [80] + [60] * min(len(desc.columns), 8)
            t = Table(stat_data, colWidths=col_widths)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#06B6D4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 15))

    # Section 5: ML Model Results
    if 'ml_results' in sections:
        models = MLModel.objects.filter(user=user, dataset=dataset)
        if models.exists():
            elements.append(Paragraph("5. ML Model Results", heading_style))
            ml_data = [['Model', 'Type', 'Accuracy/R²', 'F1 Score']]
            for m in models[:10]:
                metrics = m.metrics or {}
                acc = metrics.get('accuracy', metrics.get('r2', '-'))
                f1 = metrics.get('f1', '-')
                if isinstance(acc, float):
                    acc = f"{acc:.4f}"
                if isinstance(f1, float):
                    f1 = f"{f1:.4f}"
                ml_data.append([m.name[:30], m.get_model_type_display(), str(acc), str(f1)])
            t = Table(ml_data, colWidths=[130, 130, 100, 100])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F59E0B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ]))
            elements.append(t)

    # Footer
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#94A3B8')))
    elements.append(Paragraph("Generated by IntelliHub AI — Intelligent Data Analytics Platform", ParagraphStyle('Footer', fontSize=8, textColor=colors.HexColor('#94A3B8'), alignment=1)))

    doc.build(elements)
    file_size = os.path.getsize(filepath)
    return f"reports/{filename}", file_size


@login_required
def report_list(request):
    """List all reports for current user."""
    try:
        reports = Report.objects.filter(user=request.user).select_related('dataset')
        paginator = Paginator(reports, 25)
        page = request.GET.get('page')
        reports_page = paginator.get_page(page)
        return render(request, 'reports/list.html', {'reports': reports_page})
    except Exception as e:
        logger.exception(f"Error in report_list: {e}")
        messages.error(request, "Could not load reports.")
        return redirect('dashboard:home')


@login_required
def generate_report_view(request):
    """Show report generation form or generate PDF."""
    try:
        datasets = Dataset.objects.filter(user=request.user)

        if request.method == 'POST':
            dataset_id = request.POST.get('dataset_id')
            title = request.POST.get('title', 'Analysis Report')
            sections = request.POST.getlist('sections')
            report_type = request.POST.get('report_type', 'dataset_summary')

            if not dataset_id:
                messages.error(request, "Please select a dataset.")
                return render(request, 'reports/generate.html', {'datasets': datasets})

            dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)

            if not sections:
                sections = ['overview', 'columns', 'quality', 'statistics']

            file_path, file_size = _generate_pdf_report(dataset, title, sections, request.user)

            Report.objects.create(
                user=request.user, dataset=dataset, title=title,
                report_type=report_type, report_file=file_path,
                sections=sections, file_size=file_size,
            )

            messages.success(request, f"Report '{title}' generated successfully!")
            return redirect('reports:list')

        return render(request, 'reports/generate.html', {'datasets': datasets})
    except Exception as e:
        logger.exception(f"Error generating report: {e}")
        messages.error(request, "Could not generate report.")
        return redirect('reports:list')


@login_required
def report_download(request, pk):
    """Download a report PDF."""
    try:
        report = get_object_or_404(Report, pk=pk, user=request.user)
        if report.report_file:
            return FileResponse(open(report.report_file.path, 'rb'), as_attachment=True, filename=f"{report.title}.pdf")
        messages.error(request, "Report file not found.")
        return redirect('reports:list')
    except Exception as e:
        logger.exception(f"Error downloading report: {e}")
        messages.error(request, "Download failed.")
        return redirect('reports:list')


@login_required
@require_POST
def report_delete(request, pk):
    """Delete a report."""
    try:
        report = get_object_or_404(Report, pk=pk, user=request.user)
        if report.report_file:
            try:
                os.remove(report.report_file.path)
            except OSError:
                pass
        report.delete()
        messages.success(request, "Report deleted.")
        return redirect('reports:list')
    except Exception as e:
        logger.exception(f"Error deleting report: {e}")
        messages.error(request, "Could not delete report.")
        return redirect('reports:list')
