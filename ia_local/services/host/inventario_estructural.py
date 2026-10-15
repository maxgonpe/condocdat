from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from .inspector_llamadas import construir_indice_simbolos
from .inspector_proyecto import (
    obtener_apps_instaladas,
    obtener_archivos_python,
    obtener_modelos_proyecto,
    obtener_templates,
    obtener_urls_proyecto,
)


# ============================================================
# IA-HOST018 / IA-HOST019
# INVENTARIO ESTRUCTURAL GLOBAL Y CON ALCANCE
# ============================================================

RECURSOS = {
    "apps": ("app", "apps", "aplicacion", "aplicaciones"),
    "modelos": ("modelo", "modelos"),
    "urls": ("url", "urls", "ruta", "rutas"),
    "views": ("view", "views", "vista", "vistas"),
    "funciones": ("funcion", "funciones"),
    "templates": ("template", "templates", "plantilla", "plantillas"),
}

MARCADORES_ALCANCE_GLOBAL = (
    "proyecto",
    "django",
    "sistema",
    "codigo",
    "codigo fuente",
)

MARCADORES_CANTIDAD_GLOBAL = (
    "todos",
    "todas",
    "completo",
    "completa",
    "completos",
    "completas",
)


# ============================================================
# UTILIDADES
# ============================================================

def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _normalizar(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", _texto(valor))
    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )
    texto = texto.lower()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def _contiene_palabra(
    texto: str,
    palabra: str,
) -> bool:
    patron = (
        r"(?<![\w])"
        + re.escape(
            _normalizar(palabra)
        )
        + r"(?![\w])"
    )

    return bool(
        re.search(
            patron,
            _normalizar(texto),
        )
    )


def _esta_dentro(
    ruta: str,
    directorio: str,
) -> bool:
    try:
        (
            Path(ruta)
            .resolve()
            .relative_to(
                Path(directorio).resolve()
            )
        )
        return True
    except (
        OSError,
        RuntimeError,
        ValueError,
    ):
        return False


def _normalizar_ruta_relativa(
    valor: Any,
) -> str:
    texto = (
        _texto(valor)
        .replace("\\", "/")
    )

    while texto.startswith("./"):
        texto = texto[2:]

    return texto.strip("/")


# ============================================================
# APPS HOST
# ============================================================

def _apps_host() -> list[dict[str, Any]]:
    """
    Devuelve únicamente las apps del proyecto anfitrión.

    Excluye:
    - django.contrib
    - ia_local

    La clasificación ya la realiza inspector_proyecto.py.
    """

    return [
        item
        for item in obtener_apps_instaladas()
        if item.get("tipo") == "proyecto"
    ]


def _labels_apps_host() -> set[str]:
    return {
        _texto(
            item.get("label")
        )
        for item
        in _apps_host()
        if _texto(
            item.get("label")
        )
    }


def _paths_apps_host() -> list[str]:
    return [
        _texto(
            item.get("path")
        )
        for item
        in _apps_host()
        if _texto(
            item.get("path")
        )
    ]


def _path_ia_local() -> str:
    for item in obtener_apps_instaladas():
        if item.get("tipo") == "ia_local":
            return _texto(
                item.get("path")
            )

    return ""


def _resolver_app_mencionada(
    pregunta: str,
) -> dict[str, Any] | None:
    """
    Resuelve una app mencionada únicamente contra las apps
    reales del proyecto anfitrión.

    No contiene nombres de apps particulares.
    """

    texto = _normalizar(
        pregunta
    )

    if not texto:
        return None

    candidatos = []

    for app in _apps_host():

        valores = {
            _normalizar(
                app.get("label")
            ),
            _normalizar(
                app.get("name")
            ),
        }

        nombre = _normalizar(
            app.get("name")
        )

        if "." in nombre:
            valores.add(
                nombre.split(".")[-1]
            )

        valores = {
            item
            for item
            in valores
            if len(item) >= 2
        }

        if any(
            _contiene_palabra(
                texto,
                valor,
            )
            for valor
            in valores
        ):
            candidatos.append(
                app
            )

    if len(
        candidatos
    ) != 1:
        return None

    return candidatos[0]


