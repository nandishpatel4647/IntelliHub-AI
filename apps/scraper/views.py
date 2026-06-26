"""
IntelliHub AI — Web Scraper Views
====================================
Point-and-scrape data extraction with BeautifulSoup.
"""

import os
import logging
import pandas as pd
from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
import requests
from bs4 import BeautifulSoup
from .models import ScrapeJob

logger = logging.getLogger(__name__)


@login_required
def scraper_home(request):
    """Scraper home — new job form and history."""
    try:
        jobs = ScrapeJob.objects.filter(user=request.user)
        return render(request, 'scraper/home.html', {'jobs': jobs})
    except Exception as e:
        logger.exception(f"Error in scraper_home: {e}")
        messages.error(request, "Could not load Web Scraper.")
        return redirect('dashboard:home')


@login_required
@require_POST
def start_scrape(request):
    """Start a new scraping job."""
    try:
        import json
        body = json.loads(request.body)
        url = body.get('url', '').strip()
        job_name = body.get('job_name', 'Untitled Scrape').strip()

        if not url or not url.startswith(('http://', 'https://')):
            return JsonResponse({'error': 'Please provide a valid URL (starting with http:// or https://)'}, status=400)

        job = ScrapeJob.objects.create(user=request.user, url=url, job_name=job_name, status='running')

        try:
            headers = {'User-Agent': 'IntelliHub AI Scraper/1.0 (Educational Project)'}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, 'lxml')
            tables = soup.find_all('table')
            df = None

            if tables:
                # Find the largest table
                largest_table = max(tables, key=lambda t: len(t.find_all('tr')))
                dfs = pd.read_html(str(largest_table))
                if dfs:
                    df = dfs[0]
            else:
                # Extract from lists or structured content
                items = []
                for ul in soup.find_all(['ul', 'ol']):
                    for li in ul.find_all('li'):
                        text = li.get_text(strip=True)
                        if text:
                            items.append({'content': text})
                if items:
                    df = pd.DataFrame(items)
                else:
                    # Extract paragraphs
                    paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]
                    if paragraphs:
                        df = pd.DataFrame({'text': paragraphs})

            if df is not None and len(df) > 0:
                save_dir = os.path.join(settings.MEDIA_ROOT, 'scrapes')
                os.makedirs(save_dir, exist_ok=True)
                filename = f"scrape_{job.pk}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
                filepath = os.path.join(save_dir, filename)
                df.to_csv(filepath, index=False)

                job.status = 'done'
                job.result_file = f"scrapes/{filename}"
                job.rows_scraped = len(df)
                job.columns_scraped = len(df.columns)
                job.completed_at = timezone.now()
                job.save()

                return JsonResponse({
                    'success': True, 'job_id': job.pk, 'status': 'done',
                    'rows_scraped': len(df), 'columns': len(df.columns),
                    'message': f"Successfully scraped {len(df)} rows!"
                })
            else:
                job.status = 'failed'
                job.error_message = 'No extractable data found on this page.'
                job.save()
                return JsonResponse({'success': False, 'error': 'No data found on this page.'}, status=400)

        except requests.RequestException as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
            return JsonResponse({'error': f'Request failed: {str(e)}'}, status=400)

    except Exception as e:
        logger.exception(f"Error in start_scrape: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def scrape_detail(request, pk):
    """View scrape job details and results."""
    try:
        job = get_object_or_404(ScrapeJob, pk=pk, user=request.user)
        preview_html = ''
        if job.status == 'done' and job.result_file:
            try:
                df = pd.read_csv(job.result_file.path)
                preview_html = df.head(20).to_html(classes='intel-table', border=0, index=False)
            except Exception:
                preview_html = '<p>Could not load preview.</p>'
        return render(request, 'scraper/detail.html', {'job': job, 'preview_html': preview_html})
    except Exception as e:
        logger.exception(f"Error in scrape_detail: {e}")
        messages.error(request, "Could not load scrape details.")
        return redirect('scraper:home')


@login_required
def download_scrape(request, pk):
    """Download scrape result as CSV."""
    try:
        job = get_object_or_404(ScrapeJob, pk=pk, user=request.user)
        if job.result_file:
            return FileResponse(open(job.result_file.path, 'rb'), as_attachment=True, filename=f"{job.job_name}.csv")
        messages.error(request, "No file available for download.")
        return redirect('scraper:detail', pk=pk)
    except Exception as e:
        logger.exception(f"Error downloading scrape: {e}")
        messages.error(request, "Download failed.")
        return redirect('scraper:home')


@login_required
@require_POST
def delete_scrape(request, pk):
    """Delete a scrape job."""
    try:
        job = get_object_or_404(ScrapeJob, pk=pk, user=request.user)
        if job.result_file:
            try:
                os.remove(job.result_file.path)
            except OSError:
                pass
        job.delete()
        messages.success(request, "Scrape job deleted.")
        return redirect('scraper:home')
    except Exception as e:
        logger.exception(f"Error deleting scrape: {e}")
        messages.error(request, "Could not delete scrape job.")
        return redirect('scraper:home')
