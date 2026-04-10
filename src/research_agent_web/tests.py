from __future__ import annotations

import time
from decimal import Decimal
from importlib.util import find_spec

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from research_agent.models import SourceDocument, SourceSummary
from research_agent.presentation import build_presentable_report

from .models import (
    ApiRequestLog,
    ConversationMessage,
    ConversationSession,
    DocumentTask,
    LLMUsageEvent,
    ResearchJob,
    UserDocument,
    UserProfile,
)


class AuthApiTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

    def test_register_login_profile_and_password_change(self) -> None:
        register_response = self.client.post(
            "/api/auth/register",
            data='{"username":"tester","password":"secret123","email":"tester@example.com","display_name":"Test User"}',
            content_type="application/json",
        )
        self.assertEqual(register_response.status_code, 201)
        self.assertEqual(register_response.json()["user"]["display_name"], "Test User")

        me_response = self.client.get("/api/auth/me")
        self.assertEqual(me_response.status_code, 200)
        self.assertTrue(me_response.json()["authenticated"])
        self.assertEqual(me_response.json()["user"]["email"], "tester@example.com")

        profile_response = self.client.patch(
            "/api/auth/profile",
            data='{"email":"updated@example.com","display_name":"Updated Name"}',
            content_type="application/json",
        )
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.json()["user"]["display_name"], "Updated Name")

        password_response = self.client.post(
            "/api/auth/password",
            data='{"current_password":"secret123","new_password":"newsecret123"}',
            content_type="application/json",
        )
        self.assertEqual(password_response.status_code, 200)

        self.client.post("/api/auth/logout", data="{}", content_type="application/json")
        login_response = self.client.post(
            "/api/auth/login",
            data='{"username":"tester","password":"newsecret123"}',
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(UserProfile.objects.get(user__username="tester").display_name, "Updated Name")

    def test_profile_requires_authentication(self) -> None:
        response = self.client.patch("/api/auth/profile", data="{}", content_type="application/json")
        self.assertEqual(response.status_code, 401)


class SessionApiTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.user = User.objects.create_user(username="tester", password="secret123", email="tester@example.com")
        self.client.login(username="tester", password="secret123")

    def test_create_rename_and_delete_session(self) -> None:
        create_response = self.client.post(
            "/api/sessions",
            data='{"title":"Healthcare AI","mode":"multi","research_depth":"deep","dry_run":true}',
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        session_id = create_response.json()["id"]
        self.assertEqual(create_response.json()["research_depth"], "deep")

        rename_response = self.client.patch(
            f"/api/sessions/{session_id}",
            data='{"title":"Healthcare AI Deep Dive"}',
            content_type="application/json",
        )
        self.assertEqual(rename_response.status_code, 200)
        self.assertEqual(rename_response.json()["title"], "Healthcare AI Deep Dive")

        delete_response = self.client.delete(f"/api/sessions/{session_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(ConversationSession.objects.filter(id=session_id).exists())

    def test_sessions_require_authentication(self) -> None:
        anon = Client()
        response = anon.get("/api/sessions")
        self.assertEqual(response.status_code, 401)

    def test_sessions_search_matches_titles_and_messages(self) -> None:
        session = ConversationSession.objects.create(owner=self.user, title="Healthcare AI", research_depth="standard")
        ConversationMessage.objects.create(session=session, role="user", content="impact on startups")
        ConversationSession.objects.create(owner=self.user, title="Climate Tech", research_depth="standard")

        title_response = self.client.get("/api/sessions?q=Healthcare")
        self.assertEqual(title_response.status_code, 200)
        self.assertEqual(len(title_response.json()["sessions"]), 1)

        content_response = self.client.get("/api/sessions?q=startups")
        self.assertEqual(content_response.status_code, 200)
        self.assertEqual(len(content_response.json()["sessions"]), 1)

    def test_jobs_endpoint_returns_only_current_user_jobs(self) -> None:
        session = ConversationSession.objects.create(owner=self.user, title="Healthcare AI")
        user_message = ConversationMessage.objects.create(session=session, role="user", content="Question")
        ResearchJob.objects.create(session=session, user_message=user_message, query="Question", state="queued")

        other_user = User.objects.create_user(username="other", password="secret123")
        other_session = ConversationSession.objects.create(owner=other_user, title="Other")
        other_message = ConversationMessage.objects.create(session=other_session, role="user", content="Other question")
        ResearchJob.objects.create(session=other_session, user_message=other_message, query="Other question", state="queued")

        response = self.client.get("/api/jobs")

        self.assertEqual(response.status_code, 200)
        jobs = response.json()["jobs"]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["query"], "Question")

    def test_upload_and_query_documents(self) -> None:
        upload = SimpleUploadedFile(
            "healthcare-note.txt",
            b"Healthcare startups use AI to reduce clinician admin burden and improve triage speed.",
            content_type="text/plain",
        )
        upload_response = self.client.post("/api/documents", data={"file": upload})
        self.assertEqual(upload_response.status_code, 202)
        upload_task_id = upload_response.json()["task_id"]
        upload_status = self._wait_for_document_task(upload_task_id)
        self.assertEqual(upload_status["state"], "completed")
        self.assertEqual(upload_status["queue_backend"], "sync")

        self.assertEqual(UserDocument.objects.count(), 1)
        self.assertEqual(UserDocument.objects.first().storage_path, "")
        self.assertEqual(DocumentTask.objects.filter(task_type="ingest").count(), 1)

        query_response = self.client.post(
            "/api/documents/query",
            data='{"question":"How are startups using AI in healthcare?","include_research":true,"dry_run":true}',
            content_type="application/json",
        )
        self.assertEqual(query_response.status_code, 202)
        query_task_id = query_response.json()["task_id"]
        query_status = self._wait_for_document_task(query_task_id)

        self.assertEqual(query_status["state"], "completed")
        payload = query_status["result"]
        self.assertIn("answer", payload)
        self.assertGreaterEqual(len(payload["citations"]), 1)
        self.assertEqual(payload["mode"], "hybrid")
        self.assertGreaterEqual(len(payload["research_sources"]), 1)

    def test_cancel_and_retry_document_query_task(self) -> None:
        upload = SimpleUploadedFile(
            "healthcare-note.txt",
            b"Healthcare startups use AI for triage, coding support, and administrative workflow reduction.",
            content_type="text/plain",
        )
        upload_response = self.client.post("/api/documents", data={"file": upload})
        upload_task_id = upload_response.json()["task_id"]
        self._wait_for_document_task(upload_task_id)

        document = UserDocument.objects.first()
        task = DocumentTask.objects.create(
            owner=self.user,
            document=document,
            task_type="query",
            title="How is AI being used?",
            state="queued",
            payload={"question": "How is AI being used?", "dry_run": True},
        )

        cancel_response = self.client.post(f"/api/documents/tasks/{task.id}/cancel", data="{}", content_type="application/json")
        self.assertEqual(cancel_response.status_code, 200)

        retry_response = self.client.post(f"/api/documents/tasks/{task.id}/retry", data="{}", content_type="application/json")
        self.assertEqual(retry_response.status_code, 200)
        retried_status = self._wait_for_document_task(task.id)
        self.assertEqual(retried_status["state"], "completed")

    def test_observability_endpoint_returns_request_and_usage_metrics(self) -> None:
        session = ConversationSession.objects.create(owner=self.user, title="Healthcare AI")
        user_message = ConversationMessage.objects.create(session=session, role="user", content="Question")
        job = ResearchJob.objects.create(
            session=session,
            user_message=user_message,
            query="Question",
            state="completed",
            queue_backend="celery",
            celery_task_id="celery-123",
        )
        LLMUsageEvent.objects.create(
            research_job=job,
            provider="groq",
            model="llama-test",
            operation="planner",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=Decimal("0.012500"),
            success=True,
        )
        self.client.get("/api/jobs")

        response = self.client.get("/api/observability")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["queue"]["mode"], "thread")
        self.assertEqual(payload["usage"]["total_tokens"], 150)
        self.assertGreaterEqual(payload["requests"]["total"], 1)
        self.assertTrue(any(item["path"] == "/api/jobs" for item in payload["requests"]["top_paths"]))

    def test_export_message_as_pdf_and_docx(self) -> None:
        session = ConversationSession.objects.create(owner=self.user, title="Healthcare AI", research_depth="standard")
        assistant = ConversationMessage.objects.create(
            session=session,
            role="assistant",
            content="Summary",
            report_markdown="# Research Report\n\nUseful content",
            report_payload={"headline": "Healthcare AI Report"},
        )

        pdf_response = self.client.get(f"/api/messages/{assistant.id}/export?format=pdf")
        if find_spec("reportlab") is None:
            self.assertEqual(pdf_response.status_code, 503)
        else:
            self.assertEqual(pdf_response.status_code, 200)
            self.assertEqual(pdf_response["Content-Type"], "application/pdf")

        docx_response = self.client.get(f"/api/messages/{assistant.id}/export?format=docx")
        if find_spec("docx") is None:
            self.assertEqual(docx_response.status_code, 503)
        else:
            self.assertEqual(docx_response.status_code, 200)
            self.assertIn(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                docx_response["Content-Type"],
            )

    def test_request_logging_captures_api_calls(self) -> None:
        self.client.get("/api/jobs")
        latest_log = ApiRequestLog.objects.order_by("-created_at").first()
        self.assertIsNotNone(latest_log)
        assert latest_log is not None
        self.assertEqual(latest_log.path, "/api/jobs")
        self.assertEqual(latest_log.method, "GET")

    def _wait_for_document_task(self, task_id: str) -> dict:
        for _ in range(30):
            response = self.client.get(f"/api/documents/tasks/{task_id}")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            if payload["state"] in {"completed", "failed", "canceled"}:
                return payload
            time.sleep(0.1)
        self.fail("Timed out waiting for document task to finish.")


class PresentationTests(TestCase):
    def test_build_presentable_report_adds_confidence_and_strips_citations(self) -> None:
        markdown = (
            "# Research Report: Test Topic\n\n"
            "## Executive Summary\n"
            "AI improves workflow speed [1] while introducing adoption risk [2].\n\n"
            "## References\n"
            "1. Source A - https://example.com/a\n"
            "2. Source B - https://example.com/b\n"
        )
        sources = [
            SourceDocument(
                title="Source A",
                url="https://www.nih.gov/example-a",
                snippet="Strong public-health source.",
                content="word " * 300,
                source_type="web",
            ),
            SourceDocument(
                title="Source B",
                url="https://example.com/b",
                snippet="Secondary source.",
                content="word " * 120,
                source_type="web",
            ),
        ]
        summaries = [
            SourceSummary(source_id=1, title="Source A", url=sources[0].url, summary="A", key_points=["p1"]),
            SourceSummary(source_id=2, title="Source B", url=sources[1].url, summary="B", key_points=["p2"]),
        ]

        report = build_presentable_report(markdown, sources, summaries)

        self.assertIn("confidence", report)
        self.assertGreater(report["confidence"]["score"], 0)
        self.assertNotIn("[1]", report["response_text"])
        self.assertEqual(report["sources"][0]["id"], 1)
