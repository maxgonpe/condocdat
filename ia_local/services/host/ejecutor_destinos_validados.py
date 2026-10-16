from __future__ import annotations

from typing import Any

from django.db import DatabaseError

from .catalogo_datos import obtener_modelo_django
from .descriptor_colecciones_estructuradas import (
    obtener_coleccion_estructurada,
)
from .validador_correspondencia_virtual import (
    validar_correspondencia_virtual,
)


# ============================================================
# IA-HOST032
# EJECUCIÓN SOBRE DESTINOS VALIDADOS POR CORRESPONDENCIA VIRTUAL
# ============================================================
#
# Objetivo:
#   encadenar de forma segura:
#
#       plan origen validado
#           ↓
#       HOST031
#       correspondencia virtual validada
#           ↓
#       claves destino únicas
#           ↓
#       HOST029
#       colección estructurada destino
#           ↓
#       conteo de slots ocupados SOLO en ese subconjunto
#
# Decisión semántica:
#   las claves destino se deduplican antes de contar.
#
# Ejemplo:
#   si dos correos apuntan al mismo transmittal, ese transmittal se
#   evalúa una sola vez. Esto evita duplicar sus elementos lógicos.
#
# HOST032:
#   - NO inventa FK;
#   - NO usa fuzzy matching;
#   - NO usa LLM;
#   - NO usa SQL crudo;
#   - NO hardcodea nombres de proyectos/modelos/campos;
#   - exige que HOST031 haya validado completamente la correspondencia;
#   - usa únicamente la clave destino unique/PK ya validada;
#   - consume únicamente campos declarados por HOST029.
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


def _resultado_error(
    *,
    fase: str,
    mensaje: str,
) -> dict[str, Any]:
    return {
        "ok": False,
        "ejecutado": False,
        "fase": fase,
        "errores": [mensaje],
        "llm_invocado": False,
    }


def _construir_mapa_slots(
    coleccion: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:

    slots = []
    campos = []

    for slot in coleccion.get("slots", []):
        indice = _texto(slot.get("indice"))

        campos_slot = []

        for atributo in slot.get(
            "atributos_presentes",
            [],
        ):
            descripcion = (
                slot.get("campos", {})
                .get(atributo)
            )

            if not isinstance(descripcion, dict):
                continue

            nombre = _texto(
                descripcion.get("nombre")
            )

            if not nombre:
                continue

            campos_slot.append(
                {
                    "atributo": atributo,
                    "campo": nombre,
                }
            )
            campos.append(nombre)

        if indice and campos_slot:
            slots.append(
                {
                    "indice": indice,
                    "campos": campos_slot,
                }
            )

    campos = list(dict.fromkeys(campos))

    return slots, campos


def ejecutar_conteo_coleccion_destinos_validados(
    *,
    plan_origen: dict[str, Any],
    modelo_destino: str,
    campo_clave_destino: str,
    evidencias: list[dict[str, Any]],
    prefijo_coleccion: str,
) -> dict[str, Any]:
    """
    Cuenta elementos lógicos de una colección estructurada únicamente
    sobre los destinos únicos demostrados por HOST031.
    """

    # --------------------------------------------------------
    # 1. CORRESPONDENCIA VIRTUAL
    # --------------------------------------------------------

    correspondencia = validar_correspondencia_virtual(
        plan_origen=plan_origen,
        modelo_destino=modelo_destino,
        campo_clave_destino=campo_clave_destino,
        evidencias=evidencias,
    )

    if not correspondencia.get("ok"):
        return {
            "ok": False,
            "ejecutado": False,
            "fase": "host031",
            "errores": correspondencia.get(
                "errores",
                [
                    "HOST031 no pudo validar la correspondencia."
                ],
            ),
            "correspondencia": correspondencia,
            "llm_invocado": False,
        }

    if not correspondencia.get("validado"):
        return {
            "ok": False,
            "ejecutado": False,
            "fase": "host031",
            "errores": [
                "HOST031 no demostró una correspondencia completa."
            ],
            "correspondencia": correspondencia,
            "llm_invocado": False,
        }

    claves = correspondencia.get(
        "claves_destino_validadas",
        [],
    )

    if not isinstance(claves, list):
        return _resultado_error(
            fase="host031",
            mensaje=(
                "HOST031 no entregó claves destino en formato lista."
            ),
        )

    claves_unicas = sorted(
        {
            _texto(clave)
            for clave in claves
            if _texto(clave)
        }
    )

    if not claves_unicas:
        return _resultado_error(
            fase="host031",
            mensaje=(
                "La correspondencia fue validada pero no produjo "
                "claves destino utilizables."
            ),
        )

    # --------------------------------------------------------
    # 2. MODELO DESTINO
    # --------------------------------------------------------

    modelo_destino_label = _texto(
        correspondencia.get(
            "modelo_destino",
            modelo_destino,
        )
    )

    modelo_django = obtener_modelo_django(
        modelo_destino_label
    )

    if modelo_django is None:
        return _resultado_error(
            fase="modelo_destino",
            mensaje=(
                "El modelo destino validado por HOST031 ya no puede "
                "resolverse mediante Django."
            ),
        )

    campo_clave_destino = _texto(
        correspondencia.get(
            "campo_clave_destino",
            campo_clave_destino,
        )
    )

    try:
        campo_clave = modelo_django._meta.get_field(
            campo_clave_destino
        )
    except Exception:
        return _resultado_error(
            fase="clave_destino",
            mensaje=(
                "Django._meta ya no puede resolver la clave destino "
                "validada por HOST031."
            ),
        )

    if bool(
        getattr(
            campo_clave,
            "is_relation",
            False,
        )
    ):
        return _resultado_error(
            fase="clave_destino",
            mensaje="La clave destino dejó de ser un campo escalar.",
        )

    if not (
        bool(
            getattr(
                campo_clave,
                "primary_key",
                False,
            )
        )
        or bool(
            getattr(
                campo_clave,
                "unique",
                False,
            )
        )
    ):
        return _resultado_error(
            fase="clave_destino",
            mensaje=(
                "La clave destino ya no está declarada como "
                "primary_key o unique=True."
            ),
        )

    # --------------------------------------------------------
    # 3. COLECCIÓN ESTRUCTURADA
    # --------------------------------------------------------

    estructura = obtener_coleccion_estructurada(
        modelo=modelo_destino_label,
        prefijo=prefijo_coleccion,
    )

    if not estructura.get("resuelto"):
        return {
            "ok": False,
            "ejecutado": False,
            "fase": "host029",
            "errores": [
                estructura.get(
                    "razon",
                    "HOST029 no resolvió la colección estructurada.",
                )
            ],
            "estructura": estructura,
            "llm_invocado": False,
        }

    coleccion = estructura.get("coleccion")

    if not isinstance(coleccion, dict):
        return _resultado_error(
            fase="host029",
            mensaje="HOST029 no entregó una colección válida.",
        )

    mapa_slots, campos_coleccion = (
        _construir_mapa_slots(coleccion)
    )

    if not mapa_slots or not campos_coleccion:
        return _resultado_error(
            fase="host029",
            mensaje=(
                "La colección estructurada no contiene slots/campos "
                "utilizables."
            ),
        )

    # --------------------------------------------------------
    # 4. EJECUCIÓN SOBRE SUBCONJUNTO DESTINO
    # --------------------------------------------------------

    try:
        filtro_destino = {
            f"{campo_clave_destino}__in": claves_unicas
        }

        queryset = (
            modelo_django.objects
            .filter(**filtro_destino)
        )

        destinos_encontrados = queryset.count()

        if destinos_encontrados != len(claves_unicas):
            return {
                "ok": False,
                "ejecutado": False,
                "fase": "consistencia_destino",
                "errores": [
                    (
                        "La cantidad de destinos recuperados no coincide "
                        "con las claves validadas por HOST031."
                    )
                ],
                "claves_destino_unicas": len(claves_unicas),
                "destinos_encontrados": destinos_encontrados,
                "llm_invocado": False,
            }

        columnas = [
            campo_clave_destino,
            *campos_coleccion,
        ]

        posiciones = {
            nombre: indice
            for indice, nombre
            in enumerate(columnas)
        }

        filas = (
            queryset
            .values_list(*columnas)
            .iterator(
                chunk_size=ITERATOR_CHUNK_SIZE
            )
        )

        registros_evaluados = 0
        slots_posibles = 0
        slots_ocupados = 0
        slots_vacios = 0

        atributos = list(
            coleccion.get("atributos", [])
        )

        presencia_por_atributo = {
            atributo: 0
            for atributo in atributos
        }

        elementos_por_destino = {}

        for fila in filas:
            registros_evaluados += 1

            clave_destino = _texto(
                fila[
                    posiciones[
                        campo_clave_destino
                    ]
                ]
            )

            ocupados_destino = 0

            for slot in mapa_slots:
                slots_posibles += 1

                algun_valor = False

                for item in slot["campos"]:
                    atributo = item["atributo"]
                    nombre_campo = item["campo"]

                    valor = fila[
                        posiciones[nombre_campo]
                    ]

                    if _valor_presente(valor):
                        algun_valor = True
                        presencia_por_atributo[
                            atributo
                        ] += 1

                if algun_valor:
                    slots_ocupados += 1
                    ocupados_destino += 1
                else:
                    slots_vacios += 1

            elementos_por_destino[
                clave_destino
            ] = ocupados_destino

        cobertura_atributos = {}

        for atributo in atributos:
            presentes = presencia_por_atributo[
                atributo
            ]

            cobertura = (
                presentes / slots_ocupados
                if slots_ocupados
                else 0.0
            )

            cobertura_atributos[
                atributo
            ] = {
                "presentes": presentes,
                "slots_ocupados": slots_ocupados,
                "cobertura": round(
                    cobertura,
                    6,
                ),
            }

        destinos_con_elementos = sum(
            1
            for cantidad
            in elementos_por_destino.values()
            if cantidad > 0
        )

        destinos_sin_elementos = (
            registros_evaluados
            - destinos_con_elementos
        )

        return {
            "ok": True,
            "ejecutado": True,
            "operacion": (
                "contar_elementos_coleccion_estructurada_"
                "sobre_destinos_validados"
            ),
            "modelo_origen": correspondencia.get(
                "modelo_origen"
            ),
            "modelo_destino": modelo_destino_label,
            "tabla_destino": modelo_django._meta.db_table,
            "campo_clave_destino": campo_clave_destino,
            "cardinalidad_correspondencia": (
                correspondencia.get("cardinalidad")
            ),
            "registros_origen": correspondencia.get(
                "total_origen"
            ),
            "correspondencias_validadas": (
                correspondencia.get("total_matches")
            ),
            "claves_destino_recibidas": len(claves),
            "destinos_unicos": len(claves_unicas),
            "destinos_evaluados": registros_evaluados,
            "destinos_con_elementos": destinos_con_elementos,
            "destinos_sin_elementos": destinos_sin_elementos,
            "prefijo_coleccion": coleccion.get("prefijo"),
            "tipo_representacion": (
                "coleccion_estructurada_campos_repetidos"
            ),
            "regla_ocupacion": (
                "cualquier_atributo_no_vacio"
            ),
            "deduplicacion_destinos": True,
            "cantidad_slots_por_registro": (
                coleccion.get("cantidad_slots")
            ),
            "slots_posibles": slots_posibles,
            "slots_ocupados": slots_ocupados,
            "slots_vacios": slots_vacios,
            "total": slots_ocupados,
            "presencia_por_atributo": cobertura_atributos,
            "elementos_por_destino": elementos_por_destino,
            "claves_destino_validadas": claves_unicas,
            "correspondencia_validada": True,
            "llm_invocado": False,
            "origen": (
                "host031_mas_host029_mas_orm_seguro"
            ),
        }

    except DatabaseError as exc:
        return {
            "ok": False,
            "ejecutado": False,
            "fase": "orm",
            "errores": [str(exc)],
            "modelo_destino": modelo_destino_label,
            "llm_invocado": False,
        }

    except Exception as exc:
        return {
            "ok": False,
            "ejecutado": False,
            "fase": "general",
            "errores": [str(exc)],
            "modelo_destino": modelo_destino_label,
            "llm_invocado": False,
        }
