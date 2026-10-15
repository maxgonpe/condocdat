from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

from django.apps import apps
from django.conf import settings


# ============================================================
# UTILIDADES
# ============================================================


def _texto(
    valor: Any,
) -> str:
    return str(
        valor
        or ""
    ).strip()


def _base_dir() -> Path:
    return Path(
        settings.BASE_DIR
    ).resolve()


def _ruta_relativa(
    ruta: Path,
) -> str:

    try:
        return str(
            ruta.resolve().relative_to(
                _base_dir()
            )
        )

    except Exception:
        return str(
            ruta
        )


def _archivos_python_ia_local() -> list[Path]:

    raiz = (
        _base_dir()
        / "ia_local"
    )

    if not raiz.is_dir():
        return []

    resultado = []

    for ruta in raiz.rglob(
        "*.py"
    ):

        if "__pycache__" in ruta.parts:
            continue

        resultado.append(
            ruta
        )

    return sorted(
        resultado
    )


# ============================================================
# APPS DEL PROYECTO ANFITRIÓN
# ============================================================


def catalogar_apps_host() -> dict[str, Any]:
    """
    Identifica módulos raíz de las apps instaladas.

    No hardcodea nombres como rdi, documents, etc.
    """

    propias_host = []
    infraestructura = []
    ia_local = []

    for config in apps.get_app_configs():

        modulo = _texto(
            config.name
        )

        raiz_modulo = (
            modulo.split(
                "."
            )[0]
            if modulo
            else ""
        )

        item = {
            "label":
                config.label,

            "name":
                modulo,

            "raiz_modulo":
                raiz_modulo,

            "path":
                str(
                    Path(
                        config.path
                    ).resolve()
                ),
        }

        if (
            config.label == "ia_local"
            or modulo == "ia_local"
            or modulo.startswith(
                "ia_local."
            )
        ):

            ia_local.append(
                item
            )

            continue

        if (
            modulo.startswith(
                "django."
            )
            or config.label in {
                "admin",
                "auth",
                "contenttypes",
                "sessions",
                "messages",
                "staticfiles",
            }
        ):

            infraestructura.append(
                item
            )

            continue

        propias_host.append(
            item
        )

    raices_host = sorted(
        {
            item[
                "raiz_modulo"
            ]
            for item
            in propias_host
            if item[
                "raiz_modulo"
            ]
        }
    )

    return {
        "host":
            propias_host,

        "infraestructura":
            infraestructura,

        "ia_local":
            ia_local,

        "raices_host":
            raices_host,
    }


# ============================================================
# IMPORTS DIRECTOS AL HOST
# ============================================================


def _modulo_importado(
    nodo: ast.AST,
) -> list[dict[str, Any]]:

    resultado = []

    if isinstance(
        nodo,
        ast.Import,
    ):

        for alias in nodo.names:

            nombre = _texto(
                alias.name
            )

            if not nombre:
                continue

            resultado.append(
                {
                    "modulo":
                        nombre,

                    "simbolo":
                        None,

                    "alias":
                        alias.asname,
                }
            )

    elif isinstance(
        nodo,
        ast.ImportFrom,
    ):

        # Los imports relativos internos de ia_local no deben
        # interpretarse como dependencia del host.
        if (
            nodo.level
            and nodo.level > 0
        ):
            return []

        modulo = _texto(
            nodo.module
        )

        if not modulo:
            return []

        for alias in nodo.names:

            resultado.append(
                {
                    "modulo":
                        modulo,

                    "simbolo":
                        alias.name,

                    "alias":
                        alias.asname,
                }
            )

    return resultado


def detectar_imports_host() -> list[dict[str, Any]]:
    """
    Busca imports ESTÁTICOS desde ia_local hacia apps propias
    del proyecto anfitrión.

    Ejemplo detectable:

        from rdi.models import PlanosRecord

    No considera descubrimiento dinámico mediante Django apps.
    """

    catalogo_apps = (
        catalogar_apps_host()
    )

    raices_host = set(
        catalogo_apps[
            "raices_host"
        ]
    )

    resultado = []

    for archivo in _archivos_python_ia_local():

        try:

            contenido = archivo.read_text(
                encoding="utf-8",
                errors="replace",
            )

            arbol = ast.parse(
                contenido,
                filename=str(
                    archivo
                ),
            )

        except Exception as exc:

            resultado.append(
                {
                    "tipo":
                        "error_ast",

                    "archivo":
                        _ruta_relativa(
                            archivo
                        ),

                    "linea":
                        None,

                    "modulo":
                        None,

                    "simbolo":
                        None,

                    "error":
                        str(
                            exc
                        ),
                }
            )

            continue

        for nodo in ast.walk(
            arbol
        ):

            for importado in _modulo_importado(
                nodo
            ):

                modulo = importado[
                    "modulo"
                ]

                raiz = modulo.split(
                    "."
                )[0]

                if raiz not in raices_host:
                    continue

                resultado.append(
                    {
                        "tipo":
                            "import_host",

                        "archivo":
                            _ruta_relativa(
                                archivo
                            ),

                        "linea":
                            getattr(
                                nodo,
                                "lineno",
                                None,
                            ),

                        "modulo":
                            modulo,

                        "simbolo":
                            importado[
                                "simbolo"
                            ],

                        "alias":
                            importado[
                                "alias"
                            ],

                        "app_raiz":
                            raiz,
                    }
                )

    resultado.sort(
        key=lambda item: (
            item.get(
                "archivo"
            )
            or "",
            item.get(
                "linea"
            )
            or -1,
        )
    )

    return resultado


# ============================================================
# TEMPLATES USADOS DESDE IA_LOCAL
# ============================================================


