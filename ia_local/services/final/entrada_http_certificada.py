"""
ARC003-B06-B01 — Adaptador HTTP certificado.

Primera version: exclusivamente conteo con igualdad
textual explicita y gramatica cerrada.

No contiene vistas, no admite planes externos,
no ejecuta ORM directamente y no usa rutas alternativas.
"""

from ia_local.services.llm.certificador_limitado import PATRON
from ia_local.services.llm.trazabilidad_compuesta import (
    preparar_coleccion_restricciones,
)
from ia_local.services.host.catalogo_datos import (
    buscar_modelo_datos,
)
from ia_local.services.host.expediente_consulta import (
    crear_expediente,
)
from ia_local.services.final.ejecucion_conteo_filtrado import (
    ejecutar_conteo_filtrado_certificado,
)


VERSION = "IA-ARC003-B06-B01-v1"


def _rechazo(estado, pregunta=""):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "pregunta": pregunta,
        "tipo": "conteo",
        "respuesta": "La consulta no pudo ser autorizada o certificada.",
        "total": None,
        "registros": [],
        "campos": [],
        "ejecutado": False,
        "llm_invocado": False,
    }


def responder_consulta_http(request, pregunta):
    """
    Recibe solamente request y pregunta.

    No acepta modelo, filtros, plan, certificados ni
    identificadores de expediente del navegador.
    """

    if (
        not isinstance(pregunta, str)
        or not pregunta.strip()
        or len(pregunta) > 1000
    ):
        return _rechazo("pregunta_invalida")

    pregunta = pregunta.strip()

    if request is None:
        return _rechazo("solicitud_invalida", pregunta)

    usuario = getattr(request, "user", None)

    if (
        usuario is None
        or getattr(usuario, "is_authenticated", False)
            is not True
        or getattr(usuario, "is_active", False)
            is not True
        or not hasattr(request, "session")
    ):
        return _rechazo("identidad_no_autorizada", pregunta)

    coincidencia = PATRON.fullmatch(pregunta)

    if coincidencia is None:
        return _rechazo("gramatica_no_certificable", pregunta)

    entidad = coincidencia.group("entidad")
    evidencia = pregunta[
        coincidencia.start("campo"):
        coincidencia.end("valor")
    ]

    try:
        candidatos = buscar_modelo_datos(entidad)

        if (
            not isinstance(candidatos, list)
            or len(candidatos) != 1
            or not isinstance(candidatos[0], dict)
        ):
            return _rechazo(
                "entidad_no_inequivoca", pregunta
            )

        modelo = candidatos[0].get("label")

        if not isinstance(modelo, str) or not modelo:
            return _rechazo(
                "entidad_no_inequivoca", pregunta
            )

        # Solo evidencia obtenida del texto original.
        # El cliente no proporciona restricciones.
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

        if (
            not isinstance(coleccion, dict)
            or coleccion.get("ok") is not True
            or coleccion.get("ejecutable") is not False
        ):
            return _rechazo(
                "coleccion_no_certificable", pregunta
            )

        creado = crear_expediente(
            request, coleccion, modelo
        )

        if (
            not isinstance(creado, dict)
            or creado.get("ok") is not True
            or not isinstance(
                creado.get("identificador"), str
            )
            or type(creado.get("version")) is not int
        ):
            return _rechazo(
                "expediente_no_disponible", pregunta
            )

        # E03 vuelve a verificar semantica, identidad,
        # sesion, version y politica de lectura.
        ejecutado = ejecutar_conteo_filtrado_certificado(
            request,
            creado["identificador"],
            creado["version"],
        )

        if (
            not isinstance(ejecutado, dict)
            or ejecutado.get("ok") is not True
            or ejecutado.get("ejecutado") is not True
            or ejecutado.get("estado")
                != "conteo_filtrado_ejecutado"
            or ejecutado.get("modelo") != modelo
            or type(ejecutado.get("total")) is not int
            or ejecutado["total"] < 0
        ):
            return _rechazo(
                "ejecucion_no_autorizada", pregunta
            )

        total = ejecutado["total"]

        return {
            "ok": True,
            "version": VERSION,
            "estado": "respuesta_formateada",
            "pregunta": pregunta,
            "tipo": "conteo",
            "respuesta": (
                f"Se encontraron {total} registros."
            ),
            "modelo": modelo,
            "total": total,
            "total_disponible": total,
            "total_devuelto": 0,
            "truncado": False,
            "registros": [],
            "campos": [],
            "ejecutado": True,
            "llm_invocado": False,
        }

    except Exception:
        # No revelar detalles de base de datos, sesiones,
        # expedientes o implementacion interna.
        return _rechazo("entrada_no_disponible", pregunta)
