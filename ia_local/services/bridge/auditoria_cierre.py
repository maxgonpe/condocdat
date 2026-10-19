from __future__ import annotations

import ast
import importlib
from pathlib import Path
from typing import Any

from django.apps import apps
from django.conf import settings

from .entrada_principal import (
    VERSION as VERSION_ENTRADA,
)
from .fallback_legado import (
    obtener_estado_fallback_legado,
)
from .orquestador_principal import (
    VERSION as VERSION_ORQUESTADOR,
    clasificar_fallo_bridge,
    consultar_orquestado,
)


VERSION = "IA-BRIDGE010-v1"


# ============================================================
# UTILIDADES
# ============================================================


def _resultado(
    nombre: str,
    ok: bool,
    detalle: str,
    evidencia: Any = None,
) -> dict[str, Any]:

    return {
        "nombre":
            nombre,

        "ok":
            bool(
                ok
            ),

        "detalle":
            detalle,

        "evidencia":
            evidencia,
    }


def _ruta_ia_local() -> Path:

    config = apps.get_app_config(
        "ia_local"
    )

    return Path(
        config.path
    ).resolve()


def _archivos_python(
    ruta: Path,
) -> list[Path]:

    return sorted(
        archivo
        for archivo
        in ruta.rglob(
            "*.py"
        )
        if "__pycache__"
        not in archivo.parts
    )


# ============================================================
# APPS DEL HOST
# ============================================================


def _apps_host() -> set[str]:
    """
    Determina apps locales del proyecto anfitrión.

    Excluye:
        - ia_local
        - django.contrib
        - apps cuyo path esté fuera de BASE_DIR

    Esto evita hardcodear:
        documents
        rdi
        equipos
        etc.
    """

    base_dir = Path(
        settings.BASE_DIR
    ).resolve()

    resultado: set[str] = set()

    for config in apps.get_app_configs():

        if config.label == "ia_local":
            continue

        if config.name.startswith(
            "django."
        ):
            continue

        try:

            ruta = Path(
                config.path
            ).resolve()

            ruta.relative_to(
                base_dir
            )

        except (
            ValueError,
            TypeError,
        ):
            continue

        resultado.add(
            config.name.split(
                "."
            )[0]
        )

    return resultado


# ============================================================
# IMPORTS DIRECTOS HACIA HOST
# ============================================================


def _imports_host_en_bridge(
) -> list[dict[str, Any]]:

    raiz = _ruta_ia_local()

    bridge = (
        raiz
        / "services"
        / "bridge"
    )

    apps_host = _apps_host()

    hallazgos: list[
        dict[str, Any]
    ] = []

    for archivo in _archivos_python(
        bridge
    ):

        try:

            fuente = archivo.read_text(
                encoding="utf-8"
            )

            arbol = ast.parse(
                fuente,
                filename=str(
                    archivo
                ),
            )

        except Exception as exc:

            hallazgos.append(
                {
                    "archivo":
                        str(
                            archivo.relative_to(
                                raiz
                            )
                        ),

                    "error_ast":
                        str(
                            exc
                        ),
                }
            )

            continue

        for nodo in ast.walk(
            arbol
        ):

            modulo = None

            if isinstance(
                nodo,
                ast.ImportFrom,
            ):

                modulo = (
                    nodo.module
                    or ""
                )

            elif isinstance(
                nodo,
                ast.Import,
            ):

                for alias in nodo.names:

                    raiz_import = (
                        alias.name
                        .split(
                            "."
                        )[0]
                    )

                    if raiz_import in apps_host:

                        hallazgos.append(
                            {
                                "archivo":
                                    str(
                                        archivo.relative_to(
                                            raiz
                                        )
                                    ),

                                "linea":
                                    nodo.lineno,

                                "import":
                                    alias.name,
                            }
                        )

                continue

            if not modulo:
                continue

            raiz_import = (
                modulo.split(
                    "."
                )[0]
            )

            if raiz_import in apps_host:

                hallazgos.append(
                    {
                        "archivo":
                            str(
                                archivo.relative_to(
                                    raiz
                                )
                            ),

                        "linea":
                            nodo.lineno,

                        "import":
                            modulo,
                    }
                )

    return hallazgos


