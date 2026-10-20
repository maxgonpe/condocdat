from __future__ import annotations

import re
import unicodedata
from typing import Any

from ia_local.services.bridge.campo_operador_valor import (
    componer_campo_operador_valor,
)
from ia_local.services.query.relaciones_orm import (
    componer_relacion_orm,
)
from ia_local.services.host.plan_unificado_datos import (
    construir_plan_unificado_datos,
)


# ============================================================
# IA-QUERY011
# CONSULTAS RELACIONALES COMPUESTAS
# ============================================================
#
# Responsabilidad:
#
#   componer una consulta relacional de conteo usando piezas
#   ya certificadas:
#
#       QUERY007 -> ruta relacional
#       BRIDGE003 -> plan/filtros del modelo origen
#       HOST033 -> plan unificado relacion_orm
#
# QUERY011:
#   - NO ejecuta ORM;
#   - NO usa LLM;
#   - NO genera SQL;
#   - NO inventa relaciones;
#   - NO inventa filtros;
#   - NO filtra el modelo destino;
#   - NO lista destinos en esta versión.
#
# Operación relacional soportada:
#
#       contar_destinos_unicos
#
# ============================================================


VERSION = "IA-QUERY011-v1"


def _texto(
    valor: Any,
) -> str:

    return str(
        valor or ""
    ).strip()


def _normalizar(
    valor: Any,
) -> str:

    texto = _texto(
        valor
    ).lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caracter
        for caracter
        in texto
        if not unicodedata.combining(
            caracter
        )
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def _error(
    *,
    pregunta: str,
    estado: str,
    razon: str,
    **extra: Any,
) -> dict[str, Any]:

    salida = {
        "ok": False,
        "version": VERSION,
        "ejecutado": False,
        "estado": estado,
        "modo": "consultas_relacionales",
        "pregunta": pregunta,
        "razon": razon,
        "llm_invocado": False,
    }

    salida.update(
        extra
    )

    return salida


# ============================================================
# PARSER
# ============================================================


def _extraer_consulta(
    pregunta: str,
) -> dict[str, Any] | None:

    texto = _normalizar(
        pregunta
    )

    # --------------------------------------------------------
    # QUERY011-v1 sólo acepta conteo.
    #
    # Ejemplos:
    #
    # contar proyectos de documentos
    #
    # contar proyectos de documentos
    # cuyo estado es aprobado
    #
    # contar correos enviados de documentos
    # cuyo tema contiene estructura
    # --------------------------------------------------------

    coincidencia = re.match(
        r"^contar\s+(?P<cuerpo>.+?)$",
        texto,
    )

    if coincidencia is None:

        return None

    cuerpo = _texto(
        coincidencia.group(
            "cuerpo"
        )
    )

    filtro = None
    cuerpo_relacional = cuerpo

    # --------------------------------------------------------
    # El filtro pertenece SIEMPRE al modelo origen.
    # --------------------------------------------------------

    coincidencia_filtro = re.match(
        r"^(?P<relacion>.+?)\s+"
        r"(?P<filtro>cuyo|cuya|cuyos|cuyas)\s+"
        r"(?P<condicion>.+?)$",
        cuerpo,
    )

    if coincidencia_filtro:

        cuerpo_relacional = _texto(
            coincidencia_filtro.group(
                "relacion"
            )
        )

        filtro = (
            f"{coincidencia_filtro.group('filtro')} "
            f"{coincidencia_filtro.group('condicion')}"
        )

    return {
        "operacion":
            "contar_destinos_unicos",

        "relacion":
            cuerpo_relacional,

        "filtro_origen":
            filtro,
    }


# ============================================================
# PLAN BRIDGE003
# ============================================================


def _extraer_plan_bridge(
    resultado_bridge: dict[str, Any],
) -> dict[str, Any] | None:

    if not isinstance(
        resultado_bridge,
        dict,
    ):

        return None

    if (
        resultado_bridge.get(
            "ok"
        )
        is not True
    ):

        return None

    if (
        resultado_bridge.get(
            "estado"
        )
        != "plan_host_validado"
    ):

        return None

    # --------------------------------------------------------
    # Forma observada directamente en BRIDGE003.
    # --------------------------------------------------------

    plan_host = resultado_bridge.get(
        "plan_host"
    )

    if isinstance(
        plan_host,
        dict,
    ):

        return plan_host

    # --------------------------------------------------------
    # Forma común conservada en validacion_host.plan.
    # --------------------------------------------------------

    validacion_host = (
        resultado_bridge.get(
            "validacion_host"
        )
    )

    if isinstance(
        validacion_host,
        dict,
    ):

        if (
            validacion_host.get(
                "plan_validado"
            )
            is True
        ):

            plan = validacion_host.get(
                "plan"
            )

            if isinstance(
                plan,
                dict,
            ):

                return plan

    return None


