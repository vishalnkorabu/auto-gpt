try:
    from .celery import app as celery_app
except ModuleNotFoundError:  # pragma: no cover - dev fallback when Celery isn't installed yet.
    celery_app = None

__all__ = ("celery_app",)
