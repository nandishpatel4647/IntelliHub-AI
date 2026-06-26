"""
WSGI config for IntelliHub AI project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intellihub.settings')
application = get_wsgi_application()
