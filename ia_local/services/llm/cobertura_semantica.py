"""
IA-LLM008-F5-07-14-D05-B

Control conservador de cobertura semántica.

No certifica equivalencia integral.
No ejecuta ORM.
No autoriza ejecución.
No contiene modelos ni campos específicos del HOST.
"""

import re
import unicodedata


VERSION = "IA-LLM008-F5-07-14-D05-B-v1"


def _normalizar(valor):
    texto = unicodedata.normalize(
        "NFKD", str(valor or "").lower()
    )
    texto = "".join(
        caracter for caracter in texto
        if not unicodedata.combining(caracter)
    )
    return re.sub(r"\s+", " ", texto).strip()


def _contiene(texto, patron):
    return bool(re.search(patron, texto))


def evaluar_cobertura_semantica(
    pregunta,
    consolidacion,
):
    """
    Compara señales lingüísticas con restricciones extraídas.

    Este control SOLO puede identificar riesgos o pendientes.
    No puede conceder certificación integral ni ejecución.
    """

    texto = _normalizar(pregunta)

    if not isinstance(consolidacion, dict):
        consolidacion = {}

    restricciones = consolidacion.get("restricciones")

    if not isinstance(restricciones, list):
        restricciones = []

    restricciones = [
        r for r in restricciones
        if isinstance(r, dict)
    ]

    tipos = {
        _normalizar(r.get("tipo"))
        for r in restricciones
    }

    pendientes = []
    señales = []

    def registrar(codigo):
        if codigo not in pendientes:
            pendientes.append(codigo)

    # No se confía en marcas proporcionadas por otros componentes.
    if consolidacion.get("ok") is not True:
        registrar("extraccion_no_validada")

    if _normalizar(consolidacion.get("pregunta")) != texto:
        registrar("pregunta_original_no_coincidente")

    if consolidacion.get("requiere_revision") is True:
        registrar("revision_semantica_pendiente")

    if consolidacion.get("omisiones_conocidas"):
        registrar("omisiones_conocidas")

    if consolidacion.get("restricciones_pendientes_host"):
        registrar("restricciones_host_pendientes")

    # Señales lingüísticas: útiles para rechazar,
    # nunca suficientes para certificar.
    # ARC002-B03: detectar negaciones textuales como riesgo.
    # No se infiere el campo, valor ni operador Django.
    hay_negacion = _contiene(
        texto,
        r"\b(?:no|sin|ningun\w*|nunca|jamas)\b"
    )

    hay_or = _contiene(texto, r"\bo\b|\bu\b")
    hay_and = _contiene(texto, r"\by\b|\be\b")

    hay_relacion = _contiene(
        texto,
        r"\bde\s+(?:los|las)\s+\w+"
    )

    hay_orden = _contiene(
        texto,
        r"\b(ultimos?|primeros?|recientes?|"
        r"antiguos?|ordenad[oa]s?)\b"
    )

    hay_limite = _contiene(
        texto,
        r"\b(?:primeros?|ultimos?)\s+"
        r"(?:\d+|uno|una|dos|tres|cuatro|cinco|"
        r"seis|siete|ocho|nueve|diez)\b"
    )

    filtros = [
        r for r in restricciones
        if _normalizar(r.get("tipo")) == "filtro"
    ]

    if hay_negacion:
        señales.append("posible_negacion")
        registrar("negacion_no_certificada")
        registrar("alcance_negacion_no_certificado")

    if hay_or:
        señales.append("posible_operador_or")

        if len(filtros) < 2:
            registrar("disyuncion_no_atomizada")

        # La lista de filtros no representa el árbol lógico.
        registrar("estructura_or_no_certificada")

    if hay_and:
        señales.append("posible_operador_and")
        registrar("estructura_and_no_certificada")

    if hay_relacion:
        señales.append("posible_alcance_relacional")

        if "relacion" not in tipos:
            registrar("alcance_relacional_no_representado")

        registrar("ruta_relacional_no_certificada")

    if hay_orden:
        señales.append("posible_ordenamiento")

        if "ordenamiento" not in tipos:
            registrar("ordenamiento_no_representado")

        registrar("campo_orden_no_certificado")

    if hay_limite:
        señales.append("posible_limite")

        if "limite" not in tipos:
            registrar("limite_no_representado")

        registrar("valor_limite_no_certificado")

    # ARC002-B03-B02: evidencias textuales originales.
    # No son filtros ni prueban alcance semantico.
    evidencias_negacion = []
    try:
        from ia_local.services.llm.evidencia_negacion import (
            localizar_evidencias_negacion,
        )
        diagnostico_negacion = localizar_evidencias_negacion(
            pregunta
        )
        if (
            not isinstance(diagnostico_negacion, dict)
            or diagnostico_negacion.get("ok") is not True
            or not isinstance(
                diagnostico_negacion.get("evidencias"), list
            )
        ):
            registrar("evidencia_negacion_no_disponible")
        else:
            evidencias_negacion = diagnostico_negacion["evidencias"]

            # Mantener la cobertura conservadora si los
            # localizadores discrepan sobre una negacion.
            if evidencias_negacion:
                if "posible_negacion" not in señales:
                    señales.append("posible_negacion")
                registrar("negacion_no_certificada")
                registrar("alcance_negacion_no_certificado")

            if hay_negacion and not evidencias_negacion:
                registrar("evidencia_negacion_no_disponible")

    except Exception:
        registrar("evidencia_negacion_no_disponible")

    # Cobertura de todos los fragmentos y equivalencia
    # con el plan ejecutable: trabajo del certificador integral.
    registrar("certificacion_integral_no_disponible")

    return {
        "ok": True,
        "version": VERSION,
        "estado": "cobertura_pendiente",
        "pregunta_original": pregunta,
        "operacion_propuesta": consolidacion.get("operacion"),
        "total_restricciones": len(restricciones),
        "tipos_extraidos": sorted(tipos),
        "senales_detectadas": señales,
        "evidencias_negacion": evidencias_negacion,
        "componentes_pendientes": pendientes,
        "cobertura_verificada": False,
        "ejecutable": False,
        "ejecutado": False,
    }
