from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from django.apps import apps

from .inspector_proyecto import (
    obtener_templates,
)

from .inspector_urls import (
    construir_mapa_urls,
)


# ============================================================
# PATRONES
# ============================================================

PATRON_DJANGO_URL = re.compile(
    r"""{%\s*url\s+(['"])(?P<nombre>[^'"]+)\1[^%]*%}""",
    re.IGNORECASE,
)

PATRON_HREF = re.compile(
    r"""href\s*=\s*(['"])(?P<valor>.*?)\1""",
    re.IGNORECASE | re.DOTALL,
)

PATRON_ACTION = re.compile(
    r"""action\s*=\s*(['"])(?P<valor>.*?)\1""",
    re.IGNORECASE | re.DOTALL,
)

PATRON_FETCH = re.compile(
    r"""fetch\s*\(\s*(['"])(?P<valor>.*?)\1""",
    re.IGNORECASE | re.DOTALL,
)


# ============================================================
# UTILIDADES
# ============================================================

def _leer_template(
    ruta: str,
) -> str:

    archivo = Path(
        ruta
    )

    if not archivo.is_file():
        return ""

    try:
        return archivo.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def _numero_linea(
    contenido: str,
    posicion: int,
) -> int:

    return (
        contenido.count(
            "\n",
            0,
            posicion,
        )
        + 1
    )


def _normalizar_ruta_url(
    valor: str,
) -> str:

    ruta = str(
        valor
        or ""
    ).strip()

    if not ruta:
        return ""

    if ruta.startswith(
        (
            "http://",
            "https://",
            "//",
            "mailto:",
            "tel:",
            "javascript:",
            "#",
        )
    ):
        return ""

    ruta = ruta.split(
        "?",
        1,
    )[0]

    ruta = ruta.split(
        "#",
        1,
    )[0]

    ruta = ruta.strip()

    if ruta.startswith("/"):
        ruta = ruta[1:]

    return ruta


def _detectar_app_template(
    ruta: str,
) -> dict[str, Any] | None:

    template_path = Path(
        ruta
    ).resolve()

    candidatos = []

    for config in apps.get_app_configs():

        app_path = Path(
            config.path
        ).resolve()

        try:
            template_path.relative_to(
                app_path
            )
        except ValueError:
            continue

        candidatos.append(
            config
        )

    if not candidatos:
        return None

    candidatos.sort(
        key=lambda config: len(
            str(
                Path(
                    config.path
                ).resolve()
            )
        ),
        reverse=True,
    )

    config = candidatos[0]

    if str(
        config.name
    ).startswith(
        "django.contrib."
    ):
        tipo = "django"

    elif config.label == "ia_local":
        tipo = "ia_local"

    else:
        tipo = "proyecto"

    return {
        "label":
            config.label,

        "name":
            str(
                config.name
            ),

        "path":
            str(
                Path(
                    config.path
                ).resolve()
            ),

        "tipo":
            tipo,
    }


# ============================================================
# ÍNDICES DE URL
# ============================================================

