from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_alter_notification_kind"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="kind",
            field=models.CharField(
                choices=[
                    ("EVALUATION_STARTED", "Evaluación iniciada"),
                    ("APPLICATION_EVALUATED", "Propuesta evaluada"),
                    ("CHALLENGE_AWARDED", "Desafío adjudicado"),
                    ("CHALLENGE_CLOSED", "Recepción cerrada"),
                    ("CHALLENGE_CANCELLED", "Desafío cancelado"),
                    ("CHALLENGE_DESERTED", "Desafío desierto"),
                ],
                max_length=32,
                verbose_name="Tipo",
            ),
        ),
    ]
