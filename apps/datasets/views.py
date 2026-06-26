"""
IntelliHub AI — Dataset Manager Views
=======================================
Handles dataset upload with auto-profiling, listing with search
and pagination, detail inspection, deletion, and favouriting.
"""

import logging
import os

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import Dataset

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.json'}
EXTENSION_TO_TYPE = {
    '.csv': 'csv',
    '.xlsx': 'excel',
    '.xls': 'excel',
    '.json': 'json',
}
ITEMS_PER_PAGE = 25


# ─── Helpers ──────────────────────────────────────────────────────

def calculate_quality_score(df):
    """
    Compute a data-quality score between 0 and 100 for *df*.

    Scoring rules
    -------------
    * Start at 100.
    * For every 1 % of total cell values that are missing, subtract 0.5.
    * For every 1 % of rows that are duplicates, subtract 0.3.
    * If the DataFrame contains 3 or more distinct column dtypes, add 5
      (reward for mixed/rich schema).
    * Final score is clamped to [0, 100].
    """
    score = 100.0

    total_cells = df.shape[0] * df.shape[1]
    if total_cells > 0:
        missing_pct = (df.isnull().sum().sum() / total_cells) * 100
        score -= missing_pct * 0.5

    if len(df) > 0:
        dup_pct = (df.duplicated().sum() / len(df)) * 100
        score -= dup_pct * 0.3

    unique_dtypes = df.dtypes.nunique()
    if unique_dtypes >= 3:
        score += 5.0

    return round(max(0.0, min(100.0, score)), 2)


def _read_dataframe(file_path, file_type):
    """
    Read an uploaded file into a pandas DataFrame.

    Parameters
    ----------
    file_path : str
        Absolute path to the saved file on disk.
    file_type : str
        One of 'csv', 'excel', 'json'.

    Returns
    -------
    pd.DataFrame
    """
    if file_type == 'csv':
        return pd.read_csv(file_path, low_memory=False)
    elif file_type == 'excel':
        return pd.read_excel(file_path, engine='openpyxl')
    elif file_type == 'json':
        return pd.read_json(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


# ─── Upload ──────────────────────────────────────────────────────

@login_required
def upload_dataset(request):
    """
    Handle dataset upload (POST) or display the upload form (GET).

    POST workflow
    -------------
    1. Validate quota, file extension, and file size.
    2. Persist the file via a Dataset model instance (initially minimal).
    3. Read the file into a DataFrame and auto-profile it.
    4. Populate profiling fields, compute quality_score, and save.
    5. Redirect to the dataset detail page on success.
    """
    if request.method == 'GET':
        return render(request, 'datasets/upload.html')

    # ── POST ──────────────────────────────────────────────────
    try:
        # Quota check (method provided by the custom User model)
        if hasattr(request.user, 'has_quota_remaining') and not request.user.has_quota_remaining():
            messages.error(request, "You have reached your dataset upload quota.")
            return redirect('datasets:list')

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            messages.error(request, "No file was provided. Please select a file to upload.")
            return redirect('datasets:upload')

        # Extension & type detection
        _, ext = os.path.splitext(uploaded_file.name)
        ext = ext.lower()
        if ext not in ALLOWED_EXTENSIONS:
            messages.error(
                request,
                f"Unsupported file type '{ext}'. Allowed formats: CSV, Excel (.xlsx/.xls), JSON.",
            )
            return redirect('datasets:upload')

        file_type = EXTENSION_TO_TYPE[ext]

        # Size check
        if uploaded_file.size > MAX_FILE_SIZE_BYTES:
            size_mb = round(uploaded_file.size / (1024 * 1024), 1)
            messages.error(
                request,
                f"File is {size_mb} MB which exceeds the 50 MB limit.",
            )
            return redirect('datasets:upload')

        # Use the provided name or fall back to the original filename
        dataset_name = request.POST.get('name', '').strip()
        if not dataset_name:
            dataset_name = os.path.splitext(uploaded_file.name)[0]

        description = request.POST.get('description', '').strip()

        # Persist file first so we have a concrete path for pandas
        dataset = Dataset(
            user=request.user,
            name=dataset_name,
            description=description,
            file=uploaded_file,
            file_type=file_type,
            file_size=uploaded_file.size,
        )
        dataset.save()

        # ── Auto-profile ─────────────────────────────────────
        try:
            df = _read_dataframe(dataset.file.path, file_type)

            dataset.num_rows = int(df.shape[0])
            dataset.num_columns = int(df.shape[1])
            dataset.column_names = list(df.columns.astype(str))
            dataset.column_types = {
                col: str(dtype) for col, dtype in df.dtypes.items()
            }
            dataset.missing_values = {
                col: int(count)
                for col, count in df.isnull().sum().items()
                if count > 0
            }
            dataset.duplicate_rows = int(df.duplicated().sum())
            dataset.memory_usage = round(
                df.memory_usage(deep=True).sum() / (1024 * 1024), 2
            )
            dataset.quality_score = calculate_quality_score(df)
            dataset.save()
        except Exception as profile_err:
            logger.warning(
                "Auto-profiling failed for dataset %s (pk=%s): %s",
                dataset.name, dataset.pk, profile_err,
            )
            # Dataset is already saved with file — user can still view it

        messages.success(
            request,
            f"Dataset '{dataset.name}' uploaded successfully — "
            f"{dataset.num_rows:,} rows × {dataset.num_columns} columns.",
        )
        return redirect('datasets:detail', pk=dataset.pk)

    except Exception as e:
        logger.exception("Error uploading dataset: %s", e)
        messages.error(request, "Something went wrong while uploading the dataset.")
        return redirect('datasets:upload')


# ─── List ─────────────────────────────────────────────────────────

@login_required
def dataset_list(request):
    """
    Display all datasets owned by the current user.

    Supports:
    * Full-text search across name and description via ``?q=…``
    * Pagination (25 items per page) via ``?page=…``
    """
    try:
        search_query = request.GET.get('q', '').strip()

        qs = (
            Dataset.objects
            .filter(user=request.user)
            .select_related('user')
        )

        if search_query:
            qs = qs.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
            )

        paginator = Paginator(qs, ITEMS_PER_PAGE)
        page_number = request.GET.get('page')

        try:
            datasets = paginator.page(page_number)
        except PageNotAnInteger:
            datasets = paginator.page(1)
        except EmptyPage:
            datasets = paginator.page(paginator.num_pages)

        context = {
            'datasets': datasets,
            'search_query': search_query,
            'paginator': paginator,
            'total_count': qs.count(),
        }
        return render(request, 'datasets/list.html', context)

    except Exception as e:
        logger.exception("Error listing datasets: %s", e)
        messages.error(request, "Something went wrong while loading your datasets.")
        return redirect('dashboard:home')