# ============================================================
# ORM DIRECTO EN BRIDGE
# ============================================================


def _uso_objects_en_bridge(
) -> list[dict[str, Any]]:

    raiz = _ruta_ia_local()

    bridge = (
        raiz
        / "services"
        / "bridge"
    )

    hallazgos: list[
        dict[str, Any]
    ] = []

    for archivo in _archivos_python(
        bridge
    ):

        try:

            fuente = archivo.read_text(
                encoding="utf-8"
            )

            arbol = ast.parse(
                fuente,
                filename=str(
                    archivo
                ),
            )

        except Exception:

            continue

        for nodo in ast.walk(
            arbol
        ):

            if not isinstance(
                nodo,
                ast.Attribute,
            ):
                continue

            if nodo.attr != "objects":
                continue

            hallazgos.append(
                {
                    "archivo":
                        str(
                            archivo.relative_to(
                                raiz
                            )
                        ),

                    "linea":
                        getattr(
                            nodo,
                            "lineno",
                            None,
                        ),
                }
            )

    return hallazgos


# ============================================================
# EJECUTOR CONTROLADO → HOST
# ============================================================


def _verificar_delegacion_host(
) -> dict[str, Any]:

    raiz = _ruta_ia_local()

    archivo = (
        raiz
        / "services"
        / "bridge"
        / "ejecutor_controlado.py"
    )

    if not archivo.exists():

        return _resultado(
            "delegacion_host",
            False,
            (
                "No existe "
                "ejecutor_controlado.py."
            ),
        )

    fuente = archivo.read_text(
        encoding="utf-8"
    )

    tiene_import = (
        "ejecutar_plan_datos"
        in fuente
    )

    return _resultado(
        "delegacion_host",
        tiene_import,
        (
            "El ejecutor BRIDGE continúa "
            "delegando la ejecución final "
            "al ejecutor seguro de HOST."
            if tiene_import
            else
            (
                "No se encontró evidencia "
                "de delegación hacia HOST."
            )
        ),
        {
            "archivo":
                "services/bridge/"
                "ejecutor_controlado.py",

            "simbolo":
                "ejecutar_plan_datos",
        },
    )


# ============================================================
# POLÍTICA FALLBACK
# ============================================================


def _auditar_politica_fallback(
) -> list[dict[str, Any]]:

    resultados = []

    # --------------------------------------------------------
    # HOST REJECT
    # --------------------------------------------------------

    rechazo_host = (
        clasificar_fallo_bridge(
            {
                "ok":
                    False,

                "estado":
                    "no_ejecutado",

                "estado_bridge":
                    "rechazado_por_host",
            }
        )
    )

    resultados.append(
        _resultado(
            "fallback_bloqueado_host",
            (
                rechazo_host.get(
                    "fallback_elegible"
                )
                is False
                and
                rechazo_host.get(
                    "clasificacion"
                )
                == "rechazo_seguridad"
            ),
            (
                "Un rechazo HOST no puede "
                "activar fallback."
            ),
            rechazo_host,
        )
    )

    # --------------------------------------------------------
    # CONSULTA INCOMPLETA
    # --------------------------------------------------------

    incompleta = (
        clasificar_fallo_bridge(
            {
                "ok":
                    False,

                "estado":
                    "no_ejecutado",

                "estado_bridge":
                    "valor_libre_vacio",
            }
        )
    )

    resultados.append(
        _resultado(
            "fallback_bloqueado_incompleto",
            (
                incompleta.get(
                    "fallback_elegible"
                )
                is False
            ),
            (
                "Una consulta incompleta "
                "no puede activar fallback."
            ),
            incompleta,
        )
    )

    # --------------------------------------------------------
    # CAPACIDAD SEMÁNTICA INSUFICIENTE
    # --------------------------------------------------------

    no_resuelto = (
        clasificar_fallo_bridge(
            {
                "ok":
                    False,

                "estado":
                    "no_ejecutado",

                "estado_bridge":
                    "campo_no_resuelto",
            }
        )
    )

    resultados.append(
        _resultado(
            "fallback_semantico_elegible",
            (
                no_resuelto.get(
                    "fallback_elegible"
                )
                is True
                and
                no_resuelto.get(
                    "clasificacion"
                )
                ==
                "capacidad_semantica_insuficiente"
            ),
            (
                "Un fallo puramente semántico "
                "puede ser elegible para fallback."
            ),
            no_resuelto,
        )
    )

    return resultados


