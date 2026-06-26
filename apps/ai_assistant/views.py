"""
IntelliHub AI — AI Chat Assistant Views
==========================================
Rule-based intelligent assistant (no API key needed).
"""

import json
import logging
import pandas as pd
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.datasets.models import Dataset
from .models import ChatSession, ChatMessage

logger = logging.getLogger(__name__)


def _generate_smart_response(message, dataset_id, user):
    """Rule-based intelligent response engine."""
    msg = message.lower().strip()
    response = ""

    # Load dataset context if provided
    dataset = None
    df = None
    if dataset_id:
        try:
            dataset = Dataset.objects.get(pk=dataset_id, user=user)
            if dataset.file_type == 'csv':
                df = pd.read_csv(dataset.file.path)
            elif dataset.file_type == 'excel':
                df = pd.read_excel(dataset.file.path)
        except Exception:
            dataset = None

    # 1. Greeting
    if any(w in msg for w in ['hello', 'hi ', 'hey', 'greetings', 'good morning', 'good evening']):
        response = (
            f"👋 Hello **{user.first_name or user.username}**! Welcome to IntelliHub AI Assistant.\n\n"
            "I can help you with:\n"
            "- 📊 **Dataset analysis** — Ask about your data\n"
            "- 🤖 **ML recommendations** — Which algorithm to use\n"
            "- 🧹 **Cleaning advice** — Handle missing values & outliers\n"
            "- 📈 **Visualization tips** — Best charts for your data\n"
            "- 📚 **Statistics help** — Mean, median, correlation\n\n"
            "Try asking: *\"What does my dataset look like?\"* or *\"Which model should I use?\"*"
        )

    # 2. Dataset questions
    elif any(w in msg for w in ['dataset', 'data', 'columns', 'rows', 'shape', 'info', 'describe', 'summary']):
        if df is not None:
            numeric = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
            categorical = df.select_dtypes(include=['object', 'category']).columns.tolist()
            missing_total = int(df.isnull().sum().sum())
            response = (
                f"📊 **Dataset: {dataset.name}**\n\n"
                f"- **Shape:** {df.shape[0]} rows × {df.shape[1]} columns\n"
                f"- **Numeric columns** ({len(numeric)}): {', '.join(numeric[:8])}\n"
                f"- **Categorical columns** ({len(categorical)}): {', '.join(categorical[:8])}\n"
                f"- **Missing values:** {missing_total} total\n"
                f"- **Duplicate rows:** {int(df.duplicated().sum())}\n"
                f"- **Quality score:** {dataset.quality_score}/100\n"
                f"- **Memory usage:** {round(df.memory_usage(deep=True).sum()/1024/1024, 2)} MB\n\n"
                "💡 Try asking me to *recommend an ML model* or *suggest cleaning steps*!"
            )
        else:
            response = (
                "📊 To analyze a specific dataset, select one from the dropdown above.\n\n"
                "Here's what I can tell you about your data:\n"
                "- Column types and distributions\n"
                "- Missing value patterns\n"
                "- Statistical summaries\n"
                "- Quality assessments"
            )

    # 3. ML Recommendations
    elif any(w in msg for w in ['recommend', 'algorithm', 'model', 'which model', 'best model', 'train', 'predict']):
        if df is not None:
            n_rows = len(df)
            n_cols = len(df.columns)
            numeric = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
            categorical = df.select_dtypes(include=['object', 'category']).columns.tolist()

            response = f"🤖 **ML Recommendations for {dataset.name}**\n\n"
            response += f"Your dataset has **{n_rows} rows** and **{n_cols} columns**.\n\n"

            if len(categorical) > 0:
                response += "**For Classification** (predicting categories):\n"
                if n_rows < 1000:
                    response += "- 🏆 **Logistic Regression** — Great for small datasets\n"
                    response += "- **KNN** — Simple, works well with few features\n"
                    response += "- **Decision Tree** — Easy to interpret\n"
                else:
                    response += "- 🏆 **Random Forest** — Best overall accuracy\n"
                    response += "- **SVM** — Good with clear margins\n"
                    response += "- **Logistic Regression** — Fast baseline\n"

            if len(numeric) >= 2:
                response += "\n**For Regression** (predicting numbers):\n"
                if n_cols < 10:
                    response += "- 🏆 **Linear Regression** — Start here as baseline\n"
                    response += "- **Ridge Regression** — If you suspect multicollinearity\n"
                else:
                    response += "- 🏆 **Random Forest Regressor** — Handles complex patterns\n"
                    response += "- **Lasso Regression** — Good for feature selection\n"

            response += "\n💡 Go to **ML Studio** to start training!"
        else:
            response = (
                "🤖 **Choosing the Right ML Model:**\n\n"
                "**Classification** (predicting categories):\n"
                "- **Logistic Regression** — Binary classification baseline\n"
                "- **Random Forest** — Best general-purpose classifier\n"
                "- **SVM** — Good for complex decision boundaries\n\n"
                "**Regression** (predicting numbers):\n"
                "- **Linear Regression** — Simple, interpretable\n"
                "- **Random Forest Regressor** — Handles non-linear patterns\n"
                "- **Ridge/Lasso** — When you have many features\n\n"
                "Select a dataset above for personalized recommendations!"
            )

    # 4. Cleaning advice
    elif any(w in msg for w in ['clean', 'missing', 'null', 'nan', 'outlier', 'duplicate', 'impute']):
        if df is not None:
            missing = df.isnull().sum()
            cols_with_missing = missing[missing > 0]
            response = f"🧹 **Cleaning Report for {dataset.name}**\n\n"
            if len(cols_with_missing) > 0:
                response += "**Columns with missing values:**\n"
                for col, count in cols_with_missing.items():
                    pct = round(count / len(df) * 100, 1)
                    strategy = "median" if df[col].dtype in ['int64', 'float64'] else "mode"
                    response += f"- `{col}`: {count} missing ({pct}%) → Fill with **{strategy}**\n"
            else:
                response += "✅ No missing values found!\n"
            dups = int(df.duplicated().sum())
            if dups > 0:
                response += f"\n⚠️ **{dups} duplicate rows** found → Remove them\n"
            response += "\n💡 Go to **Data Cleaning** for one-click auto-clean!"
        else:
            response = (
                "🧹 **Data Cleaning Best Practices:**\n\n"
                "**Missing Values:**\n"
                "- Numeric: Fill with **median** (robust to outliers)\n"
                "- Categorical: Fill with **mode** (most frequent)\n"
                "- High % missing (>50%): Consider **dropping** the column\n\n"
                "**Outliers:**\n"
                "- Use **IQR method**: values beyond Q1-1.5×IQR or Q3+1.5×IQR\n"
                "- Cap (clip) rather than delete\n\n"
                "**Duplicates:**\n"
                "- Always check and remove before training models"
            )

    # 5. Visualization tips
    elif any(w in msg for w in ['visual', 'chart', 'plot', 'graph', 'correlation', 'distribution']):
        response = (
            "📈 **Visualization Guide:**\n\n"
            "**Explore Distribution:**\n"
            "- **Histogram** — Shape of a single numeric variable\n"
            "- **Box Plot** — Detect outliers and quartiles\n"
            "- **Violin Plot** — Distribution + density\n\n"
            "**Compare Variables:**\n"
            "- **Scatter Plot** — Relationship between two numbers\n"
            "- **Heatmap** — Correlation between all features\n"
            "- **Line Chart** — Trends over time\n\n"
            "**Categorical Data:**\n"
            "- **Bar Chart** — Compare counts/values\n"
            "- **Pie Chart** — Proportions (max 8 categories)\n"
            "- **Treemap** — Hierarchical proportions\n\n"
            "💡 Go to **EDA Studio** to create interactive charts!"
        )

    # 6. Statistics
    elif any(w in msg for w in ['mean', 'median', 'std', 'average', 'statistic', 'skew', 'variance']):
        if df is not None:
            numeric = df.select_dtypes(include=['int64', 'float64'])
            if len(numeric.columns) > 0:
                response = f"📐 **Statistics for {dataset.name}:**\n\n"
                for col in numeric.columns[:6]:
                    response += (
                        f"**{col}:** Mean={numeric[col].mean():.2f}, "
                        f"Median={numeric[col].median():.2f}, "
                        f"Std={numeric[col].std():.2f}, "
                        f"Min={numeric[col].min():.2f}, Max={numeric[col].max():.2f}\n"
                    )
            else:
                response = "No numeric columns found in this dataset."
        else:
            response = (
                "📐 **Key Statistical Concepts:**\n\n"
                "- **Mean** — Average of all values\n"
                "- **Median** — Middle value (robust to outliers)\n"
                "- **Std Dev** — How spread out the data is\n"
                "- **Skewness** — Symmetry of distribution\n"
                "- **Correlation** — Linear relationship between two variables (-1 to +1)"
            )

    # 7. Help
    elif any(w in msg for w in ['help', 'how to', 'what can', 'features', 'guide', 'tutorial']):
        response = (
            "🚀 **IntelliHub AI Features:**\n\n"
            "1. 📊 **Datasets** — Upload CSV, Excel, JSON with auto-profiling\n"
            "2. 🧹 **Data Cleaning** — AI-powered cleaning with one click\n"
            "3. 📈 **EDA Studio** — 10+ interactive chart types\n"
            "4. 🤖 **ML Studio** — Train 11+ algorithms instantly\n"
            "5. 🧠 **Deep Learning** — Build neural networks\n"
            "6. 🕷️ **Web Scraper** — Extract data from websites\n"
            "7. 🔌 **REST API** — Access your data programmatically\n"
            "8. 📄 **Reports** — Generate PDF analysis reports\n\n"
            "Just ask me anything about your data!"
        )

    # 8. Fallback
    else:
        response = (
            f"🤔 I'm not sure about that, but here's what I can help with:\n\n"
            "- **\"Describe my dataset\"** — Get data overview\n"
            "- **\"Which model should I use?\"** — ML recommendations\n"
            "- **\"How to clean my data?\"** — Cleaning strategies\n"
            "- **\"What chart should I use?\"** — Visualization guide\n"
            "- **\"Show statistics\"** — Key metrics for your data\n\n"
            "Try selecting a dataset above for personalized answers!"
        )

    return response


