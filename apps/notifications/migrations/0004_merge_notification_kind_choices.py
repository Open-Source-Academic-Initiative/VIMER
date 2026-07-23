from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0003_alter_notification_kind"),
        ("notifications", "0003_lifecycle_notification_kinds"),
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
                    (
                        "REPRESENTATIVE_JOIN_REQUESTED",
                        "Solicitud de unión creada",
                    ),
                    (
                        "REPRESENTATIVE_JOIN_APPROVED",
                        "Solicitud de unión aprobada",
                    ),
                    (
                        "REPRESENTATIVE_JOIN_REJECTED",
                        "Solicitud de unión rechazada",
                    ),
                    (
                        "REPRESENTATIVE_JOIN_EXPIRED",
                        "Solicitud de unión expirada",
                    ),
                    (
                        "ORGANIZATION_OWNERSHIP_TRANSFERRED",
                        "Titularidad transferida",
                    ),
                ],
                max_length=40,
                verbose_name="Tipo",
            ),
        ),
    ]