# ============================================================
# MÓDULOS / VERSIONES
# ============================================================


def _auditar_modulos(
) -> list[dict[str, Any]]:

    modulos = [
        (
            "sem_a_host",
            "ia_local.services.bridge."
            "sem_a_host",
        ),
        (
            "compositor_sem_host",
            "ia_local.services.bridge."
            "compositor_sem_host",
        ),
        (
            "campo_operador_valor",
            "ia_local.services.bridge."
            "campo_operador_valor",
        ),
        (
            "ejecutor_controlado",
            "ia_local.services.bridge."
            "ejecutor_controlado",
        ),
        (
            "respuesta_compacta",
            "ia_local.services.bridge."
            "respuesta_compacta",
        ),
        (
            "entrada_principal",
            "ia_local.services.bridge."
            "entrada_principal",
        ),
        (
            "orquestador_principal",
            "ia_local.services.bridge."
            "orquestador_principal",
        ),
        (
            "fallback_legado",
            "ia_local.services.bridge."
            "fallback_legado",
        ),
    ]

    resultados = []

    for nombre, ruta in modulos:

        try:

            modulo = importlib.import_module(
                ruta
            )

            version = getattr(
                modulo,
                "VERSION",
                None,
            )

            resultados.append(
                _resultado(
                    f"modulo_{nombre}",
                    True,
                    (
                        f"{ruta} importable."
                    ),
                    {
                        "version":
                            version,
                    },
                )
            )

        except Exception as exc:

            resultados.append(
                _resultado(
                    f"modulo_{nombre}",
                    False,
                    (
                        f"No se pudo importar "
                        f"{ruta}."
                    ),
                    {
                        "error":
                            str(
                                exc
                            ),
                    },
                )
            )

    return resultados


# ============================================================
# PRUEBA RUNTIME
# ============================================================


def _auditar_runtime(
    pregunta: str | None,
    *,
    limite: int,
) -> list[dict[str, Any]]:

    if not pregunta:

        return [
            _resultado(
                "runtime",
                True,
                (
                    "Prueba runtime omitida "
                    "porque no se proporcionó "
                    "una pregunta."
                ),
            )
        ]

    resultado = consultar_orquestado(
        pregunta,
        limite=limite,
        diagnostico=False,
        permitir_fallback_legado=False,
    )

    ok = (
        isinstance(
            resultado,
            dict,
        )
        and
        resultado.get(
            "ok"
        )
        is True
        and
        resultado.get(
            "ejecutado"
        )
        is True
        and
        resultado.get(
            "motor_usado"
        )
        == "bridge"
        and
        resultado.get(
            "fallback_usado"
        )
        is False
    )

    resultados = [
        _resultado(
            "runtime_consulta",
            ok,
            (
                "La consulta runtime fue "
                "resuelta por BRIDGE."
                if ok
                else
                (
                    "La consulta runtime no "
                    "cumplió el contrato esperado."
                )
            ),
            resultado,
        )
    ]

    if (
        ok
        and
        resultado.get(
            "tipo"
        )
        == "lista"
    ):

        total_devuelto = (
            resultado.get(
                "total_devuelto",
                0,
            )
        )

        resultados.append(
            _resultado(
                "runtime_limite",
                (
                    total_devuelto
                    <= limite
                ),
                (
                    "El límite solicitado "
                    "fue respetado."
                ),
                {
                    "limite":
                        limite,

                    "total_devuelto":
                        total_devuelto,
                },
            )
        )

    return resultados