# ============================================================
# ARCHIVOS HOST
# ============================================================

def _archivos_python_host() -> list[dict[str, Any]]:
    paths_host = (
        _paths_apps_host()
    )

    resultado = []

    for item in obtener_archivos_python():

        ruta = _texto(
            item.get("ruta")
        )

        if not ruta:
            continue

        if not any(
            _esta_dentro(
                ruta,
                app_path,
            )
            for app_path
            in paths_host
        ):
            continue

        resultado.append(
            item
        )

    resultado.sort(
        key=lambda item: (
            _normalizar_ruta_relativa(
                item.get("archivo")
            )
            .lower()
        )
    )

    return resultado


def _extraer_referencia_archivo_python(
    pregunta: str,
) -> str | None:
    texto = _normalizar(
        pregunta
    )

    if not texto:
        return None

    coincidencias = re.findall(
        r"(?<![\w])"
        r"([a-z0-9_./\\-]+\.py)"
        r"(?![\w])",
        texto,
    )

    if not coincidencias:
        return None

    referencias = []

    for item in coincidencias:

        normalizada = (
            _normalizar_ruta_relativa(
                item
            )
        )

        if (
            normalizada
            and normalizada
            not in referencias
        ):
            referencias.append(
                normalizada
            )

    if len(
        referencias
    ) != 1:
        return None

    return referencias[0]


def _resolver_archivo_python_mencionado(
    pregunta: str,
) -> dict[str, Any] | None:
    """
    Resuelve una referencia de archivo .py contra el inventario
    físico real del host.

    Admite:
        documents/views.py
        rdi/services.py

    También admite un sufijo único. Si la referencia resulta
    ambigua, no se resuelve.
    """

    referencia = (
        _extraer_referencia_archivo_python(
            pregunta
        )
    )

    if not referencia:
        return None

    archivos = (
        _archivos_python_host()
    )

    exactos = []

    for item in archivos:

        relativo = (
            _normalizar_ruta_relativa(
                item.get("archivo")
            )
            .lower()
        )

        if relativo == referencia:
            exactos.append(
                item
            )

    if len(
        exactos
    ) == 1:
        return exactos[0]

    candidatos = []

    sufijo = (
        f"/{referencia}"
    )

    for item in archivos:

        relativo = (
            _normalizar_ruta_relativa(
                item.get("archivo")
            )
            .lower()
        )

        if (
            relativo == referencia
            or relativo.endswith(
                sufijo
            )
        ):
            candidatos.append(
                item
            )

    if len(
        candidatos
    ) != 1:
        return None

    return candidatos[0]


# ============================================================
# DETECCIÓN DE RECURSO
# ============================================================

def _detectar_recurso(
    pregunta: str,
) -> str | None:
    """
    Detecta el recurso estructural solicitado sin confundir
    referencias técnicas con la intención de la pregunta.

    IA-HOST019-C02 protege dos tipos de objetivos:

        documents/views.py
        transmital.views.transmital_create

    En ambos casos, las palabras internas como "views", "models"
    o "urls" pertenecen al OBJETIVO técnico y no deben decidir
    por sí solas el recurso solicitado.
    """

    texto = _normalizar(
        pregunta
    )

    if not texto:
        return None

    # --------------------------------------------------------
    # 1. ENMASCARAR ARCHIVOS PYTHON
    #
    # Ejemplo:
    #   documents/views.py
    #
    # "views" no debe convertirse en recurso.
    # --------------------------------------------------------

    texto_recurso = re.sub(
        r"(?<![\w])"
        r"[a-z0-9_./\\-]+\.py"
        r"(?![\w])",
        " ",
        texto,
    )

    # --------------------------------------------------------
    # 2. ENMASCARAR QUALNAMES / REFERENCIAS DOTTED
    #
    # Ejemplos:
    #   transmital.views.transmital_create
    #   documents.views.document_list
    #   documents.Document
    #
    # La referencia completa representa el OBJETIVO.
    # Sus componentes internos no participan en la detección
    # del recurso.
    #
    # Así:
    #
    #   ¿Cómo funciona transmital.views.transmital_create?
    #
    # no se interpreta como:
    #
    #   listar views de la app transmital
    #
    # y puede continuar hacia HOST021.
    # --------------------------------------------------------

    texto_recurso = re.sub(
        r"(?<![\w])"
        r"[a-z_][a-z0-9_]*"
        r"(?:\.[a-z_][a-z0-9_]*)+"
        r"(?![\w])",
        " ",
        texto_recurso,
    )

    texto_recurso = re.sub(
        r"\s+",
        " ",
        texto_recurso,
    ).strip()

    for (
        nombre_recurso,
        aliases,
    ) in RECURSOS.items():

        if any(
            _contiene_palabra(
                texto_recurso,
                alias,
            )
            for alias
            in aliases
        ):
            return nombre_recurso

    return None


