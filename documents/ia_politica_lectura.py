"""
ARC003-B05-D03-B
Politica de lectura de Condocdat para ia_local.

Permite exclusivamente conteos globales de documentos
filtrados por igualdad textual de status.

No consulta datos, no ejecuta ORM, no modifica modelos.
Denegacion por defecto.
"""

from django.conf import settings


PERMISO = "documents.view_document"
MODELO = "documents.Document"
CAMPO = "status"

AJUSTE_GLOBAL = (
    "IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO"
)


def autorizar_lectura_documentos(
    *,
    usuario,
    modelo,
    operacion,
    campos,
    plan,
):
    def denegar():
        return {
            "permitido": False,
            "modelo": modelo,
            "operacion": operacion,
            "campos": list(campos)
                if isinstance(campos, (list, tuple))
                else [],
            "alcance": "no_autorizado",
        }

    if (
        usuario is None
        or getattr(usuario, "is_authenticated", False)
            is not True
        or getattr(usuario, "is_active", False)
            is not True
        or getattr(usuario, "pk", None) is None
    ):
        return denegar()

    # La habilitacion debe ser el booleano True,
    # no una cadena como "true" o "1".
    if getattr(
        settings,
        AJUSTE_GLOBAL,
        False,
    ) is not True:
        return denegar()

    try:
        if usuario.has_perm(PERMISO) is not True:
            return denegar()
    except Exception:
        return denegar()

    if (
        modelo != MODELO
        or operacion != "contar"
        or campos != (CAMPO,)
        or not isinstance(plan, dict)
        or plan.get("modelo") != MODELO
        or plan.get("operacion") != "contar"
        or plan.get("orden") != []
        or plan.get("condiciones_no_resueltas") != []
    ):
        return denegar()

    filtros = plan.get("filtros")

    if (
        not isinstance(filtros, list)
        or len(filtros) != 1
        or not isinstance(filtros[0], dict)
    ):
        return denegar()

    filtro = filtros[0]

    if (
        filtro.get("campo") != CAMPO
        or filtro.get("lookup") != CAMPO
        or filtro.get("operador") != "exact"
        or filtro.get("negado") is not False
        or filtro.get("tipo") != "CharField"
        or not isinstance(filtro.get("valor"), str)
    ):
        return denegar()

    return {
        "permitido": True,
        "modelo": MODELO,
        "operacion": "contar",
        "campos": [CAMPO],
        "alcance": "universo_completo",
    }
