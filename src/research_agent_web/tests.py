from __future__ import annotations

from django.test import Client, TestCase

from research_agent.models import SourceDocument, SourceSummary
from research_agent.presentation import build_presentable_report

from .models import ConversationSession


class SessionApiTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

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
