from django.db import models


class IAReglaSemantica(models.Model):

    TIPO_EXACTA = "EXACTA"
    TIPO_PATRON = "PATRON"

    TIPOS = [
        (TIPO_EXACTA, "Pregunta exacta"),
        (TIPO_PATRON, "Patrón"),
    ]

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        default=TIPO_EXACTA,
        db_index=True,
    )

    pregunta = models.TextField()

    pregunta_normalizada = models.TextField(
        db_index=True,
    )

    tema = models.CharField(
        max_length=50,
    )

    operacion = models.CharField(
        max_length=30,
        default="listar",
    )

    filtros = models.JSONField(
        default=dict,
        blank=True,
    )

    cantidad = models.CharField(
        max_length=20,
        default="varios",
    )

    orden = models.CharField(
        max_length=20,
        default="ninguno",
    )

    activa = models.BooleanField(
        default=True,
        db_index=True,
    )

    veces_usada = models.PositiveIntegerField(
        default=0,
    )

    observacion = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-updated_at",
            "-pk",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "tipo",
                    "pregunta_normalizada",
                ],
                name="uniq_ia_regla_tipo_pregunta_normalizada",
            ),
        ]

    
    def __str__(self):
        return self.pregunta