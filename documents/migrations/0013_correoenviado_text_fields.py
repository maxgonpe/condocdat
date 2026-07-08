from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0012_correoenviado_document"),
    ]

    operations = [
        migrations.AlterField(
            model_name="correoenviado",
            name="destinatarios",
            field=models.TextField(
                help_text="Emails separados por coma o punto y coma",
            ),
        ),
        migrations.AlterField(
            model_name="correoenviado",
            name="copia",
            field=models.TextField(
                blank=True,
                default="",
                help_text="CC, separados por coma o punto y coma",
            ),
        ),
        migrations.AlterField(
            model_name="correoenviado",
            name="adjuntos_nombres",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Nombres de archivos adjuntos separados por coma",
            ),
        ),
        migrations.AlterField(
            model_name="correoenviado",
            name="error_msg",
            field=models.TextField(blank=True, default=""),
        ),
    ]
