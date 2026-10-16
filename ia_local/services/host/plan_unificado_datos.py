from __future__ import annotations

from typing import Any

from .catalogo_datos import obtener_modelo_django
from .validador_plan_datos import validar_plan_datos


# ============================================================
# IA-HOST033
# PLAN UNIFICADO DE CONSULTA DE DATOS
# ============================================================
#
# Objetivo:
#   representar en un único contrato declarativo una consulta
#   suficientemente rica para que HOST034 pueda decidir qué
#   ejecutor seguro corresponde.
#
# HOST033:
#   - NO ejecuta ORM;
#   - NO usa LLM;
#   - NO descubre semántica por sí solo;
#   - NO inventa rutas ni correspondencias;
#   - NO modifica planes existentes;
#   - valida y normaliza componentes ya resueltos por HOST023-HOST032.
#
# El contrato unificado puede representar:
#
#   estrategia = "directa"
#   estrategia = "relacion_orm"
#   estrategia = "coleccion_serializada"
#   estrategia = "coleccion_estructurada"
#   estrategia = "correspondencia_virtual"
#
# ============================================================


ESTRATEGIAS_PERMITIDAS = {
    "directa",
    "relacion_orm",
    "coleccion_serializada",
    "coleccion_estructurada",
    "correspondencia_virtual",
}

OPERACIONES_SEMANTICAS_PERMITIDAS = {
    "listar_registros",
    "contar_registros",
    "contar_objetivo",
    "sumar_objetivo",
    "promediar_objetivo",
    "minimo_objetivo",
    "maximo_objetivo",
}


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _error(
    *,
    fase: str,
    mensaje: str,
) -> dict[str, Any]:
    return {
        "ok": False,
        "plan_unificado_valido": False,
        "fase": fase,
        "errores": [mensaje],
        "llm_invocado": False,
    }


def _validar_modelo(
    label: str,
) -> tuple[bool, Any, str | None]:

    modelo = obtener_modelo_django(
        label
    )

    if modelo is None:
        return (
            False,
            None,
            (
                f"El modelo {label!r} no pudo resolverse "
                "de forma inequívoca."
            ),
        )

    return True, modelo, None


def _validar_objetivo(
    objetivo: dict[str, Any] | None,
) -> tuple[bool, dict[str, Any] | None, str | None]:

    if objetivo is None:
        return True, None, None

    if not isinstance(
        objetivo,
        dict,
    ):
        return (
            False,
            None,
            "El objetivo debe ser un diccionario o None.",
        )

    salida = {
        "resuelto": bool(
            objetivo.get(
                "resuelto",
                False,
            )
        ),
        "tipo_objetivo": _texto(
            objetivo.get(
                "tipo_objetivo"
            )
        ),
        "nombre": _texto(
            objetivo.get(
                "nombre"
            )
        ),
        "tipo_django": _texto(
            objetivo.get(
                "tipo_django"
            )
        ),
        "foco": _texto(
            objetivo.get(
                "foco"
            )
        ),
    }

    return True, salida, None


def _validar_operacion(
    operacion: dict[str, Any] | None,
) -> tuple[bool, dict[str, Any] | None, str | None]:

    if operacion is None:
        return True, None, None

    if not isinstance(
        operacion,
        dict,
    ):
        return (
            False,
            None,
            "La operación semántica debe ser un diccionario o None.",
        )

    nombre = _texto(
        operacion.get(
            "operacion_semantica"
        )
    )

    if (
        nombre
        and nombre
        not in OPERACIONES_SEMANTICAS_PERMITIDAS
    ):
        return (
            False,
            None,
            (
                "Operación semántica no permitida: "
                f"{nombre!r}."
            ),
        )

    salida = {
        "operacion_semantica": nombre,
        "compatible": bool(
            operacion.get(
                "compatible",
                False,
            )
        ),
        "accion_plan": operacion.get(
            "accion_plan"
        ),
    }

    return True, salida, None


