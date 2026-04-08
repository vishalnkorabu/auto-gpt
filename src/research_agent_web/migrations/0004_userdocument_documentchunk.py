from __future__ import annotations

import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("research_agent_web", "0003_conversationsession_owner"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserDocument",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("file_type", models.CharField(max_length=32)),
                ("content", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[("processed", "Processed"), ("failed", "Failed")],
                        default="processed",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="research_documents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="documents",
                        to="research_agent_web.conversationsession",
                    ),
                ),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="DocumentChunk",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("chunk_index", models.PositiveIntegerField()),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="chunks",
                        to="research_agent_web.userdocument",
                    ),
                ),
            ],
            options={
                "ordering": ["chunk_index", "id"],
                "unique_together": {("document", "chunk_index")},
            },
        ),
    ]
