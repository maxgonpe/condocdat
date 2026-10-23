"""Interpretación relacional reutilizable.

Qwen propone una expresión. QUERY007 y HOST la certifican.
Este componente nunca ejecuta un plan de datos.
"""
import json
import re
from typing import Any

from ia_local.services.host.catalogo_datos import (
    construir_catalogo_datos,
)
from ia_local.services.host.respuesta_llm import (
    consultar_ollama,
)
from ia_local.services.host.interprete_datos import (
    _extraer_json,
)
from ia_local.services.llm.relaciones_controladas import (
    certificar_relacion,
)

VERSION = "IA-LLM008-F4-04-v1"

PROMPT = """
Eres un intérprete de relaciones entre entidades Django.

Tu tarea es identificar si la pregunta solicita navegar
una relación entre dos modelos disponibles en el catálogo.

Responde exclusivamente mediante un objeto JSON:

{
  "operacion": "listar",
  "modelo_origen": "app.ModeloOrigen",
  "modelo_destino": "app.ModeloDestino",
  "expresion": "listar destinos de origen"
}

Reglas:
- No inventes modelos ni relaciones.
- Usa solamente las entidades del catálogo proporcionado.
- La expresión debe comenzar con 'listar '.
- La expresión describe el destino DE un origen.
- No construyas SQL, código Python ni consultas ORM.
- No incluyas una ruta ORM en la respuesta.
- No propongas filtros, agregaciones ni conteos.
- Si hay ambigüedad, devuelve {}.
- Si la solicitud no es una navegación relacional,
  devuelve {}.
- No cambies el significado de la pregunta.
"""


def _error(
    pregunta: str,
    estado: str,
    *,
    llm_invocado: bool = False,
    detalle: str | None = None,
) -> dict[str, Any]:
    resultado = {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "pregunta": pregunta,
        "llm_invocado": llm_invocado,
        "ejecutado": False,
    }
    if detalle:
        resultado["detalle"] = detalle
    return resultado


def _catalogo_relacional():
    """Expone solo metadatos de modelos del catálogo HOST."""
    catalogo = construir_catalogo_datos()

    if not isinstance(catalogo, list) or not catalogo:
        return None, None

    # Límite defensivo: no construir contextos incompletos.
    if len(catalogo) > 150:
        return None, None

    modelos = {}
    for entrada in catalogo:
        if not isinstance(entrada, dict):
            return None, None

        label = entrada.get("label")
        if not isinstance(label, str) or not label:
            return None, None

        if label in modelos:
            return None, None

        modelos[label] = {
            "label": label,
            "nombre": str(entrada.get("modelo") or ""),
            "descripcion": str(entrada.get("verbose_name") or ""),
            "plural": str(
                entrada.get("verbose_name_plural") or ""
            ),
        }

    # Relaciones directas del catálogo; Qwen no recibe
    # campos empresariales, valores ni registros.
    enlaces = []
    for entrada in catalogo:
        origen = entrada["label"]
        for relacion in entrada.get("relaciones", []):
            if not isinstance(relacion, dict):
                continue
            destino = relacion.get("modelo_relacionado")
            nombre = relacion.get("nombre")

            if (
                destino in modelos
                and isinstance(nombre, str)
                and nombre
            ):
                enlaces.append({
                    "modelo": origen,
                    "campo": nombre,
                    "relacionado": destino,
                })

    if len(enlaces) > 600:
        return None, None

    contexto = json.dumps(
        {
            "modelos": list(modelos.values()),
            "relaciones_de_catalogo": enlaces,
            "nota": (
                "Las relaciones son contexto orientativo. "
                "La certificación definitiva pertenece a HOST."
            ),
        },
        ensure_ascii=False,
    )

    return modelos, contexto


