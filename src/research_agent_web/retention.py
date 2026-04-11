from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone

from .models import UserDocument


@dataclass
class CleanupResult:
    deleted_documents: int
    deleted_chunks: int
    retention_days: int


def get_retention_cutoff(*, now=None):
    reference_time = now or timezone.now()
    return reference_time - timezone.timedelta(days=settings.DOCUMENT_RETENTION_DAYS)


def get_expired_processed_documents(*, now=None):
    if not settings.DOCUMENT_RETENTION_ENABLED:
        return UserDocument.objects.none()
    cutoff = get_retention_cutoff(now=now)
    return UserDocument.objects.filter(status="processed", updated_at__lt=cutoff)


def cleanup_processed_documents(*, now=None) -> CleanupResult:
    expired = get_expired_processed_documents(now=now)
    document_ids = list(expired.values_list("id", flat=True))
    if not document_ids:
        return CleanupResult(deleted_documents=0, deleted_chunks=0, retention_days=settings.DOCUMENT_RETENTION_DAYS)

    chunk_total = sum(document.chunks.count() for document in expired.prefetch_related("chunks"))
    deleted_documents, _ = expired.delete()
    return CleanupResult(
        deleted_documents=len(document_ids) if deleted_documents else 0,
        deleted_chunks=chunk_total,
        retention_days=settings.DOCUMENT_RETENTION_DAYS,
    )
