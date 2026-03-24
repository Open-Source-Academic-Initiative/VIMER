from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
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
                ],
                max_length=32,
                verbose_name="Tipo",
            ),
        ),
    ]
