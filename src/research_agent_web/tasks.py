from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

try:
    from celery import shared_task
except ModuleNotFoundError:  # pragma: no cover - allows local dev without Celery installed.
    def shared_task(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator

from django.utils import timezone

from research_agent.agent import ResearchAgent
from research_agent.config import load_settings
from research_agent.presentation import build_presentable_report

from .models import ConversationMessage, JobProgressEvent, ResearchJob, SavedReport


@shared_task(bind=True)
def run_research_job(self, job_id: str) -> None:
    run_research_job_sync(job_id)


def run_research_job_sync(job_id: str) -> None:
    parsed_job_id = UUID(job_id)
    job = ResearchJob.objects.select_related("session").get(id=parsed_job_id)

    def emit(message: str) -> None:
        _append_progress(parsed_job_id, message)

    ResearchJob.objects.filter(id=parsed_job_id).update(state="running", updated_at=timezone.now())

    try:
        settings = load_settings(require_api_keys=not job.dry_run)
        agent = ResearchAgent(settings)
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("reports/api") / run_id
        result = agent.run(
            query=job.query,
            output_dir=output_dir,
            mode=job.mode,
            dry_run=job.dry_run,
            progress_callback=emit,
        )
        answer = _build_brief(result.markdown)
        report = build_presentable_report(result.markdown, result.sources, result.summaries)
        assistant_message = ConversationMessage.objects.create(
            session_id=job.session_id,
            role="assistant",
            content=answer,
            report_markdown=result.markdown,
            report_payload=report,
            sources_count=len(result.sources),
        )
        SavedReport.objects.create(
            session_id=job.session_id,
            assistant_message=assistant_message,
            headline=report.get("headline", "Research report"),
            confidence_score=report.get("confidence", {}).get("score", 0.0),
            citations_count=report.get("stats", {}).get("citations_count", 0),
            sources_count=report.get("stats", {}).get("sources_count", 0),
            output_dir=str(output_dir),
        )
        ResearchJob.objects.filter(id=parsed_job_id).update(
            state="completed",
            assistant_message=assistant_message,
            output_dir=str(output_dir),
            completed_at=timezone.now(),
            updated_at=timezone.now(),
        )
    except Exception as exc:
        ResearchJob.objects.filter(id=parsed_job_id).update(
            state="failed",
            error=f"Run failed: {exc}",
            updated_at=timezone.now(),
        )
        raise


def _append_progress(job_id: UUID, message: str) -> None:
    last_event = JobProgressEvent.objects.filter(job_id=job_id).order_by("-sequence").first()
    if last_event and last_event.message == message:
        return
    next_sequence = 1 if last_event is None else last_event.sequence + 1
    JobProgressEvent.objects.create(job_id=job_id, sequence=next_sequence, message=message)


def _build_brief(report_markdown: str) -> str:
    lines = [line.strip() for line in report_markdown.splitlines() if line.strip()]
    if not lines:
        return "No report content produced."
    for i, line in enumerate(lines):
        if "Executive Summary" in line and i + 1 < len(lines):
            return lines[i + 1]
    return lines[0]
