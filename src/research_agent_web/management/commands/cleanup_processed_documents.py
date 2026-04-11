from __future__ import annotations

from django.core.management.base import BaseCommand

from research_agent_web.retention import cleanup_processed_documents


class Command(BaseCommand):
    help = "Delete processed documents older than the configured retention window."

    def handle(self, *args, **options):
        result = cleanup_processed_documents()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {result.deleted_documents} documents and {result.deleted_chunks} chunks "
                f"older than {result.retention_days} days."
            )
        )
