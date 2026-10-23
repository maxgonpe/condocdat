"""
IA-ARC001-C04-B03.

Adaptador de compatibilidad entre FINAL004 y la vista HTML.
No ejecuta consultas, no certifica y no altera las decisiones.
"""


def adaptar_final_html(resultado):
    if not isinstance(resultado, dict):
        raise ValueError("FINAL devolvió un contrato inválido.")

    diagnostico = resultado.get("diagnostico")
    if not isinstance(diagnostico, dict):
        diagnostico = {}

    respuesta = resultado.get("respuesta") or ""

    if not isinstance(respuesta, str):
        respuesta = str(respuesta)

    return {
        "diagnostico": diagnostico,
        "respuesta_estructurada": resultado,
        "respuesta_texto": respuesta,
        "registros": resultado.get("registros") or [],
        "ok": resultado.get("ok") is True,
        "ejecutado": resultado.get("ejecutado") is True,
    }
