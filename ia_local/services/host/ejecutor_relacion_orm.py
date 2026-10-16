from __future__ import annotations

from typing import Any

from django.db import DatabaseError

from .catalogo_datos import obtener_modelo_django
from .resolvedor_ruta_datos import validar_ruta_orm_relacional
from .validador_plan_datos import validar_plan_datos


# ============================================================
# IA-HOST034-C01
# EJECUTOR SEGURO DE RUTA RELACIONAL
# ============================================================
#
# Ejecuta únicamente una ruta ORM previamente validada por HOST025.
#
# Operación soportada en esta fase:
#
#     contar_destinos_unicos
#
# Regla:
#   - se filtra primero el modelo origen usando un plan validado;
#   - se revalida la ruta con Django._meta;
#   - se obtiene el PK terminal de la ruta;
#   - se cuentan PK destino distintos y no nulos.
#
# No usa SQL crudo.
# No usa LLM.
# No inventa relaciones.
# ============================================================


OPERACIONES_RELACIONALES_PERMITIDAS = {
    "contar_destinos_unicos",
}


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _error(
    *,
    fase: str,
    mensaje: str,
    modelo: str | None = None,
    ruta_orm: str | None = None,
) -> dict[str, Any]:

    salida = {
        "ok": False,
        "ejecutado": False,
        "fase": fase,
        "errores": [mensaje],
        "llm_invocado": False,
    }

    if modelo:
        salida["modelo"] = modelo

    if ruta_orm:
        salida["ruta_orm"] = ruta_orm

    return salida


def ejecutar_conteo_ruta_relacional(
    *,
    plan: dict[str, Any],
    ruta_validada: dict[str, Any],
    operacion_relacional: str = "contar_destinos_unicos",
) -> dict[str, Any]:
    """
    Cuenta objetos destino únicos alcanzables mediante una ruta
    ORM HOST025 desde el conjunto origen filtrado.
    """

    operacion_relacional = _texto(
        operacion_relacional
    )

    if (
        operacion_relacional
        not in OPERACIONES_RELACIONALES_PERMITIDAS
    ):
        return _error(
            fase="operacion",
            mensaje=(
                "Operación relacional no permitida: "
                f"{operacion_relacional!r}."
            ),
        )

    validacion_plan = validar_plan_datos(
        plan
    )

    if not validacion_plan.get(
        "plan_validado"
    ):
        return {
            "ok": False,
            "ejecutado": False,
            "fase": "validacion_plan",
            "errores": validacion_plan.get(
                "errores",
                [],
            ),
            "validacion": validacion_plan,
            "llm_invocado": False,
        }

    plan_seguro = validacion_plan.get(
        "plan"
    )

    if not isinstance(
        plan_seguro,
        dict,
    ):
        return _error(
            fase="validacion_plan",
            mensaje="La validación no produjo un plan seguro.",
        )

    modelo_plan = _texto(
        plan_seguro.get(
            "modelo"
        )
    )

    if not isinstance(
        ruta_validada,
        dict,
    ):
        return _error(
            fase="ruta",
            mensaje="La ruta HOST025 no tiene formato válido.",
            modelo=modelo_plan,
        )

    if not bool(
        ruta_validada.get(
            "valida",
            ruta_validada.get(
                "resuelta",
                False,
            ),
        )
    ):
        return _error(
            fase="ruta",
            mensaje="La ruta relacional no está validada.",
            modelo=modelo_plan,
        )

    ruta_orm = _texto(
        ruta_validada.get(
            "ruta_orm",
            ruta_validada.get(
                "ruta",
            ),
        )
    )

    if not ruta_orm:
        return _error(
            fase="ruta",
            mensaje="HOST025 no entregó ruta_orm.",
            modelo=modelo_plan,
        )

    modelo_ruta = _texto(
        ruta_validada.get(
            "modelo_origen"
        )
    )

    if (
        modelo_ruta
        and modelo_ruta != modelo_plan
    ):
        return _error(
            fase="consistencia",
            mensaje=(
                "El modelo origen de la ruta y el modelo del "
                "plan no coinciden."
            ),
            modelo=modelo_plan,
            ruta_orm=ruta_orm,
        )

    # Revalidación viva contra Django._meta.
    ruta_viva = validar_ruta_orm_relacional(
        modelo=modelo_plan,
        ruta_orm=ruta_orm,
    )

    if not (
        ruta_viva.get("ok")
        and ruta_viva.get("valida")
    ):
        return _error(
            fase="ruta",
            mensaje=(
                "La ruta dejó de ser válida contra Django._meta."
            ),
            modelo=modelo_plan,
            ruta_orm=ruta_orm,
        )

    modelo_django = obtener_modelo_django(
        modelo_plan
    )

    if modelo_django is None:
        return _error(
            fase="modelo",
            mensaje=(
                "El modelo origen ya no puede resolverse "
                "inequívocamente."
            ),
            modelo=modelo_plan,
            ruta_orm=ruta_orm,
        )

    filtros_orm = {
        filtro["lookup"]: filtro["valor"]
        for filtro
        in plan_seguro.get(
            "filtros",
            [],
        )
    }

    lookup_pk_destino = (
        f"{ruta_orm}__pk"
    )

    try:
        queryset = modelo_django.objects.all()

        if filtros_orm:
            queryset = queryset.filter(
                **filtros_orm
            )

        registros_origen = queryset.count()

        valores_destino = (
            queryset
            .exclude(
                **{
                    lookup_pk_destino:
                        None
                }
            )
            .values_list(
                lookup_pk_destino,
                flat=True,
            )
            .distinct()
        )

        total = valores_destino.count()

        return {
            "ok": True,
            "ejecutado": True,
            "operacion": operacion_relacional,
            "modelo_origen": modelo_plan,
            "modelo_destino": ruta_viva.get(
                "modelo_destino"
            ),
            "ruta_orm": ruta_orm,
            "profundidad": ruta_viva.get(
                "profundidad"
            ),
            "contiene_relacion_multiple": (
                ruta_viva.get(
                    "contiene_relacion_multiple",
                    False,
                )
            ),
            "filtros": plan_seguro.get(
                "filtros",
                [],
            ),
            "registros_origen": registros_origen,
            "total": total,
            "criterio_conteo": (
                "pk_destino_distinto_no_nulo"
            ),
            "origen": "orm_seguro_ruta_host025",
            "llm_invocado": False,
        }

    except DatabaseError as exc:
        return _error(
            fase="orm",
            mensaje=str(exc),
            modelo=modelo_plan,
            ruta_orm=ruta_orm,
        )

    except Exception as exc:
        return _error(
            fase="general",
            mensaje=str(exc),
            modelo=modelo_plan,
            ruta_orm=ruta_orm,
        )
