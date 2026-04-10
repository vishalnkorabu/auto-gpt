from __future__ import annotations

import json
import sys
from threading import Thread
from uuid import UUID

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from .document_service import delete_uploaded_file, persist_upload
from .export_service import export_report_as_docx, export_report_as_pdf
from .models import ConversationMessage, ConversationSession, DocumentTask, ResearchJob, UserDocument, UserProfile
from .observability import build_observability_snapshot
from .tasks import run_document_task, run_document_task_sync, run_research_job, run_research_job_sync


@require_GET
def health(_request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@require_GET
def auth_me(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False})
    return JsonResponse(
        {
            "authenticated": True,
            "user": _serialize_user(request.user),
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def auth_register(request: HttpRequest) -> JsonResponse:
    payload = _json_body(request)
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    email = (payload.get("email") or "").strip()
    display_name = (payload.get("display_name") or username).strip()
    if len(username) < 3 or len(password) < 6:
        return JsonResponse({"detail": "Username must be 3+ chars and password 6+ chars."}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({"detail": "Username already exists."}, status=400)
    if email and User.objects.filter(email__iexact=email).exists():
        return JsonResponse({"detail": "Email already exists."}, status=400)

    user = User.objects.create_user(username=username, password=password, email=email)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.display_name = display_name[:120] or username
    profile.save(update_fields=["display_name", "updated_at"])
    login(request, user)
    return JsonResponse({"authenticated": True, "user": _serialize_user(user)}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def auth_login(request: HttpRequest) -> JsonResponse:
    payload = _json_body(request)
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"detail": "Invalid credentials."}, status=401)
    login(request, user)
    return JsonResponse({"authenticated": True, "user": _serialize_user(user)})


@csrf_exempt
@require_http_methods(["POST"])
def auth_logout(request: HttpRequest) -> JsonResponse:
    logout(request)
    return JsonResponse({"authenticated": False})


@csrf_exempt
@require_http_methods(["PATCH"])
def auth_profile(request: HttpRequest) -> JsonResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user

    payload = _json_body(request)
    email = (payload.get("email") or "").strip()
    display_name = (payload.get("display_name") or "").strip()

    if email and User.objects.filter(email__iexact=email).exclude(id=user.id).exists():
        return JsonResponse({"detail": "Email already exists."}, status=400)

    user.email = email
    user.save(update_fields=["email"])
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if display_name:
        profile.display_name = display_name[:120]
        profile.save(update_fields=["display_name", "updated_at"])

    return JsonResponse({"user": _serialize_user(user)})


@csrf_exempt
@require_http_methods(["POST"])
def auth_password(request: HttpRequest) -> JsonResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user

    payload = _json_body(request)
    current_password = payload.get("current_password") or ""
    new_password = payload.get("new_password") or ""

    if len(new_password) < 6:
        return JsonResponse({"detail": "New password must be at least 6 characters."}, status=400)
    if not user.check_password(current_password):
        return JsonResponse({"detail": "Current password is incorrect."}, status=400)

    user.set_password(new_password)
    user.save(update_fields=["password"])
    login(request, user)
    return JsonResponse({"updated": True})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def sessions_view(request: HttpRequest) -> JsonResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user

    if request.method == "GET":
        query = request.GET.get("q", "").strip()
        queryset = ConversationSession.objects.filter(owner=user)
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(messages__content__icontains=query)
                | Q(messages__report_markdown__icontains=query)
            ).distinct()
        sessions = [
            {
                "id": str(session.id),
                "title": session.title,
                "mode": session.mode,
                "research_depth": session.research_depth,
                "dry_run": session.dry_run,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "message_count": session.messages.count(),
                "reports_count": session.reports.count(),
            }
            for session in queryset[:50]
        ]
        return JsonResponse({"sessions": sessions})

    payload = _json_body(request)
    title = (payload.get("title") or "New research session").strip()
    mode = payload.get("mode") or "multi"
    research_depth = (payload.get("research_depth") or "standard").strip().lower()
    dry_run = bool(payload.get("dry_run", False))
    session = ConversationSession.objects.create(
        owner=user,
        title=title,
        mode=mode,
        research_depth=research_depth,
        dry_run=dry_run,
    )
    return JsonResponse(_serialize_session(session), status=201)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE"])
def session_detail(request: HttpRequest, session_id: UUID) -> JsonResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user

    try:
        session = _get_session(user, session_id)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=404)

    if request.method == "PATCH":
        payload = _json_body(request)
        title = (payload.get("title") or "").strip()
        if not title:
            return JsonResponse({"detail": "Title is required."}, status=400)
        session.title = title[:255]
        session.research_depth = (payload.get("research_depth") or session.research_depth).strip().lower()
        session.save(update_fields=["title", "research_depth", "updated_at"])
        return JsonResponse(_serialize_session(session))

    if request.method == "DELETE":
        session.delete()
        return JsonResponse({"deleted": True})

    return JsonResponse(_serialize_session(session))