# ============================================================
# DETECCIÓN DE CONSULTA DE INVENTARIO
# ============================================================

def detectar_consulta_inventario(
    pregunta: str,
) -> dict[str, Any] | None:
    """
    Detecta inventarios estructurales:

    HOST018:
        alcance global del proyecto.

    HOST019:
        alcance de app.
        alcance de archivo Python.

    Ejemplos:
        ¿Qué modelos Django existen en este proyecto?
        ¿Qué modelos tiene documents?
        ¿Qué URLs tiene rdi?
        ¿Qué funciones existen en documents/views.py?

    Toda app y archivo se valida contra el host real.
    No utiliza LLM.
    """

    texto = _normalizar(
        pregunta
    )

    if not texto:
        return None

    recurso = _detectar_recurso(
        pregunta
    )

    if not recurso:
        return None

    # ========================================================
    # 1. ALCANCE DE ARCHIVO
    # ========================================================

    archivo = (
        _resolver_archivo_python_mencionado(
            pregunta
        )
    )

    if archivo:

        # HOST019 comienza con funciones por archivo.
        # Otros recursos requieren evidencia estructural adicional
        # y se incorporarán en specs posteriores.
        if recurso != "funciones":
            return None

        objetivo = (
            _normalizar_ruta_relativa(
                archivo.get(
                    "archivo"
                )
            )
        )

        return {
            "tipo":
                "estructura",

            "subtipo":
                "inventario",

            "accion":
                "listar",

            "recurso":
                recurso,

            "alcance":
                "archivo",

            "objetivo":
                objetivo,

            "validado":
                True,

            "origen":
                "determinista",

            "confianza":
                "alta",
        }

    # ========================================================
    # 2. ALCANCE DE APP
    # ========================================================

    app = (
        _resolver_app_mencionada(
            pregunta
        )
    )

    if app:

        if recurso == "apps":
            return None

        return {
            "tipo":
                "estructura",

            "subtipo":
                "inventario",

            "accion":
                "listar",

            "recurso":
                recurso,

            "alcance":
                "app",

            "objetivo":
                _texto(
                    app.get(
                        "label"
                    )
                ),

            "objetivo_nombre":
                _texto(
                    app.get(
                        "name"
                    )
                ),

            "validado":
                True,

            "origen":
                "determinista",

            "confianza":
                "alta",
        }

    # ========================================================
    # 3. ALCANCE GLOBAL HOST018
    # ========================================================

    tiene_alcance_global = any(
        marcador in texto
        for marcador
        in MARCADORES_ALCANCE_GLOBAL
    )

    tiene_cantidad_global = any(
        _contiene_palabra(
            texto,
            marcador,
        )
        for marcador
        in MARCADORES_CANTIDAD_GLOBAL
    )

    tiene_forma_existencial = bool(
        re.search(
            r"\b(que|cuales)\b"
            r".*\b(existen|hay|registrad[oa]s?)\b",
            texto,
        )
    )

    if not (
        tiene_alcance_global
        or tiene_cantidad_global
        or tiene_forma_existencial
    ):
        return None

    return {
        "tipo":
            "estructura",

        "subtipo":
            "inventario",

        "accion":
            "listar",

        "recurso":
            recurso,

        "alcance":
            "proyecto",

        "validado":
            True,

        "origen":
            "determinista",

        "confianza":
            "alta",
    }