def _validar_ruta(
    ruta: dict[str, Any] | None,
) -> tuple[bool, dict[str, Any] | None, str | None]:

    if ruta is None:
        return True, None, None

    if not isinstance(
        ruta,
        dict,
    ):
        return (
            False,
            None,
            "La ruta debe ser un diccionario o None.",
        )

    ruta_orm = _texto(
        ruta.get(
            "ruta_orm",
            ruta.get(
                "ruta",
            ),
        )
    )

    valida = bool(
        ruta.get(
            "valida",
            ruta.get(
                "resuelta",
                False,
            ),
        )
    )

    return (
        True,
        {
            "ok": bool(
                ruta.get(
                    "ok",
                    True,
                )
            ),
            "valida": valida,
            "resuelta": valida,
            "ruta_orm": ruta_orm,
            "ruta": ruta_orm,
            "modelo_origen": _texto(
                ruta.get(
                    "modelo_origen"
                )
            ),
            "modelo_destino": _texto(
                ruta.get(
                    "modelo_destino"
                )
            ),
            "profundidad": ruta.get(
                "profundidad"
            ),
            "pasos": list(
                ruta.get(
                    "pasos",
                    [],
                )
            ),
            "contiene_relacion_multiple": bool(
                ruta.get(
                    "contiene_relacion_multiple",
                    False,
                )
            ),
            "origen": _texto(
                ruta.get(
                    "origen"
                )
            ),
            "llm_invocado": False,
        },
        None,
    )


def _validar_representacion(
    representacion: dict[str, Any] | None,
) -> tuple[bool, dict[str, Any] | None, str | None]:

    if representacion is None:
        return True, None, None

    if not isinstance(
        representacion,
        dict,
    ):
        return (
            False,
            None,
            (
                "La representación debe ser un diccionario "
                "o None."
            ),
        )

    nombre = _texto(
        representacion.get(
            "nombre",
            representacion.get(
                "campo",
            ),
        )
    )

    salida = {
        "ok": bool(
            representacion.get(
                "ok",
                True,
            )
        ),
        "resuelto": bool(
            representacion.get(
                "resuelto",
                True,
            )
        ),
        "modelo": _texto(
            representacion.get(
                "modelo"
            )
        ),
        "nombre": nombre,
        "campo": nombre,
        "tipo_django": _texto(
            representacion.get(
                "tipo_django"
            )
        ),
        "tipo_representacion": _texto(
            representacion.get(
                "tipo_representacion"
            )
        ),
        "prefijo": _texto(
            representacion.get(
                "prefijo"
            )
        ),
        "formato": _texto(
            representacion.get(
                "formato"
            )
        ),
        "separador": representacion.get(
            "separador"
        ),
        "nombre_separador": _texto(
            representacion.get(
                "nombre_separador"
            )
        ),
        "confianza": _texto(
            representacion.get(
                "confianza"
            )
        ),
        "requiere_validacion_codigo": bool(
            representacion.get(
                "requiere_validacion_codigo",
                False,
            )
        ),
        "contable_como_coleccion": bool(
            representacion.get(
                "contable_como_coleccion",
                False,
            )
        ),
        "llm_invocado": False,
    }

    return True, salida, None


def _validar_serializacion(
    validacion: dict[str, Any] | None,
) -> tuple[bool, dict[str, Any] | None, str | None]:

    if validacion is None:
        return True, None, None

    if not isinstance(
        validacion,
        dict,
    ):
        return (
            False,
            None,
            (
                "La validación de serialización debe ser un "
                "diccionario o None."
            ),
        )

    salida = {
        "ok": bool(
            validacion.get(
                "ok",
                False,
            )
        ),
        "resuelto": bool(
            validacion.get(
                "resuelto",
                False,
            )
        ),
        "aplica": bool(
            validacion.get(
                "aplica",
                False,
            )
        ),
        "validado": bool(
            validacion.get(
                "validado",
                False,
            )
        ),
        "modelo": _texto(
            validacion.get(
                "modelo"
            )
        ),
        "campo": _texto(
            validacion.get(
                "campo"
            )
        ),
        "tipo_representacion": _texto(
            validacion.get(
                "tipo_representacion"
            )
        ),
        "separador": validacion.get(
            "separador"
        ),
        "separador_normalizado": validacion.get(
            "separador_normalizado"
        ),
        "estrategia_conteo": _texto(
            validacion.get(
                "estrategia_conteo"
            )
        ),
        "total_escrituras_compatibles": validacion.get(
            "total_escrituras_compatibles"
        ),
        "total_lecturas_compatibles": validacion.get(
            "total_lecturas_compatibles"
        ),
        "total_incompatibilidades": validacion.get(
            "total_incompatibilidades"
        ),
        "razon": _texto(
            validacion.get(
                "razon"
            )
        ),
        "origen": _texto(
            validacion.get(
                "origen"
            )
        ),
        "llm_invocado": False,
    }

    return True, salida, None


