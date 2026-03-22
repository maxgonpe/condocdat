# RDIRecord.informado (mismas opciones que Document.informado)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rdi", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="rdirecord",
            name="informado",
            field=models.CharField(
                choices=[
                    ("no_informados", "No informados"),
                    ("informados", "Informados"),
                    ("otra_vez_informados", "Otra vez informados"),
                ],
                db_index=True,
                default="no_informados",
                help_text="Estado de información (mismo criterio que documentos Informar).",
                max_length=32,
            ),
        ),
    ]
