"""
ARC003-B05-D03-A
Politica de lectura de Condocdat para ia_local.

Este modulo pertenece al anfitrion, no al nucleo ia_local.

Estado inicial: denegacion por defecto.
No autoriza consultas reales.
"""

MODELO_ADMITIDO = "documents.Document"
CAMPO_ADMITIDO = "status"
OPERACION_ADMITIDA = "contar"


def autorizar_lectura_documentos(
    *,
    usuario,
    modelo,
    operacion,
    campos,
    plan,
):
    """
    Politica del anfitrion Condocdat.

    En esta etapa NO existe una concesion de lectura
    del universo completo de documentos.

    Toda solicitud se rechaza, incluso si coincide
    con el contrato funcional previsto.
    """

    return {
        "permitido": False,
        "modelo": modelo,
        "operacion": operacion,
        "campos": list(campos),
        "alcance": "no_autorizado",
    }
