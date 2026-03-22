# Generated manually for Document.informado

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0007_alter_document_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="informado",
            field=models.CharField(
                choices=[
                    ("no_informados", "No informados"),
                    ("informados", "Informados"),
                    ("otra_vez_informados", "Otra vez informados"),
                ],
                db_index=True,
                default="no_informados",
                help_text="Estado de información para documentos ODATA-BUF / TRN-PRO-CM-TRN-",
                max_length=32,
            ),
        ),
    ]
