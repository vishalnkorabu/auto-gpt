from __future__ import annotations

import time

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from research_agent.models import SourceDocument, SourceSummary
from research_agent.presentation import build_presentable_report

from .models import ConversationMessage, ConversationSession, DocumentTask, ResearchJob, UserDocument


class SessionApiTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.user = User.objects.create_user(username="tester", password="secret123")
        self.client.login(username="tester", password="secret123")

    def test_create_rename_and_delete_session(self) -> None:
        create_response = self.client.post(
            "/api/sessions",
            data='{"title":"Healthcare AI","mode":"multi","dry_run":true}',
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        session_id = create_response.json()["id"]

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

        self.assertEqual(UserDocument.objects.count(), 1)
        self.assertEqual(DocumentTask.objects.filter(task_type="ingest").count(), 1)

        query_response = self.client.post(
            "/api/documents/query",
            data='{"question":"How are startups using AI in healthcare?"}',
            content_type="application/json",
        )
        self.assertEqual(query_response.status_code, 202)
        query_task_id = query_response.json()["task_id"]
        query_status = self._wait_for_document_task(query_task_id)

        self.assertEqual(query_status["state"], "completed")
        payload = query_status["result"]
        self.assertIn("answer", payload)
        self.assertGreaterEqual(len(payload["citations"]), 1)

    def _wait_for_document_task(self, task_id: str) -> dict:
        for _ in range(30):
            response = self.client.get(f"/api/documents/tasks/{task_id}")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            if payload["state"] in {"completed", "failed"}:
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