@login_required
def chat_home(request):
    """Chat assistant home page."""
    try:
        sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')
        datasets = Dataset.objects.filter(user=request.user)

        # Get or create default session
        if sessions.exists():
            current_session = sessions.first()
        else:
            current_session = ChatSession.objects.create(user=request.user, title='New Chat')

        chat_messages = current_session.messages.all()
        context = {
            'current_session': current_session,
            'sessions': sessions,
            'chat_messages': chat_messages,
            'datasets': datasets,
        }
        return render(request, 'ai_assistant/chat.html', context)
    except Exception as e:
        logger.exception(f"Error in chat_home: {e}")
        messages.error(request, "Could not load AI Assistant.")
        return redirect('dashboard:home')


@login_required
def chat_session_view(request, session_pk):
    """View a specific chat session."""
    try:
        current_session = get_object_or_404(ChatSession, pk=session_pk, user=request.user)
        sessions = ChatSession.objects.filter(user=request.user)
        datasets = Dataset.objects.filter(user=request.user)
        chat_messages = current_session.messages.all()
        context = {
            'current_session': current_session,
            'sessions': sessions,
            'chat_messages': chat_messages,
            'datasets': datasets,
        }
        return render(request, 'ai_assistant/chat.html', context)
    except Exception as e:
        logger.exception(f"Error in chat_session_view: {e}")
        messages.error(request, "Could not load chat session.")
        return redirect('ai_assistant:home')


