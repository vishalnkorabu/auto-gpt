from __future__ import annotations

import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application


sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "research_agent_django.settings")

application = get_wsgi_application()
