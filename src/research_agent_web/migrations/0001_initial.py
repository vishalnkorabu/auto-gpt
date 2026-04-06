from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ConversationSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("mode", models.CharField(default="multi", max_length=16)),
                ("dry_run", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="ConversationMessage",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[("user", "User"), ("assistant", "Assistant")], max_length=16)),
                ("content", models.TextField()),
                ("report_markdown", models.TextField(blank=True, default="")),
                ("report_payload", models.JSONField(blank=True, null=True)),
                ("sources_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="messages",
                        to="research_agent_web.conversationsession",
                    ),
                ),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.CreateModel(
            name="ResearchJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("query", models.TextField()),
                ("mode", models.CharField(default="multi", max_length=16)),
                ("dry_run", models.BooleanField(default=False)),
                (
                    "state",
                    models.CharField(
                        choices=[("queued", "Queued"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed")],
                        default="queued",
                        max_length=16,
                    ),
                ),
                ("output_dir", models.CharField(blank=True, default="", max_length=500)),
                ("error", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "assistant_message",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="job_result",
                        to="research_agent_web.conversationmessage",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="jobs",
                        to="research_agent_web.conversationsession",
                    ),
                ),
                (
                    "user_message",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="jobs",
                        to="research_agent_web.conversationmessage",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="JobProgressEvent",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("sequence", models.PositiveIntegerField()),
                ("message", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="progress_events",
                        to="research_agent_web.researchjob",
                    ),
                ),
            ],
            options={"ordering": ["sequence", "id"], "unique_together": {("job", "sequence")}},
        ),
    ]