@login_required
@require_POST
def send_message(request):
    """Handle sending a message and generating AI response."""
    try:
        body = json.loads(request.body)
        session_id = body.get('session_id')
        message = body.get('message', '').strip()
        dataset_id = body.get('dataset_id')

        if not message:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)

        session = get_object_or_404(ChatSession, pk=session_id, user=request.user)

        # Save user message
        ChatMessage.objects.create(session=session, role='user', content=message)

        # Generate response
        response = _generate_smart_response(message, dataset_id, request.user)

        # Save assistant response
        ChatMessage.objects.create(session=session, role='assistant', content=response)

        # Update session title on first message
        if session.messages.filter(role='user').count() == 1:
            session.title = message[:50]
            session.save()

        return JsonResponse({'response': response, 'session_id': session.pk})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.exception(f"Error in send_message: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def new_session(request):
    """Create a new chat session."""
    try:
        session = ChatSession.objects.create(user=request.user, title='New Chat')
        return redirect('ai_assistant:session', session_pk=session.pk)
    except Exception as e:
        logger.exception(f"Error creating session: {e}")
        messages.error(request, "Could not create new chat.")
        return redirect('ai_assistant:home')


@login_required
@require_POST
def delete_session(request, session_pk):
    """Delete a chat session."""
    try:
        session = get_object_or_404(ChatSession, pk=session_pk, user=request.user)
        session.delete()
        messages.success(request, "Chat session deleted.")
        return redirect('ai_assistant:home')
    except Exception as e:
        logger.exception(f"Error deleting session: {e}")
        messages.error(request, "Could not delete chat session.")
        return redirect('ai_assistant:home')