def _construir_indices_urls(
    mapa_urls: list[dict[str, Any]],
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:

    por_nombre: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    por_ruta: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for item in mapa_urls:

        nombre = str(
            item.get(
                "name",
                ""
            )
            or ""
        ).strip()

        namespace = str(
            item.get(
                "namespace",
                ""
            )
            or ""
        ).strip()

        ruta = _normalizar_ruta_url(
            item.get(
                "ruta",
                ""
            )
        )

        if nombre:

            claves = {
                nombre,
            }

            if namespace:
                claves.add(
                    f"{namespace}:{nombre}"
                )

            for clave in claves:
                por_nombre.setdefault(
                    clave,
                    [],
                ).append(
                    item
                )

        if ruta:
            por_ruta.setdefault(
                ruta,
                [],
            ).append(
                item
            )

    return (
        por_nombre,
        por_ruta,
    )


# ============================================================
# EXTRACCIÓN DE REFERENCIAS
# ============================================================

def _extraer_urls_django(
    contenido: str,
) -> list[dict[str, Any]]:

    resultado = []

    for match in PATRON_DJANGO_URL.finditer(
        contenido
    ):

        nombre = str(
            match.group(
                "nombre"
            )
            or ""
        ).strip()

        if not nombre:
            continue

        resultado.append(
            {
                "tipo":
                    "django_url",

                "valor":
                    nombre,

                "linea":
                    _numero_linea(
                        contenido,
                        match.start(),
                    ),
            }
        )

    return resultado


def _extraer_atributos(
    contenido: str,
    patron: re.Pattern,
    tipo: str,
) -> list[dict[str, Any]]:

    resultado = []

    for match in patron.finditer(
        contenido
    ):

        valor = str(
            match.group(
                "valor"
            )
            or ""
        ).strip()

        if not valor:
            continue

        # Las referencias que contienen template tags serán
        # resueltas por el detector {% url ... %}.
        if "{%" in valor:
            continue

        # Variables puras no tienen ruta estática resoluble.
        if "{{" in valor:
            continue

        ruta = _normalizar_ruta_url(
            valor
        )

        if not ruta:
            continue

        resultado.append(
            {
                "tipo":
                    tipo,

                "valor":
                    valor,

                "ruta_normalizada":
                    ruta,

                "linea":
                    _numero_linea(
                        contenido,
                        match.start(),
                    ),
            }
        )

    return resultado


def extraer_referencias_template(
    contenido: str,
) -> list[dict[str, Any]]:

    resultado = []

    resultado.extend(
        _extraer_urls_django(
            contenido
        )
    )

    resultado.extend(
        _extraer_atributos(
            contenido,
            PATRON_HREF,
            "href",
        )
    )

    resultado.extend(
        _extraer_atributos(
            contenido,
            PATRON_ACTION,
            "action",
        )
    )

    resultado.extend(
        _extraer_atributos(
            contenido,
            PATRON_FETCH,
            "fetch",
        )
    )

    resultado.sort(
        key=lambda item: (
            item.get(
                "linea",
                0,
            ),
            item.get(
                "tipo",
                "",
            ),
            item.get(
                "valor",
                "",
            ),
        )
    )

    return resultado


# ============================================================
# RESOLUCIÓN
# ============================================================

def _resolver_referencia(
    referencia: dict[str, Any],
    *,
    por_nombre: dict[
        str,
        list[dict[str, Any]],
    ],
    por_ruta: dict[
        str,
        list[dict[str, Any]],
    ],
) -> dict[str, Any]:

    tipo = referencia[
        "tipo"
    ]

    destinos = []

    if tipo == "django_url":

        clave = str(
            referencia[
                "valor"
            ]
        ).strip()

        destinos = list(
            por_nombre.get(
                clave,
                [],
            )
        )

    else:

        ruta = str(
            referencia.get(
                "ruta_normalizada",
                ""
            )
            or ""
        )

        destinos = list(
            por_ruta.get(
                ruta,
                [],
            )
        )

    return {
        **referencia,

        "resuelta":
            bool(
                destinos
            ),

        "destinos":
            destinos,
    }


# ============================================================
# PERFIL DE TEMPLATE
# ============================================================

def construir_perfil_template(
    template: dict[str, Any],
    *,
    por_nombre: dict[
        str,
        list[dict[str, Any]],
    ],
    por_ruta: dict[
        str,
        list[dict[str, Any]],
    ],
) -> dict[str, Any]:

    archivo = str(
        template.get(
            "archivo",
            ""
        )
        or ""
    )

    ruta = str(
        template.get(
            "ruta",
            ""
        )
        or ""
    )

    contenido = _leer_template(
        ruta
    )

    app = _detectar_app_template(
        ruta
    )

    referencias = (
        extraer_referencias_template(
            contenido
        )
        if contenido
        else []
    )

    referencias_resueltas = []

    for referencia in referencias:

        resultado = _resolver_referencia(
            referencia,
            por_nombre=por_nombre,
            por_ruta=por_ruta,
        )

        referencias_resueltas.append(
            resultado
        )

    resueltas = [
        item
        for item
        in referencias_resueltas
        if item[
            "resuelta"
        ]
    ]

    no_resueltas = [
        item
        for item
        in referencias_resueltas
        if not item[
            "resuelta"
        ]
    ]

    return {
        "archivo":
            archivo,

        "ruta":
            ruta,

        "bytes":
            template.get(
                "bytes",
                0,
            ),

        "app":
            app,

        "referencias":
            referencias_resueltas,

        "total_referencias":
            len(
                referencias_resueltas
            ),

        "referencias_resueltas":
            len(
                resueltas
            ),

        "referencias_no_resueltas":
            len(
                no_resueltas
            ),
    }


# ============================================================
# MAPA TEMPLATE -> URL -> VIEW
# ============================================================

def construir_mapa_templates() -> list[dict[str, Any]]:

    templates = (
        obtener_templates()
    )

    mapa_urls = (
        construir_mapa_urls()
    )

    (
        por_nombre,
        por_ruta,
    ) = _construir_indices_urls(
        mapa_urls
    )

    resultado = []

    for template in templates:

        perfil = construir_perfil_template(
            template,
            por_nombre=por_nombre,
            por_ruta=por_ruta,
        )

        resultado.append(
            perfil
        )

    resultado.sort(
        key=lambda item: item[
            "archivo"
        ].lower()
    )

    return resultado


# ============================================================
# RESUMEN
# ============================================================

def construir_resumen_templates() -> dict[str, Any]:

    mapa = construir_mapa_templates()

    total_referencias = sum(
        item[
            "total_referencias"
        ]
        for item
        in mapa
    )

    total_resueltas = sum(
        item[
            "referencias_resueltas"
        ]
        for item
        in mapa
    )

    total_no_resueltas = sum(
        item[
            "referencias_no_resueltas"
        ]
        for item
        in mapa
    )

    proyecto = [
        item
        for item
        in mapa
        if (
            item.get(
                "app"
            )
            and item[
                "app"
            ][
                "tipo"
            ] == "proyecto"
        )
    ]

    ia_local = [
        item
        for item
        in mapa
        if (
            item.get(
                "app"
            )
            and item[
                "app"
            ][
                "tipo"
            ] == "ia_local"
        )
    ]

    sin_app = [
        item
        for item
        in mapa
        if not item.get(
            "app"
        )
    ]

    return {
        "totales": {
            "templates":
                len(
                    mapa
                ),

            "referencias":
                total_referencias,

            "resueltas":
                total_resueltas,

            "no_resueltas":
                total_no_resueltas,

            "proyecto":
                len(
                    proyecto
                ),

            "ia_local":
                len(
                    ia_local
                ),

            "sin_app":
                len(
                    sin_app
                ),
        },

        "templates":
            mapa,

        "proyecto":
            proyecto,

        "ia_local":
            ia_local,

        "sin_app":
            sin_app,
    }


# ============================================================
# BÚSQUEDA
# ============================================================

def buscar_template(
    texto: str,
) -> list[dict[str, Any]]:

    objetivo = str(
        texto
        or ""
    ).strip().lower()

    if not objetivo:
        return []

    resultado = []

    for item in construir_mapa_templates():

        if objetivo in item[
            "archivo"
        ].lower():

            resultado.append(
                item
            )

    return resultado