# ============================================================
# RESOLUCIÓN DEFENSIVA DE OBJETIVOS
# ============================================================

def _resolver_app_por_objetivo(
    objetivo: Any,
) -> dict[str, Any] | None:

    objetivo_normalizado = _normalizar(
        objetivo
    )

    if not objetivo_normalizado:
        return None

    candidatos = []

    for app in _apps_host():

        valores = {
            _normalizar(
                app.get("label")
            ),
            _normalizar(
                app.get("name")
            ),
        }

        nombre = _normalizar(
            app.get("name")
        )

        if "." in nombre:
            valores.add(
                nombre.split(".")[-1]
            )

        if objetivo_normalizado in valores:
            candidatos.append(
                app
            )

    if len(
        candidatos
    ) != 1:
        return None

    return candidatos[0]


def _resolver_archivo_por_objetivo(
    objetivo: Any,
) -> dict[str, Any] | None:

    objetivo_normalizado = (
        _normalizar_ruta_relativa(
            objetivo
        )
        .lower()
    )

    if not objetivo_normalizado:
        return None

    candidatos = []

    for item in _archivos_python_host():

        relativo = (
            _normalizar_ruta_relativa(
                item.get("archivo")
            )
            .lower()
        )

        if relativo == objetivo_normalizado:
            candidatos.append(
                item
            )

    if len(
        candidatos
    ) != 1:
        return None

    return candidatos[0]


# ============================================================
# INVENTARIOS
# ============================================================

def _inventario_apps() -> list[dict[str, Any]]:
    resultado = []

    for item in _apps_host():
        resultado.append(
            {
                "label":
                    item.get(
                        "label"
                    ),

                "name":
                    item.get(
                        "name"
                    ),

                "verbose_name":
                    item.get(
                        "verbose_name"
                    ),

                "path":
                    item.get(
                        "path"
                    ),

                "modelos":
                    item.get(
                        "modelos"
                    ),

                "tipo":
                    item.get(
                        "tipo"
                    ),
            }
        )

    resultado.sort(
        key=lambda item: (
            _texto(
                item.get(
                    "label"
                )
            )
            .lower()
        )
    )

    return resultado


