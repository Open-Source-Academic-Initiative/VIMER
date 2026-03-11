import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("corporate", "0002_rename_tax_id_and_translate_roles"),
        ("marketplace", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="challenge",
            name="publisher",
            field=models.ForeignKey(
                limit_choices_to={"role": "DEMAND_SIDE"},
                on_delete=django.db.models.deletion.CASCADE,
                related_name="published_challenges",
                to="corporate.organization",
            ),
        ),
        migrations.AlterField(
            model_name="application",
            name="applicant",
            field=models.ForeignKey(
                limit_choices_to={"role": "SUPPLY_SIDE"},
                on_delete=django.db.models.deletion.CASCADE,
                related_name="submitted_proposals",
                to="corporate.organization",
            ),
        ),
    ]