# ============================================================
# API PÚBLICA
# ============================================================


def componer_consulta_relacional(
    pregunta: str,
    *,
    limite: int = 20,
) -> dict[str, Any]:

    pregunta = _texto(
        pregunta
    )

    if not pregunta:

        return _error(
            pregunta=pregunta,
            estado="pregunta_vacia",
            razon=(
                "La consulta está vacía."
            ),
        )

    componentes = (
        _extraer_consulta(
            pregunta
        )
    )

    if componentes is None:

        return _error(
            pregunta=pregunta,
            estado=(
                "estructura_relacional_"
                "no_detectada"
            ),
            razon=(
                "QUERY011-v1 sólo admite consultas "
                "relacionales explícitas iniciadas "
                "por 'contar'."
            ),
        )

    # --------------------------------------------------------
    # 1. QUERY007
    #
    # QUERY007 trabaja con navegación:
    #
    #       listar destino de origen
    #
    # QUERY011 cambia únicamente la intención externa:
    #
    #       contar destino de origen
    #
    # La ruta estructural es la misma.
    # --------------------------------------------------------

    pregunta_relacional = (
        f"listar "
        f"{componentes['relacion']}"
    )

    relacion = (
        componer_relacion_orm(
            pregunta_relacional
        )
    )

    if (
        not isinstance(
            relacion,
            dict,
        )
        or relacion.get(
            "ok"
        )
        is not True
        or relacion.get(
            "estado"
        )
        != "ruta_relacional_validada"
    ):

        return _error(
            pregunta=pregunta,
            estado="ruta_relacional_no_resuelta",
            razon=(
                "QUERY007 no pudo certificar "
                "la ruta relacional solicitada."
            ),
            pregunta_relacional=(
                pregunta_relacional
            ),
            relacion=relacion,
        )

    modelo_origen = _texto(
        relacion.get(
            "modelo_origen"
        )
    )

    modelo_destino = _texto(
        relacion.get(
            "modelo_destino"
        )
    )

    ruta_orm = _texto(
        relacion.get(
            "ruta_orm"
        )
    )

    ruta_validada = (
        relacion.get(
            "validacion_ruta"
        )
    )

    if (
        not modelo_origen
        or not modelo_destino
        or not ruta_orm
        or not isinstance(
            ruta_validada,
            dict,
        )
        or ruta_validada.get(
            "ok"
        )
        is not True
        or ruta_validada.get(
            "valida"
        )
        is not True
    ):

        return _error(
            pregunta=pregunta,
            estado=(
                "contrato_relacional_"
                "incompleto"
            ),
            razon=(
                "QUERY007 resolvió la consulta, "
                "pero no entregó un contrato HOST025 "
                "completo."
            ),
            relacion=relacion,
        )

    # --------------------------------------------------------
    # 2. PLAN BASE DEL MODELO ORIGEN
    #
    # Siempre se construye mediante BRIDGE003.
    #
    # Sin filtro:
    #
    #       listar documentos
    #
    # Con filtro:
    #
    #       listar documentos cuyo estado es aprobado
    #
    # --------------------------------------------------------

    origen_natural = _texto(
        relacion.get(
            "origen_solicitado"
        )
    )

    if not origen_natural:

        return _error(
            pregunta=pregunta,
            estado="origen_natural_ausente",
            razon=(
                "QUERY007 no preservó la expresión "
                "natural del modelo origen."
            ),
            relacion=relacion,
        )

    filtro_origen = componentes.get(
        "filtro_origen"
    )

    if filtro_origen:

        pregunta_origen = (
            f"listar "
            f"{origen_natural} "
            f"{filtro_origen}"
        )

    else:

        pregunta_origen = (
            f"listar "
            f"{origen_natural}"
        )

    bridge = (
        componer_campo_operador_valor(
            pregunta_origen,
            limite=limite,
        )
    )

    plan_base = (
        _extraer_plan_bridge(
            bridge
        )
    )

    if not isinstance(
        plan_base,
        dict,
    ):

        return _error(
            pregunta=pregunta,
            estado=(
                "filtro_origen_no_resuelto"
                if filtro_origen
                else "plan_origen_no_resuelto"
            ),
            razon=(
                "BRIDGE003 no pudo construir un "
                "plan HOST válido para el modelo origen."
            ),
            modelo_origen=modelo_origen,
            pregunta_origen=pregunta_origen,
            bridge=bridge,
        )

    # --------------------------------------------------------
    # SEGURIDAD:
    #
    # El plan que produjo BRIDGE003 debe corresponder
    # exactamente al modelo origen de QUERY007.
    # --------------------------------------------------------

    modelo_plan = _texto(
        plan_base.get(
            "modelo"
        )
    )

    if (
        modelo_plan
        != modelo_origen
    ):

        return _error(
            pregunta=pregunta,
            estado=(
                "inconsistencia_modelo_origen"
            ),
            razon=(
                "El modelo certificado por BRIDGE003 "
                "no coincide con el modelo origen "
                "certificado por QUERY007."
            ),
            modelo_origen=modelo_origen,
            modelo_plan=modelo_plan,
            pregunta_origen=pregunta_origen,
        )

    # --------------------------------------------------------
    # 3. HOST033
    #
    # Única operación relacional soportada actualmente:
    #
    #       contar_destinos_unicos
    # --------------------------------------------------------

    plan_unificado_resultado = (
        construir_plan_unificado_datos(
            plan_base=plan_base,
            estrategia="relacion_orm",
            ruta=ruta_validada,
            operacion_relacional=(
                "contar_destinos_unicos"
            ),
            metadatos={
                "origen_query":
                    VERSION,

                "pregunta_original":
                    pregunta,

                "filtro_aplicado_a":
                    "modelo_origen",
            },
        )
    )

    if (
        not isinstance(
            plan_unificado_resultado,
            dict,
        )
        or plan_unificado_resultado.get(
            "ok"
        )
        is not True
        or plan_unificado_resultado.get(
            "plan_unificado_valido"
        )
        is not True
    ):

        return _error(
            pregunta=pregunta,
            estado=(
                "plan_unificado_rechazado"
            ),
            razon=(
                "HOST033 rechazó la composición "
                "relacional."
            ),
            modelo_origen=modelo_origen,
            modelo_destino=modelo_destino,
            ruta_orm=ruta_orm,
            plan_base=plan_base,
            plan_unificado_resultado=(
                plan_unificado_resultado
            ),
        )

    plan_unificado = (
        plan_unificado_resultado.get(
            "plan_unificado"
        )
    )

    if not isinstance(
        plan_unificado,
        dict,
    ):

        return _error(
            pregunta=pregunta,
            estado=(
                "plan_unificado_ausente"
            ),
            razon=(
                "HOST033 indicó éxito, pero no "
                "entregó plan_unificado."
            ),
            plan_unificado_resultado=(
                plan_unificado_resultado
            ),
        )

    # --------------------------------------------------------
    # RESULTADO QUERY011
    # --------------------------------------------------------

    return {
        "ok": True,
        "version": VERSION,
        "ejecutado": False,
        "estado":
            "consulta_relacional_validada",
        "modo":
            "consultas_relacionales",
        "pregunta":
            pregunta,

        "operacion_relacional":
            "contar_destinos_unicos",

        "modelo_origen":
            modelo_origen,

        "modelo_destino":
            modelo_destino,

        "ruta_orm":
            ruta_orm,

        "profundidad":
            relacion.get(
                "profundidad"
            ),

        "contiene_relacion_multiple":
            relacion.get(
                "contiene_relacion_multiple"
            ),

        "filtro_origen":
            filtro_origen,

        "pregunta_origen":
            pregunta_origen,

        "plan_base":
            plan_base,

        "relacion":
            relacion,

        "bridge":
            bridge,

        "plan_unificado":
            plan_unificado,

        "plan_unificado_resultado":
            plan_unificado_resultado,

        "llm_invocado":
            False,

        "razon": (
            "QUERY011 compuso una consulta relacional "
            "de conteo sobre destinos únicos usando "
            "QUERY007, BRIDGE003 y HOST033."
        ),
    }