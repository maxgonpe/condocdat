from __future__ import annotations

from typing import Any

from ia_local.models import (
    IAHistorialConsulta,
)


VERSION = "IA-FINAL007-v1"


def _texto(
    valor: Any,
) -> str:

    if valor is None:
        return ""

    return str(
        valor
    ).strip()


def _total_seguro(
    valor: Any,
) -> int | None:

    if valor is None:
        return None

    if isinstance(
        valor,
        bool,
    ):
        return None

    try:

        return int(
            valor
        )

    except (
        TypeError,
        ValueError,
    ):

        return None


def registrar_traza_consulta(
    *,
    pregunta: str,
    resultado: dict[str, Any],
    usuario: str = "",
) -> dict[str, Any]:
    """
    Registra únicamente información compacta y estable
    de una respuesta FINAL004.

    No almacena:
    - diagnostico
    - contratos completos
    - registros devueltos
    - planes HOST
    - SQL
    """

    if not isinstance(
        resultado,
        dict,
    ):

        return {
            "ok": False,
            "version": VERSION,
            "estado":
                "resultado_invalido",
            "registrado": False,
        }

    traza = IAHistorialConsulta.objects.create(
        pregunta=_texto(
            pregunta
        ),

        usuario=_texto(
            usuario
        ),

        ok=bool(
            resultado.get(
                "ok",
                False,
            )
        ),

        estado=_texto(
            resultado.get(
                "estado"
            )
        ),

        intencion=_texto(
            resultado.get(
                "intencion"
            )
        ),

        modelo=_texto(
            resultado.get(
                "modelo"
            )
        ),

        tipo=_texto(
            resultado.get(
                "tipo"
            )
        ),

        componente=_texto(
            resultado.get(
                "componente"
            )
        ),

        tipo_contrato=_texto(
            resultado.get(
                "tipo_contrato"
            )
        ),

        ejecutor=_texto(
            resultado.get(
                "ejecutor"
            )
        ),

        ejecutado=bool(
            resultado.get(
                "ejecutado",
                False,
            )
        ),

        total=_total_seguro(
            resultado.get(
                "total"
            )
        ),

        llm_invocado=bool(
            resultado.get(
                "llm_invocado",
                False,
            )
        ),

        version_final=_texto(
            resultado.get(
                "version"
            )
        ),
    )

    return {
        "ok": True,
        "version": VERSION,
        "estado":
            "traza_registrada",
        "registrado": True,
        "id":
            traza.pk,
    }


def listar_trazas_recientes(
    *,
    limite: int = 20,
) -> list[dict[str, Any]]:

    try:
        limite = int(
            limite
        )
    except (
        TypeError,
        ValueError,
    ):
        limite = 20

    limite = max(
        1,
        min(
            limite,
            100,
        ),
    )

    filas = (
        IAHistorialConsulta.objects
        .order_by(
            "-creado_en",
            "-id",
        )[:limite]
    )

    return [
        {
            "id":
                fila.pk,

            "pregunta":
                fila.pregunta,

            "usuario":
                fila.usuario,

            "ok":
                fila.ok,

            "estado":
                fila.estado,

            "intencion":
                fila.intencion,

            "modelo":
                fila.modelo,

            "tipo":
                fila.tipo,

            "componente":
                fila.componente,

            "tipo_contrato":
                fila.tipo_contrato,

            "ejecutor":
                fila.ejecutor,

            "ejecutado":
                fila.ejecutado,

            "total":
                fila.total,

            "llm_invocado":
                fila.llm_invocado,

            "version_final":
                fila.version_final,

            "creado_en":
                fila.creado_en,
        }

        for fila
        in filas
    ]