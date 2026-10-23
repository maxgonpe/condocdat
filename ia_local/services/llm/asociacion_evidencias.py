"""
ARC002-B03-C01 — Asociaciones textuales de evidencias.

Relaciona marcadores negativos con restricciones existentes
mediante posiciones verificables en la pregunta original.

No interpreta alcances lógicos, no certifica ni ejecuta.
"""

from typing import Any


VERSION = "IA-ARC002-B03-C01-v1"


def asociar_evidencias_requisitos(
    coleccion: dict[str, Any],
    diagnostico: dict[str, Any],
) -> dict[str, Any]:

    base = {
        "ok": False,
        "version": VERSION,
        "estado": "entrada_invalida",
        "pregunta_original": None,
        "asociaciones": [],
        "pendientes": [],
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
    }

    if not isinstance(coleccion, dict) or not isinstance(
        diagnostico, dict
    ):
        return base

    pregunta = coleccion.get("pregunta_original")

    if (
        coleccion.get("ok") is not True
        or coleccion.get("estado")
            != "coleccion_normalizada_pendiente"
        or coleccion.get("ejecutable") is not False
        or coleccion.get("ejecutado") is not False
        or diagnostico.get("ok") is not True
        or diagnostico.get("pregunta_original") != pregunta
        or not isinstance(pregunta, str)
        or not pregunta.strip()
    ):
        return base

    restricciones = coleccion.get("restricciones")
    evidencias = diagnostico.get("evidencias")

    if not isinstance(restricciones, list) or not isinstance(
        evidencias, list
    ):
        return base

    # ARC002-B03-C02: verificar integridad estructural
    # reconstruyendo mediante los contratos originales.
    from ia_local.services.llm.trazabilidad_compuesta import (
        preparar_coleccion_restricciones,
    )
    from ia_local.services.llm.evidencia_negacion import (
        localizar_evidencias_negacion,
    )

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

    if reconstruida.get("ok") is not True:
        return base

    claves_coleccion = (
        "identificador_coleccion",
        "restricciones",
        "total_restricciones",
        "tipos_presentes",
        "pendientes",
    )

    if any(
        coleccion.get(clave) != reconstruida.get(clave)
        for clave in claves_coleccion
    ):
        return base

    # Los identificadores de evidencias son locales.
    # La comprobacion se realiza contra la pregunta
    # original, no contra una propuesta de HOST.
    evidencias_originales = localizar_evidencias_negacion(
        pregunta
    )

    if (
        evidencias_originales.get("ok") is not True
        or diagnostico.get("estado")
            != evidencias_originales.get("estado")
        or diagnostico.get("cantidad")
            != evidencias_originales.get("cantidad")
        or evidencias != evidencias_originales.get("evidencias")
    ):
        return base

    if (
        diagnostico.get("alcance_certificado") is not False
        or diagnostico.get("cobertura_verificada") is not False
        or diagnostico.get("ejecutable") is not False
        or diagnostico.get("ejecutado") is not False
    ):
        return base

    ubicaciones = {}

    for restriccion in restricciones:
        if not isinstance(restriccion, dict):
            return base

        identificador = restriccion.get("id")
        fragmento = restriccion.get("evidencia_textual")

        if (
            not isinstance(identificador, str)
            or not identificador
            or not isinstance(fragmento, str)
            or not fragmento.strip()
        ):
            return base

        # ARC002-B03-C03:
        # Obtener offsets sobre el texto original.
        # casefold() puede modificar su longitud.
        import re

        posiciones = [
            coincidencia.span()
            for coincidencia in re.finditer(
                re.escape(fragmento),
                pregunta,
                flags=re.IGNORECASE,
            )
        ]

        ubicaciones[identificador] = posiciones

    asociaciones = []
    pendientes = []

    for evidencia in evidencias:
        if not isinstance(evidencia, dict):
            return base

        marcador = evidencia.get("marcador_textual")
        inicio = evidencia.get("inicio")
        fin = evidencia.get("fin")
        id_evidencia = evidencia.get("id_local")

        if (
            not isinstance(id_evidencia, str)
            or not isinstance(marcador, str)
            or type(inicio) is not int
            or type(fin) is not int
            or inicio < 0
            or fin <= inicio
            or pregunta[inicio:fin] != marcador
            or evidencia.get("certificada") is not False
        ):
            return base

        candidatos = []

        for identificador, posiciones in ubicaciones.items():
            if any(
                a <= inicio and fin <= b
                for a, b in posiciones
            ):
                candidatos.append(identificador)

        if len(candidatos) == 1:
            estado = "asociacion_textual"
        elif len(candidatos) > 1:
            estado = "asociacion_ambigua"
        else:
            estado = "sin_asociacion"

        asociaciones.append({
            "id_evidencia": id_evidencia,
            "marcador_textual": marcador,
            "inicio": inicio,
            "fin": fin,
            "estado": estado,
            "requisitos_candidatos": candidatos,
            "alcance_certificado": False,
            "certificada_host": False,
        })

        pendientes.append(id_evidencia)

    return {
        **base,
        "ok": True,
        "estado": "asociaciones_textuales_pendientes",
        "pregunta_original": pregunta,
        "asociaciones": asociaciones,
        "pendientes": pendientes,
    }