@require_GET
def session_messages(request: HttpRequest, session_id: UUID) -> JsonResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user
    try:
        session = _get_session(user, session_id)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=404)
    messages = [_serialize_message(message) for message in session.messages.all()]
    return JsonResponse({"session": _serialize_session(session), "messages": messages})


@require_GET
def session_reports(request: HttpRequest, session_id: UUID) -> JsonResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user
    try:
        session = _get_session(user, session_id)
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
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user

    payload = _json_body(request)
    query = (payload.get("query") or "").strip()
    if len(query) < 3:
        return JsonResponse({"detail": "Query must be at least 3 characters."}, status=400)

    mode = payload.get("mode") or "multi"
    research_depth = (payload.get("research_depth") or "standard").strip().lower()
    dry_run = bool(payload.get("dry_run", False))
    session_id = payload.get("session_id")

    try:
        session = _resolve_session(
            user=user,
            session_id=session_id,
            query=query,
            mode=mode,
            research_depth=research_depth,
            dry_run=dry_run,
        )
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
            research_depth=research_depth,
            dry_run=dry_run,
            state="queued",
        )

    _dispatch_research_job(str(job.id))
    return JsonResponse({"job_id": str(job.id), "session_id": str(session.id)}, status=202)


@require_GET
def chat_status(request: HttpRequest, job_id: UUID) -> JsonResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user

    try:
        job = ResearchJob.objects.select_related("assistant_message", "session").get(id=job_id, session__owner=user)
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


@require_GET
def jobs_view(request: HttpRequest) -> JsonResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user

    jobs = [
        _serialize_research_job(job)
        for job in ResearchJob.objects.select_related("session").filter(session__owner=user)[:30]
    ]
    document_jobs = [
        _serialize_document_task(task)
        for task in DocumentTask.objects.select_related("session", "document").filter(owner=user)[:30]
    ]
    combined = sorted(jobs + document_jobs, key=lambda item: item["created_at"], reverse=True)[:40]
    return JsonResponse(
        {
            "jobs": combined
        }
    )


@require_GET
def observability_view(request: HttpRequest) -> JsonResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user

    queue_mode = "celery" if settings.RESEARCH_USE_CELERY else "thread"
    snapshot = build_observability_snapshot(user_id=user.id)
    snapshot["queue"] = {
        "mode": queue_mode,
        "broker_url": settings.CELERY_BROKER_URL if settings.RESEARCH_USE_CELERY else "",
        "queue_name": settings.RESEARCH_QUEUE_NAME,
    }
    return JsonResponse(snapshot)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def documents_view(request: HttpRequest) -> JsonResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user

    if request.method == "GET":
        documents = UserDocument.objects.select_related("session").filter(owner=user)[:50]
        return JsonResponse({"documents": [_serialize_document(document) for document in documents]})

    upload = request.FILES.get("file")
    if upload is None:
        return JsonResponse({"detail": "File is required."}, status=400)

    session_id = request.POST.get("session_id") or None
    session = None
    if session_id:
        try:
            session = _get_session(user, UUID(session_id))
        except ValueError as exc:
            return JsonResponse({"detail": str(exc)}, status=404)

    try:
        storage_path, inferred_type = persist_upload(upload=upload, owner_id=user.id)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    document = UserDocument.objects.create(
        owner=user,
        session=session,
        name=upload.name[:255],
        file_type=inferred_type,
        storage_path=storage_path,
        content="",
        status="processing",
    )
    task = DocumentTask.objects.create(
        owner=user,
        session=session,
        document=document,
        task_type="ingest",
        title=f"Ingest {document.name}",
        payload={"document_id": str(document.id), "name": document.name},
    )
    _dispatch_document_task(str(task.id))
    return JsonResponse({"task_id": str(task.id), "document": _serialize_document(document)}, status=202)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE"])
