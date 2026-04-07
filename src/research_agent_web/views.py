from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import Thread
from uuid import UUID

from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from research_agent.agent import ResearchAgent
from research_agent.config import load_settings
from research_agent.presentation import build_presentable_report

from .models import ConversationMessage, ConversationSession, JobProgressEvent, ResearchJob, SavedReport


@require_GET
def health(_request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def sessions_view(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        sessions = [
            {
                "id": str(session.id),
                "title": session.title,
                "mode": session.mode,
                "dry_run": session.dry_run,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "message_count": session.messages.count(),
            }
            for session in ConversationSession.objects.all()[:50]
        ]
        return JsonResponse({"sessions": sessions})

    payload = _json_body(request)
    title = (payload.get("title") or "New research session").strip()
    mode = payload.get("mode") or "multi"
    dry_run = bool(payload.get("dry_run", False))
    session = ConversationSession.objects.create(title=title, mode=mode, dry_run=dry_run)
    return JsonResponse(_serialize_session(session), status=201)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE"])
def session_detail(request: HttpRequest, session_id: UUID) -> JsonResponse:
    try:
        session = _get_session(session_id)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=404)

    if request.method == "PATCH":
        payload = _json_body(request)
        title = (payload.get("title") or "").strip()
        if not title:
            return JsonResponse({"detail": "Title is required."}, status=400)
        session.title = title[:255]
        session.save(update_fields=["title", "updated_at"])
        return JsonResponse(_serialize_session(session))

    if request.method == "DELETE":
        session.delete()
        return JsonResponse({"deleted": True})

    return JsonResponse(_serialize_session(session))


@require_GET
def session_messages(_request: HttpRequest, session_id: UUID) -> JsonResponse:
    try:
        session = _get_session(session_id)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=404)
    messages = [_serialize_message(message) for message in session.messages.all()]
    return JsonResponse({"session": _serialize_session(session), "messages": messages})


@require_GET
def session_reports(_request: HttpRequest, session_id: UUID) -> JsonResponse:
    try:
        session = _get_session(session_id)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=404)
    reports = [
        {
            "id": report.id,
            "headline": report.headline,
            "confidence_score": report.confidence_score,
            "citations_count": report.citations_count,
            "sources_count": report.sources_count,
            "output_dir": report.output_dir,
            "created_at": report.created_at.isoformat(),
        }
        for report in session.reports.all()
    ]
    return JsonResponse({"session": _serialize_session(session), "reports": reports})


@csrf_exempt
@require_http_methods(["POST"])
def chat_start(request: HttpRequest) -> JsonResponse:
    payload = _json_body(request)
    query = (payload.get("query") or "").strip()
    if len(query) < 3:
        return JsonResponse({"detail": "Query must be at least 3 characters."}, status=400)

    mode = payload.get("mode") or "multi"
    dry_run = bool(payload.get("dry_run", False))
    session_id = payload.get("session_id")

    try:
        session = _resolve_session(session_id=session_id, query=query, mode=mode, dry_run=dry_run)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=404)
    with transaction.atomic():
        user_message = ConversationMessage.objects.create(
            session=session,
            role="user",
            content=query,
        )
        job = ResearchJob.objects.create(
            session=session,
            user_message=user_message,
            query=query,
            mode=mode,
            dry_run=dry_run,
            state="queued",
        )
        JobProgressEvent.objects.create(job=job, sequence=1, message="Queued research job.")

    thread = Thread(target=_run_job, args=(job.id,), daemon=True)
    thread.start()
    return JsonResponse({"job_id": str(job.id), "session_id": str(session.id)}, status=202)


@require_GET
def chat_status(_request: HttpRequest, job_id: UUID) -> JsonResponse:
    try:
        job = ResearchJob.objects.select_related("assistant_message", "session").get(id=job_id)
    except ResearchJob.DoesNotExist:
        return JsonResponse({"detail": "Job not found."}, status=404)

    payload = {
        "job_id": str(job.id),
        "session_id": str(job.session_id),
        "state": job.state,
        "progress_messages": [event.message for event in job.progress_events.all()],
        "result": _serialize_message(job.assistant_message) if job.assistant_message_id else None,
        "error": job.error or None,
    }
    return JsonResponse(payload)


def _run_job(job_id: UUID) -> None:
    job = ResearchJob.objects.select_related("session").get(id=job_id)

    def emit(message: str) -> None:
        _append_progress(job_id, message)

    ResearchJob.objects.filter(id=job_id).update(state="running", updated_at=timezone.now())

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
        ResearchJob.objects.filter(id=job_id).update(
            state="completed",
            assistant_message=assistant_message,
            output_dir=str(output_dir),
            completed_at=timezone.now(),
            updated_at=timezone.now(),
        )
    except Exception as exc:
        ResearchJob.objects.filter(id=job_id).update(
            state="failed",
            error=f"Run failed: {exc}",
            updated_at=timezone.now(),
        )


def _append_progress(job_id: UUID, message: str) -> None:
    last_event = JobProgressEvent.objects.filter(job_id=job_id).order_by("-sequence").first()
    if last_event and last_event.message == message:
        return
    next_sequence = 1 if last_event is None else last_event.sequence + 1
    JobProgressEvent.objects.create(job_id=job_id, sequence=next_sequence, message=message)


def _resolve_session(session_id: str | None, query: str, mode: str, dry_run: bool) -> ConversationSession:
    if session_id:
        return _get_session(UUID(session_id))
    return ConversationSession.objects.create(
        title=_title_from_query(query),
        mode=mode,
        dry_run=dry_run,
    )


def _get_session(session_id: UUID) -> ConversationSession:
    try:
        return ConversationSession.objects.get(id=session_id)
    except ConversationSession.DoesNotExist as exc:
        raise ValueError("Session not found.") from exc


def _serialize_session(session: ConversationSession) -> dict:
    return {
        "id": str(session.id),
        "title": session.title,
        "mode": session.mode,
        "dry_run": session.dry_run,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "reports_count": session.reports.count(),
    }


def _serialize_message(message: ConversationMessage | None) -> dict | None:
    if message is None:
        return None
    return {
        "id": message.id,
        "role": message.role,
        "text": message.content,
        "created_at": message.created_at.isoformat(),
        "sources_count": message.sources_count,
        "report_markdown": message.report_markdown,
        "report": message.report_payload,
    }


def _json_body(request: HttpRequest) -> dict:
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def _build_brief(report_markdown: str) -> str:
    lines = [line.strip() for line in report_markdown.splitlines() if line.strip()]
    if not lines:
        return "No report content produced."
    for i, line in enumerate(lines):
        if "Executive Summary" in line and i + 1 < len(lines):
            return lines[i + 1]
    return lines[0]


def _title_from_query(query: str) -> str:
    title = query.strip()
    return title[:80] + ("..." if len(title) > 80 else "")
