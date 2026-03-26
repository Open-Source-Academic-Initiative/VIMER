from django.db import migrations, models
from django.utils import timezone


def backfill_application_lifecycle(apps, schema_editor):
    Application = apps.get_model("marketplace", "Application")
    for application in Application.objects.all().iterator():
        timestamp = application.applied_at or timezone.now()
        application.status = "SUBMITTED"
        application.created_at = timestamp
        application.updated_at = timestamp
        application.save(
            update_fields=["status", "created_at", "updated_at"],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0007_challengeevaluationcriterion"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="status",
            field=models.CharField(
                choices=[("DRAFT", "Borrador"), ("SUBMITTED", "Enviada")],
                default="SUBMITTED",
                max_length=16,
                verbose_name="Estado",
            ),
        ),
        migrations.AddField(
            model_name="application",
            name="created_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="application",
            name="updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="application",
            name="applied_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Fecha de envío",
            ),
        ),
        migrations.RunPython(
            backfill_application_lifecycle,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="application",
            name="status",
            field=models.CharField(
                choices=[("DRAFT", "Borrador"), ("SUBMITTED", "Enviada")],
                default="DRAFT",
                max_length=16,
                verbose_name="Estado",
            ),
        ),
        migrations.AlterField(
            model_name="application",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="application",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
