from __future__ import annotations

from django.apps import AppConfig


class ResearchAgentWebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "research_agent_web"

    def ready(self) -> None:
        from . import signals  # noqa: F401
