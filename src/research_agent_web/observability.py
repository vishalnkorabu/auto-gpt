from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from typing import Iterator
from uuid import UUID

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from research_agent.observability import LLMUsageRecord, usage_recorder

from .models import ApiRequestLog, DocumentTask, LLMUsageEvent, ResearchJob


@contextmanager
def observe_research_job(job_id: UUID) -> Iterator[None]:
    def recorder(record: LLMUsageRecord) -> None:
        LLMUsageEvent.objects.create(
            research_job_id=job_id,
            provider=record.provider,
            model=record.model,
            operation=record.operation,
            duration_ms=record.duration_ms,
            prompt_tokens=record.prompt_tokens,
            completion_tokens=record.completion_tokens,
            total_tokens=record.total_tokens,
            estimated_cost_usd=Decimal(f"{record.estimated_cost_usd:.6f}"),
            success=record.success,
            error_message=record.error_message,
        )

    with usage_recorder(recorder):
        yield


@contextmanager
def observe_document_task(task_id: UUID) -> Iterator[None]:
    def recorder(record: LLMUsageRecord) -> None:
        LLMUsageEvent.objects.create(
            document_task_id=task_id,
            provider=record.provider,
            model=record.model,
            operation=record.operation,
            duration_ms=record.duration_ms,
            prompt_tokens=record.prompt_tokens,
            completion_tokens=record.completion_tokens,
            total_tokens=record.total_tokens,
            estimated_cost_usd=Decimal(f"{record.estimated_cost_usd:.6f}"),
            success=record.success,
            error_message=record.error_message,
        )

    with usage_recorder(recorder):
        yield


def build_observability_snapshot(*, user_id: int | None = None) -> dict:
    since = timezone.now() - timezone.timedelta(days=7)

    request_logs = ApiRequestLog.objects.filter(created_at__gte=since)
    research_jobs = ResearchJob.objects.filter(created_at__gte=since)
    document_tasks = DocumentTask.objects.filter(created_at__gte=since)
    usage_events = LLMUsageEvent.objects.filter(created_at__gte=since)

    if user_id is not None:
        request_logs = request_logs.filter(Q(user_id=user_id))
        research_jobs = research_jobs.filter(session__owner_id=user_id)
        document_tasks = document_tasks.filter(owner_id=user_id)
        usage_events = usage_events.filter(Q(research_job__session__owner_id=user_id) | Q(document_task__owner_id=user_id))

    request_totals = request_logs.aggregate(
        total=Count("id"),
        errors=Count("id", filter=Q(status_code__gte=400)),
        avg_duration=Avg("duration_ms"),
    )
    research_totals = research_jobs.aggregate(
        total=Count("id"),
        queued=Count("id", filter=Q(state="queued")),
        running=Count("id", filter=Q(state="running")),
        completed=Count("id", filter=Q(state="completed")),
        failed=Count("id", filter=Q(state="failed")),
    )
    document_totals = document_tasks.aggregate(
        total=Count("id"),
        queued=Count("id", filter=Q(state="queued")),
        running=Count("id", filter=Q(state="running")),
        completed=Count("id", filter=Q(state="completed")),
        failed=Count("id", filter=Q(state="failed")),
        canceled=Count("id", filter=Q(state="canceled")),
    )
    usage_totals = usage_events.aggregate(
        prompt_tokens=Sum("prompt_tokens"),
        completion_tokens=Sum("completion_tokens"),
        total_tokens=Sum("total_tokens"),
        estimated_cost_usd=Sum("estimated_cost_usd"),
        llm_errors=Count("id", filter=Q(success=False)),
    )
    top_paths = list(
        request_logs.values("path")
        .annotate(count=Count("id"), avg_duration=Avg("duration_ms"))
        .order_by("-count", "path")[:5]
    )
    recent_errors = [
        {
            "kind": "request",
            "path": item.path,
            "message": item.error_message or f"HTTP {item.status_code}",
            "created_at": item.created_at.isoformat(),
        }
        for item in request_logs.filter(Q(status_code__gte=400) | ~Q(error_message="")).order_by("-created_at")[:5]
    ]
    recent_errors.extend(
        {
            "kind": "llm",
            "path": item.operation,
            "message": item.error_message or "LLM call failed",
            "created_at": item.created_at.isoformat(),
        }
        for item in usage_events.filter(success=False).order_by("-created_at")[:5]
    )

    return {
        "window_days": 7,
        "requests": {
            "total": request_totals["total"] or 0,
            "errors": request_totals["errors"] or 0,
            "avg_duration_ms": round(request_totals["avg_duration"] or 0, 2),
            "top_paths": [
                {
                    "path": row["path"],
                    "count": row["count"],
                    "avg_duration_ms": round(row["avg_duration"] or 0, 2),
                }
                for row in top_paths
            ],
        },
        "research_jobs": research_totals,
        "document_tasks": document_totals,
        "usage": {
            "prompt_tokens": usage_totals["prompt_tokens"] or 0,
            "completion_tokens": usage_totals["completion_tokens"] or 0,
            "total_tokens": usage_totals["total_tokens"] or 0,
            "estimated_cost_usd": float(usage_totals["estimated_cost_usd"] or 0),
            "llm_errors": usage_totals["llm_errors"] or 0,
        },
        "recent_errors": recent_errors[:5],
    }
