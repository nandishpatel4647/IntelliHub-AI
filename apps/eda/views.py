"""
IntelliHub AI — EDA & Visualization Views
============================================
Auto-EDA with 10+ Plotly chart types and AI insights.
"""

import json
import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.datasets.models import Dataset

logger = logging.getLogger(__name__)

PLOTLY_TEMPLATE = 'plotly_dark'
CHART_COLORS = ['#7C3AED', '#06B6D4', '#10B981', '#F59E0B', '#EC4899', '#2563EB']
LAYOUT_DEFAULTS = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Inter, sans-serif', color='#94A3B8'),
    title_font=dict(family='Space Grotesk, sans-serif', size=18, color='#F8FAFC'),
    margin=dict(t=50, l=20, r=20, b=20),
)


def _load_df(dataset):
    """Load dataset file into DataFrame."""
    if dataset.file_type == 'csv':
        return pd.read_csv(dataset.file.path)
    elif dataset.file_type == 'excel':
        return pd.read_excel(dataset.file.path)
    return pd.read_json(dataset.file.path)


@login_required
def eda_home(request):
    """EDA landing — pick a dataset to analyze."""
    try:
        datasets = Dataset.objects.filter(user=request.user).select_related('user')
        return render(request, 'eda/home.html', {'datasets': datasets})
    except Exception as e:
        logger.exception(f"Error in eda_home: {e}")
        messages.error(request, "Could not load EDA studio.")
        return redirect('dashboard:home')


@login_required
def eda_dashboard(request, dataset_pk):
    """Full EDA dashboard for a specific dataset."""
    try:
        dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)
        df = _load_df(dataset)
        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()

        describe_html = ''
        if numeric_cols:
            describe_html = df[numeric_cols].describe().round(2).to_html(
                classes='intel-table', border=0
            )

        context = {
            'dataset': dataset,
            'numeric_cols': numeric_cols,
            'categorical_cols': categorical_cols,
            'all_cols': list(df.columns),
            'describe_html': describe_html,
            'num_numeric': len(numeric_cols),
            'num_categorical': len(categorical_cols),
        }
        return render(request, 'eda/dashboard.html', context)
    except Exception as e:
        logger.exception(f"Error in eda_dashboard: {e}")
        messages.error(request, "Could not load EDA dashboard.")
        return redirect('eda:home')