def document_detail(request: HttpRequest, document_id: UUID) -> JsonResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user

    try:
        document = UserDocument.objects.select_related("session").get(id=document_id, owner=user)
    except UserDocument.DoesNotExist:
        return JsonResponse({"detail": "Document not found."}, status=404)

    if request.method == "GET":
        return JsonResponse({"document": _serialize_document(document)})

    if request.method == "PATCH":
        payload = _json_body(request)
        updates: list[str] = []

        if "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                return JsonResponse({"detail": "Document name is required."}, status=400)
            document.name = name[:255]
            updates.append("name")

        if "session_id" in payload:
            session_id = payload.get("session_id")
            if session_id in {"", None}:
                document.session = None
            else:
                try:
                    document.session = _get_session(user, UUID(str(session_id)))
                except (ValueError, TypeError) as exc:
                    return JsonResponse({"detail": str(exc)}, status=404)
            updates.append("session")

        if not updates:
            return JsonResponse({"detail": "No document updates were provided."}, status=400)

        updates.append("updated_at")
        document.save(update_fields=updates)
        return JsonResponse({"document": _serialize_document(document)})

    if document.storage_path:
        delete_uploaded_file(document.storage_path)

    document.tasks.filter(state__in={"queued", "running"}).update(
        state="canceled",
        error="Document deleted by user.",
        updated_at=timezone.now(),
        completed_at=timezone.now(),
    )
    document.delete()
    return JsonResponse({"deleted": True, "document_id": str(document_id)})


@csrf_exempt
@require_http_methods(["POST"])
def document_query(request: HttpRequest) -> JsonResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user

    payload = _json_body(request)
    question = (payload.get("question") or "").strip()
    if len(question) < 3:
        return JsonResponse({"detail": "Question must be at least 3 characters."}, status=400)

    session_id = payload.get("session_id")
    document_ids = payload.get("document_ids") or []
    include_research = bool(payload.get("include_research", False))
    session = None
    if session_id:
        try:
            session = _get_session(user, UUID(session_id))
        except ValueError as exc:
            return JsonResponse({"detail": str(exc)}, status=404)

    documents = UserDocument.objects.filter(owner=user, status="processed")
    if session_id:
        documents = documents.filter(session_id=session_id)
    if document_ids:
        documents = documents.filter(id__in=document_ids)
    if not documents.exists():
        return JsonResponse({"detail": "No processed documents matched this query."}, status=404)

    task = DocumentTask.objects.create(
        owner=user,
        session=session,
        task_type="query",
        title=question[:255],
        payload={
            "question": question,
            "document_ids": document_ids,
            "include_research": include_research,
            "research_mode": payload.get("research_mode") or "multi",
            "research_depth": (payload.get("research_depth") or "standard").strip().lower(),
            "dry_run": bool(payload.get("dry_run", False)),
        },
    )
    _dispatch_document_task(str(task.id))
    return JsonResponse({"task_id": str(task.id)}, status=202)


