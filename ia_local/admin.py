from django.contrib import admin

from .models import (
    IAAliasCampo,
    IAAliasEntidad,
    IAAliasValor,
    IAPropuestaAprendizaje,
    IAReglaDeclarativa,
    IAReglaSemantica,
)


# ============================================================
# REGLAS SEMÁNTICAS LEGADAS
# ============================================================


@admin.register(IAReglaSemantica)
class IAReglaSemanticaAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "tipo",
        "pregunta",
        "tema",
        "operacion",
        "activa",
        "veces_usada",
        "updated_at",
    )

    list_filter = (
        "tipo",
        "activa",
        "operacion",
    )

    search_fields = (
        "pregunta",
        "pregunta_normalizada",
        "tema",
        "observacion",
    )

    readonly_fields = (
        "veces_usada",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-updated_at",
        "-id",
    )


# ============================================================
# IA-SEM002
# ALIASES DE ENTIDAD
# ============================================================


@admin.register(IAAliasEntidad)
class IAAliasEntidadAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "expresion",
        "modelo_destino",
        "origen",
        "activa",
        "prioridad",
        "veces_usada",
        "updated_at",
    )

    list_filter = (
        "origen",
        "activa",
    )

    search_fields = (
        "expresion",
        "expresion_normalizada",
        "modelo_destino",
        "observacion",
    )

    readonly_fields = (
        "expresion_normalizada",
        "veces_usada",
        "created_at",
        "updated_at",
    )

    ordering = (
        "expresion_normalizada",
        "id",
    )


# ============================================================
# IA-SEM003
# ALIASES DE CAMPO
# ============================================================


@admin.register(IAAliasCampo)
class IAAliasCampoAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "modelo",
        "expresion",
        "campo_destino",
        "origen",
        "activa",
        "prioridad",
        "veces_usada",
        "updated_at",
    )

    list_filter = (
        "origen",
        "activa",
        "modelo",
    )

    search_fields = (
        "modelo",
        "expresion",
        "expresion_normalizada",
        "campo_destino",
        "observacion",
    )

    readonly_fields = (
        "expresion_normalizada",
        "veces_usada",
        "created_at",
        "updated_at",
    )

    ordering = (
        "modelo",
        "expresion_normalizada",
        "id",
    )


# ============================================================
# IA-SEM004
# ALIASES DE VALOR
# ============================================================


@admin.register(IAAliasValor)
class IAAliasValorAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "modelo",
        "campo",
        "expresion",
        "valor_destino",
        "origen",
        "activa",
        "prioridad",
        "veces_usada",
        "updated_at",
    )

    list_filter = (
        "origen",
        "activa",
        "modelo",
        "campo",
    )

    search_fields = (
        "modelo",
        "campo",
        "expresion",
        "expresion_normalizada",
        "valor_destino",
        "observacion",
    )

    readonly_fields = (
        "expresion_normalizada",
        "veces_usada",
        "created_at",
        "updated_at",
    )

    ordering = (
        "modelo",
        "campo",
        "expresion_normalizada",
        "id",
    )


# ============================================================
# IA-SEM005
# REGLAS DECLARATIVAS
# ============================================================


@admin.register(IAReglaDeclarativa)
class IAReglaDeclarativaAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "expresion",
        "modelo",
        "operacion",
        "origen",
        "activa",
        "prioridad",
        "veces_usada",
        "updated_at",
    )

    list_filter = (
        "origen",
        "activa",
        "operacion",
        "modelo",
    )

    search_fields = (
        "expresion",
        "expresion_normalizada",
        "modelo",
        "operacion",
        "observacion",
    )

    readonly_fields = (
        "expresion_normalizada",
        "veces_usada",
        "created_at",
        "updated_at",
    )

    ordering = (
        "prioridad",
        "expresion_normalizada",
        "id",
    )


# ============================================================
# IA-SEM007
# PROPUESTAS DE APRENDIZAJE
# ============================================================


@admin.register(IAPropuestaAprendizaje)
class IAPropuestaAprendizajeAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "tipo",
        "expresion",
        "estado",
        "created_at",
        "resolved_at",
    )

    list_filter = (
        "tipo",
        "estado",
    )

    search_fields = (
        "expresion",
        "expresion_normalizada",
        "motivo",
        "huella",
    )

    readonly_fields = (
        "expresion_normalizada",
        "huella",
        "validacion",
        "resultado",
        "created_at",
        "updated_at",
        "resolved_at",
    )

    ordering = (
        "-created_at",
        "-id",
    )