FUNCIONES_TEMPLATE = {
    "render",
    "render_to_string",
    "get_template",
    "select_template",
}


def _nombre_llamada(
    nodo: ast.Call,
) -> str:

    funcion = nodo.func

    if isinstance(
        funcion,
        ast.Name,
    ):
        return funcion.id

    if isinstance(
        funcion,
        ast.Attribute,
    ):
        return funcion.attr

    return ""


def _extraer_template_literal(
    nodo: ast.Call,
    funcion: str,
) -> str | None:
    """
    Detecta templates literales en llamadas conocidas.

    render(request, "template.html", ...)
    render_to_string("template.html", ...)
    get_template("template.html")
    """

    indice = 0

    if funcion == "render":
        indice = 1

    if len(
        nodo.args
    ) <= indice:
        return None

    argumento = nodo.args[
        indice
    ]

    if isinstance(
        argumento,
        ast.Constant,
    ) and isinstance(
        argumento.value,
        str,
    ):

        return argumento.value

    return None


def _resolver_template(
    nombre: str,
) -> dict[str, Any]:

    base = _base_dir()

    candidatos = []

    # Template autocontenido esperado.
    candidatos.append(
        (
            "ia_local",
            base
            / "ia_local"
            / "templates"
            / nombre,
        )
    )

    # Directorio global habitual.
    candidatos.append(
        (
            "proyecto",
            base
            / "templates"
            / nombre,
        )
    )

    # Templates de otras apps instaladas.
    for config in apps.get_app_configs():

        candidatos.append(
            (
                (
                    "ia_local"
                    if config.label
                    == "ia_local"
                    else "otra_app"
                ),
                Path(
                    config.path
                )
                / "templates"
                / nombre,
            )
        )

    encontrados = []

    vistos = set()

    for origen, ruta in candidatos:

        clave = str(
            ruta.resolve()
        )

        if clave in vistos:
            continue

        vistos.add(
            clave
        )

        if not ruta.is_file():
            continue

        encontrados.append(
            {
                "origen":
                    origen,

                "ruta":
                    _ruta_relativa(
                        ruta
                    ),
            }
        )

    autocontenido = any(
        item[
            "origen"
        ] == "ia_local"
        for item
        in encontrados
    )

    return {
        "template":
            nombre,

        "encontrados":
            encontrados,

        "autocontenido":
            autocontenido,
    }


def detectar_templates_externos() -> list[dict[str, Any]]:

    resultado = []

    for archivo in _archivos_python_ia_local():

        try:

            contenido = archivo.read_text(
                encoding="utf-8",
                errors="replace",
            )

            arbol = ast.parse(
                contenido,
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
                ast.Call,
            ):
                continue

            funcion = _nombre_llamada(
                nodo
            )

            if funcion not in FUNCIONES_TEMPLATE:
                continue

            nombre = _extraer_template_literal(
                nodo,
                funcion,
            )

            if not nombre:
                continue

            resolucion = (
                _resolver_template(
                    nombre
                )
            )

            resultado.append(
                {
                    "archivo":
                        _ruta_relativa(
                            archivo
                        ),

                    "linea":
                        getattr(
                            nodo,
                            "lineno",
                            None,
                        ),

                    "funcion":
                        funcion,

                    "template":
                        nombre,

                    "autocontenido":
                        resolucion[
                            "autocontenido"
                        ],

                    "encontrados":
                        resolucion[
                            "encontrados"
                        ],
                }
            )

    resultado.sort(
        key=lambda item: (
            item[
                "archivo"
            ],
            item[
                "linea"
            ]
            or -1,
        )
    )

    return resultado


# ============================================================
# CONFIGURACIÓN PORTABLE
# ============================================================


def auditar_configuracion() -> dict[str, Any]:

    return {
        "ollama_url":
            getattr(
                settings,
                "IA_LOCAL_OLLAMA_URL",
                None,
            ),

        "ollama_model":
            getattr(
                settings,
                "IA_LOCAL_OLLAMA_MODEL",
                None,
            ),

        "ollama_timeout":
            getattr(
                settings,
                "IA_LOCAL_OLLAMA_TIMEOUT",
                None,
            ),

        "root_urlconf":
            getattr(
                settings,
                "ROOT_URLCONF",
                None,
            ),

        "ia_local_instalada":
            apps.is_installed(
                "ia_local"
            ),
    }


# ============================================================
# INFORME GENERAL
# ============================================================


def auditar_portabilidad() -> dict[str, Any]:

    apps_host = (
        catalogar_apps_host()
    )

    imports_host = (
        detectar_imports_host()
    )

    templates = (
        detectar_templates_externos()
    )

    templates_no_autocontenidos = [
        item
        for item
        in templates
        if not item[
            "autocontenido"
        ]
    ]

    errores_ast = [
        item
        for item
        in imports_host
        if item.get(
            "tipo"
        ) == "error_ast"
    ]

    imports_reales = [
        item
        for item
        in imports_host
        if item.get(
            "tipo"
        ) == "import_host"
    ]

    return {
        "apps_host":
            apps_host,

        "imports_host":
            imports_reales,

        "templates_usados":
            templates,

        "templates_no_autocontenidos":
            templates_no_autocontenidos,

        "errores_ast":
            errores_ast,

        "configuracion":
            auditar_configuracion(),

        "resumen": {
            "apps_host":
                len(
                    apps_host[
                        "host"
                    ]
                ),

            "imports_host":
                len(
                    imports_reales
                ),

            "templates_usados":
                len(
                    templates
                ),

            "templates_no_autocontenidos":
                len(
                    templates_no_autocontenidos
                ),

            "errores_ast":
                len(
                    errores_ast
                ),
        },
    }