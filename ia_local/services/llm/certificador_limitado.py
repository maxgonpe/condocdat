"""
ARC003-B04-B02 - Certificacion semantica de gramatica cerrada.

Solo admite conteo con una igualdad textual explicita.
No invoca LLM, no ejecuta ORM y no autoriza ejecucion.
"""

import re

from ia_local.services.host.catalogo_datos import (
    buscar_modelo_datos,
)
from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)
from ia_local.services.llm.trazabilidad_compuesta import (
    preparar_coleccion_restricciones,
)
from ia_local.services.llm.vinculo_semantico import (
    vincular_contexto_semantico,
    verificar_vinculo_semantico,
)


VERSION = "IA-ARC003-B04-B02-v1"

PATRON = re.compile(
    r"\s*¿?\s*cu[aá]ntos\s+"
    r"(?P<entidad>[^\W\d_]+)\s+"
    r"tienen\s+"
    r"(?P<campo>[a-zA-Z_][a-zA-Z_0-9]*)\s+"
    r"igual\s+a\s+"
    r"(?P<valor>[a-zA-Z0-9_-]+)\s*\??\s*",
    flags=re.IGNORECASE,
)

CLAVES_PLAN = {
    "modelo",
    "tabla",
    "operacion",
    "filtros",
    "orden",
    "limite",
    "condiciones_no_resueltas",
}


def _rechazo(estado):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "certificacion_limitada": False,
        "certificacion_semantica_integral": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }


def certificar_consulta_limitada(pregunta, plan_host):
    if (
        not isinstance(pregunta, str)
        or not pregunta.strip()
        or len(pregunta) > 1000
        or not isinstance(plan_host, dict)
    ):
        return _rechazo("entrada_invalida")

    coincidencia = PATRON.fullmatch(pregunta)
    if coincidencia is None:
        return _rechazo("gramatica_no_certificable")

    entidad = coincidencia.group("entidad")
    campo = coincidencia.group("campo")
    valor = coincidencia.group("valor")

    # Resolver exclusivamente contra el catalogo del servidor.
    candidatos = buscar_modelo_datos(entidad)

    if len(candidatos) != 1:
        return _rechazo("entidad_no_inequivoca")

    descripcion = candidatos[0]
    modelo = descripcion["label"]

    # Primera version: solo campos textuales consultables.
    campos = [
        item
        for item in descripcion.get("campos", [])
        if (
            isinstance(item, dict)
            and item.get("nombre") == campo
            and item.get("consultable") is True
            and item.get("tipo") in ("CharField", "TextField")
        )
    ]

    if len(campos) != 1:
        return _rechazo("campo_no_certificable")

    # Rechazar campos extras, declaraciones de certificacion,
    # filtros multiples y cualquier operacion diferente.
    if (
        set(plan_host) != CLAVES_PLAN
        or plan_host.get("modelo") != modelo
        or plan_host.get("operacion") != "contar"
        or plan_host.get("orden") != []
        or plan_host.get("condiciones_no_resueltas") != []
    ):
        return _rechazo("plan_fuera_del_contrato")

    filtros = plan_host.get("filtros")

    if not isinstance(filtros, list) or len(filtros) != 1:
        return _rechazo("cantidad_filtros_no_certificable")

    filtro = filtros[0]

    if not isinstance(filtro, dict):
        return _rechazo("filtro_invalido")

    if (
        filtro.get("campo") != campo
        or filtro.get("operador") != "exact"
        or filtro.get("valor") != valor
        or filtro.get("negado") is not False
        or filtro.get("lookup") != campo
    ):
        return _rechazo("filtro_no_equivalente")

    # Reconstruir la propuesta desde las partes verificadas
    # contra la pregunta, no desde afirmaciones de Qwen.
    propuesta = {
        "modelo": modelo,
        "operacion": "contar",
        "filtros": [{
            "campo": campo,
            "operador": "exact",
            "valor": valor,
        }],
        "orden": [],
        "limite": plan_host.get("limite"),
        "condiciones_no_resueltas": [],
    }

    validacion = validar_plan_datos(propuesta)

    if (
        not isinstance(validacion, dict)
        or validacion.get("ok") is not True
        or validacion.get("plan_validado") is not True
        or validacion.get("errores") != []
        or validacion.get("plan") != plan_host
    ):
        return _rechazo("plan_host_no_coincidente")

    evidencia = pregunta[
        coincidencia.start("campo"):
        coincidencia.end("valor")
    ]

    coleccion = preparar_coleccion_restricciones({
        "ok": True,
        "estado": "consolidacion_diagnostica",
        "pregunta": pregunta,
        "restricciones": [{
            "tipo": "filtro",
            "evidencia_textual": evidencia,
            "origen": "gramatica_determinista_b04",
        }],
        "ejecutable": False,
        "ejecutado": False,
    })

    if coleccion.get("ok") is not True:
        return _rechazo("coleccion_no_valida")

    vinculo = vincular_contexto_semantico(
        pregunta,
        coleccion,
        plan_host,
    )

    verificacion = verificar_vinculo_semantico(
        pregunta,
        coleccion,
        plan_host,
        vinculo,
    )

    if (
        vinculo.get("ok") is not True
        or verificacion.get("ok") is not True
        or verificacion.get("coincidencia_verificada") is not True
    ):
        return _rechazo("vinculo_no_verificado")

    return {
        "ok": True,
        "version": VERSION,
        "estado": "certificado_limitado",
        "certificacion_limitada": True,
        "certificacion_semantica_integral": False,
        "gramatica": "conteo_igualdad_textual_v1",
        "modelo": modelo,
        "campo": campo,
        "operador": "exact",
        "valor": valor,
        "huella_plan": vinculo["huella_plan"],
        "identificador_vinculo": vinculo["identificador_vinculo"],
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }
