from __future__ import annotations

from typing import Any

from django.db import DatabaseError, models

from .catalogo_datos import obtener_modelo_django
from .validador_plan_datos import validar_plan_datos


# ============================================================
# IA-HOST028
# EJECUTOR SEGURO DE CONTEO SOBRE COLECCIÓN SERIALIZADA
# ============================================================
#
# Responsabilidad:
#   ejecutar, sobre datos reales, una operación ya demostrada por:
#
#       HOST026 -> coleccion_serializada
#       HOST027 -> contrato de serialización validado
#
# Estrategia soportada:
#
#       elementos_no_vacios
#
# Seguridad:
#   - vuelve a validar el plan con validar_plan_datos();
#   - NO acepta lookups ORM libres fuera del plan validado;
#   - NO ejecuta SQL manual;
#   - NO usa raw();
#   - NO usa LLM;
#   - valida que modelo/campo/separador coincidan entre contratos;
#   - sólo lee el campo objetivo mediante values_list();
#   - ignora "limite" del plan porque el resultado es una agregación
#     sobre TODO el queryset filtrado.
#
# Esta pieza NO sustituye ejecutor_datos.py.
# ============================================================


ITERATOR_CHUNK_SIZE = 2000


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _resultado_error(
    *,
    fase: str,
    mensaje: str,
    modelo: str | None = None,
    campo: str | None = None,
    validacion: dict[str, Any] | None = None,
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

    if campo:
        salida["campo"] = campo

    if validacion is not None:
        salida["validacion"] = validacion

    return salida


def _contar_elementos_no_vacios(
    valor: Any,
    *,
    separador: str,
) -> int:
    """
    Cuenta elementos no vacíos de una representación textual delimitada.

    No intenta interpretar formatos distintos ni separadores alternativos.
    """
    if valor is None:
        return 0

    texto = str(valor)

    if not texto.strip():
        return 0

    return sum(
        1
        for item in texto.split(separador)
        if item.strip()
    )


def ejecutar_conteo_coleccion_serializada(
    *,
    plan: dict[str, Any],
    representacion_host: dict[str, Any],
    validacion_serializacion: dict[str, Any],
) -> dict[str, Any]:
    """
    Ejecuta un conteo seguro de elementos de una colección textual
    delimitada, después de volver a validar todos los contratos.
    """

    # --------------------------------------------------------
    # 1. PLAN BASE
    # --------------------------------------------------------

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
        return _resultado_error(
            fase="validacion_plan",
            mensaje="La validación no produjo un plan seguro.",
            validacion=validacion_plan,
        )

    modelo_plan = _texto(
        plan_seguro.get(
            "modelo"
        )
    )

    # --------------------------------------------------------
    # 2. REPRESENTACIÓN HOST026
    # --------------------------------------------------------

    if not isinstance(
        representacion_host,
        dict,
    ):
        return _resultado_error(
            fase="representacion",
            mensaje="La representación HOST026 no tiene formato válido.",
            modelo=modelo_plan,
        )

    if not bool(
        representacion_host.get(
            "resuelto"
        )
    ):
        return _resultado_error(
            fase="representacion",
            mensaje="HOST026 no resolvió la representación del objetivo.",
            modelo=modelo_plan,
        )

    if (
        _texto(
            representacion_host.get(
                "tipo_representacion"
            )
        )
        != "coleccion_serializada"
    ):
        return _resultado_error(
            fase="representacion",
            mensaje=(
                "HOST028 sólo ejecuta objetivos con representación "
                "coleccion_serializada."
            ),
            modelo=modelo_plan,
        )

    modelo_representacion = _texto(
        representacion_host.get(
            "modelo"
        )
    )

    campo = _texto(
        representacion_host.get(
            "nombre"
        )
    )

    separador = representacion_host.get(
        "separador"
    )

    if (
        not campo
        or not isinstance(
            separador,
            str,
        )
        or separador == ""
    ):
        return _resultado_error(
            fase="representacion",
            mensaje=(
                "HOST026 no entregó campo y separador suficientes."
            ),
            modelo=modelo_plan,
            campo=campo or None,
        )

    if (
        modelo_representacion
        and modelo_representacion
        != modelo_plan
    ):
        return _resultado_error(
            fase="consistencia",
            mensaje=(
                "El modelo del plan y el modelo de HOST026 no coinciden."
            ),
            modelo=modelo_plan,
            campo=campo,
        )

    # --------------------------------------------------------
    # 3. CONTRATO HOST027
    # --------------------------------------------------------

    if not isinstance(
        validacion_serializacion,
        dict,
    ):
        return _resultado_error(
            fase="serializacion",
            mensaje="La validación HOST027 no tiene formato válido.",
            modelo=modelo_plan,
            campo=campo,
        )

    if not bool(
        validacion_serializacion.get(
            "aplica"
        )
    ):
        return _resultado_error(
            fase="serializacion",
            mensaje="HOST027 indicó que la validación no aplica.",
            modelo=modelo_plan,
            campo=campo,
        )

    if not bool(
        validacion_serializacion.get(
            "validado"
        )
    ):
        return _resultado_error(
            fase="serializacion",
            mensaje=(
                "El contrato de serialización no está validado."
            ),
            modelo=modelo_plan,
            campo=campo,
        )

    if (
        _texto(
            validacion_serializacion.get(
                "modelo"
            )
        )
        != modelo_plan
    ):
        return _resultado_error(
            fase="consistencia",
            mensaje=(
                "El modelo del plan y el modelo de HOST027 no coinciden."
            ),
            modelo=modelo_plan,
            campo=campo,
        )

    if (
        _texto(
            validacion_serializacion.get(
                "campo"
            )
        )
        != campo
    ):
        return _resultado_error(
            fase="consistencia",
            mensaje=(
                "El campo de HOST026 y el campo validado por HOST027 "
                "no coinciden."
            ),
            modelo=modelo_plan,
            campo=campo,
        )

    separador_validado = (
        validacion_serializacion.get(
            "separador"
        )
    )

    if (
        not isinstance(
            separador_validado,
            str,
        )
        or separador_validado
        != separador
    ):
        return _resultado_error(
            fase="consistencia",
            mensaje=(
                "El separador de HOST026 y el validado por HOST027 "
                "no coinciden."
            ),
            modelo=modelo_plan,
            campo=campo,
        )

    estrategia = _texto(
        validacion_serializacion.get(
            "estrategia_conteo"
        )
    )

    if estrategia != "elementos_no_vacios":
        return _resultado_error(
            fase="estrategia",
            mensaje=(
                f"Estrategia de conteo no soportada: "
                f"{estrategia!r}."
            ),
            modelo=modelo_plan,
            campo=campo,
        )

    # --------------------------------------------------------
    # 4. MODELO Y CAMPO DJANGO
    # --------------------------------------------------------

    modelo_django = obtener_modelo_django(
        modelo_plan
    )

    if modelo_django is None:
        return _resultado_error(
            fase="modelo",
            mensaje=(
                "El modelo validado ya no puede resolverse "
                "en el registro Django."
            ),
            modelo=modelo_plan,
            campo=campo,
        )

    try:
        campo_django = (
            modelo_django._meta.get_field(
                campo
            )
        )
    except Exception:
        return _resultado_error(
            fase="campo",
            mensaje=(
                "El campo validado ya no puede resolverse "
                "mediante Django._meta."
            ),
            modelo=modelo_plan,
            campo=campo,
        )

    if getattr(
        campo_django,
        "is_relation",
        False,
    ):
        return _resultado_error(
            fase="campo",
            mensaje=(
                "HOST028 no ejecuta relaciones ORM; "
                "esperaba un campo textual escalar."
            ),
            modelo=modelo_plan,
            campo=campo,
        )

    if not isinstance(
        campo_django,
        (
            models.CharField,
            models.TextField,
        ),
    ):
        return _resultado_error(
            fase="campo",
            mensaje=(
                "HOST028 sólo admite colecciones serializadas "
                "en CharField o TextField."
            ),
            modelo=modelo_plan,
            campo=campo,
        )

    # --------------------------------------------------------
    # 5. FILTROS YA VALIDADOS
    # --------------------------------------------------------

    filtros_orm = {
        filtro["lookup"]: filtro["valor"]
        for filtro in plan_seguro.get(
            "filtros",
            [],
        )
    }

    # --------------------------------------------------------
    # 6. EJECUCIÓN
    # --------------------------------------------------------

    try:
        queryset = (
            modelo_django.objects.all()
        )

        if filtros_orm:
            queryset = queryset.filter(
                **filtros_orm
            )

        valores = queryset.values_list(
            campo,
            flat=True,
        ).iterator(
            chunk_size=ITERATOR_CHUNK_SIZE
        )

        total_elementos = 0
        registros_evaluados = 0
        registros_con_elementos = 0
        registros_sin_elementos = 0

        for valor in valores:
            registros_evaluados += 1

            cantidad = (
                _contar_elementos_no_vacios(
                    valor,
                    separador=separador,
                )
            )

            total_elementos += cantidad

            if cantidad:
                registros_con_elementos += 1
            else:
                registros_sin_elementos += 1

        return {
            "ok": True,
            "ejecutado": True,
            "operacion": "contar_elementos_coleccion_serializada",
            "modelo": modelo_plan,
            "tabla": plan_seguro.get(
                "tabla"
            ),
            "campo": campo,
            "tipo_django": campo_django.__class__.__name__,
            "tipo_representacion": "coleccion_serializada",
            "estrategia_conteo": estrategia,
            "separador": separador,
            "filtros": plan_seguro.get(
                "filtros",
                [],
            ),
            "orden": [],
            "limite": None,
            "limite_ignorado_por_agregacion": (
                plan_seguro.get(
                    "limite"
                )
            ),
            "registros_evaluados": registros_evaluados,
            "registros_con_elementos": registros_con_elementos,
            "registros_sin_elementos": registros_sin_elementos,
            "total": total_elementos,
            "resultados": [],
            "origen": "orm_seguro_coleccion_serializada",
            "llm_invocado": False,
        }

    except DatabaseError as exc:
        return {
            "ok": False,
            "ejecutado": False,
            "fase": "orm",
            "errores": [
                str(exc)
            ],
            "modelo": modelo_plan,
            "campo": campo,
            "llm_invocado": False,
        }

    except Exception as exc:
        return {
            "ok": False,
            "ejecutado": False,
            "fase": "general",
            "errores": [
                str(exc)
            ],
            "modelo": modelo_plan,
            "campo": campo,
            "llm_invocado": False,
        }
