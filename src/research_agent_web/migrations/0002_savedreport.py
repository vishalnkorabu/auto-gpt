from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("research_agent_web", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SavedReport",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("headline", models.CharField(max_length=255)),
                ("confidence_score", models.FloatField(default=0.0)),
                ("citations_count", models.PositiveIntegerField(default=0)),
                ("sources_count", models.PositiveIntegerField(default=0)),
                ("output_dir", models.CharField(blank=True, default="", max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "assistant_message",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        related_name="saved_report",
                        to="research_agent_web.conversationmessage",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="reports",
                        to="research_agent_web.conversationsession",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