@require_GET
def document_task_status(request: HttpRequest, task_id: UUID) -> JsonResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user

    try:
        task = DocumentTask.objects.select_related("document", "session").get(id=task_id, owner=user)
    except DocumentTask.DoesNotExist:
        return JsonResponse({"detail": "Task not found."}, status=404)

    return JsonResponse(
        {
            "task_id": str(task.id),
            "task_type": task.task_type,
            "state": task.state,
            "title": task.title,
            "queue_backend": task.queue_backend,
            "document": _serialize_document(task.document) if task.document_id else None,
            "progress_messages": [event.message for event in task.progress_events.all()],
            "result": task.result,
            "error": task.error or None,
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def document_task_cancel(request: HttpRequest, task_id: UUID) -> JsonResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user

    try:
        task = DocumentTask.objects.select_related("document").get(id=task_id, owner=user)
    except DocumentTask.DoesNotExist:
        return JsonResponse({"detail": "Task not found."}, status=404)

    if task.state not in {"queued", "running"}:
        return JsonResponse({"detail": "Only queued or running tasks can be canceled."}, status=400)

    if task.task_type == "ingest" and task.document_id and task.document.storage_path:
        delete_uploaded_file(task.document.storage_path)
        task.document.storage_path = ""
        task.document.status = "failed"
        task.document.save(update_fields=["storage_path", "status", "updated_at"])

    task.state = "canceled"
    task.error = "Task canceled by user."
    task.save(update_fields=["state", "error", "updated_at"])
    return JsonResponse({"task_id": str(task.id), "state": task.state})


@csrf_exempt
@require_http_methods(["POST"])
def document_task_retry(request: HttpRequest, task_id: UUID) -> JsonResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user

    try:
        task = DocumentTask.objects.select_related("document", "session").get(id=task_id, owner=user)
    except DocumentTask.DoesNotExist:
        return JsonResponse({"detail": "Task not found."}, status=404)

    if task.state not in {"failed", "canceled"}:
        return JsonResponse({"detail": "Only failed or canceled tasks can be retried."}, status=400)

    if task.task_type == "ingest" and (task.document is None or not task.document.storage_path):
        return JsonResponse({"detail": "This ingest task cannot be retried because the raw upload is no longer available."}, status=400)

    task.progress_events.all().delete()
    task.state = "queued"
    task.error = ""
    task.result = None
    task.completed_at = None
    task.save(update_fields=["state", "error", "result", "completed_at", "updated_at"])
    if task.document_id and task.task_type == "ingest":
        task.document.status = "processing"
        task.document.save(update_fields=["status", "updated_at"])
    _dispatch_document_task(str(task.id))
    return JsonResponse({"task_id": str(task.id), "state": task.state})


@require_GET
def message_export(request: HttpRequest, message_id: int) -> HttpResponse:
    user = _require_user(request)
    if isinstance(user, JsonResponse):
        return user

    try:
        message = ConversationMessage.objects.select_related("session").get(id=message_id, session__owner=user, role="assistant")
    except ConversationMessage.DoesNotExist:
        return JsonResponse({"detail": "Message not found."}, status=404)

    format_name = (request.GET.get("format") or "pdf").strip().lower()
    title = (message.report_payload or {}).get("headline") or f"Research response {message.id}"
    body = message.report_markdown or message.content

    if format_name == "pdf":
        try:
            payload = export_report_as_pdf(title, body)
        except RuntimeError as exc:
            return JsonResponse({"detail": str(exc)}, status=503)
        response = HttpResponse(payload, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="research-response-{message.id}.pdf"'
        return response
    if format_name == "docx":
        try:
            payload = export_report_as_docx(title, body)
        except RuntimeError as exc:
            return JsonResponse({"detail": str(exc)}, status=503)
        response = HttpResponse(
            payload,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = f'attachment; filename="research-response-{message.id}.docx"'
        return response

    return JsonResponse({"detail": "format must be pdf or docx."}, status=400)


def _require_user(request: HttpRequest) -> User | JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    return request.user


def _resolve_session(
    user: User,
    session_id: str | None,
    query: str,
    mode: str,
    research_depth: str,
    dry_run: bool,
) -> ConversationSession:
    if session_id:
        session = _get_session(user, UUID(session_id))
        if session.mode != mode or session.dry_run != dry_run or session.research_depth != research_depth:
            session.mode = mode
            session.dry_run = dry_run
            session.research_depth = research_depth
            session.save(update_fields=["mode", "dry_run", "research_depth", "updated_at"])
        return session
    return ConversationSession.objects.create(
        owner=user,
        title=_title_from_query(query),
        mode=mode,
        research_depth=research_depth,
        dry_run=dry_run,
    )


def _get_session(user: User, session_id: UUID) -> ConversationSession:
    try:
        return ConversationSession.objects.get(id=session_id, owner=user)
    except ConversationSession.DoesNotExist as exc:
        raise ValueError("Session not found.") from exc


def _serialize_session(session: ConversationSession) -> dict:
    return {
        "id": str(session.id),
        "title": session.title,
        "mode": session.mode,
        "research_depth": session.research_depth,
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


def _serialize_document(document: UserDocument) -> dict:
    return {
        "id": str(document.id),
        "name": document.name,
        "file_type": document.file_type,
        "status": document.status,
        "session_id": str(document.session_id) if document.session_id else None,
        "session_title": document.session.title if document.session_id else None,
        "chunk_count": document.chunks.count(),
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
    }


def _json_body(request: HttpRequest) -> dict:
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def _title_from_query(query: str) -> str:
    title = query.strip()
    return title[:80] + ("..." if len(title) > 80 else "")


def _dispatch_research_job(job_id: str) -> None:
    if settings.RESEARCH_USE_CELERY:
        try:
            async_result = run_research_job.apply_async(args=[job_id], queue=settings.RESEARCH_QUEUE_NAME)
            ResearchJob.objects.filter(id=job_id).update(
                queue_backend="celery",
                celery_task_id=async_result.id,
                updated_at=timezone.now(),
            )
            return
        except Exception:
            pass

    ResearchJob.objects.filter(id=job_id).update(queue_backend="thread", celery_task_id="", updated_at=timezone.now())
    thread = Thread(target=run_research_job_sync, args=(job_id,), daemon=True)
    thread.start()


def _latest_progress(job: ResearchJob) -> str:
    latest = job.progress_events.order_by("-sequence").first()
    return latest.message if latest else ""


def _dispatch_document_task(task_id: str) -> None:
    if "test" in sys.argv:
        DocumentTask.objects.filter(id=task_id).update(queue_backend="sync", celery_task_id="", updated_at=timezone.now())
        run_document_task_sync(task_id)
        return

    if settings.RESEARCH_USE_CELERY:
        try:
            async_result = run_document_task.apply_async(args=[task_id], queue=settings.RESEARCH_QUEUE_NAME)
            DocumentTask.objects.filter(id=task_id).update(
                queue_backend="celery",
                celery_task_id=async_result.id,
                updated_at=timezone.now(),
            )
            return
        except Exception:
            pass

    DocumentTask.objects.filter(id=task_id).update(queue_backend="thread", celery_task_id="", updated_at=timezone.now())
    thread = Thread(target=run_document_task_sync, args=(task_id,), daemon=True)
    thread.start()


def _latest_document_progress(task: DocumentTask) -> str:
    latest = task.progress_events.order_by("-sequence").first()
    return latest.message if latest else ""


def _serialize_research_job(job: ResearchJob) -> dict:
    return {
        "id": str(job.id),
        "kind": "research",
        "session_id": str(job.session_id),
        "session_title": job.session.title,
        "query": job.query,
        "mode": job.mode,
        "research_depth": job.research_depth,
        "dry_run": job.dry_run,
        "state": job.state,
        "queue_backend": job.queue_backend,
        "celery_task_id": job.celery_task_id or None,
        "error": job.error,
        "output_dir": job.output_dir,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "latest_progress": _latest_progress(job),
    }


def _serialize_document_task(task: DocumentTask) -> dict:
    return {
        "id": str(task.id),
        "kind": f"document-{task.task_type}",
        "session_id": str(task.session_id) if task.session_id else None,
        "session_title": task.session.title if task.session_id else "No session",
        "query": task.title,
        "mode": "document",
        "dry_run": False,
        "state": task.state,
        "queue_backend": task.queue_backend,
        "celery_task_id": task.celery_task_id or None,
        "error": task.error,
        "output_dir": "",
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "latest_progress": _latest_document_progress(task),
    }


def _serialize_user(user: User) -> dict:
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"display_name": user.username})
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": profile.display_name or user.username,
    }
