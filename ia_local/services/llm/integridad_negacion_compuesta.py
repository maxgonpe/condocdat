"""
ARC002-C07-B02 — Integridad conjunta de negaciones y requisitos.

Recalcula evidencias y asociaciones desde contratos originales.
No certifica equivalencias ni autoriza ejecucion.
"""

from ia_local.services.llm.evidencia_negacion import (
    localizar_evidencias_negacion,
)
from ia_local.services.llm.asociacion_evidencias import (
    asociar_evidencias_requisitos,
)
from ia_local.services.llm.integridad_requisitos import (
    diagnosticar_integridad_requisitos,
)
from ia_local.services.llm.trazabilidad_compuesta import (
    preparar_coleccion_restricciones,
)

VERSION = "IA-ARC002-C07-B02-v1"


def auditar_integridad_negativa_compuesta(
    coleccion,
    evidencias_recibidas=None,
    asociaciones_recibidas=None,
):
    base = {
        "ok": False,
        "version": VERSION,
        "estado": "entrada_invalida",
        "pregunta_original": None,
        "identificador_coleccion": None,
        "integridad_requisitos": None,
        "evidencias_negativas": [],
        "asociaciones": [],
        "discrepancias": [],
        "pendientes": [],
        "integridad_estructural_verificada": False,
        "integridad_completa": False,
        "cobertura_verificada": False,
        "equivalencia_semantica_certificada": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    if not isinstance(coleccion, dict):
        return base

    pregunta = coleccion.get("pregunta_original")
    restricciones = coleccion.get("restricciones")

    if (
        coleccion.get("ok") is not True
        or coleccion.get("estado")
            != "coleccion_normalizada_pendiente"
        or coleccion.get("ejecutable") is not False
        or coleccion.get("ejecutado") is not False
        or not isinstance(pregunta, str)
        or not pregunta.strip()
        or not isinstance(restricciones, list)
    ):
        return base

    # Reconstruccion independiente de la coleccion,
    # utilizando los datos originales conservados.
    originales = []

    for restriccion in restricciones:
        if not isinstance(restriccion, dict):
            return base

        datos = restriccion.get("datos_originales")

        if not isinstance(datos, dict):
            return base

        originales.append(datos)

    reconstruida = preparar_coleccion_restricciones({
        "ok": True,
        "estado": "consolidacion_diagnostica",
        "pregunta": pregunta,
        "restricciones": originales,
        "ejecutable": False,
        "ejecutado": False,
    })

    claves = (
        "identificador_coleccion",
        "restricciones",
        "total_restricciones",
        "tipos_presentes",
        "pendientes",
    )

    if (
        reconstruida.get("ok") is not True
        or any(
            coleccion.get(clave) != reconstruida.get(clave)
            for clave in claves
        )
    ):
        return {
            **base,
            "estado": "coleccion_inconsistente",
        }

    integridad = diagnosticar_integridad_requisitos(
        coleccion
    )

    if integridad.get("ok") is not True:
        return {
            **base,
            "estado": "integridad_requisitos_invalida",
        }

    evidencias = localizar_evidencias_negacion(
        pregunta
    )

    if evidencias.get("ok") is not True:
        return base

    # Los contratos recibidos opcionalmente se contrastan
    # contra resultados recalculados, nunca se consideran
    # evidencia suficiente por si solos.
    if (
        evidencias_recibidas is not None
        and evidencias_recibidas != evidencias
    ):
        return {
            **base,
            "estado": "evidencias_adulteradas",
        }

    asociaciones = asociar_evidencias_requisitos(
        coleccion,
        evidencias,
    )

    if asociaciones.get("ok") is not True:
        return {
            **base,
            "estado": "asociaciones_invalidas",
        }

    if (
        asociaciones_recibidas is not None
        and asociaciones_recibidas != asociaciones
    ):
        return {
            **base,
            "estado": "asociaciones_adulteradas",
        }

    discrepancias = []
    pendientes = [
        "certificacion_semantica_integral",
    ]

    for asociacion in asociaciones["asociaciones"]:
        estado = asociacion["estado"]
        identificador = asociacion["id_evidencia"]

        if estado == "asociacion_ambigua":
            discrepancias.append({
                "id_evidencia": identificador,
                "motivo": "asociacion_ambigua",
            })
        elif estado == "sin_asociacion":
            discrepancias.append({
                "id_evidencia": identificador,
                "motivo": "evidencia_sin_requisito",
            })
        elif estado != "asociacion_textual":
            return {
                **base,
                "estado": "estado_asociacion_desconocido",
            }

        pendientes.append(identificador)

    return {
        **base,
        "ok": True,
        "estado": (
            "integridad_con_discrepancias_pendientes"
            if discrepancias
            else "integridad_textual_pendiente"
        ),
        "pregunta_original": pregunta,
        "identificador_coleccion": coleccion[
            "identificador_coleccion"
        ],
        "integridad_requisitos": integridad,
        "evidencias_negativas": evidencias["evidencias"],
        "asociaciones": asociaciones["asociaciones"],
        "discrepancias": discrepancias,
        "pendientes": pendientes,
        "integridad_estructural_verificada": True,
    }
