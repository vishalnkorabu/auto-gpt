from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("research_agent_web", "0006_documenttask_canceled"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversationsession",
            name="research_depth",
            field=models.CharField(default="standard", max_length=16),
        ),
        migrations.AddField(
            model_name="researchjob",
            name="research_depth",
            field=models.CharField(default="standard", max_length=16),
        ),
    ]