# ============================================================
# AUDITORÍA GENERAL
# ============================================================


def auditar_cierre_bridge(
    *,
    pregunta_runtime: str | None = None,
    limite_runtime: int = 1,
) -> dict[str, Any]:

    pruebas: list[
        dict[str, Any]
    ] = []

    # --------------------------------------------------------
    # VERSIONES PRINCIPALES
    # --------------------------------------------------------

    pruebas.append(
        _resultado(
            "entrada_oficial",
            (
                VERSION_ENTRADA
                == "IA-BRIDGE008-v1"
            ),
            (
                "La entrada oficial BRIDGE008 "
                "está disponible."
            ),
            {
                "version":
                    VERSION_ENTRADA,
            },
        )
    )

    pruebas.append(
        _resultado(
            "orquestador_oficial",
            (
                VERSION_ORQUESTADOR
                == "IA-BRIDGE009-v1"
            ),
            (
                "El orquestador BRIDGE009 "
                "está disponible."
            ),
            {
                "version":
                    VERSION_ORQUESTADOR,
            },
        )
    )

    # --------------------------------------------------------
    # MÓDULOS
    # --------------------------------------------------------

    pruebas.extend(
        _auditar_modulos()
    )

    # --------------------------------------------------------
    # ORM DIRECTO
    # --------------------------------------------------------

    uso_objects = (
        _uso_objects_en_bridge()
    )

    pruebas.append(
        _resultado(
            "sin_orm_directo_bridge",
            not uso_objects,
            (
                "BRIDGE no contiene accesos "
                "directos mediante .objects."
                if not uso_objects
                else
                (
                    "Se encontraron accesos "
                    "ORM directos dentro de BRIDGE."
                )
            ),
            uso_objects,
        )
    )

    # --------------------------------------------------------
    # IMPORTS HOST
    # --------------------------------------------------------

    imports_host = (
        _imports_host_en_bridge()
    )

    pruebas.append(
        _resultado(
            "sin_imports_host_bridge",
            not imports_host,
            (
                "BRIDGE no importa directamente "
                "apps del proyecto anfitrión."
                if not imports_host
                else
                (
                    "BRIDGE contiene imports directos "
                    "hacia apps del host."
                )
            ),
            imports_host,
        )
    )

    # --------------------------------------------------------
    # DELEGACIÓN HOST
    # --------------------------------------------------------

    pruebas.append(
        _verificar_delegacion_host()
    )

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    pruebas.extend(
        _auditar_politica_fallback()
    )

    estado_fallback = (
        obtener_estado_fallback_legado()
    )

    pruebas.append(
        _resultado(
            "fallback_opcional",
            isinstance(
                estado_fallback,
                dict,
            ),
            (
                "El proveedor de fallback se "
                "resuelve de forma opcional y "
                "declarativa."
            ),
            {
                clave:
                    valor
                for clave, valor
                in estado_fallback.items()
                if clave != "callable"
            },
        )
    )

    # --------------------------------------------------------
    # RUNTIME
    # --------------------------------------------------------

    pruebas.extend(
        _auditar_runtime(
            pregunta_runtime,
            limite=limite_runtime,
        )
    )

    fallos = [
        prueba
        for prueba
        in pruebas
        if not prueba.get(
            "ok",
            False,
        )
    ]

    return {
        "ok":
            not fallos,

        "version":
            VERSION,

        "estado":
            (
                "cerrable"
                if not fallos
                else
                "con_fallos"
            ),

        "total_pruebas":
            len(
                pruebas
            ),

        "total_ok":
            len(
                pruebas
            )
            -
            len(
                fallos
            ),

        "total_fallos":
            len(
                fallos
            ),

        "apps_host":
            sorted(
                _apps_host()
            ),

        "pruebas":
            pruebas,

        "fallos":
            fallos,
    }