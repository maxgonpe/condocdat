from __future__ import annotations

from typing import Any

from django.db import DatabaseError

from .catalogo_datos import obtener_modelo_django
from .descriptor_colecciones_estructuradas import (
    obtener_coleccion_estructurada,
)
from .ejecutor_datos import ejecutar_plan_datos
from .ejecutor_coleccion_estructurada import (
    contar_coleccion_estructurada_modelo,
)
from .ejecutor_coleccion_datos import (
    ejecutar_conteo_coleccion_serializada,
)
from .ejecutor_relacion_orm import (
    ejecutar_conteo_ruta_relacional,
)
from .plan_unificado_datos import (
    validar_plan_unificado_datos,
)


# ============================================================
# IA-HOST034
# ORQUESTADOR DE EJECUCIÓN DE PLAN UNIFICADO
# ============================================================
#
# Responsabilidad:
#   recibir un contrato HOST033 ya construido y:
#
#       1. revalidarlo;
#       2. leer su estrategia;
#       3. delegar únicamente en una vía de ejecución permitida;
#       4. normalizar el resultado.
#
# HOST034 NO:
#   - interpreta lenguaje natural;
#   - descubre modelos;
#   - resuelve semántica nueva;
#   - inventa rutas;
#   - inventa correspondencias;
#   - usa LLM;
#   - usa SQL crudo.
#
# Estrategias ejecutables en HOST034-C01:
#
#   directa
#       -> ejecutar_plan_datos()
#
#   relacion_orm
#       -> ejecutar_conteo_ruta_relacional()
#
#   coleccion_serializada
#       -> ejecutar_conteo_coleccion_serializada()
#
#   coleccion_estructurada
#       -> contar_coleccion_estructurada_modelo()
#
#   correspondencia_virtual
#       -> ejecuta exclusivamente sobre las claves destino YA
#          validadas y preservadas por HOST033.
#
# Cada rama exige el contrato/evidencia de su HOST especializado.
#
# ============================================================


ITERATOR_CHUNK_SIZE = 1000


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _valor_presente(valor: Any) -> bool:
    if valor is None:
        return False

    if isinstance(valor, str):
        return bool(valor.strip())

    return True


def _error(
    *,
    fase: str,
    mensaje: str,
    estrategia: str | None = None,
) -> dict[str, Any]:

    salida = {
        "ok": False,
        "ejecutado": False,
        "fase": fase,
        "errores": [mensaje],
        "llm_invocado": False,
    }

    if estrategia:
        salida["estrategia"] = estrategia

    return salida


def _resultado_normalizado(
    *,
    estrategia: str,
    ejecutor: str,
    resultado: dict[str, Any],
) -> dict[str, Any]:

    return {
        "ok": bool(
            resultado.get(
                "ok",
                False,
            )
        ),
        "ejecutado": bool(
            resultado.get(
                "ejecutado",
                resultado.get(
                    "ok",
                    False,
                ),
            )
        ),
        "estrategia": estrategia,
        "ejecutor": ejecutor,
        "resultado": resultado,
        "llm_invocado": False,
    }


