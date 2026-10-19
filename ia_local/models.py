from __future__ import annotations

from django.db import models

from ia_local.services.semantica.normalizacion import (
    normalizar_texto,
)


# ============================================================
# REGLAS SEMÁNTICAS EXISTENTES
# ============================================================


class IAReglaSemantica(models.Model):

    TIPO_EXACTA = "EXACTA"
    TIPO_PATRON = "PATRON"

    TIPOS = [
        (
            TIPO_EXACTA,
            "Pregunta exacta",
        ),
        (
            TIPO_PATRON,
            "Patrón",
        ),
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


# ============================================================
# IA-SEM002
# ALIASES DE ENTIDADES
# ============================================================


class IAAliasEntidad(models.Model):

    ORIGEN_MANUAL = "MANUAL"
    ORIGEN_APRENDIDO = "APRENDIDO"

    ORIGENES = [
        (
            ORIGEN_MANUAL,
            "Registrado manualmente",
        ),
        (
            ORIGEN_APRENDIDO,
            "Aprendido desde corrección",
        ),
    ]

    expresion = models.CharField(
        max_length=200,
    )

    expresion_normalizada = models.CharField(
        max_length=200,
        unique=True,
        db_index=True,
    )

    modelo_destino = models.CharField(
        max_length=200,
        db_index=True,
    )

    origen = models.CharField(
        max_length=20,
        choices=ORIGENES,
        default=ORIGEN_MANUAL,
        db_index=True,
    )

    activa = models.BooleanField(
        default=True,
        db_index=True,
    )

    prioridad = models.PositiveSmallIntegerField(
        default=100,
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
            "expresion_normalizada",
            "pk",
        ]

    def save(
        self,
        *args,
        **kwargs,
    ):

        self.expresion = str(
            self.expresion
            or ""
        ).strip()

        self.expresion_normalizada = (
            normalizar_texto(
                self.expresion
            )
        )

        self.modelo_destino = str(
            self.modelo_destino
            or ""
        ).strip()

        super().save(
            *args,
            **kwargs,
        )

    def __str__(self):

        return (
            f"{self.expresion} "
            f"→ {self.modelo_destino}"
        )


# ============================================================
# IA-SEM003
# ALIASES DE CAMPOS
# ============================================================


class IAAliasCampo(models.Model):

    ORIGEN_MANUAL = "MANUAL"
    ORIGEN_APRENDIDO = "APRENDIDO"

    ORIGENES = [
        (
            ORIGEN_MANUAL,
            "Registrado manualmente",
        ),
        (
            ORIGEN_APRENDIDO,
            "Aprendido desde corrección",
        ),
    ]

    modelo = models.CharField(
        max_length=200,
        db_index=True,
    )

    expresion = models.CharField(
        max_length=200,
    )

    expresion_normalizada = models.CharField(
        max_length=200,
        db_index=True,
    )

    campo_destino = models.CharField(
        max_length=200,
        db_index=True,
    )

    origen = models.CharField(
        max_length=20,
        choices=ORIGENES,
        default=ORIGEN_MANUAL,
        db_index=True,
    )

    activa = models.BooleanField(
        default=True,
        db_index=True,
    )

    prioridad = models.PositiveSmallIntegerField(
        default=100,
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
            "modelo",
            "expresion_normalizada",
            "pk",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "modelo",
                    "expresion_normalizada",
                ],
                name="uniq_ia_alias_campo_modelo_expresion",
            ),
        ]

    def save(
        self,
        *args,
        **kwargs,
    ):

        self.modelo = str(
            self.modelo
            or ""
        ).strip()

        self.expresion = str(
            self.expresion
            or ""
        ).strip()

        self.expresion_normalizada = (
            normalizar_texto(
                self.expresion
            )
        )

        self.campo_destino = str(
            self.campo_destino
            or ""
        ).strip()

        super().save(
            *args,
            **kwargs,
        )

    def __str__(self):

        return (
            f"{self.modelo}: "
            f"{self.expresion} "
            f"→ {self.campo_destino}"
        )


# ============================================================
# IA-SEM004
# ALIASES DE VALORES DE NEGOCIO
# ============================================================


class IAAliasValor(models.Model):
    """
    Traduce una expresión del negocio al valor real utilizado
    por un campo Django concreto.

    Ejemplo conceptual:

        documents.Document
        campo: status
        expresión: "por revisar"
        valor: "P"
    """

    ORIGEN_MANUAL = "MANUAL"
    ORIGEN_APRENDIDO = "APRENDIDO"

    ORIGENES = [
        (
            ORIGEN_MANUAL,
            "Registrado manualmente",
        ),
        (
            ORIGEN_APRENDIDO,
            "Aprendido desde corrección",
        ),
    ]

    modelo = models.CharField(
        max_length=200,
        db_index=True,
    )

    campo = models.CharField(
        max_length=200,
        db_index=True,
    )

    expresion = models.CharField(
        max_length=200,
    )

    expresion_normalizada = models.CharField(
        max_length=200,
        db_index=True,
    )

    valor_destino = models.TextField()

    origen = models.CharField(
        max_length=20,
        choices=ORIGENES,
        default=ORIGEN_MANUAL,
        db_index=True,
    )

    activa = models.BooleanField(
        default=True,
        db_index=True,
    )

    prioridad = models.PositiveSmallIntegerField(
        default=100,
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
            "modelo",
            "campo",
            "expresion_normalizada",
            "pk",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "modelo",
                    "campo",
                    "expresion_normalizada",
                ],
                name="uniq_ia_alias_valor_modelo_campo_expr",
            ),
        ]

    def save(
        self,
        *args,
        **kwargs,
    ):

        self.modelo = str(
            self.modelo
            or ""
        ).strip()

        self.campo = str(
            self.campo
            or ""
        ).strip()

        self.expresion = str(
            self.expresion
            or ""
        ).strip()

        self.expresion_normalizada = (
            normalizar_texto(
                self.expresion
            )
        )

        self.valor_destino = str(
            self.valor_destino
            if self.valor_destino is not None
            else ""
        ).strip()

        super().save(
            *args,
            **kwargs,
        )

    def __str__(self):

        return (
            f"{self.modelo}.{self.campo}: "
            f"{self.expresion} "
            f"→ {self.valor_destino}"
        ) 


