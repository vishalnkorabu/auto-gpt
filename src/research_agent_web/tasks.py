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
from research_agent.config import apply_research_depth, load_settings
from research_agent.presentation import build_presentable_report

from .document_service import answer_document_question, build_hybrid_answer, delete_uploaded_file, process_document
from .models import (
    ConversationMessage,
    DocumentTask,
    DocumentTaskProgressEvent,
    JobProgressEvent,
    ResearchJob,
    SavedReport,
    UserDocument,
)
from .observability import observe_document_task, observe_research_job


@shared_task(bind=True)
def run_research_job(self, job_id: str) -> None:
    run_research_job_sync(job_id)


@shared_task(bind=True)
def run_document_task(self, task_id: str) -> None:
    run_document_task_sync(task_id)


def run_research_job_sync(job_id: str) -> None:
    parsed_job_id = UUID(job_id)
    job = ResearchJob.objects.select_related("session").get(id=parsed_job_id)

    def emit(message: str) -> None:
        _append_progress(parsed_job_id, message)

    ResearchJob.objects.filter(id=parsed_job_id).update(
        state="running",
        started_at=timezone.now(),
        updated_at=timezone.now(),
    )

    try:
        with observe_research_job(parsed_job_id):
            settings = apply_research_depth(
                load_settings(require_api_keys=not job.dry_run),
                job.research_depth,
            )
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


def run_document_task_sync(task_id: str) -> None:
    parsed_task_id = UUID(task_id)
    task = DocumentTask.objects.select_related("document", "session").get(id=parsed_task_id)

    def emit(message: str) -> None:
        _append_document_progress(parsed_task_id, message)

    if task.state == "canceled":
        return

    DocumentTask.objects.filter(id=parsed_task_id).update(
        state="running",
        started_at=timezone.now(),
        updated_at=timezone.now(),
        error="",
        result=None,
    )

    try:
        with observe_document_task(parsed_task_id):
            if task.task_type == "ingest":
                if task.document_id is None:
                    raise ValueError("Document ingest task is missing a document.")
                _ensure_task_not_canceled(parsed_task_id)
                emit("Reading uploaded file.")
                result = process_document(task.document)
                _ensure_task_not_canceled(parsed_task_id)
                emit("Chunking complete.")
                DocumentTask.objects.filter(id=parsed_task_id).update(
                    state="completed",
                    result=result,
                    completed_at=timezone.now(),
                    updated_at=timezone.now(),
                )
                return

            if task.task_type == "query":
                _ensure_task_not_canceled(parsed_task_id)
                emit("Selecting relevant document chunks.")
                document_ids = task.payload.get("document_ids") or []
                queryset = UserDocument.objects.prefetch_related("chunks").filter(owner_id=task.owner_id, status="processed")
                if task.session_id:
                    queryset = queryset.filter(session_id=task.session_id)
                if document_ids:
                    queryset = queryset.filter(id__in=document_ids)
                documents = list(queryset[:12])
                if not documents:
                    raise ValueError("No processed documents matched this query.")
                _ensure_task_not_canceled(parsed_task_id)
                emit("Generating grounded document answer.")
                question = task.payload.get("question", "")
                result = answer_document_question(question, documents)
                if task.payload.get("include_research"):
                    _ensure_task_not_canceled(parsed_task_id)
                    emit("Running live web research.")
                    dry_run = bool(task.payload.get("dry_run", False))
                    settings = apply_research_depth(
                        load_settings(require_api_keys=not dry_run),
                        task.payload.get("research_depth") or "standard",
                    )
                    agent = ResearchAgent(settings)
                    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_dir = Path("reports/document_hybrid") / run_id
                    research_result = agent.run(
                        query=question,
                        output_dir=output_dir,
                        mode=task.payload.get("research_mode", "multi"),
                        dry_run=dry_run,
                        progress_callback=emit,
                    )
                    presentable = build_presentable_report(
                        research_result.markdown,
                        research_result.sources,
                        research_result.summaries,
                    )
                    result = build_hybrid_answer(
                        question=question,
                        document_result=result,
                        research_summary=presentable.get("summary") or presentable.get("response_text", ""),
                        research_sources=presentable.get("sources", []),
                        settings=settings,
                    )
                emit("Document answer ready.")
                DocumentTask.objects.filter(id=parsed_task_id).update(
                    state="completed",
                    result=result,
                    completed_at=timezone.now(),
                    updated_at=timezone.now(),
                )
                return

        raise ValueError(f"Unsupported document task type: {task.task_type}")
    except TaskCanceledError:
        task = DocumentTask.objects.select_related("document").get(id=parsed_task_id)
        if task.document_id and task.task_type == "ingest":
            if task.document.storage_path:
                delete_uploaded_file(task.document.storage_path)
            UserDocument.objects.filter(id=task.document_id).update(
                status="failed",
                storage_path="",
                updated_at=timezone.now(),
            )
        DocumentTask.objects.filter(id=parsed_task_id).update(
            state="canceled",
            error="Task canceled by user.",
            updated_at=timezone.now(),
        )
        return
    except Exception as exc:
        if task.document_id and task.task_type == "ingest":
            UserDocument.objects.filter(id=task.document_id).update(status="failed", updated_at=timezone.now())
        DocumentTask.objects.filter(id=parsed_task_id).update(
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


def _append_document_progress(task_id: UUID, message: str) -> None:
    last_event = DocumentTaskProgressEvent.objects.filter(task_id=task_id).order_by("-sequence").first()
    if last_event and last_event.message == message:
        return
    next_sequence = 1 if last_event is None else last_event.sequence + 1
    DocumentTaskProgressEvent.objects.create(task_id=task_id, sequence=next_sequence, message=message)


def _build_brief(report_markdown: str) -> str:
    lines = [line.strip() for line in report_markdown.splitlines() if line.strip()]
    if not lines:
        return "No report content produced."
    for i, line in enumerate(lines):
        if "Executive Summary" in line and i + 1 < len(lines):
            return lines[i + 1]
    return lines[0]


class TaskCanceledError(Exception):
    pass


def _ensure_task_not_canceled(task_id: UUID) -> None:
    state = DocumentTask.objects.filter(id=task_id).values_list("state", flat=True).first()
    if state == "canceled":
        raise TaskCanceledError()
