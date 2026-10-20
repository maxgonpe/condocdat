from __future__ import annotations

from typing import Any

from .catalogo_datos import obtener_modelo_django


# ============================================================
# IA-HOST035
# VALIDADOR DE AGRUPAMIENTO DE DATOS
# ============================================================
#
# Responsabilidad:
#
#   recibir componentes YA resueltos por HOST:
#
#       modelo
#       campo_agrupacion
#       operacion_semantica
#       objetivo_agregado
#
#   y certificar que la combinación puede representarse como
#   un agrupamiento seguro.
#
# HOST035:
#   - NO ejecuta ORM;
#   - NO usa LLM;
#   - NO interpreta lenguaje natural;
#   - NO resuelve aliases;
#   - NO inventa campos;
#   - NO genera SQL;
#   - NO usa annotate()/values()/aggregate().
#
# ============================================================


VERSION = "IA-HOST035-v1"


OPERACIONES_AGRUPABLES = {
    "contar_registros",
    "sumar_objetivo",
    "promediar_objetivo",
    "minimo_objetivo",
    "maximo_objetivo",
}


def _texto(
    valor: Any,
) -> str:

    return str(
        valor or ""
    ).strip()


def _error(
    *,
    fase: str,
    razon: str,
    **extra: Any,
) -> dict[str, Any]:

    salida = {
        "ok": False,
        "version": VERSION,
        "agrupamiento_valido": False,
        "fase": fase,
        "razon": razon,
        "llm_invocado": False,
    }

    salida.update(
        extra
    )

    return salida


def _resolver_campo_modelo(
    *,
    modelo_django: Any,
    nombre: str,
) -> Any | None:

    nombre = _texto(
        nombre
    )

    if not nombre:

        return None

    try:

        return modelo_django._meta.get_field(
            nombre
        )

    except Exception:

        return None


