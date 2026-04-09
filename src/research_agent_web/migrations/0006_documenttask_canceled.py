from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("research_agent_web", "0005_documenttask_and_updates"),
    ]

    operations = [
        migrations.AlterField(
            model_name="documenttask",
            name="state",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("running", "Running"),
                    ("completed", "Completed"),
                    ("failed", "Failed"),
                    ("canceled", "Canceled"),
                ],
                default="queued",
                max_length=16,
            ),
        ),
    ]
