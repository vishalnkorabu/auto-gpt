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


class JobProgressEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    job = models.ForeignKey(ResearchJob, on_delete=models.CASCADE, related_name="progress_events")
    sequence = models.PositiveIntegerField()
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence", "id"]
        unique_together = ("job", "sequence")
