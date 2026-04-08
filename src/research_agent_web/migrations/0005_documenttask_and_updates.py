from __future__ import annotations

import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("research_agent_web", "0004_userdocument_documentchunk"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="userdocument",
            name="storage_path",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AlterField(
            model_name="userdocument",
            name="status",
            field=models.CharField(
                choices=[("processing", "Processing"), ("processed", "Processed"), ("failed", "Failed")],
                default="processing",
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name="DocumentTask",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "task_type",
                    models.CharField(choices=[("ingest", "Ingest"), ("query", "Query")], max_length=16),
                ),
                ("title", models.CharField(max_length=255)),
                (
                    "state",
                    models.CharField(
                        choices=[("queued", "Queued"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed")],
                        default="queued",
                        max_length=16,
                    ),
                ),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("result", models.JSONField(blank=True, null=True)),
                ("error", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "document",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.CASCADE,
                        related_name="tasks",
                        to="research_agent_web.userdocument",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="document_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.CASCADE,
                        related_name="document_tasks",
                        to="research_agent_web.conversationsession",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="DocumentTaskProgressEvent",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("sequence", models.PositiveIntegerField()),
                ("message", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="progress_events",
                        to="research_agent_web.documenttask",
                    ),
                ),
            ],
            options={
                "ordering": ["sequence", "id"],
                "unique_together": {("task", "sequence")},
            },
        ),
    ]
