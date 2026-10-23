"""Alternativas de filtros recertificadas por HOST.

No modifica planes existentes ni ejecuta ORM.
"""
import hashlib
import json
from typing import Any

from ia_local.config.cardinalidad import (
    LIMITE_MUESTRA_PREDETERMINADO,
)
from ia_local.services.llm.candidatos_filtros import (
    descubrir_filtros_choices,
)
from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)

VERSION = "IA-LLM008-F5-05-08-v1"


def _base(estado):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "opciones": [],
        "requiere_aclaracion": False,
        "certificada_host": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }


def _id_opcion(modelo, evidencia, campo, valor):
    datos = json.dumps(
        [modelo, evidencia.casefold(), campo, valor],
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(
        datos.encode("utf-8")
    ).hexdigest()[:24]


def preparar_aclaracion_filtro(
    modelo: str,
    evidencia_textual: str,
) -> dict[str, Any]:

    if (
        not isinstance(modelo, str)
        or not isinstance(evidencia_textual, str)
        or not modelo.strip()
        or not evidencia_textual.strip()
    ):
        return _base("entrada_invalida")

    descubrimiento = descubrir_filtros_choices(
        modelo, evidencia_textual
    )

    if descubrimiento.get("ok") is not True:
        return _base("descubrimiento_no_resuelto")

    modelo_canonico = descubrimiento.get("modelo")
    alternativas = descubrimiento.get("alternativas")

    if (
        not isinstance(modelo_canonico, str)
        or not isinstance(alternativas, list)
    ):
        return _base("contrato_descubrimiento_invalido")

    opciones = []
    ids = set()

    for candidato in alternativas:
        if not isinstance(candidato, dict):
            return _base("candidato_invalido")

        campo = candidato.get("campo")
        valor = candidato.get("valor")
        operador = candidato.get("operador_propuesto")
        etiqueta = candidato.get("etiqueta")

        if (
            not isinstance(campo, str)
            or not isinstance(operador, str)
            or not isinstance(etiqueta, str)
            or not campo
            or not etiqueta
        ):
            return _base("candidato_invalido")

        propuesta = {
            "modelo": modelo_canonico,
            "operacion": "listar",
            "filtros": [{
                "campo": campo,
                "operador": operador,
                "valor": valor,
            }],
            "orden": [],
            "limite": LIMITE_MUESTRA_PREDETERMINADO,
            "condiciones_no_resueltas": [],
        }

        resultado = validar_plan_datos(propuesta)

        if (
            not isinstance(resultado, dict)
            or resultado.get("ok") is not True
            or resultado.get("plan_validado") is not True
        ):
            continue

        plan = resultado.get("plan")
        filtros = (
            plan.get("filtros")
            if isinstance(plan, dict) else None
        )

        if not isinstance(filtros, list) or len(filtros) != 1:
            continue

        certificado = filtros[0]

        if (
            not isinstance(certificado, dict)
            or certificado.get("campo") != campo
            or certificado.get("operador") != operador
            or certificado.get("valor") != valor
        ):
            continue

        ident = _id_opcion(
            modelo_canonico,
            evidencia_textual,
            campo,
            valor,
        )

        if ident in ids:
            return _base("identificador_duplicado")

        ids.add(ident)

        opciones.append({
            "id": ident,
            "etiqueta": f"{etiqueta} ({campo})",
            "campo": campo,
            "operador": operador,
            "valor": valor,
        })

    opciones.sort(key=lambda item: item["id"])

    if len(opciones) > 1:
        estado = "requiere_aclaracion_filtro"
    elif len(opciones) == 1:
        estado = "candidato_unico_certificado"
    else:
        estado = "sin_opciones_certificadas"

    return {
        **_base(estado),
        "ok": len(opciones) > 0,
        "modelo": modelo_canonico,
        "evidencia_textual": evidencia_textual,
        "opciones": opciones,
        "requiere_aclaracion": len(opciones) > 1,
        # Cada alternativa supera HOST, pero no representa
        # aún una elección confirmada ni un plan completo.
        "alternativas_validadas_host": len(opciones),
    }


def verificar_eleccion_filtro(
    modelo: str,
    evidencia_textual: str,
    opcion_id: str,
) -> dict[str, Any]:

    # Recalcular opciones evita aceptar campos o valores
    # introducidos por el cliente.
    aclaracion = preparar_aclaracion_filtro(
        modelo, evidencia_textual
    )

    if not aclaracion.get("ok"):
        return _base("aclaracion_no_disponible")

    if (
        not isinstance(opcion_id, str)
        or not opcion_id
    ):
        return _base("eleccion_invalida")

    opciones = [
        o for o in aclaracion["opciones"]
        if o["id"] == opcion_id
    ]

    if len(opciones) != 1:
        return _base("eleccion_no_certificada")

    seleccion = opciones[0]

    return {
        **_base("eleccion_filtro_certificada"),
        "ok": True,
        "modelo": aclaracion["modelo"],
        "evidencia_textual": evidencia_textual,
        "seleccion": seleccion,
        "certificada_host": True,
        "requiere_validacion_plan_completo": True,
    }
