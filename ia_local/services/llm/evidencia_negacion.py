"""
ARC002-B03-B01 — Evidencia textual de negaciones.

Localiza marcadores negativos conservando el texto original.
El contexto cercano NO representa alcance lógico certificado.
No interpreta, certifica ni ejecuta consultas.
"""

import re


VERSION = "IA-ARC002-B03-B01-v1"

PATRON_NEGACION = re.compile(
    r"\b(?:no|sin|ning[uú]n\w*|nunca|jam[aá]s)\b",
    re.IGNORECASE,
)


def localizar_evidencias_negacion(pregunta):
    base = {
        "ok": False,
        "version": VERSION,
        "estado": "pregunta_invalida",
        "pregunta_original": None,
        "evidencias": [],
        "cantidad": 0,
        "alcance_certificado": False,
        "cobertura_verificada": False,
        "ejecutable": False,
        "ejecutado": False,
    }

    if (
        not isinstance(pregunta, str)
        or not pregunta.strip()
        or len(pregunta) > 1000
    ):
        return base

    evidencias = []

    for indice, coincidencia in enumerate(
        PATRON_NEGACION.finditer(pregunta), start=1
    ):
        inicio, fin = coincidencia.span()

        # Contexto diagnóstico, limitado a 100 caracteres.
        # No debe considerarse el alcance de la negación.
        extremo = min(len(pregunta), fin + 100)
        contexto = pregunta[fin:extremo]

        for posicion, caracter in enumerate(contexto):
            if caracter in ".;!?¿¡":
                contexto = contexto[:posicion]
                break

        evidencias.append({
            "id_local": f"neg-{indice:04d}",
            "tipo": "negacion_textual",
            "marcador_textual": pregunta[inicio:fin],
            "inicio": inicio,
            "fin": fin,
            "fragmento_contextual": contexto.strip(),
            "alcance_semantico": None,
            "campo_host": None,
            "operador_django": None,
            "certificada": False,
        })

    return {
        **base,
        "ok": True,
        "estado": (
            "negaciones_detectadas_pendientes"
            if evidencias
            else "sin_marcadores_detectados"
        ),
        "pregunta_original": pregunta,
        "evidencias": evidencias,
        "cantidad": len(evidencias),
    }
