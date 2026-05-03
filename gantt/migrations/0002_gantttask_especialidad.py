from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gantt", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="gantttask",
            name="especialidad",
            field=models.CharField(blank=True, db_index=True, default="", max_length=128),
        ),
    ]
