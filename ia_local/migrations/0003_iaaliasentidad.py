from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "ia_local",
            "0002_iareglasemantica_uniq_ia_regla_tipo_pregunta_normalizada",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="IAAliasEntidad",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "expresion",
                    models.CharField(
                        max_length=200,
                    ),
                ),
                (
                    "expresion_normalizada",
                    models.CharField(
                        db_index=True,
                        max_length=200,
                        unique=True,
                    ),
                ),
                (
                    "modelo_destino",
                    models.CharField(
                        db_index=True,
                        max_length=200,
                    ),
                ),
                (
                    "origen",
                    models.CharField(
                        choices=[
                            (
                                "MANUAL",
                                "Registrado manualmente",
                            ),
                            (
                                "APRENDIDO",
                                "Aprendido desde corrección",
                            ),
                        ],
                        db_index=True,
                        default="MANUAL",
                        max_length=20,
                    ),
                ),
                (
                    "activa",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                    ),
                ),
                (
                    "prioridad",
                    models.PositiveSmallIntegerField(
                        default=100,
                    ),
                ),
                (
                    "veces_usada",
                    models.PositiveIntegerField(
                        default=0,
                    ),
                ),
                (
                    "observacion",
                    models.TextField(
                        blank=True,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                    ),
                ),
            ],
            options={
                "ordering": [
                    "expresion_normalizada",
                    "pk",
                ],
            },
        ),
    ]