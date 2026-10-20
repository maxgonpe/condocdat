from __future__ import annotations

from typing import Any

from ia_local.services.query.condiciones_and import (
    construir_plan_and,
)

from ia_local.services.query.condiciones_or import (
    componer_condiciones_or,
)

from ia_local.services.query.grupos_logicos import (
    componer_grupos_logicos,
)

from ia_local.services.query.ordenamiento_natural import (
    componer_ordenamiento_natural,
)
from ia_local.services.query.fechas_absolutas import (
    componer_fechas_absolutas,
)
from ia_local.services.query.fechas_relativas import (
    componer_fechas_relativas,
)
from ia_local.services.query.relaciones_orm import (
    componer_relacion_orm,
)

from ia_local.services.query.colecciones_estructuras import (
    describir_coleccion_natural,
)

from ia_local.services.query.agregaciones import (
    componer_agregacion,
)
from ia_local.services.query.agrupamientos import (
    componer_agrupamiento,
)
from ia_local.services.query.consultas_relacionales import (
    componer_consulta_relacional,
)


# ============================================================
# IA-QUERY012
# SEGURIDAD / REGRESIÓN / CIERRE
# ============================================================
#
# Responsabilidad:
#
#   ejecutar una batería declarativa sobre QUERY001-QUERY011
#   y verificar:
#
#   - resolución positiva;
#   - rechazo seguro;
#   - ausencia de ejecución ORM desde QUERY;
#   - ausencia de LLM;
#   - conservación de contratos críticos;
#   - aislamiento entre modelo origen y destino.
#
# QUERY012:
#   - NO ejecuta ORM directamente;
#   - NO usa LLM;
#   - NO genera SQL;
#   - NO modifica datos;
#   - NO crea modelos;
#   - NO crea aliases.
#
# ============================================================


VERSION = "IA-QUERY012-v1"


def _resultado_prueba(
    *,
    nombre: str,
    esperado: bool,
    resultado: dict[str, Any],
    validaciones: list[tuple[str, bool]],
) -> dict[str, Any]:

    fallos = [
        descripcion
        for descripcion, cumple
        in validaciones
        if not cumple
    ]

    ok = (
        isinstance(
            resultado,
            dict,
        )
        and bool(
            resultado.get(
                "ok"
            )
        )
        is esperado
        and not fallos
    )

    return {
        "nombre": nombre,
        "ok": ok,
        "esperado_ok": esperado,
        "resultado_ok": (
            resultado.get(
                "ok"
            )
            if isinstance(
                resultado,
                dict,
            )
            else None
        ),
        "estado": (
            resultado.get(
                "estado"
            )
            if isinstance(
                resultado,
                dict,
            )
            else None
        ),
        "fallos": fallos,
        "llm_invocado": (
            resultado.get(
                "llm_invocado"
            )
            if isinstance(
                resultado,
                dict,
            )
            else None
        ),
        "ejecutado": (
            resultado.get(
                "ejecutado"
            )
            if isinstance(
                resultado,
                dict,
            )
            else None
        ),
    }


