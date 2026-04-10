from __future__ import annotations

import uuid

from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=120, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]


class ConversationSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="research_sessions")
    title = models.CharField(max_length=255)
    mode = models.CharField(max_length=16, default="multi")
    research_depth = models.CharField(max_length=16, default="standard")
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
    research_depth = models.CharField(max_length=16, default="standard")
    dry_run = models.BooleanField(default=False)
    state = models.CharField(max_length=16, choices=STATE_CHOICES, default="queued")
    queue_backend = models.CharField(max_length=16, default="thread")
    celery_task_id = models.CharField(max_length=255, blank=True, default="")
    output_dir = models.CharField(max_length=500, blank=True, default="")
    error = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
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
        ("canceled", "Canceled"),
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
    queue_backend = models.CharField(max_length=16, default="thread")
    celery_task_id = models.CharField(max_length=255, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
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


class LLMUsageEvent(models.Model):
    research_job = models.ForeignKey(
        ResearchJob,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="usage_events",
    )
    document_task = models.ForeignKey(
        DocumentTask,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="usage_events",
    )
    provider = models.CharField(max_length=32)
    model = models.CharField(max_length=120)
    operation = models.CharField(max_length=64, default="llm.generate")
    duration_ms = models.PositiveIntegerField(default=0)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    estimated_cost_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class ApiRequestLog(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="api_request_logs")
    method = models.CharField(max_length=16)
    path = models.CharField(max_length=255)
    status_code = models.PositiveSmallIntegerField()
    duration_ms = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
