from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0011_correoenviado_grupos_y_conteos"),
    ]

    operations = [
        migrations.AddField(
            model_name="correoenviado",
            name="document",
            field=models.ForeignKey(
                blank=True,
                help_text="Documento informado al enviar (si se indicó en el formulario)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="correos_enviados",
                to="documents.document",
            ),
        ),
    ]