def interpretar_relacion_negocio(
    pregunta: str,
) -> dict[str, Any]:
    """Solicita una propuesta a Qwen y la certifica con HOST."""

    pregunta = pregunta.strip() if isinstance(pregunta, str) else ""

    if not pregunta:
        return _error(pregunta, "pregunta_vacia")

    if len(pregunta) > 1000:
        return _error(pregunta, "pregunta_demasiado_larga")

    # IA-LLM008-F4-05-R1
    # No aceptar una relación simple si la pregunta exige
    # ordenamiento, capacidad aún no preservada por este contrato.
    patron_orden = (
        r"\b(?:últim\w*|ultim\w*|primer\w*|recient\w*|"
        r"ordenad\w*|ordenar|"
        r"más\s+nuev\w*|mas\s+nuev\w*|"
        r"más\s+antigu\w*|mas\s+antigu\w*)\b"
    )

    if re.search(patron_orden, pregunta, flags=re.IGNORECASE):
        return {
            **_error(
                pregunta,
                "operacion_relacional_no_soportada",
                llm_invocado=False,
            ),
            "capacidad_pendiente": "ordenamiento_relacional",
            "razon": (
                "La pregunta solicita ordenar resultados. "
                "La interpretación relacional actual no conserva "
                "todavía ese criterio."
            ),
            "ejecutable": False,
        }

    try:
        modelos, contexto = _catalogo_relacional()
    except Exception:
        return _error(pregunta, "catalogo_no_disponible")

    if not modelos or not contexto:
        return _error(pregunta, "catalogo_relacional_invalido")

    try:
        respuesta = consultar_ollama(
            pregunta=pregunta,
            contexto=contexto,
            prompt_sistema=PROMPT,
        )
    except Exception:
        return _error(
            pregunta,
            "error_comunicacion_llm",
            llm_invocado=True,
        )

    if not isinstance(respuesta, dict) or respuesta.get("ok") is not True:
        return _error(
            pregunta,
            "interpretacion_llm_fallida",
            llm_invocado=True,
        )

    propuesta = _extraer_json(respuesta.get("respuesta"))

    if not isinstance(propuesta, dict) or not propuesta:
        return _error(
            pregunta,
            "interpretacion_no_resuelta",
            llm_invocado=True,
        )

    # Contrato cerrado: no aceptar campos ORM propuestos.
    campos = {
        "operacion",
        "modelo_origen",
        "modelo_destino",
        "expresion",
    }

    if set(propuesta) != campos:
        return _error(
            pregunta,
            "contrato_llm_invalido",
            llm_invocado=True,
        )

    origen = propuesta["modelo_origen"]
    destino = propuesta["modelo_destino"]
    expresion = propuesta["expresion"]

    if (
        propuesta["operacion"] != "listar"
        or not isinstance(origen, str)
        or not isinstance(destino, str)
        or origen not in modelos
        or destino not in modelos
        or not isinstance(expresion, str)
        or len(expresion) > 300
        or not re.match(r"^listar\s+\S", expresion, re.I)
    ):
        return _error(
            pregunta,
            "propuesta_relacional_no_permitida",
            llm_invocado=True,
        )

    # No se confía en rutas, modelos o campos del LLM.
    # La ruta se deriva nuevamente mediante QUERY007/HOST.
    certificado = certificar_relacion(expresion)

    if (
        not isinstance(certificado, dict)
        or certificado.get("ok") is not True
        or certificado.get("estado") != "relacion_certificada"
        or certificado.get("ejecutado") is not False
        or certificado.get("modelo_origen") != origen
        or certificado.get("modelo_destino") != destino
    ):
        return {
            **_error(
                pregunta,
                "relacion_no_certificada",
                llm_invocado=True,
            ),
            "expresion_propuesta": expresion,
            "estado_certificacion": (
                certificado.get("estado")
                if isinstance(certificado, dict)
                else "contrato_invalido"
            ),
        }

    return {
        "ok": True,
        "version": VERSION,
        "estado": "relacion_certificada",
        "pregunta": pregunta,
        "operacion_propuesta": "listar",
        "expresion_propuesta": expresion,
        "modelo_origen": origen,
        "modelo_destino": destino,
        "ruta_orm": certificado.get("ruta_orm"),
        "profundidad": certificado.get("profundidad"),
        "validacion_ruta": certificado.get("validacion_ruta"),
        "llm_invocado": True,
        "ejecutado": False,
        "ejecutable": False,
        "componente_certificador": "QUERY007/HOST",
    }
