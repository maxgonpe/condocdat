# Manual migration (environment without Django runtime).

import django.utils.timezone
import transmital.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("transmital", "0003_fecha_caratula_default"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transmital",
            name="fecha_caratula",
            field=models.DateField(
                blank=True, default=transmital.models.default_fecha_caratula, null=True
            ),
        ),
        migrations.AlterField(
            model_name="transmital",
            name="fecha_envio",
            field=models.DateField(
                blank=True, default=django.utils.timezone.localdate, null=True
            ),
        ),
    ]