# ─── Detail ───────────────────────────────────────────────────────

@login_required
def dataset_detail(request, pk):
    """
    Show detailed profiling information for a single dataset.

    Includes a 10-row data preview rendered as an HTML table and
    per-column statistics (missing count, unique values, and
    descriptive stats for numeric columns).
    """
    try:
        dataset = get_object_or_404(
            Dataset.objects.select_related('user'),
            pk=pk,
            user=request.user,
        )

        preview_html = ''
        column_stats = []

        try:
            df = _read_dataframe(dataset.file.path, dataset.file_type)

            # 10-row preview
            preview_html = (
                df.head(10)
                .to_html(
                    classes='intel-table',
                    index=False,
                    border=0,
                    na_rep='—',
                )
            )

            # Per-column statistics
            for col in df.columns:
                stat = {
                    'name': str(col),
                    'dtype': str(df[col].dtype),
                    'missing': int(df[col].isnull().sum()),
                    'missing_pct': round(
                        df[col].isnull().sum() / len(df) * 100, 1
                    ) if len(df) > 0 else 0.0,
                    'unique': int(df[col].nunique()),
                }

                if pd.api.types.is_numeric_dtype(df[col]):
                    desc = df[col].describe()
                    stat.update({
                        'mean': round(float(desc.get('mean', 0)), 4),
                        'std': round(float(desc.get('std', 0)), 4),
                        'min': round(float(desc.get('min', 0)), 4),
                        'max': round(float(desc.get('max', 0)), 4),
                    })

                column_stats.append(stat)
        except Exception as read_err:
            logger.warning(
                "Could not read dataset file for preview (pk=%s): %s",
                pk, read_err,
            )
            messages.warning(
                request,
                "Unable to generate data preview. The file may be corrupted.",
            )

        # Calculate total missing values across all columns
        total_missing = sum(dataset.missing_values.values()) if dataset.missing_values else 0

        context = {
            'dataset': dataset,
            'preview_html': preview_html,
            'column_stats': column_stats,
            'shape': f"{dataset.num_rows:,} × {dataset.num_columns}",
            'total_missing': total_missing,
        }
        return render(request, 'datasets/detail.html', context)

    except Exception as e:
        logger.exception("Error viewing dataset detail (pk=%s): %s", pk, e)
        messages.error(request, "Something went wrong while loading the dataset.")
        return redirect('datasets:list')


# ─── Delete ───────────────────────────────────────────────────────

@login_required
def dataset_delete(request, pk):
    """
    Delete a dataset and its file from disk.  POST only.
    """
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('datasets:list')

    try:
        dataset = get_object_or_404(Dataset, pk=pk, user=request.user)
        dataset_name = dataset.name

        # Remove physical file
        if dataset.file and os.path.isfile(dataset.file.path):
            try:
                os.remove(dataset.file.path)
            except OSError as file_err:
                logger.warning("Could not delete file for dataset %s: %s", pk, file_err)

        # Remove version files
        for version in dataset.versions.all():
            if version.file and os.path.isfile(version.file.path):
                try:
                    os.remove(version.file.path)
                except OSError:
                    pass

        dataset.delete()

        messages.success(request, f"Dataset '{dataset_name}' has been deleted.")
        return redirect('datasets:list')

    except Exception as e:
        logger.exception("Error deleting dataset (pk=%s): %s", pk, e)
        messages.error(request, "Something went wrong while deleting the dataset.")
        return redirect('datasets:list')


# ─── Toggle Favourite ────────────────────────────────────────────

@login_required
def dataset_toggle_favorite(request, pk):
    """
    Toggle the ``is_favorite`` flag on a dataset.  POST only.

    Returns a JSON response with the new favourite state so the
    front-end can update the star icon without a full page reload.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        dataset = get_object_or_404(Dataset, pk=pk, user=request.user)
        dataset.is_favorite = not dataset.is_favorite
        dataset.save(update_fields=['is_favorite'])

        return JsonResponse({
            'success': True,
            'is_favorite': dataset.is_favorite,
        })

    except Exception as e:
        logger.exception("Error toggling favourite (pk=%s): %s", pk, e)
        return JsonResponse({'error': 'Something went wrong.'}, status=500)
