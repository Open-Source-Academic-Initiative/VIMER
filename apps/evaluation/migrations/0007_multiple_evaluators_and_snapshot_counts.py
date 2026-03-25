from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evaluation", "0006_challengeevaluationroleassignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="awarddecision",
            name="winning_assessment_count",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="Cantidad total de evaluaciones registradas al adjudicar",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="applicationcriterionevaluation",
            name="unique_application_evaluation_per_criterion",
        ),
        migrations.AddConstraint(
            model_name="applicationcriterionevaluation",
            constraint=models.UniqueConstraint(
                fields=("application", "criterion", "evaluated_by"),
                name="unique_application_evaluation_per_criterion_and_evaluator",
            ),
        ),
        migrations.AlterModelOptions(
            name="applicationcriterionevaluation",
            options={
                "ordering": ["criterion__position", "evaluated_by__username", "id"],
                "verbose_name": "Evaluación de criterio",
                "verbose_name_plural": "Evaluaciones de criterio",
            },
        ),
    ]
