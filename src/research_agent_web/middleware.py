from __future__ import annotations

from time import perf_counter

from django.http import HttpRequest, HttpResponse

from .models import ApiRequestLog


class ApiRequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        started_at = perf_counter()
        error_message = ""
        try:
            response = self.get_response(request)
        except Exception as exc:
            error_message = str(exc)
            self._record(request, 500, started_at, error_message)
            raise
        self._record(request, response.status_code, started_at, error_message)
        return response

    def _record(self, request: HttpRequest, status_code: int, started_at: float, error_message: str) -> None:
        if not request.path.startswith("/api/"):
            return
        duration_ms = int((perf_counter() - started_at) * 1000)
        ApiRequestLog.objects.create(
            user=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
            method=request.method,
            path=request.path[:255],
            status_code=status_code,
            duration_ms=duration_ms,
            error_message=error_message,
        )
