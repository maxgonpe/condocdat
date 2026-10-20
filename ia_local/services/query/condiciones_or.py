from __future__ import annotations

import re
from typing import Any

from ia_local.services.bridge.campo_operador_valor import (
    componer_campo_operador_valor,
)


VERSION = "IA-QUERY002-v1"

# QUERY002 sólo compone lógica.
# No ejecuta ORM.
# No usa Q().
# No modifica HOST.
# Cada condición debe haber sido previamente certificada
# por BRIDGE003 -> HOST.


def _respuesta_error(
    *,
    estado: str,
    pregunta: str,
    razon: str,
    **extra: Any,
) -> dict[str, Any]:
    salida: dict[str, Any] = {
        "ok": False,
        "version": VERSION,
        "ejecutado": False,
        "estado": estado,
        "pregunta": pregunta,
        "razon": razon,
        "llm_invocado": False,
    }

    salida.update(extra)

    return salida


def _extraer_plan_bridge003(
    resultado: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Extrae únicamente un plan que BRIDGE003 haya conseguido
    validar efectivamente mediante HOST.
    """

    if not isinstance(resultado, dict):
        return None

    validacion = resultado.get("validacion_host")

    if isinstance(validacion, dict):
        if (
            validacion.get("ok") is True
            and validacion.get("plan_validado") is True
        ):
            plan = validacion.get("plan")

            if isinstance(plan, dict):
                return plan

    plan_host = resultado.get("plan_host")

    if (
        resultado.get("ok") is True
        and isinstance(plan_host, dict)
    ):
        return plan_host

    return None


def _contiene_and_fuera_de_comillas(
    texto: str,
) -> bool:
    """
    Detecta AND/y/además fuera de comillas.

    QUERY002 no permite mezclar AND y OR todavía.
    """

    tokens = _tokenizar_fuera_de_comillas(texto)

    for token in tokens:
        normalizado = token.casefold()

        if normalizado in {
            "y",
            "and",
            "ademas",
            "además",
        }:
            return True

    return False


def _tokenizar_fuera_de_comillas(
    texto: str,
) -> list[str]:
    """
    Devuelve palabras encontradas fuera de comillas simples
    o dobles.

    No interpreta semántica. Sólo protege la separación lógica.
    """

    tokens: list[str] = []
    actual: list[str] = []

    comilla: str | None = None
    escape = False

    def cerrar_token() -> None:
        if actual:
            tokens.append("".join(actual))
            actual.clear()

    for caracter in texto:
        if escape:
            if comilla is None:
                actual.append(caracter)

            escape = False
            continue

        if caracter == "\\":
            if comilla is not None:
                escape = True
            else:
                actual.append(caracter)

            continue

        if comilla is not None:
            if caracter == comilla:
                comilla = None

            continue

        if caracter in {'"', "'"}:
            cerrar_token()
            comilla = caracter
            continue

        if caracter.isspace():
            cerrar_token()
            continue

        actual.append(caracter)

    cerrar_token()

    return tokens


def _dividir_or_fuera_de_comillas(
    texto: str,
) -> dict[str, Any]:
    """
    Divide únicamente por:

        o
        or

    cuando aparecen como palabras completas fuera de comillas.

    Conserva literalmente el contenido original de cada condición.
    """

    texto = str(texto or "").strip()

    if not texto:
        return {
            "ok": False,
            "estado": "pregunta_vacia",
            "condiciones": [],
        }

    partes: list[str] = []
    buffer: list[str] = []

    comilla: str | None = None
    escape = False
    i = 0
    largo = len(texto)

    while i < largo:
        caracter = texto[i]

        if escape:
            buffer.append(caracter)
            escape = False
            i += 1
            continue

        if caracter == "\\" and comilla is not None:
            buffer.append(caracter)
            escape = True
            i += 1
            continue

        if comilla is not None:
            buffer.append(caracter)

            if caracter == comilla:
                comilla = None

            i += 1
            continue

        if caracter in {'"', "'"}:
            comilla = caracter
            buffer.append(caracter)
            i += 1
            continue

        # Intentamos reconocer "o" / "or" sólo como palabra completa.
        coincidencia = re.match(
            r"(?i)(?:o|or)\b",
            texto[i:],
        )

        if coincidencia:
            inicio_valido = (
                i == 0
                or texto[i - 1].isspace()
            )

            fin = i + len(coincidencia.group(0))

            fin_valido = (
                fin >= largo
                or texto[fin].isspace()
            )

            if inicio_valido and fin_valido:
                parte = "".join(buffer).strip()

                if not parte:
                    return {
                        "ok": False,
                        "estado": "or_mal_formado",
                        "condiciones": [],
                        "razon": (
                            "Se encontró un operador OR sin "
                            "condición previa."
                        ),
                    }

                partes.append(parte)
                buffer = []

                i = fin

                while (
                    i < largo
                    and texto[i].isspace()
                ):
                    i += 1

                continue

        buffer.append(caracter)
        i += 1

    if comilla is not None:
        return {
            "ok": False,
            "estado": "comillas_no_balanceadas",
            "condiciones": [],
            "razon": (
                "La consulta contiene una cadena entre comillas "
                "sin cierre."
            ),
        }

    ultima = "".join(buffer).strip()

    if not ultima:
        if partes:
            return {
                "ok": False,
                "estado": "or_mal_formado",
                "condiciones": [],
                "razon": (
                    "La consulta termina con un operador OR "
                    "sin condición posterior."
                ),
            }

        return {
            "ok": False,
            "estado": "pregunta_vacia",
            "condiciones": [],
        }

    partes.append(ultima)

    if len(partes) < 2:
        return {
            "ok": False,
            "estado": "sin_multiples_condiciones_or",
            "condiciones": partes,
            "razon": (
                "No se detectaron múltiples condiciones OR."
            ),
        }

    return {
        "ok": True,
        "estado": "condiciones_or_detectadas",
        "condiciones": partes,
    }


def _separar_prefijo_y_primera_condicion(
    pregunta: str,
) -> tuple[str, str] | None:
    """
    Ejemplo:

        listar documentos cuyo tema contiene estructura

    retorna:

        ("listar documentos", "cuyo tema contiene estructura")
    """

    coincidencia = re.search(
        r"\b(cuyo|cuya|cuyos|cuyas)\b",
        pregunta,
        flags=re.IGNORECASE,
    )

    if not coincidencia:
        return None

    prefijo = pregunta[:coincidencia.start()].strip()
    condicion = pregunta[coincidencia.start():].strip()

    if not prefijo or not condicion:
        return None

    return prefijo, condicion


def _normalizar_condicion_relativa(
    condicion: str,
) -> str:
    condicion = condicion.strip()

    if re.match(
        r"^(cuyo|cuya|cuyos|cuyas)\b",
        condicion,
        flags=re.IGNORECASE,
    ):
        return condicion

    return f"cuyo {condicion}"


def componer_condiciones_or(
    pregunta: str,
    limite: int = 20,
) -> dict[str, Any]:
    """
    IA-QUERY002.

    Construye un contrato lógico OR a partir de múltiples
    condiciones simples.

    Cada rama:
      1. se resuelve con BRIDGE003;
      2. BRIDGE003 la entrega a HOST;
      3. sólo si HOST la valida se acepta en el grupo OR.

    QUERY002 NO ejecuta ORM.
    """

    pregunta = str(pregunta or "").strip()

    if not pregunta:
        return _respuesta_error(
            estado="pregunta_vacia",
            pregunta=pregunta,
            razon="La pregunta está vacía.",
        )

    if _contiene_and_fuera_de_comillas(pregunta):
        return _respuesta_error(
            estado="logica_mixta_no_soportada",
            pregunta=pregunta,
            razon=(
                "QUERY002 sólo admite OR puro. "
                "La combinación AND/OR corresponde a QUERY003."
            ),
        )

    division = _dividir_or_fuera_de_comillas(
        pregunta
    )

    if division.get("ok") is not True:
        return _respuesta_error(
            estado=str(
                division.get(
                    "estado",
                    "division_or_no_resuelta",
                )
            ),
            pregunta=pregunta,
            razon=str(
                division.get(
                    "razon",
                    "No fue posible separar condiciones OR.",
                )
            ),
            division=division,
        )

    condiciones = division["condiciones"]

    primera = _separar_prefijo_y_primera_condicion(
        condiciones[0]
    )

    if primera is None:
        return _respuesta_error(
            estado="prefijo_consulta_no_resuelto",
            pregunta=pregunta,
            razon=(
                "No fue posible separar la operación/entidad "
                "de la primera condición."
            ),
        )

    prefijo, primera_condicion = primera

    condiciones_normalizadas = [
        primera_condicion
    ]

    for condicion in condiciones[1:]:
        condiciones_normalizadas.append(
            _normalizar_condicion_relativa(
                condicion
            )
        )

    modelo_base: str | None = None
    operacion_base: str | None = None

    resoluciones: list[dict[str, Any]] = []
    condiciones_logicas: list[dict[str, Any]] = []

    for indice, condicion in enumerate(
        condiciones_normalizadas
    ):
        pregunta_condicion = (
            f"{prefijo} {condicion}"
        ).strip()

        resultado_bridge = (
            componer_campo_operador_valor(
                pregunta_condicion,
                limite=limite,
            )
        )

        plan = _extraer_plan_bridge003(
            resultado_bridge
        )

        if plan is None:
            return _respuesta_error(
                estado="condicion_no_resuelta",
                pregunta=pregunta,
                razon=(
                    "BRIDGE003 no produjo un plan HOST "
                    "validado para una de las ramas OR."
                ),
                condicion_indice=indice,
                condicion=condicion,
                pregunta_condicion=pregunta_condicion,
                estado_bridge=resultado_bridge.get(
                    "estado"
                ),
                bridge003=resultado_bridge,
                resoluciones=resoluciones,
            )

        filtros = plan.get("filtros")

        if (
            not isinstance(filtros, list)
            or len(filtros) != 1
        ):
            return _respuesta_error(
                estado="rama_or_invalida",
                pregunta=pregunta,
                razon=(
                    "Cada rama OR debe resolver exactamente "
                    "un filtro HOST."
                ),
                condicion_indice=indice,
                condicion=condicion,
                resoluciones=resoluciones,
            )

        modelo = plan.get("modelo")
        operacion = plan.get("operacion")

        if indice == 0:
            modelo_base = modelo
            operacion_base = operacion
        else:
            if modelo != modelo_base:
                return _respuesta_error(
                    estado="modelos_incompatibles",
                    pregunta=pregunta,
                    razon=(
                        "Todas las ramas OR deben pertenecer "
                        "al mismo modelo."
                    ),
                    modelo_base=modelo_base,
                    modelo_encontrado=modelo,
                    condicion_indice=indice,
                    resoluciones=resoluciones,
                )

            if operacion != operacion_base:
                return _respuesta_error(
                    estado="operaciones_incompatibles",
                    pregunta=pregunta,
                    razon=(
                        "Todas las ramas OR deben utilizar "
                        "la misma operación."
                    ),
                    operacion_base=operacion_base,
                    operacion_encontrada=operacion,
                    condicion_indice=indice,
                    resoluciones=resoluciones,
                )

        filtro = dict(filtros[0])

        resoluciones.append(
            {
                "indice": indice,
                "condicion": condicion,
                "pregunta_condicion": pregunta_condicion,
                "modelo": modelo,
                "operacion": operacion,
                "filtro": filtro,
            }
        )

        condiciones_logicas.append(
            {
                "campo": filtro.get("campo"),
                "operador": filtro.get("operador"),
                "lookup": filtro.get("lookup"),
                "valor": filtro.get("valor"),
                "tipo": filtro.get("tipo"),
            }
        )

    contrato = {
        "modelo": modelo_base,
        "operacion": operacion_base,
        "logica": {
            "operador": "OR",
            "condiciones": condiciones_logicas,
        },
        "limite": limite,
    }

    return {
        "ok": True,
        "version": VERSION,
        "ejecutado": False,
        "estado": "plan_or_validado",
        "modo": "or",
        "pregunta": pregunta,
        "cantidad_condiciones": len(
            condiciones_logicas
        ),
        "contrato_logico": contrato,
        "resoluciones": resoluciones,
        "llm_invocado": False,
        "razon": (
            "QUERY002 construyó un contrato OR cuyas ramas "
            "fueron certificadas individualmente por HOST. "
            "El OR completo no fue ejecutado."
        ),
    }