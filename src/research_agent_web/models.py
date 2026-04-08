from __future__ import annotations

import uuid

from django.contrib.auth.models import User
from django.db import models


class ConversationSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="research_sessions")
    title = models.CharField(max_length=255)
    mode = models.CharField(max_length=16, default="multi")
    dry_run = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class ConversationMessage(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(ConversationSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    report_markdown = models.TextField(blank=True, default="")
    report_payload = models.JSONField(null=True, blank=True)
    sources_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class ResearchJob(models.Model):
    STATE_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ConversationSession, on_delete=models.CASCADE, related_name="jobs")
    user_message = models.ForeignKey(
        ConversationMessage,
        on_delete=models.CASCADE,
        related_name="jobs",
    )
    assistant_message = models.OneToOneField(
        ConversationMessage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="job_result",
    )
    query = models.TextField()
    mode = models.CharField(max_length=16, default="multi")
    dry_run = models.BooleanField(default=False)
    state = models.CharField(max_length=16, choices=STATE_CHOICES, default="queued")
    output_dir = models.CharField(max_length=500, blank=True, default="")
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class SavedReport(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(ConversationSession, on_delete=models.CASCADE, related_name="reports")
    assistant_message = models.OneToOneField(
        ConversationMessage,
        on_delete=models.CASCADE,
        related_name="saved_report",
    )
    headline = models.CharField(max_length=255)
    confidence_score = models.FloatField(default=0.0)
    citations_count = models.PositiveIntegerField(default=0)
    sources_count = models.PositiveIntegerField(default=0)
    output_dir = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class UserDocument(models.Model):
    STATUS_CHOICES = [
        ("processing", "Processing"),
        ("processed", "Processed"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="research_documents")
    session = models.ForeignKey(
        ConversationSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=32)
    storage_path = models.CharField(max_length=500, blank=True, default="")
    content = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="processing")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class DocumentChunk(models.Model):
    id = models.BigAutoField(primary_key=True)
    document = models.ForeignKey(UserDocument, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["chunk_index", "id"]
        unique_together = ("document", "chunk_index")


class DocumentTask(models.Model):
    TASK_CHOICES = [
        ("ingest", "Ingest"),
        ("query", "Query"),
    ]
    STATE_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="document_tasks")
    session = models.ForeignKey(
        ConversationSession,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="document_tasks",
    )
    document = models.ForeignKey(
        UserDocument,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    task_type = models.CharField(max_length=16, choices=TASK_CHOICES)
    title = models.CharField(max_length=255)
    state = models.CharField(max_length=16, choices=STATE_CHOICES, default="queued")
    payload = models.JSONField(default=dict, blank=True)
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class JobProgressEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    job = models.ForeignKey(ResearchJob, on_delete=models.CASCADE, related_name="progress_events")
    sequence = models.PositiveIntegerField()
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence", "id"]
        unique_together = ("job", "sequence")


class DocumentTaskProgressEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    task = models.ForeignKey(DocumentTask, on_delete=models.CASCADE, related_name="progress_events")
    sequence = models.PositiveIntegerField()
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence", "id"]
        unique_together = ("task", "sequence")
