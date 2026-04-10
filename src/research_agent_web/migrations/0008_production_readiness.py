from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("research_agent_web", "0007_research_depth_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApiRequestLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("method", models.CharField(max_length=16)),
                ("path", models.CharField(max_length=255)),
                ("status_code", models.PositiveSmallIntegerField()),
                ("duration_ms", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="api_request_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("display_name", models.CharField(blank=True, default="", max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["user__username"]},
        ),
        migrations.CreateModel(
            name="LLMUsageEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(max_length=32)),
                ("model", models.CharField(max_length=120)),
                ("operation", models.CharField(default="llm.generate", max_length=64)),
                ("duration_ms", models.PositiveIntegerField(default=0)),
                ("prompt_tokens", models.PositiveIntegerField(default=0)),
                ("completion_tokens", models.PositiveIntegerField(default=0)),
                ("total_tokens", models.PositiveIntegerField(default=0)),
                ("estimated_cost_usd", models.DecimalField(decimal_places=6, default=0, max_digits=12)),
                ("success", models.BooleanField(default=True)),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document_task",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="usage_events",
                        to="research_agent_web.documenttask",
                    ),
                ),
                (
                    "research_job",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="usage_events",
                        to="research_agent_web.researchjob",
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddField(
            model_name="documenttask",
            name="celery_task_id",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="documenttask",
            name="queue_backend",
            field=models.CharField(default="thread", max_length=16),
        ),
        migrations.AddField(
            model_name="documenttask",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="researchjob",
            name="celery_task_id",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="researchjob",
            name="queue_backend",
            field=models.CharField(default="thread", max_length=16),
        ),
        migrations.AddField(
            model_name="researchjob",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