def _inventario_modelos(
    app: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:

    labels_host = (
        _labels_apps_host()
    )

    app_label_objetivo = (
        _texto(
            app.get(
                "label"
            )
        )
        if app
        else ""
    )

    resultado = []

    for item in obtener_modelos_proyecto():

        app_label = _texto(
            item.get(
                "app_label"
            )
        )

        if app_label not in labels_host:
            continue

        if (
            app_label_objetivo
            and app_label
            != app_label_objetivo
        ):
            continue

        resultado.append(
            {
                "label":
                    item.get(
                        "label"
                    ),

                "app_label":
                    item.get(
                        "app_label"
                    ),

                "modelo":
                    item.get(
                        "modelo"
                    ),

                "tabla":
                    item.get(
                        "tabla"
                    ),

                "verbose_name":
                    item.get(
                        "verbose_name"
                    ),

                "verbose_name_plural":
                    item.get(
                        "verbose_name_plural"
                    ),

                "campos":
                    item.get(
                        "campos"
                    ),
            }
        )

    resultado.sort(
        key=lambda item: (
            _texto(
                item.get(
                    "label"
                )
            )
            .lower()
        )
    )

    return resultado


def _view_pertenece_app(
    view: str,
    app: dict[str, Any],
) -> bool:

    view = _texto(
        view
    )

    if not view:
        return False

    valores = {
        _texto(
            app.get(
                "name"
            )
        ),
        _texto(
            app.get(
                "label"
            )
        ),
    }

    for valor in valores:

        if not valor:
            continue

        if (
            view == valor
            or view.startswith(
                f"{valor}."
            )
        ):
            return True

    return False


def _view_pertenece_host(
    view: str,
) -> bool:

    for app in _apps_host():

        if _view_pertenece_app(
            view,
            app,
        ):
            return True

    return False


def _inventario_urls(
    app: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:

    resultado = []

    for item in obtener_urls_proyecto():

        if item.get(
            "error"
        ):
            continue

        view = _texto(
            item.get(
                "view"
            )
        )

        if app:

            if not _view_pertenece_app(
                view,
                app,
            ):
                continue

        elif not _view_pertenece_host(
            view
        ):
            continue

        resultado.append(
            {
                "ruta":
                    item.get(
                        "ruta"
                    ),

                "name":
                    item.get(
                        "name"
                    ),

                "namespace":
                    item.get(
                        "namespace"
                    ),

                "view":
                    view,
            }
        )

    resultado.sort(
        key=lambda item: (
            _texto(
                item.get(
                    "ruta"
                )
            ),
            _texto(
                item.get(
                    "view"
                )
            ),
        )
    )

    return resultado


def _inventario_views(
    app: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:

    agrupadas: dict[
        str,
        dict[str, Any],
    ] = {}

    for item in _inventario_urls(
        app=app
    ):

        view = _texto(
            item.get(
                "view"
            )
        )

        if not view:
            continue

        if view not in agrupadas:

            agrupadas[
                view
            ] = {
                "view":
                    view,

                "urls":
                    [],
            }

        agrupadas[
            view
        ][
            "urls"
        ].append(
            {
                "ruta":
                    item.get(
                        "ruta"
                    ),

                "name":
                    item.get(
                        "name"
                    ),

                "namespace":
                    item.get(
                        "namespace"
                    ),
            }
        )

    resultado = list(
        agrupadas.values()
    )

    resultado.sort(
        key=lambda item: (
            _texto(
                item.get(
                    "view"
                )
            )
            .lower()
        )
    )

    return resultado


def _simbolo_pertenece_app(
    item: dict[str, Any],
    app: dict[str, Any],
) -> bool:

    ruta = _texto(
        item.get(
            "ruta"
        )
    )

    app_path = _texto(
        app.get(
            "path"
        )
    )

    if not (
        ruta
        and app_path
    ):
        return False

    return _esta_dentro(
        ruta,
        app_path,
    )


def _inventario_funciones(
    app: dict[str, Any] | None = None,
    archivo: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:

    paths_host = (
        _paths_apps_host()
    )

    archivo_objetivo = (
        _normalizar_ruta_relativa(
            archivo.get(
                "archivo"
            )
        )
        if archivo
        else ""
    )

    indice = (
        construir_indice_simbolos()
    )

    resultado = []

    for item in indice.get(
        "simbolos",
        [],
    ):

        if item.get(
            "tipo"
        ) not in {
            "funcion",
            "funcion_async",
        }:
            continue

        ruta = _texto(
            item.get(
                "ruta"
            )
        )

        if not any(
            _esta_dentro(
                ruta,
                app_path,
            )
            for app_path
            in paths_host
        ):
            continue

        if (
            app
            and not _simbolo_pertenece_app(
                item,
                app,
            )
        ):
            continue

        if archivo_objetivo:

            relativo = (
                _normalizar_ruta_relativa(
                    item.get(
                        "archivo"
                    )
                )
            )

            if relativo != archivo_objetivo:
                continue

        resultado.append(
            {
                "nombre":
                    item.get(
                        "nombre"
                    ),

                "qualname":
                    item.get(
                        "qualname"
                    ),

                "modulo":
                    item.get(
                        "modulo"
                    ),

                "archivo":
                    item.get(
                        "archivo"
                    ),

                "tipo":
                    item.get(
                        "tipo"
                    ),

                "linea_inicio":
                    item.get(
                        "linea_inicio"
                    ),

                "linea_fin":
                    item.get(
                        "linea_fin"
                    ),
            }
        )

    resultado.sort(
        key=lambda item: (
            _texto(
                item.get(
                    "qualname"
                )
            )
            .lower()
        )
    )

    return resultado


def _template_pertenece_app(
    item: dict[str, Any],
    app: dict[str, Any],
) -> bool:
    """
    Acepta dos formas demostrables:

    1. template físicamente dentro de la app;
    2. convención Django:
       templates/<app_label>/...
       o templates/<app_name>/...
    """

    ruta = _texto(
        item.get(
            "ruta"
        )
    )

    app_path = _texto(
        app.get(
            "path"
        )
    )

    if (
        ruta
        and app_path
        and _esta_dentro(
            ruta,
            app_path,
        )
    ):
        return True

    archivo = (
        _normalizar_ruta_relativa(
            item.get(
                "archivo"
            )
        )
    )

    partes = [
        parte
        for parte
        in archivo.split("/")
        if parte
    ]

    if "templates" not in partes:
        return False

    indice_templates = (
        partes.index(
            "templates"
        )
    )

    despues = partes[
        indice_templates + 1:
    ]

    if not despues:
        return False

    candidatos = {
        _normalizar(
            app.get(
                "label"
            )
        ),
        _normalizar(
            app.get(
                "name"
            )
        ).split(".")[-1],
    }

    return (
        _normalizar(
            despues[0]
        )
        in candidatos
    )


def _inventario_templates(
    app: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:

    ia_local_path = (
        _path_ia_local()
    )

    resultado = []

    for item in obtener_templates():

        ruta = _texto(
            item.get(
                "ruta"
            )
        )

        if (
            ia_local_path
            and _esta_dentro(
                ruta,
                ia_local_path,
            )
        ):
            continue

        if (
            app
            and not _template_pertenece_app(
                item,
                app,
            )
        ):
            continue

        resultado.append(
            {
                "archivo":
                    item.get(
                        "archivo"
                    ),

                "ruta":
                    ruta,

                "bytes":
                    item.get(
                        "bytes"
                    ),
            }
        )

    resultado.sort(
        key=lambda item: (
            _texto(
                item.get(
                    "archivo"
                )
            )
            .lower()
        )
    )

    return resultado


# ============================================================
# RESPUESTAS DETERMINISTAS
# ============================================================

def _descripcion_alcance(
    alcance: str,
    objetivo: str | None,
) -> str:

    if (
        alcance == "app"
        and objetivo
    ):
        return (
            f"en la aplicación {objetivo}"
        )

    if (
        alcance == "archivo"
        and objetivo
    ):
        return (
            f"en el archivo {objetivo}"
        )

    return (
        "en el proyecto anfitrión"
    )


def _respuesta_apps(
    resultados: list[dict[str, Any]],
) -> str:

    lineas = [
        (
            f"Se encontraron {len(resultados)} "
            "aplicaciones del proyecto anfitrión:"
        )
    ]

    for item in resultados:

        linea = (
            f"- {item.get('label')}"
        )

        verbose_name = _texto(
            item.get(
                "verbose_name"
            )
        )

        if verbose_name:
            linea += (
                f" ({verbose_name})"
            )

        lineas.append(
            linea
        )

    return "\n".join(
        lineas
    )


def _respuesta_modelos(
    resultados: list[dict[str, Any]],
    *,
    alcance: str,
    objetivo: str | None,
) -> str:

    descripcion = (
        _descripcion_alcance(
            alcance,
            objetivo,
        )
    )

    lineas = [
        (
            f"Se encontraron {len(resultados)} "
            f"modelos Django {descripcion}:"
        )
    ]

    for item in resultados:

        lineas.append(
            (
                f"- {item.get('label')} "
                f"[tabla: {item.get('tabla')}]"
            )
        )

    return "\n".join(
        lineas
    )


def _respuesta_urls(
    resultados: list[dict[str, Any]],
    *,
    alcance: str,
    objetivo: str | None,
) -> str:

    descripcion = (
        _descripcion_alcance(
            alcance,
            objetivo,
        )
    )

    lineas = [
        (
            f"Se encontraron {len(resultados)} "
            f"URLs {descripcion}:"
        )
    ]

    for item in resultados:

        lineas.append(
            (
                f"- {item.get('ruta')} "
                f"→ {item.get('view')}"
            )
        )

    return "\n".join(
        lineas
    )


def _respuesta_views(
    resultados: list[dict[str, Any]],
    *,
    alcance: str,
    objetivo: str | None,
) -> str:

    descripcion = (
        _descripcion_alcance(
            alcance,
            objetivo,
        )
    )

    lineas = [
        (
            f"Se encontraron {len(resultados)} "
            f"views {descripcion}:"
        )
    ]

    for item in resultados:

        lineas.append(
            f"- {item.get('view')}"
        )

    return "\n".join(
        lineas
    )


def _respuesta_funciones(
    resultados: list[dict[str, Any]],
    *,
    alcance: str,
    objetivo: str | None,
) -> str:

    descripcion = (
        _descripcion_alcance(
            alcance,
            objetivo,
        )
    )

    lineas = [
        (
            f"Se encontraron {len(resultados)} "
            "funciones Python de nivel superior "
            f"{descripcion}:"
        )
    ]

    for item in resultados:

        lineas.append(
            (
                f"- {item.get('qualname')} "
                f"[{item.get('archivo')}:"
                f"{item.get('linea_inicio')}]"
            )
        )

    return "\n".join(
        lineas
    )


def _respuesta_templates(
    resultados: list[dict[str, Any]],
    *,
    alcance: str,
    objetivo: str | None,
) -> str:

    descripcion = (
        _descripcion_alcance(
            alcance,
            objetivo,
        )
    )

    lineas = [
        (
            f"Se encontraron {len(resultados)} "
            f"templates {descripcion}:"
        )
    ]

    for item in resultados:

        lineas.append(
            f"- {item.get('archivo')}"
        )

    return "\n".join(
        lineas
    )


# ============================================================
# EJECUCIÓN PÚBLICA
# ============================================================

def ejecutar_consulta_inventario(
    pregunta: str,
    plan: dict[str, Any],
) -> dict[str, Any]:
    """
    Ejecuta inventarios estructurales HOST018/HOST019.

    Los hechos provienen exclusivamente de los inspectores HOST.
    Qwen no participa.
    """

    recurso = _texto(
        plan.get(
            "recurso"
        )
    )

    alcance = _texto(
        plan.get(
            "alcance"
        )
    )

    objetivo = (
        _texto(
            plan.get(
                "objetivo"
            )
        )
        or None
    )

    app = None
    archivo = None

    # ========================================================
    # VALIDACIÓN DEFENSIVA DEL ALCANCE
    # ========================================================

    if alcance == "app":

        app = (
            _resolver_app_por_objetivo(
                objetivo
            )
        )

        if not app:

            return {
                "ok":
                    False,

                "pregunta":
                    pregunta,

                "respondido_por":
                    "host",

                "llm_invocado":
                    False,

                "error": (
                    "La aplicación solicitada no pudo "
                    "validarse contra el proyecto anfitrión."
                ),
            }

        objetivo = _texto(
            app.get(
                "label"
            )
        )

    elif alcance == "archivo":

        archivo = (
            _resolver_archivo_por_objetivo(
                objetivo
            )
        )

        if not archivo:

            return {
                "ok":
                    False,

                "pregunta":
                    pregunta,

                "respondido_por":
                    "host",

                "llm_invocado":
                    False,

                "error": (
                    "El archivo solicitado no pudo "
                    "validarse contra el proyecto anfitrión."
                ),
            }

        objetivo = (
            _normalizar_ruta_relativa(
                archivo.get(
                    "archivo"
                )
            )
        )

    elif alcance != "proyecto":

        return {
            "ok":
                False,

            "pregunta":
                pregunta,

            "respondido_por":
                "host",

            "llm_invocado":
                False,

            "error": (
                "El alcance estructural solicitado "
                "no está soportado."
            ),
        }

    # ========================================================
    # EJECUCIÓN
    # ========================================================

    if recurso == "apps":

        if alcance != "proyecto":

            return {
                "ok":
                    False,

                "pregunta":
                    pregunta,

                "respondido_por":
                    "host",

                "llm_invocado":
                    False,

                "error": (
                    "El inventario de aplicaciones "
                    "sólo admite alcance de proyecto."
                ),
            }

        resultados = (
            _inventario_apps()
        )

        respuesta = (
            _respuesta_apps(
                resultados
            )
        )

    elif recurso == "modelos":

        if alcance == "archivo":

            return {
                "ok":
                    False,

                "pregunta":
                    pregunta,

                "respondido_por":
                    "host",

                "llm_invocado":
                    False,

                "error": (
                    "HOST019 no resuelve todavía "
                    "modelos por archivo."
                ),
            }

        resultados = (
            _inventario_modelos(
                app=app
            )
        )

        respuesta = (
            _respuesta_modelos(
                resultados,
                alcance=alcance,
                objetivo=objetivo,
            )
        )

    elif recurso == "urls":

        if alcance == "archivo":

            return {
                "ok":
                    False,

                "pregunta":
                    pregunta,

                "respondido_por":
                    "host",

                "llm_invocado":
                    False,

                "error": (
                    "HOST019 no resuelve todavía "
                    "URLs por archivo."
                ),
            }

        resultados = (
            _inventario_urls(
                app=app
            )
        )

        respuesta = (
            _respuesta_urls(
                resultados,
                alcance=alcance,
                objetivo=objetivo,
            )
        )

    elif recurso == "views":

        if alcance == "archivo":

            return {
                "ok":
                    False,

                "pregunta":
                    pregunta,

                "respondido_por":
                    "host",

                "llm_invocado":
                    False,

                "error": (
                    "HOST019 no resuelve todavía "
                    "views por archivo."
                ),
            }

        resultados = (
            _inventario_views(
                app=app
            )
        )

        respuesta = (
            _respuesta_views(
                resultados,
                alcance=alcance,
                objetivo=objetivo,
            )
        )

    elif recurso == "funciones":

        resultados = (
            _inventario_funciones(
                app=app,
                archivo=archivo,
            )
        )

        respuesta = (
            _respuesta_funciones(
                resultados,
                alcance=alcance,
                objetivo=objetivo,
            )
        )

    elif recurso == "templates":

        if alcance == "archivo":

            return {
                "ok":
                    False,

                "pregunta":
                    pregunta,

                "respondido_por":
                    "host",

                "llm_invocado":
                    False,

                "error": (
                    "HOST019 no resuelve templates "
                    "por archivo."
                ),
            }

        resultados = (
            _inventario_templates(
                app=app
            )
        )

        respuesta = (
            _respuesta_templates(
                resultados,
                alcance=alcance,
                objetivo=objetivo,
            )
        )

    else:

        return {
            "ok":
                False,

            "pregunta":
                pregunta,

            "respondido_por":
                "host",

            "llm_invocado":
                False,

            "error": (
                "El recurso estructural solicitado "
                "no está soportado."
            ),
        }

    return {
        "ok":
            True,

        "pregunta":
            pregunta,

        "respondido_por":
            "host",

        "llm_invocado":
            False,

        "hay_evidencia":
            True,

        "tipo":
            "inventario_estructural",

        "recurso":
            recurso,

        "alcance":
            alcance,

        "objetivo":
            objetivo,

        "total":
            len(
                resultados
            ),

        "plan":
            plan,

        "resultados":
            resultados,

        "deteccion": {
            "inventario":
                recurso,

            "alcance":
                alcance,

            "objetivo":
                objetivo,

            "total":
                len(
                    resultados
                ),
        },

        "contexto": (
            "Inventario estructural obtenido directamente "
            "desde el proyecto Django anfitrión. "
            "La app o el archivo fueron validados contra "
            "el host real. No se utilizó LLM para "
            "determinar los hechos."
        ),

        "respuesta":
            respuesta,
    }
