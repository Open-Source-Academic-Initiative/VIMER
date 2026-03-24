from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("evaluation", "0005_alter_challengetimelineentry_event_type"),
        ("marketplace", "0007_challengeevaluationcriterion"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ChallengeEvaluationRoleAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("EVALUATOR", "Evaluador designado"), ("ADJUDICATOR", "Adjudicador designado"), ("OBSERVER", "Observador de evaluación")], max_length=24, verbose_name="Rol de evaluación")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("challenge", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="evaluation_role_assignments", to="marketplace.challenge")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="challenge_evaluation_role_assignments", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Asignación de rol de evaluación",
                "verbose_name_plural": "Asignaciones de roles de evaluación",
                "ordering": ["role", "user__username", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="challengeevaluationroleassignment",
            constraint=models.UniqueConstraint(fields=("challenge", "user", "role"), name="unique_challenge_evaluation_role_assignment"),
        ),
        migrations.AddConstraint(
            model_name="challengeevaluationroleassignment",
            constraint=models.UniqueConstraint(condition=Q(role="ADJUDICATOR"), fields=("challenge", "role"), name="unique_adjudicator_per_challenge"),
        ),
    ]