def ejecutar_regresion_query() -> dict[str, Any]:

    pruebas: list[dict[str, Any]] = []

    # --------------------------------------------------------
    # QUERY001
    # --------------------------------------------------------

    r = construir_plan_and(
        "listar documentos cuyo tema contiene estructura "
        "y cuyo codigo contiene ODATA"
    )

    pruebas.append(
        _resultado_prueba(
            nombre="QUERY001_AND",
            esperado=True,
            resultado=r,
            validaciones=[
                (
                    "QUERY001 no debe ejecutar ORM.",
                    r.get("ejecutado") is False,
                ),
                (
                    "QUERY001 no debe invocar LLM.",
                    r.get("llm_invocado") is False,
                ),
            ],
        )
    )

    # --------------------------------------------------------
    # QUERY002
    # --------------------------------------------------------

    r = componer_condiciones_or(
        "listar documentos cuyo tema contiene estructura "
        "o cuyo codigo contiene ODATA"
    )

    pruebas.append(
        _resultado_prueba(
            nombre="QUERY002_OR",
            esperado=True,
            resultado=r,
            validaciones=[
                (
                    "QUERY002 no debe ejecutar ORM.",
                    r.get("ejecutado") is False,
                ),
                (
                    "QUERY002 no debe invocar LLM.",
                    r.get("llm_invocado") is False,
                ),
            ],
        )
    )

    # --------------------------------------------------------
    # QUERY003
    # --------------------------------------------------------

    r = componer_grupos_logicos(
        "listar documentos cuyo tema contiene estructura "
        "y (cuyo codigo contiene ODATA o cuyo id mayor que 10)"
    )

    pruebas.append(
        _resultado_prueba(
            nombre="QUERY003_GRUPO_LOGICO",
            esperado=True,
            resultado=r,
            validaciones=[
                (
                    "QUERY003 no debe ejecutar ORM.",
                    r.get("ejecutado") is False,
                ),
                (
                    "QUERY003 no debe invocar LLM.",
                    r.get("llm_invocado") is False,
                ),
            ],
        )
    )

    # --------------------------------------------------------
    # QUERY004
    # --------------------------------------------------------

    r = componer_ordenamiento_natural(
        "listar documentos ordenados por fecha descendente"
    )

    pruebas.append(
        _resultado_prueba(
            nombre="QUERY004_ORDEN",
            esperado=True,
            resultado=r,
            validaciones=[
                (
                    "QUERY004 no debe ejecutar ORM.",
                    r.get("ejecutado") is False,
                ),
                (
                    "QUERY004 no debe invocar LLM.",
                    r.get("llm_invocado") is False,
                ),
            ],
        )
    )

    # --------------------------------------------------------
    # QUERY005
    # --------------------------------------------------------

    r = componer_fechas_absolutas(
        "listar documentos cuya fecha "
        "desde 2026-10-01 hasta 2026-10-20"
    )

    pruebas.append(
        _resultado_prueba(
            nombre="QUERY005_FECHA_ABSOLUTA",
            esperado=True,
            resultado=r,
            validaciones=[
                (
                    "QUERY005 no debe ejecutar ORM.",
                    r.get("ejecutado") is False,
                ),
                (
                    "QUERY005 no debe invocar LLM.",
                    r.get("llm_invocado") is False,
                ),
            ],
        )
    )

    # --------------------------------------------------------
    # QUERY006
    # --------------------------------------------------------

    from datetime import date

    r = componer_fechas_relativas(
        "listar documentos de hoy",
        fecha_referencia=date(
            2026,
            10,
            20,
        ),
    )

    pruebas.append(
        _resultado_prueba(
            nombre="QUERY006_FECHA_RELATIVA",
            esperado=True,
            resultado=r,
            validaciones=[
                (
                    "QUERY006 no debe ejecutar ORM.",
                    r.get("ejecutado") is False,
                ),
                (
                    "QUERY006 no debe invocar LLM.",
                    r.get("llm_invocado") is False,
                ),
            ],
        )
    )

    # --------------------------------------------------------
    # QUERY007
    # --------------------------------------------------------

    r = componer_relacion_orm(
        "listar proyectos de documentos de correos enviados"
    )

    pruebas.append(
        _resultado_prueba(
            nombre="QUERY007_RELACION_MULTISALTO",
            esperado=True,
            resultado=r,
            validaciones=[
                (
                    "QUERY007 debe resolver document__project.",
                    r.get("ruta_orm")
                    == "document__project",
                ),
                (
                    "QUERY007 no debe ejecutar ORM.",
                    r.get("ejecutado") is False,
                ),
                (
                    "QUERY007 no debe invocar LLM.",
                    r.get("llm_invocado") is False,
                ),
            ],
        )
    )

    # --------------------------------------------------------
    # QUERY008
    # --------------------------------------------------------

    r = describir_coleccion_natural(
        "coleccion correos enviados de documentos"
    )

    pruebas.append(
        _resultado_prueba(
            nombre="QUERY008_COLECCION",
            esperado=True,
            resultado=r,
            validaciones=[
                (
                    "QUERY008 no debe ejecutar ORM.",
                    r.get("ejecutado") is False,
                ),
                (
                    "QUERY008 no debe invocar LLM.",
                    r.get("llm_invocado") is False,
                ),
            ],
        )
    )

    # --------------------------------------------------------
    # QUERY009
    # --------------------------------------------------------

    r = componer_agregacion(
        "promedio de number de documentos"
    )

    pruebas.append(
        _resultado_prueba(
            nombre="QUERY009_AGREGACION",
            esperado=True,
            resultado=r,
            validaciones=[
                (
                    "QUERY009 debe usar promediar_campo.",
                    r.get("accion_plan")
                    == "promediar_campo",
                ),
                (
                    "QUERY009 no debe ejecutar ORM.",
                    r.get("ejecutado") is False,
                ),
                (
                    "QUERY009 no debe invocar LLM.",
                    r.get("llm_invocado") is False,
                ),
            ],
        )
    )

    # --------------------------------------------------------
    # QUERY010
    # --------------------------------------------------------

    r = componer_agrupamiento(
        "promedio de number por estado de documentos"
    )

    pruebas.append(
        _resultado_prueba(
            nombre="QUERY010_AGRUPAMIENTO",
            esperado=True,
            resultado=r,
            validaciones=[
                (
                    "QUERY010 debe quedar validado.",
                    r.get("estado")
                    == "agrupamiento_validado",
                ),
                (
                    "QUERY010 no debe ejecutar ORM.",
                    r.get("ejecutado") is False,
                ),
                (
                    "QUERY010 no debe invocar LLM.",
                    r.get("llm_invocado") is False,
                ),
            ],
        )
    )

    # --------------------------------------------------------
    # QUERY011
    # --------------------------------------------------------

    r = componer_consulta_relacional(
        "contar proyectos de documentos "
        "cuyo tema contiene estructura"
    )

    plan_base = (
        r.get(
            "plan_base"
        )
        if isinstance(
            r,
            dict,
        )
        else None
    )

    filtros = (
        plan_base.get(
            "filtros",
            [],
        )
        if isinstance(
            plan_base,
            dict,
        )
        else []
    )

    pruebas.append(
        _resultado_prueba(
            nombre="QUERY011_RELACIONAL_FILTRADA",
            esperado=True,
            resultado=r,
            validaciones=[
                (
                    "QUERY011 debe conservar Document "
                    "como modelo origen.",
                    r.get("modelo_origen")
                    == "documents.Document",
                ),
                (
                    "QUERY011 debe resolver Project "
                    "como destino.",
                    r.get("modelo_destino")
                    == "documents.Project",
                ),
                (
                    "QUERY011 debe usar ruta project.",
                    r.get("ruta_orm")
                    == "project",
                ),
                (
                    "QUERY011 debe aplicar el filtro "
                    "al modelo origen.",
                    bool(
                        filtros
                    )
                    and filtros[0].get(
                        "campo"
                    )
                    == "title",
                ),
                (
                    "QUERY011 no debe ejecutar ORM.",
                    r.get("ejecutado") is False,
                ),
                (
                    "QUERY011 no debe invocar LLM.",
                    r.get("llm_invocado") is False,
                ),
            ],
        )
    )

    # ========================================================
    # NEGATIVAS / SEGURIDAD
    # ========================================================

    r = componer_relacion_orm(
        "listar planetas de documentos"
    )

    pruebas.append(
        _resultado_prueba(
            nombre="SEGURIDAD_RELACION_INVENTADA",
            esperado=False,
            resultado=r,
            validaciones=[
                (
                    "Una relación inventada no debe "
                    "ejecutar ORM.",
                    r.get("ejecutado") is False,
                ),
                (
                    "Una relación inventada no debe "
                    "invocar LLM.",
                    r.get("llm_invocado") is False,
                ),
            ],
        )
    )

    r = componer_agregacion(
        "suma de tema de documentos"
    )

    pruebas.append(
        _resultado_prueba(
            nombre="SEGURIDAD_AGREGACION_INCOMPATIBLE",
            esperado=False,
            resultado=r,
            validaciones=[
                (
                    "CharField no debe admitirse "
                    "como suma.",
                    r.get("estado")
                    == "agregacion_incompatible",
                ),
                (
                    "El rechazo no debe ejecutar ORM.",
                    r.get("ejecutado") is False,
                ),
            ],
        )
    )

    r = componer_agrupamiento(
        "cuantos documentos por planetas"
    )

    pruebas.append(
        _resultado_prueba(
            nombre="SEGURIDAD_GRUPO_INVENTADO",
            esperado=False,
            resultado=r,
            validaciones=[
                (
                    "Campo inventado debe ser rechazado.",
                    r.get("estado")
                    == "campo_agrupacion_no_resuelto",
                ),
                (
                    "El rechazo no debe ejecutar ORM.",
                    r.get("ejecutado") is False,
                ),
            ],
        )
    )

    r = componer_consulta_relacional(
        "listar proyectos de documentos"
    )

    pruebas.append(
        _resultado_prueba(
            nombre="SEGURIDAD_OPERACION_RELACIONAL_NO_PERMITIDA",
            esperado=False,
            resultado=r,
            validaciones=[
                (
                    "QUERY011-v1 no debe aceptar listar.",
                    r.get("estado")
                    == "estructura_relacional_no_detectada",
                ),
                (
                    "No debe ejecutar ORM.",
                    r.get("ejecutado") is False,
                ),
            ],
        )
    )

    # ========================================================
    # RESULTADO GLOBAL
    # ========================================================

    aprobadas = sum(
        1
        for prueba
        in pruebas
        if prueba[
            "ok"
        ]
    )

    total = len(
        pruebas
    )

    fallidas = [
        prueba
        for prueba
        in pruebas
        if not prueba[
            "ok"
        ]
    ]

    return {
        "ok":
            aprobadas == total,

        "version":
            VERSION,

        "estado":
            (
                "regresion_completa"
                if aprobadas == total
                else "regresion_con_fallos"
            ),

        "total":
            total,

        "aprobadas":
            aprobadas,

        "fallidas":
            len(
                fallidas
            ),

        "pruebas":
            pruebas,

        "fallos":
            fallidas,

        "ejecutado":
            False,

        "llm_invocado":
            False,
    }