def _validar_correspondencia(
    correspondencia: dict[str, Any] | None,
) -> tuple[bool, dict[str, Any] | None, str | None]:

    if correspondencia is None:
        return True, None, None

    if not isinstance(
        correspondencia,
        dict,
    ):
        return (
            False,
            None,
            (
                "La correspondencia virtual debe ser un "
                "diccionario o None."
            ),
        )

    salida = {
        "validado": bool(
            correspondencia.get(
                "validado",
                False,
            )
        ),
        "modelo_origen": _texto(
            correspondencia.get(
                "modelo_origen"
            )
        ),
        "modelo_destino": _texto(
            correspondencia.get(
                "modelo_destino"
            )
        ),
        "campo_clave_destino": _texto(
            correspondencia.get(
                "campo_clave_destino"
            )
        ),
        "cardinalidad": _texto(
            correspondencia.get(
                "cardinalidad"
            )
        ),
        "cobertura": correspondencia.get(
            "cobertura"
        ),
        "destinos_unicos": correspondencia.get(
            "destinos_unicos"
        ),
        "claves_destino_validadas": list(
            correspondencia.get(
                "claves_destino_validadas",
                [],
            )
        ),
    }

    return True, salida, None


def construir_plan_unificado_datos(
    *,
    plan_base: dict[str, Any],
    estrategia: str,
    objetivo: dict[str, Any] | None = None,
    operacion_semantica: dict[str, Any] | None = None,
    ruta: dict[str, Any] | None = None,
    representacion: dict[str, Any] | None = None,
    validacion_serializacion: dict[str, Any] | None = None,
    correspondencia_virtual: dict[str, Any] | None = None,
    modelo_destino: str | None = None,
    campo_clave_destino: str | None = None,
    prefijo_coleccion: str | None = None,
    operacion_relacional: str = "contar_destinos_unicos",
    metadatos: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Construye y valida un plan unificado sin ejecutar datos.
    """

    estrategia = _texto(
        estrategia
    )

    if estrategia not in ESTRATEGIAS_PERMITIDAS:
        return _error(
            fase="estrategia",
            mensaje=(
                f"Estrategia no permitida: {estrategia!r}."
            ),
        )

    # --------------------------------------------------------
    # 1. PLAN BASE
    # --------------------------------------------------------

    validacion_base = validar_plan_datos(
        plan_base
    )

    if not validacion_base.get(
        "plan_validado"
    ):
        return {
            "ok": False,
            "plan_unificado_valido": False,
            "fase": "plan_base",
            "errores": validacion_base.get(
                "errores",
                [],
            ),
            "validacion_plan_base": validacion_base,
            "llm_invocado": False,
        }

    plan_seguro = validacion_base.get(
        "plan"
    )

    if not isinstance(
        plan_seguro,
        dict,
    ):
        return _error(
            fase="plan_base",
            mensaje="No se obtuvo un plan base validado.",
        )

    modelo_base_label = _texto(
        plan_seguro.get(
            "modelo"
        )
    )

    ok_modelo, modelo_base, error_modelo = (
        _validar_modelo(
            modelo_base_label
        )
    )

    if not ok_modelo:
        return _error(
            fase="modelo_base",
            mensaje=error_modelo or "Modelo base inválido.",
        )

    # --------------------------------------------------------
    # 2. COMPONENTES OPCIONALES
    # --------------------------------------------------------

    ok, objetivo_norm, error = _validar_objetivo(
        objetivo
    )
    if not ok:
        return _error(
            fase="objetivo",
            mensaje=error or "Objetivo inválido.",
        )

    ok, operacion_norm, error = _validar_operacion(
        operacion_semantica
    )
    if not ok:
        return _error(
            fase="operacion",
            mensaje=error or "Operación inválida.",
        )

    ok, ruta_norm, error = _validar_ruta(
        ruta
    )
    if not ok:
        return _error(
            fase="ruta",
            mensaje=error or "Ruta inválida.",
        )

    ok, representacion_norm, error = (
        _validar_representacion(
            representacion
        )
    )
    if not ok:
        return _error(
            fase="representacion",
            mensaje=error or "Representación inválida.",
        )

    ok, serializacion_norm, error = (
        _validar_serializacion(
            validacion_serializacion
        )
    )
    if not ok:
        return _error(
            fase="validacion_serializacion",
            mensaje=error or "Validación de serialización inválida.",
        )

    ok, correspondencia_norm, error = (
        _validar_correspondencia(
            correspondencia_virtual
        )
    )
    if not ok:
        return _error(
            fase="correspondencia_virtual",
            mensaje=error or "Correspondencia inválida.",
        )

    # --------------------------------------------------------
    # 3. VALIDACIONES POR ESTRATEGIA
    # --------------------------------------------------------

    modelo_destino = _texto(
        modelo_destino
    )
    campo_clave_destino = _texto(
        campo_clave_destino
    )
    prefijo_coleccion = _texto(
        prefijo_coleccion
    )

    operacion_relacional = _texto(
        operacion_relacional
    )

    if estrategia == "relacion_orm":
        if not ruta_norm or not ruta_norm.get(
            "valida"
        ):
            return _error(
                fase="estrategia",
                mensaje=(
                    "La estrategia relacion_orm exige una ruta "
                    "HOST025 previamente validada."
                ),
            )

        if not ruta_norm.get(
            "ruta_orm"
        ):
            return _error(
                fase="estrategia",
                mensaje="La ruta HOST025 no contiene ruta_orm.",
            )

        if (
            ruta_norm.get(
                "modelo_origen"
            )
            and ruta_norm.get(
                "modelo_origen"
            )
            != modelo_base._meta.label
        ):
            return _error(
                fase="consistencia",
                mensaje=(
                    "El modelo origen de HOST025 y el modelo "
                    "base no coinciden."
                ),
            )

        if (
            operacion_relacional
            != "contar_destinos_unicos"
        ):
            return _error(
                fase="operacion_relacional",
                mensaje=(
                    "HOST033-C01 sólo admite "
                    "contar_destinos_unicos en esta fase."
                ),
            )

    if estrategia == "coleccion_serializada":
        if not representacion_norm:
            return _error(
                fase="estrategia",
                mensaje=(
                    "La estrategia coleccion_serializada exige "
                    "una representación HOST026."
                ),
            )

        if (
            representacion_norm.get(
                "tipo_representacion"
            )
            != "coleccion_serializada"
        ):
            return _error(
                fase="estrategia",
                mensaje=(
                    "La representación no es una "
                    "coleccion_serializada."
                ),
            )

        if not serializacion_norm:
            return _error(
                fase="estrategia",
                mensaje=(
                    "La estrategia coleccion_serializada exige "
                    "la validación HOST027."
                ),
            )

        if not (
            serializacion_norm.get(
                "aplica"
            )
            and serializacion_norm.get(
                "validado"
            )
        ):
            return _error(
                fase="estrategia",
                mensaje=(
                    "El contrato HOST027 de serialización no "
                    "está validado."
                ),
            )

        if (
            serializacion_norm.get(
                "modelo"
            )
            and serializacion_norm.get(
                "modelo"
            )
            != modelo_base._meta.label
        ):
            return _error(
                fase="consistencia",
                mensaje=(
                    "El modelo HOST027 y el modelo base no coinciden."
                ),
            )

        if (
            serializacion_norm.get(
                "campo"
            )
            != representacion_norm.get(
                "nombre"
            )
        ):
            return _error(
                fase="consistencia",
                mensaje=(
                    "El campo HOST026 y el campo HOST027 no coinciden."
                ),
            )

        if (
            serializacion_norm.get(
                "separador"
            )
            != representacion_norm.get(
                "separador"
            )
        ):
            return _error(
                fase="consistencia",
                mensaje=(
                    "El separador HOST026 y HOST027 no coinciden."
                ),
            )

    if estrategia == "coleccion_estructurada":
        if not prefijo_coleccion:
            return _error(
                fase="estrategia",
                mensaje=(
                    "La estrategia coleccion_estructurada exige "
                    "prefijo_coleccion."
                ),
            )

    if estrategia == "correspondencia_virtual":
        if not correspondencia_norm:
            return _error(
                fase="estrategia",
                mensaje=(
                    "La estrategia correspondencia_virtual exige "
                    "una correspondencia previamente validada."
                ),
            )

        if not correspondencia_norm.get(
            "validado"
        ):
            return _error(
                fase="estrategia",
                mensaje=(
                    "La correspondencia virtual entregada no está "
                    "validada."
                ),
            )

        if not modelo_destino:
            modelo_destino = _texto(
                correspondencia_norm.get(
                    "modelo_destino"
                )
            )

        if not campo_clave_destino:
            campo_clave_destino = _texto(
                correspondencia_norm.get(
                    "campo_clave_destino"
                )
            )

        if not modelo_destino:
            return _error(
                fase="estrategia",
                mensaje=(
                    "La estrategia correspondencia_virtual exige "
                    "modelo_destino."
                ),
            )

        ok_destino, modelo_destino_django, error_destino = (
            _validar_modelo(
                modelo_destino
            )
        )

        if not ok_destino:
            return _error(
                fase="modelo_destino",
                mensaje=(
                    error_destino
                    or "Modelo destino inválido."
                ),
            )

        if not campo_clave_destino:
            return _error(
                fase="clave_destino",
                mensaje=(
                    "La estrategia correspondencia_virtual exige "
                    "campo_clave_destino."
                ),
            )

        try:
            campo_destino = (
                modelo_destino_django._meta.get_field(
                    campo_clave_destino
                )
            )
        except Exception:
            return _error(
                fase="clave_destino",
                mensaje=(
                    "El campo clave destino no existe en el "
                    "modelo destino."
                ),
            )

        if bool(
            getattr(
                campo_destino,
                "is_relation",
                False,
            )
        ):
            return _error(
                fase="clave_destino",
                mensaje=(
                    "El campo clave destino no puede ser una "
                    "relación."
                ),
            )

    # --------------------------------------------------------
    # 4. CONTRATO FINAL
    # --------------------------------------------------------

    plan_unificado = {
        "version": "IA-HOST033-v1-C01",
        "modelo_base": {
            "label": modelo_base._meta.label,
            "tabla": modelo_base._meta.db_table,
        },
        "plan_base": plan_seguro,
        "objetivo": objetivo_norm,
        "operacion_semantica": operacion_norm,
        "estrategia": estrategia,
        "ruta": ruta_norm,
        "representacion": representacion_norm,
        "validacion_serializacion": serializacion_norm,
        "contrato_relacional": {
            "ruta_validada": ruta_norm,
            "operacion_relacional": operacion_relacional,
        } if estrategia == "relacion_orm" else None,
        "correspondencia_virtual": correspondencia_norm,
        "destino": {
            "modelo": modelo_destino or None,
            "campo_clave": (
                campo_clave_destino
                or None
            ),
            "prefijo_coleccion": (
                prefijo_coleccion
                or None
            ),
        },
        "metadatos": (
            dict(metadatos)
            if isinstance(
                metadatos,
                dict,
            )
            else {}
        ),
        "ejecucion": {
            "permitida": True,
            "ejecutada": False,
            "ejecutor_sugerido": {
                "directa": "ejecutor_datos",
                "relacion_orm": "ejecutor_relacion_orm",
                "coleccion_serializada": (
                    "ejecutor_coleccion_datos"
                ),
                "coleccion_estructurada": (
                    "ejecutor_coleccion_estructurada"
                ),
                "correspondencia_virtual": (
                    "ejecutor_destinos_validados"
                ),
            }[
                estrategia
            ],
        },
        "evidencia": {
            "plan_base_validado": True,
            "modelo_base_resuelto": True,
            "llm_invocado": False,
        },
    }

    return {
        "ok": True,
        "plan_unificado_valido": True,
        "plan_unificado": plan_unificado,
        "llm_invocado": False,
    }


def validar_plan_unificado_datos(
    plan_unificado: dict[str, Any],
) -> dict[str, Any]:
    """
    Revalida la forma mínima del contrato generado por HOST033.
    No ejecuta ORM.
    """

    if not isinstance(
        plan_unificado,
        dict,
    ):
        return _error(
            fase="forma",
            mensaje="El plan unificado debe ser un diccionario.",
        )

    version = _texto(
        plan_unificado.get(
            "version"
        )
    )

    if version not in {
        "IA-HOST033-v1",
        "IA-HOST033-v1-C01",
    }:
        return _error(
            fase="version",
            mensaje=(
                f"Versión de plan no soportada: {version!r}."
            ),
        )

    estrategia = _texto(
        plan_unificado.get(
            "estrategia"
        )
    )

    if estrategia not in ESTRATEGIAS_PERMITIDAS:
        return _error(
            fase="estrategia",
            mensaje="Estrategia inválida en plan unificado.",
        )

    modelo_base = plan_unificado.get(
        "modelo_base"
    )

    if not isinstance(
        modelo_base,
        dict,
    ):
        return _error(
            fase="modelo_base",
            mensaje="Falta modelo_base.",
        )

    label = _texto(
        modelo_base.get(
            "label"
        )
    )

    ok_modelo, _, error_modelo = _validar_modelo(
        label
    )

    if not ok_modelo:
        return _error(
            fase="modelo_base",
            mensaje=error_modelo or "Modelo base inválido.",
        )

    plan_base = plan_unificado.get(
        "plan_base"
    )

    validacion_base = validar_plan_datos(
        plan_base
    )

    if not validacion_base.get(
        "plan_validado"
    ):
        return {
            "ok": False,
            "plan_unificado_valido": False,
            "fase": "plan_base",
            "errores": validacion_base.get(
                "errores",
                [],
            ),
            "llm_invocado": False,
        }

    if estrategia == "coleccion_serializada":
        if version != "IA-HOST033-v1-C01":
            return _error(
                fase="version",
                mensaje=(
                    "coleccion_serializada ejecutable exige "
                    "IA-HOST033-v1-C01."
                ),
            )

        serializacion = plan_unificado.get(
            "validacion_serializacion"
        )

        if not (
            isinstance(
                serializacion,
                dict,
            )
            and serializacion.get(
                "aplica"
            )
            and serializacion.get(
                "validado"
            )
        ):
            return _error(
                fase="validacion_serializacion",
                mensaje=(
                    "Falta un contrato HOST027 validado."
                ),
            )

    if estrategia == "relacion_orm":
        if version != "IA-HOST033-v1-C01":
            return _error(
                fase="version",
                mensaje=(
                    "relacion_orm ejecutable exige "
                    "IA-HOST033-v1-C01."
                ),
            )

        contrato = plan_unificado.get(
            "contrato_relacional"
        )

        if not isinstance(
            contrato,
            dict,
        ):
            return _error(
                fase="contrato_relacional",
                mensaje="Falta contrato_relacional.",
            )

        ruta_validada = contrato.get(
            "ruta_validada"
        )

        if not (
            isinstance(
                ruta_validada,
                dict,
            )
            and ruta_validada.get(
                "valida"
            )
            and ruta_validada.get(
                "ruta_orm"
            )
        ):
            return _error(
                fase="contrato_relacional",
                mensaje=(
                    "El contrato no conserva una ruta HOST025 válida."
                ),
            )

    return {
        "ok": True,
        "plan_unificado_valido": True,
        "version": version,
        "estrategia": estrategia,
        "modelo_base": label,
        "ejecutor_sugerido": (
            plan_unificado.get(
                "ejecucion",
                {}
            ).get(
                "ejecutor_sugerido"
            )
        ),
        "llm_invocado": False,
    }
