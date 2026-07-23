from decimal import Decimal, ROUND_DOWN

from django.db import migrations, models


def distribute_legacy_weights(apps, schema_editor):
    Criterion = apps.get_model("marketplace", "ChallengeEvaluationCriterion")
    challenge_ids = (
        Criterion.objects.order_by()
        .values_list("challenge_id", flat=True)
        .distinct()
    )
    economic_terms = (
        "costo",
        "precio",
        "económ",
        "econom",
        "valor ofert",
    )
    for challenge_id in challenge_ids:
        criteria = list(
            Criterion.objects.filter(challenge_id=challenge_id).order_by(
                "position",
                "id",
            )
        )
        if not criteria:
            continue
        base_weight = (
            Decimal("100") / len(criteria)
        ).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        weights = [base_weight] * len(criteria)
        weights[0] += Decimal("100") - sum(weights)
        for criterion, weight in zip(criteria, weights, strict=True):
            normalized_label = criterion.label.casefold()
            criterion.weight = weight
            criterion.criterion_type = (
                "ECONOMIC"
                if any(term in normalized_label for term in economic_terms)
                else "TECHNICAL"
            )
            criterion.save(
                update_fields=["weight", "criterion_type"],
            )


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0010_challengelifecycleevent_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="challengeevaluationcriterion",
            name="criterion_type",
            field=models.CharField(
                choices=[
                    ("TECHNICAL", "Técnico"),
                    ("ECONOMIC", "Económico"),
                ],
                default="TECHNICAL",
                max_length=16,
                verbose_name="Tipo de criterio",
            ),
        ),
        migrations.AddField(
            model_name="challengeevaluationcriterion",
            name="weight",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=5,
                null=True,
                verbose_name="Peso porcentual",
            ),
        ),
        migrations.RunPython(
            distribute_legacy_weights,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="challengeevaluationcriterion",
            name="weight",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("100.00"),
                max_digits=5,
                verbose_name="Peso porcentual",
            ),
        ),
        migrations.AddConstraint(
            model_name="challengeevaluationcriterion",
            constraint=models.CheckConstraint(
                condition=models.Q(weight__gt=0, weight__lte=100),
                name="evaluation_criterion_weight_between_zero_and_100",
            ),
        ),
    ]
