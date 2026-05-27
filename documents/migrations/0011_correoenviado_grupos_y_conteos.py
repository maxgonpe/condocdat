from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0010_userpresence"),
    ]

    operations = [
        migrations.AddField(
            model_name="correoenviado",
            name="copia_count",
            field=models.PositiveIntegerField(
                default=0, help_text="Cantidad total de destinatarios en CC"
            ),
        ),
        migrations.AddField(
            model_name="correoenviado",
            name="copia_grupos",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Nombres de grupos usados en CC, separados por coma",
                max_length=512,
            ),
        ),
        migrations.AddField(
            model_name="correoenviado",
            name="destinatarios_count",
            field=models.PositiveIntegerField(
                default=0, help_text="Cantidad total de destinatarios en Para"
            ),
        ),
        migrations.AddField(
            model_name="correoenviado",
            name="destinatarios_grupos",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Nombres de grupos usados en Para, separados por coma",
                max_length=512,
            ),
        ),
    ]