def _mapa_slots(
    coleccion: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:

    slots = []
    campos = []

    for slot in coleccion.get(
        "slots",
        [],
    ):
        indice = _texto(
            slot.get(
                "indice"
            )
        )

        campos_slot = []

        for atributo in slot.get(
            "atributos_presentes",
            [],
        ):
            descripcion = (
                slot.get(
                    "campos",
                    {},
                ).get(
                    atributo
                )
            )

            if not isinstance(
                descripcion,
                dict,
            ):
                continue

            nombre = _texto(
                descripcion.get(
                    "nombre"
                )
            )

            if not nombre:
                continue

            campos_slot.append(
                {
                    "atributo":
                        atributo,

                    "campo":
                        nombre,
                }
            )

            campos.append(
                nombre
            )

        if indice and campos_slot:
            slots.append(
                {
                    "indice":
                        indice,

                    "campos":
                        campos_slot,
                }
            )

    return (
        slots,
        list(
            dict.fromkeys(
                campos
            )
        ),
    )


def _ejecutar_correspondencia_virtual(
    plan_unificado: dict[str, Any],
) -> dict[str, Any]:
    """
    Ejecuta el destino YA validado por HOST031/HOST033.

    No vuelve a descubrir la correspondencia.
    No vuelve a buscar por texto.
    Usa sólo:
        - modelo destino validado;
        - clave destino;
        - claves destino validadas;
        - colección estructurada declarada.
    """

    correspondencia = (
        plan_unificado.get(
            "correspondencia_virtual"
        )
    )

    destino = (
        plan_unificado.get(
            "destino",
            {}
        )
    )

    if not isinstance(
        correspondencia,
        dict,
    ):
        return _error(
            fase="correspondencia_virtual",
            mensaje=(
                "El plan no contiene correspondencia virtual."
            ),
            estrategia="correspondencia_virtual",
        )

    if not correspondencia.get(
        "validado"
    ):
        return _error(
            fase="correspondencia_virtual",
            mensaje=(
                "La correspondencia del plan no está validada."
            ),
            estrategia="correspondencia_virtual",
        )

    modelo_destino = _texto(
        destino.get(
            "modelo"
        )
        or correspondencia.get(
            "modelo_destino"
        )
    )

    campo_clave = _texto(
        destino.get(
            "campo_clave"
        )
        or correspondencia.get(
            "campo_clave_destino"
        )
    )

    prefijo = _texto(
        destino.get(
            "prefijo_coleccion"
        )
    )

    claves = correspondencia.get(
        "claves_destino_validadas",
        []
    )

    if not isinstance(
        claves,
        list,
    ):
        return _error(
            fase="correspondencia_virtual",
            mensaje=(
                "Las claves destino validadas no tienen "
                "formato lista."
            ),
            estrategia="correspondencia_virtual",
        )

    claves_unicas = sorted(
        {
            _texto(
                clave
            )
            for clave
            in claves
            if _texto(
                clave
            )
        }
    )

    if not claves_unicas:
        return _error(
            fase="correspondencia_virtual",
            mensaje=(
                "La correspondencia validada no contiene "
                "claves destino utilizables."
            ),
            estrategia="correspondencia_virtual",
        )

    if not (
        modelo_destino
        and campo_clave
        and prefijo
    ):
        return _error(
            fase="destino",
            mensaje=(
                "La ejecución por correspondencia virtual exige "
                "modelo destino, campo clave y prefijo de colección."
            ),
            estrategia="correspondencia_virtual",
        )

    modelo_django = obtener_modelo_django(
        modelo_destino
    )

    if modelo_django is None:
        return _error(
            fase="modelo_destino",
            mensaje=(
                "El modelo destino ya no puede resolverse "
                "de forma inequívoca."
            ),
            estrategia="correspondencia_virtual",
        )

    try:
        campo_django = (
            modelo_django._meta.get_field(
                campo_clave
            )
        )
    except Exception:
        return _error(
            fase="clave_destino",
            mensaje=(
                "La clave destino ya no existe en Django._meta."
            ),
            estrategia="correspondencia_virtual",
        )

    if bool(
        getattr(
            campo_django,
            "is_relation",
            False,
        )
    ):
        return _error(
            fase="clave_destino",
            mensaje=(
                "La clave destino no puede ser una relación."
            ),
            estrategia="correspondencia_virtual",
        )

    if not (
        bool(
            getattr(
                campo_django,
                "primary_key",
                False,
            )
        )
        or bool(
            getattr(
                campo_django,
                "unique",
                False,
            )
        )
    ):
        return _error(
            fase="clave_destino",
            mensaje=(
                "La clave destino ya no es unique/PK."
            ),
            estrategia="correspondencia_virtual",
        )

    estructura = obtener_coleccion_estructurada(
        modelo=modelo_destino,
        prefijo=prefijo,
    )

    if not estructura.get(
        "resuelto"
    ):
        return _error(
            fase="coleccion_estructurada",
            mensaje=estructura.get(
                "razon",
                (
                    "HOST029 no pudo resolver la colección "
                    "estructurada."
                ),
            ),
            estrategia="correspondencia_virtual",
        )

    coleccion = estructura.get(
        "coleccion"
    )

    if not isinstance(
        coleccion,
        dict,
    ):
        return _error(
            fase="coleccion_estructurada",
            mensaje=(
                "HOST029 no entregó una colección válida."
            ),
            estrategia="correspondencia_virtual",
        )

    slots, campos = _mapa_slots(
        coleccion
    )

    if not slots or not campos:
        return _error(
            fase="coleccion_estructurada",
            mensaje=(
                "La colección no contiene slots/campos "
                "ejecutables."
            ),
            estrategia="correspondencia_virtual",
        )

    try:
        queryset = (
            modelo_django.objects.filter(
                **{
                    f"{campo_clave}__in":
                        claves_unicas
                }
            )
        )

        destinos_evaluados = (
            queryset.count()
        )

        if (
            destinos_evaluados
            != len(
                claves_unicas
            )
        ):
            return _error(
                fase="consistencia_destino",
                mensaje=(
                    "Las claves validadas y los destinos "
                    "recuperados ya no coinciden."
                ),
                estrategia="correspondencia_virtual",
            )

        columnas = [
            campo_clave,
            *campos,
        ]

        posiciones = {
            nombre: indice
            for indice, nombre
            in enumerate(
                columnas
            )
        }

        filas = (
            queryset
            .values_list(
                *columnas
            )
            .iterator(
                chunk_size=ITERATOR_CHUNK_SIZE
            )
        )

        slots_ocupados = 0
        slots_posibles = 0

        elementos_por_destino = {}

        for fila in filas:
            clave = _texto(
                fila[
                    posiciones[
                        campo_clave
                    ]
                ]
            )

            ocupados_destino = 0

            for slot in slots:
                slots_posibles += 1

                ocupado = any(
                    _valor_presente(
                        fila[
                            posiciones[
                                item[
                                    "campo"
                                ]
                            ]
                        ]
                    )
                    for item
                    in slot[
                        "campos"
                    ]
                )

                if ocupado:
                    slots_ocupados += 1
                    ocupados_destino += 1

            elementos_por_destino[
                clave
            ] = ocupados_destino

        destinos_con_elementos = sum(
            1
            for cantidad
            in elementos_por_destino.values()
            if cantidad > 0
        )

        resultado = {
            "ok": True,
            "ejecutado": True,
            "operacion": (
                "contar_elementos_coleccion_estructurada_"
                "sobre_destinos_prevalidados"
            ),
            "modelo_destino": modelo_django._meta.label,
            "tabla_destino": modelo_django._meta.db_table,
            "campo_clave_destino": campo_clave,
            "prefijo_coleccion": prefijo,
            "claves_destino_validadas": len(
                claves_unicas
            ),
            "destinos_evaluados": destinos_evaluados,
            "destinos_con_elementos": (
                destinos_con_elementos
            ),
            "destinos_sin_elementos": (
                destinos_evaluados
                - destinos_con_elementos
            ),
            "cantidad_slots_por_registro": (
                coleccion.get(
                    "cantidad_slots"
                )
            ),
            "slots_posibles": slots_posibles,
            "slots_ocupados": slots_ocupados,
            "slots_vacios": (
                slots_posibles
                - slots_ocupados
            ),
            "total": slots_ocupados,
            "elementos_por_destino": (
                elementos_por_destino
            ),
            "deduplicacion_destinos": True,
            "correspondencia_prevalidada": True,
            "llm_invocado": False,
        }

        return resultado

    except DatabaseError as exc:
        return _error(
            fase="orm",
            mensaje=str(
                exc
            ),
            estrategia="correspondencia_virtual",
        )


def ejecutar_plan_unificado_datos(
    plan_unificado: dict[str, Any],
) -> dict[str, Any]:
    """
    Punto único de ejecución para contratos HOST033-v1.
    """

    validacion = validar_plan_unificado_datos(
        plan_unificado
    )

    if not validacion.get(
        "plan_unificado_valido"
    ):
        return {
            "ok": False,
            "ejecutado": False,
            "fase": "validacion_host033",
            "errores": validacion.get(
                "errores",
                [
                    "HOST033 rechazó el plan unificado."
                ],
            ),
            "validacion": validacion,
            "llm_invocado": False,
        }

    estrategia = _texto(
        plan_unificado.get(
            "estrategia"
        )
    )

    # --------------------------------------------------------
    # DIRECTA
    # --------------------------------------------------------

    if estrategia == "directa":
        resultado = ejecutar_plan_datos(
            plan_unificado.get(
                "plan_base",
                {},
            )
        )

        return _resultado_normalizado(
            estrategia=estrategia,
            ejecutor="ejecutor_datos",
            resultado=resultado,
        )

    # --------------------------------------------------------
    # RELACIÓN ORM VALIDADA POR HOST025
    # --------------------------------------------------------

    if estrategia == "relacion_orm":
        contrato = plan_unificado.get(
            "contrato_relacional",
            {},
        )

        ruta_validada = contrato.get(
            "ruta_validada"
        )

        operacion_relacional = _texto(
            contrato.get(
                "operacion_relacional",
                "contar_destinos_unicos",
            )
        )

        resultado = ejecutar_conteo_ruta_relacional(
            plan=plan_unificado.get(
                "plan_base",
                {},
            ),
            ruta_validada=ruta_validada,
            operacion_relacional=operacion_relacional,
        )

        return _resultado_normalizado(
            estrategia=estrategia,
            ejecutor="ejecutor_relacion_orm",
            resultado=resultado,
        )

    # --------------------------------------------------------
    # COLECCIÓN SERIALIZADA HOST026 + HOST027 + HOST028
    # --------------------------------------------------------

    if estrategia == "coleccion_serializada":
        representacion = plan_unificado.get(
            "representacion"
        )

        validacion_serializacion = (
            plan_unificado.get(
                "validacion_serializacion"
            )
        )

        resultado = (
            ejecutar_conteo_coleccion_serializada(
                plan=plan_unificado.get(
                    "plan_base",
                    {},
                ),
                representacion_host=representacion,
                validacion_serializacion=(
                    validacion_serializacion
                ),
            )
        )

        return _resultado_normalizado(
            estrategia=estrategia,
            ejecutor="ejecutor_coleccion_datos",
            resultado=resultado,
        )

    # --------------------------------------------------------
    # COLECCIÓN ESTRUCTURADA SOBRE TODO EL MODELO
    # --------------------------------------------------------

    if estrategia == "coleccion_estructurada":
        destino = plan_unificado.get(
            "destino",
            {},
        )

        modelo = _texto(
            destino.get(
                "modelo"
            )
            or plan_unificado.get(
                "modelo_base",
                {},
            ).get(
                "label"
            )
        )

        prefijo = _texto(
            destino.get(
                "prefijo_coleccion"
            )
        )

        if not prefijo:
            return _error(
                fase="destino",
                mensaje=(
                    "La estrategia coleccion_estructurada "
                    "no contiene prefijo_coleccion."
                ),
                estrategia=estrategia,
            )

        resultado = (
            contar_coleccion_estructurada_modelo(
                modelo=modelo,
                prefijo=prefijo,
            )
        )

        return _resultado_normalizado(
            estrategia=estrategia,
            ejecutor=(
                "ejecutor_coleccion_estructurada"
            ),
            resultado=resultado,
        )

    # --------------------------------------------------------
    # CORRESPONDENCIA VIRTUAL PREVALIDADA
    # --------------------------------------------------------

    if estrategia == "correspondencia_virtual":
        resultado = (
            _ejecutar_correspondencia_virtual(
                plan_unificado
            )
        )

        return _resultado_normalizado(
            estrategia=estrategia,
            ejecutor=(
                "ejecutor_destinos_prevalidados"
            ),
            resultado=resultado,
        )

    return _error(
        fase="estrategia",
        mensaje=(
            f"Estrategia no soportada: {estrategia!r}."
        ),
        estrategia=estrategia,
    )
