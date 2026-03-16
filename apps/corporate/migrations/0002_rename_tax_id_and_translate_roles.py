from django.db import migrations, models


def translate_roles_forward(apps, schema_editor):
    Organization = apps.get_model("corporate", "Organization")
    Organization.objects.filter(role="DEMANDANTE").update(role="DEMAND_SIDE")
    Organization.objects.filter(role="OFERENTE").update(role="SUPPLY_SIDE")


def translate_roles_backward(apps, schema_editor):
    Organization = apps.get_model("corporate", "Organization")
    Organization.objects.filter(role="DEMAND_SIDE").update(role="DEMANDANTE")
    Organization.objects.filter(role="SUPPLY_SIDE").update(role="OFERENTE")


class Migration(migrations.Migration):
    dependencies = [
        ("corporate", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="organization",
            old_name="nit",
            new_name="tax_id",
        ),
        migrations.AlterField(
            model_name="organization",
            name="role",
            field=models.CharField(
                choices=[
                    ("DEMAND_SIDE", "Solicitante"),
                    ("SUPPLY_SIDE", "Proveedor tecnológico"),
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(translate_roles_forward, translate_roles_backward),
    ]