def validar_agrupamiento_datos(
    *,
    modelo: str,
    campo_agrupacion: dict[str, Any],
    operacion_semantica: dict[str, Any],
    objetivo_agregado: dict[str, Any] | None = None,
) -> dict[str, Any]:

    # --------------------------------------------------------
    # MODELO
    # --------------------------------------------------------

    modelo = _texto(
        modelo
    )

    modelo_django = (
        obtener_modelo_django(
            modelo
        )
    )

    if modelo_django is None:

        return _error(
            fase="modelo",
            razon=(
                "El modelo principal no pudo resolverse "
                "de forma inequívoca."
            ),
            modelo=modelo,
        )

    # --------------------------------------------------------
    # CAMPO DE AGRUPACIÓN
    # --------------------------------------------------------

    if not isinstance(
        campo_agrupacion,
        dict,
    ):

        return _error(
            fase="campo_agrupacion",
            razon=(
                "El campo de agrupación debe venir "
                "certificado como diccionario HOST."
            ),
            modelo=modelo,
        )

    nombre_agrupacion = _texto(
        campo_agrupacion.get(
            "nombre"
        )
    )

    if not nombre_agrupacion:

        return _error(
            fase="campo_agrupacion",
            razon=(
                "El campo de agrupación no contiene "
                "un nombre canónico."
            ),
            modelo=modelo,
        )

    campo_django = (
        _resolver_campo_modelo(
            modelo_django=modelo_django,
            nombre=nombre_agrupacion,
        )
    )

    if campo_django is None:

        return _error(
            fase="campo_agrupacion",
            razon=(
                "El campo de agrupación no existe "
                "en Django._meta."
            ),
            modelo=modelo,
            campo_agrupacion=campo_agrupacion,
        )

    # --------------------------------------------------------
    # RESTRICCIÓN INICIAL:
    # sólo campos concretos del modelo principal.
    #
    # No relaciones reversas ni rutas __ todavía.
    # Eso se ampliará después.
    # --------------------------------------------------------

    if getattr(
        campo_django,
        "auto_created",
        False,
    ):

        return _error(
            fase="campo_agrupacion",
            razon=(
                "Las relaciones reversas auto-creadas "
                "no están habilitadas como campo de "
                "agrupación en HOST035-v1."
            ),
            modelo=modelo,
            campo_agrupacion=campo_agrupacion,
        )

    if (
        getattr(
            campo_django,
            "many_to_many",
            False,
        )
        or getattr(
            campo_django,
            "one_to_many",
            False,
        )
    ):

        return _error(
            fase="campo_agrupacion",
            razon=(
                "Una relación multivaluada no puede "
                "usarse como clave de agrupación en "
                "HOST035-v1."
            ),
            modelo=modelo,
            campo_agrupacion=campo_agrupacion,
        )

    # --------------------------------------------------------
    # OPERACIÓN
    # --------------------------------------------------------

    if not isinstance(
        operacion_semantica,
        dict,
    ):

        return _error(
            fase="operacion",
            razon=(
                "La operación semántica debe venir "
                "certificada por HOST024."
            ),
            modelo=modelo,
        )

    if (
        operacion_semantica.get(
            "ok"
        )
        is not True
        or operacion_semantica.get(
            "resuelto"
        )
        is not True
        or operacion_semantica.get(
            "compatible"
        )
        is not True
    ):

        return _error(
            fase="operacion",
            razon=(
                "La operación no está certificada "
                "como compatible por HOST024."
            ),
            modelo=modelo,
            operacion_semantica=(
                operacion_semantica
            ),
        )

    nombre_operacion = _texto(
        operacion_semantica.get(
            "operacion_semantica"
        )
    )

    if (
        nombre_operacion
        not in OPERACIONES_AGRUPABLES
    ):

        return _error(
            fase="operacion",
            razon=(
                "La operación semántica no está "
                "habilitada para agrupamiento."
            ),
            modelo=modelo,
            operacion_semantica=(
                operacion_semantica
            ),
        )

    # --------------------------------------------------------
    # OBJETIVO AGREGADO
    # --------------------------------------------------------

    if (
        nombre_operacion
        == "contar_registros"
    ):

        if objetivo_agregado is not None:

            return _error(
                fase="objetivo_agregado",
                razon=(
                    "contar_registros no requiere "
                    "objetivo agregado."
                ),
                modelo=modelo,
            )

    else:

        if not isinstance(
            objetivo_agregado,
            dict,
        ):

            return _error(
                fase="objetivo_agregado",
                razon=(
                    "La operación agregada requiere "
                    "un objetivo certificado."
                ),
                modelo=modelo,
            )

        nombre_objetivo = _texto(
            objetivo_agregado.get(
                "nombre"
            )
        )

        if not nombre_objetivo:

            return _error(
                fase="objetivo_agregado",
                razon=(
                    "El objetivo agregado no contiene "
                    "un nombre canónico."
                ),
                modelo=modelo,
            )

        campo_objetivo = (
            _resolver_campo_modelo(
                modelo_django=modelo_django,
                nombre=nombre_objetivo,
            )
        )

        if campo_objetivo is None:

            return _error(
                fase="objetivo_agregado",
                razon=(
                    "El objetivo agregado no existe "
                    "en Django._meta."
                ),
                modelo=modelo,
                objetivo_agregado=(
                    objetivo_agregado
                ),
            )

    # --------------------------------------------------------
    # CONTRATO VALIDADO
    # --------------------------------------------------------

    return {
        "ok": True,
        "version": VERSION,
        "agrupamiento_valido": True,
        "modelo": modelo,

        "campo_agrupacion": {
            "nombre":
                nombre_agrupacion,

            "tipo_django":
                campo_django.__class__.__name__,

            "relacion":
                bool(
                    getattr(
                        campo_django,
                        "is_relation",
                        False,
                    )
                ),

            "modelo_relacionado":
                (
                    campo_django.related_model._meta.label
                    if (
                        getattr(
                            campo_django,
                            "is_relation",
                            False,
                        )
                        and getattr(
                            campo_django,
                            "related_model",
                            None,
                        )
                        is not None
                    )
                    else None
                ),
        },

        "operacion_semantica": {
            "operacion_semantica":
                nombre_operacion,

            "accion_plan":
                operacion_semantica.get(
                    "accion_plan"
                ),
        },

        "objetivo_agregado":
            objetivo_agregado,

        "ejecutable":
            False,

        "ejecutor_sugerido":
            "ejecutor_agrupamiento_datos",

        "origen":
            "determinista",

        "llm_invocado":
            False,

        "razon":
            (
                "HOST035 certificó la combinación "
                "de campo agrupador y operación "
                "agregada contra Django._meta."
            ),
    }