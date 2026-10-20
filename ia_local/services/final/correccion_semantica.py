from __future__ import annotations

from typing import Any

from ia_local.services.semantica.aprendizaje_controlado import (
    proponer_aprendizaje,
)


VERSION = "IA-FINAL008-v1"


def proponer_correccion_semantica(
    *,
    tipo: str,
    expresion: str,
    datos: dict[str, Any],
    motivo: str = "",
) -> dict[str, Any]:
    """
    IA-FINAL008

    Adaptador entre la capa FINAL y el aprendizaje
    semántico controlado IA-SEM007.

    Esta función:

    - NO crea aliases directamente.
    - NO crea reglas directamente.
    - NO confirma propuestas.
    - NO ejecuta ORM de negocio.
    - NO invoca LLM.

    Toda validación y persistencia de la propuesta
    se delega a SEM007.
    """

    if not isinstance(
        datos,
        dict,
    ):

        return {
            "ok": False,
            "version": VERSION,
            "estado": "datos_invalidos",
            "propuesta_creada": False,
            "llm_invocado": False,
        }

    tipo = str(
        tipo
        or ""
    ).strip()

    expresion = str(
        expresion
        or ""
    ).strip()

    motivo = str(
        motivo
        or ""
    ).strip()

    if not tipo:

        return {
            "ok": False,
            "version": VERSION,
            "estado": "tipo_vacio",
            "propuesta_creada": False,
            "llm_invocado": False,
        }

    if not expresion:

        return {
            "ok": False,
            "version": VERSION,
            "estado": "expresion_vacia",
            "propuesta_creada": False,
            "llm_invocado": False,
        }

    resultado_sem = proponer_aprendizaje(
        tipo=tipo,
        expresion=expresion,
        datos=datos,
        motivo=motivo,
    )

    return {
        "ok":
            bool(
                resultado_sem.get(
                    "ok",
                    False,
                )
            ),

        "version":
            VERSION,

        "estado":
            resultado_sem.get(
                "estado",
                "resultado_sem_desconocido",
            ),

        "propuesta_creada":
            bool(
                resultado_sem.get(
                    "creada",
                    False,
                )
            ),

        "propuesta":
            resultado_sem.get(
                "propuesta"
            ),

        "propuesta_id":
            (
                resultado_sem.get(
                    "propuesta_id"
                )
                or (
                    resultado_sem.get(
                        "propuesta"
                    )
                    or {}
                ).get(
                    "id"
                )
            ),

        "sem":
            resultado_sem,

        "llm_invocado":
            False,
    }