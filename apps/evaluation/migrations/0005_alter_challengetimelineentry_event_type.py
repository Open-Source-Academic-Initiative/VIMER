from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evaluation", "0004_awarddecision_evaluation_snapshot"),
    ]

    operations = [
        migrations.AlterField(
            model_name="challengetimelineentry",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("EVALUATION_STARTED", "Evaluación iniciada"),
                    ("APPLICATION_EVALUATED", "Propuesta evaluada"),
                    ("CHALLENGE_AWARDED", "Desafío adjudicado"),
                ],
                max_length=32,
                verbose_name="Tipo de evento",
            ),
        ),
    ]
