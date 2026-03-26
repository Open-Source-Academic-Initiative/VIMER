import apps.corporate.avatar_utils
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("corporate", "0002_rename_tax_id_and_translate_roles"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="logo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="corporate/logos/",
                validators=[apps.corporate.avatar_utils.validate_logo_image],
            ),
        ),
    ]
