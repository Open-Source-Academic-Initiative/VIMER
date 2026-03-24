from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evaluation", "0003_applicationcriterionevaluation"),
    ]

    operations = [
        migrations.AddField(
            model_name="awarddecision",
            name="winning_average_score",
            field=models.FloatField(
                blank=True,
                null=True,
                verbose_name="Promedio registrado al adjudicar",
            ),
        ),
        migrations.AddField(
            model_name="awarddecision",
            name="winning_criteria_total",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="Cantidad total de criterios al adjudicar",
            ),
        ),
        migrations.AddField(
            model_name="awarddecision",
            name="winning_eligible_ranking_position",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="Posición elegible registrada al adjudicar",
            ),
        ),
        migrations.AddField(
            model_name="awarddecision",
            name="winning_evaluated_criteria_count",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="Cantidad de criterios evaluados al adjudicar",
            ),
        ),
        migrations.AddField(
            model_name="awarddecision",
            name="winning_ranking_position",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="Posición comparativa registrada al adjudicar",
            ),
        ),
        migrations.AddField(
            model_name="awarddecision",
            name="winning_total_score",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="Puntaje total registrado al adjudicar",
            ),
        ),
    ]