# ============================================================
# IA-SEM005
# REGLAS SEMÁNTICAS DECLARATIVAS
# ============================================================


class IAReglaDeclarativa(models.Model):
    """
    Concepto de negocio expresado mediante estructura Django verificable.

    Ejemplo:

        expresión:
            documentos por revisar

        modelo:
            documents.Document

        operación:
            listar

        condiciones:
            [
                {
                    "campo": "status",
                    "operador": "exact",
                    "valor": "PENDING",
                }
            ]

    SEM005 no ejecuta ORM.
    Sólo almacena conocimiento previamente validado.
    """

    ORIGEN_MANUAL = "MANUAL"
    ORIGEN_APRENDIDO = "APRENDIDO"

    ORIGENES = [
        (
            ORIGEN_MANUAL,
            "Registrada manualmente",
        ),
        (
            ORIGEN_APRENDIDO,
            "Aprendida desde corrección",
        ),
    ]

    expresion = models.CharField(
        max_length=250,
    )

    expresion_normalizada = models.CharField(
        max_length=250,
        unique=True,
        db_index=True,
    )

    modelo = models.CharField(
        max_length=200,
        db_index=True,
    )

    operacion = models.CharField(
        max_length=30,
        default="listar",
    )

    condiciones = models.JSONField(
        default=list,
        blank=True,
    )

    origen = models.CharField(
        max_length=20,
        choices=ORIGENES,
        default=ORIGEN_MANUAL,
        db_index=True,
    )

    activa = models.BooleanField(
        default=True,
        db_index=True,
    )

    prioridad = models.PositiveSmallIntegerField(
        default=100,
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
            "prioridad",
            "expresion_normalizada",
            "pk",
        ]

    def save(
        self,
        *args,
        **kwargs,
    ):

        self.expresion = str(
            self.expresion
            or ""
        ).strip()

        self.expresion_normalizada = (
            normalizar_texto(
                self.expresion
            )
        )

        self.modelo = str(
            self.modelo
            or ""
        ).strip()

        self.operacion = str(
            self.operacion
            or "listar"
        ).strip().lower()

        super().save(
            *args,
            **kwargs,
        )

    def __str__(self):

        return (
            f"{self.expresion} "
            f"→ {self.modelo} "
            f"[{self.operacion}]"
        )  



# ============================================================
# IA-SEM007
# PROPUESTAS DE APRENDIZAJE CONTROLADO
# ============================================================


class IAPropuestaAprendizaje(models.Model):
    """
    Propuesta pendiente de convertir una corrección humana
    en conocimiento semántico persistente.

    La propuesta NO es conocimiento activo.

    Sólo después de confirmarse se delega en SEM002-SEM005.
    """

    TIPO_ENTIDAD = "ENTIDAD"
    TIPO_CAMPO = "CAMPO"
    TIPO_VALOR = "VALOR"
    TIPO_REGLA = "REGLA"

    TIPOS = [
        (
            TIPO_ENTIDAD,
            "Alias de entidad",
        ),
        (
            TIPO_CAMPO,
            "Alias de campo",
        ),
        (
            TIPO_VALOR,
            "Alias de valor",
        ),
        (
            TIPO_REGLA,
            "Regla declarativa",
        ),
    ]

    ESTADO_PENDIENTE = "PENDIENTE"
    ESTADO_APLICADA = "APLICADA"
    ESTADO_RECHAZADA = "RECHAZADA"
    ESTADO_INVALIDADA = "INVALIDADA"

    ESTADOS = [
        (
            ESTADO_PENDIENTE,
            "Pendiente de confirmación",
        ),
        (
            ESTADO_APLICADA,
            "Aplicada",
        ),
        (
            ESTADO_RECHAZADA,
            "Rechazada",
        ),
        (
            ESTADO_INVALIDADA,
            "Invalidada",
        ),
    ]

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        db_index=True,
    )

    expresion = models.CharField(
        max_length=250,
    )

    expresion_normalizada = models.CharField(
        max_length=250,
        db_index=True,
    )

    datos = models.JSONField(
        default=dict,
    )

    validacion = models.JSONField(
        default=dict,
        blank=True,
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default=ESTADO_PENDIENTE,
        db_index=True,
    )

    huella = models.CharField(
        max_length=64,
        db_index=True,
    )

    motivo = models.TextField(
        blank=True,
    )

    resultado = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:

        ordering = [
            "-created_at",
            "-pk",
        ]

    def __str__(self):

        return (
            f"{self.get_tipo_display()}: "
            f"{self.expresion} "
            f"[{self.estado}]"
        )