@login_required
def generate_chart(request, dataset_pk):
    """Generate a Plotly chart via AJAX — returns JSON."""
    try:
        dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)
        df = _load_df(dataset)

        chart_type = request.GET.get('type', 'histogram')
        col_x = request.GET.get('x')
        col_y = request.GET.get('y')
        col_color = request.GET.get('color') or None
        col_size = request.GET.get('size') or None

        fig = None

        if chart_type == 'histogram' and col_x and col_x in df.columns:
            fig = px.histogram(
                df, x=col_x, color=col_color, template=PLOTLY_TEMPLATE,
                color_discrete_sequence=CHART_COLORS,
                title=f"Distribution of {col_x}"
            )
            fig.update_layout(bargap=0.1)

        elif chart_type == 'scatter' and col_x and col_y:
            fig = px.scatter(
                df, x=col_x, y=col_y, color=col_color, template=PLOTLY_TEMPLATE,
                color_discrete_sequence=CHART_COLORS,
                title=f"{col_x} vs {col_y}", opacity=0.7
            )

        elif chart_type == 'heatmap':
            numeric_df = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32'])
            if numeric_df.shape[1] < 2:
                return JsonResponse({'error': 'Need at least 2 numeric columns for heatmap'}, status=400)
            corr = numeric_df.corr()
            fig = px.imshow(
                corr, template=PLOTLY_TEMPLATE, color_continuous_scale='RdBu_r',
                title="Feature Correlation Heatmap", text_auto='.2f'
            )

        elif chart_type == 'box' and col_x and col_x in df.columns:
            fig = px.box(
                df, y=col_x, x=col_color, template=PLOTLY_TEMPLATE,
                color_discrete_sequence=CHART_COLORS,
                title=f"Box Plot of {col_x}"
            )

        elif chart_type == 'violin' and col_x and col_x in df.columns:
            fig = px.violin(
                df, y=col_x, x=col_color, box=True, template=PLOTLY_TEMPLATE,
                color_discrete_sequence=CHART_COLORS,
                title=f"Violin Plot of {col_x}"
            )

        elif chart_type == 'bar' and col_x and col_x in df.columns:
            counts = df[col_x].value_counts().head(15)
            fig = px.bar(
                x=counts.index.astype(str), y=counts.values, template=PLOTLY_TEMPLATE,
                color_discrete_sequence=CHART_COLORS,
                title=f"Top Values in {col_x}",
                labels={'x': col_x, 'y': 'Count'}
            )

        elif chart_type == 'pie' and col_x and col_x in df.columns:
            counts = df[col_x].value_counts().head(8)
            fig = px.pie(
                values=counts.values, names=counts.index.astype(str),
                template=PLOTLY_TEMPLATE, color_discrete_sequence=CHART_COLORS,
                title=f"{col_x} Distribution"
            )

        elif chart_type == 'line' and col_x and col_y:
            fig = px.line(
                df, x=col_x, y=col_y, color=col_color, template=PLOTLY_TEMPLATE,
                color_discrete_sequence=CHART_COLORS,
                title=f"{col_y} over {col_x}"
            )

        elif chart_type == 'treemap' and col_x and col_x in df.columns:
            counts = df[col_x].value_counts().head(20).reset_index()
            counts.columns = [col_x, 'count']
            fig = px.treemap(
                counts, path=[col_x], values='count', template=PLOTLY_TEMPLATE,
                color_discrete_sequence=CHART_COLORS,
                title=f"Treemap of {col_x}"
            )

        elif chart_type == 'bubble' and col_x and col_y:
            fig = px.scatter(
                df, x=col_x, y=col_y, size=col_size, color=col_color,
                template=PLOTLY_TEMPLATE, color_discrete_sequence=CHART_COLORS,
                title=f"Bubble Chart: {col_x} vs {col_y}", opacity=0.7
            )

        if fig is None:
            return JsonResponse({'error': 'Invalid chart configuration. Check parameters.'}, status=400)

        fig.update_layout(**LAYOUT_DEFAULTS)

        return JsonResponse({
            'chart': json.loads(fig.to_json()),
            'ai_insight': _generate_ai_insight(df, chart_type, col_x, col_y),
        })
    except Exception as e:
        logger.exception(f"Error generating chart: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def _generate_ai_insight(df, chart_type, col_x=None, col_y=None):
    """Generate a plain-English AI insight for the chart."""
    try:
        if chart_type == 'heatmap':
            numeric_df = df.select_dtypes(include=['int64', 'float64'])
            if numeric_df.shape[1] >= 2:
                corr = numeric_df.corr()
                upper = corr.where(
                    pd.np.triu(pd.np.ones(corr.shape), k=1).astype(bool)
                    if hasattr(pd, 'np') else
                    __import__('numpy').triu(__import__('numpy').ones(corr.shape), k=1).astype(bool)
                )
                max_corr = upper.abs().unstack().dropna().sort_values(ascending=False)
                if not max_corr.empty:
                    pair = max_corr.index[0]
                    val = max_corr.iloc[0]
                    raw = corr.loc[pair[0], pair[1]]
                    direction = "positive" if raw > 0 else "negative"
                    return (f"💡 Strongest correlation: <strong>{pair[0]}</strong> and "
                            f"<strong>{pair[1]}</strong> have a {direction} correlation of {val:.2f}.")

        if chart_type == 'histogram' and col_x and col_x in df.columns:
            if df[col_x].dtype in ['int64', 'float64']:
                skew = df[col_x].skew()
                if skew > 0.5:
                    desc = "right-skewed (long tail to the right)"
                elif skew < -0.5:
                    desc = "left-skewed (long tail to the left)"
                else:
                    desc = "approximately normally distributed"
                return (f"💡 <strong>{col_x}</strong> is {desc} (skewness: {skew:.2f}). "
                        f"Mean: {df[col_x].mean():.2f}, Median: {df[col_x].median():.2f}.")

        if chart_type == 'scatter' and col_x and col_y:
            if col_x in df.columns and col_y in df.columns:
                if df[col_x].dtype in ['int64', 'float64'] and df[col_y].dtype in ['int64', 'float64']:
                    corr_val = df[col_x].corr(df[col_y])
                    if abs(corr_val) > 0.7:
                        strength = "strong"
                    elif abs(corr_val) > 0.3:
                        strength = "moderate"
                    else:
                        strength = "weak"
                    direction = "positive" if corr_val > 0 else "negative"
                    return (f"💡 There is a <strong>{strength} {direction}</strong> correlation "
                            f"between {col_x} and {col_y} (r = {corr_val:.2f}).")

        if chart_type == 'bar' and col_x and col_x in df.columns:
            top_val = df[col_x].value_counts().index[0]
            top_count = df[col_x].value_counts().iloc[0]
            return (f"💡 The most common value in <strong>{col_x}</strong> is "
                    f"<strong>{top_val}</strong> ({top_count} occurrences, "
                    f"{round(top_count/len(df)*100, 1)}% of data).")

        return "💡 Chart generated successfully. Hover over data points to explore patterns."
    except Exception:
        return "💡 Chart generated. Explore the visualization for insights."
