from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from .catalogo_datos import obtener_modelo_django


PATRON_CAMPO_REPETIDO = re.compile(
    r"^(?P<prefijo>[A-Za-z][A-Za-z0-9_]*)_"
    r"(?P<indice>\d+)_"
    r"(?P<atributo>[A-Za-z][A-Za-z0-9_]*)$"
)

MINIMO_SLOTS = 2
MINIMO_ATRIBUTOS_COMUNES = 2


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _describir_campo(campo) -> dict[str, Any]:
    return {
        "nombre": getattr(campo, "name", ""),
        "tipo_django": campo.__class__.__name__,
        "null": bool(getattr(campo, "null", False)),
        "blank": bool(getattr(campo, "blank", False)),
        "editable": bool(getattr(campo, "editable", True)),
        "relacion": bool(getattr(campo, "is_relation", False)),
        "concrete": bool(getattr(campo, "concrete", False)),
    }


def _orden_indice(indice: str) -> tuple[int, str]:
    try:
        return (int(indice), indice)
    except (TypeError, ValueError):
        return (10**18, str(indice))


def descubrir_colecciones_estructuradas(
    *,
    modelo: str,
    minimo_slots: int = MINIMO_SLOTS,
    minimo_atributos_comunes: int = MINIMO_ATRIBUTOS_COMUNES,
) -> dict[str, Any]:
    """
    Descubre colecciones lógicas representadas por campos repetidos
    con patrón <prefijo>_<indice>_<atributo>.

    No consulta datos ni ejecuta QuerySets.
    """

    try:
        minimo_slots = max(2, int(minimo_slots))
    except (TypeError, ValueError):
        minimo_slots = MINIMO_SLOTS

    try:
        minimo_atributos_comunes = max(1, int(minimo_atributos_comunes))
    except (TypeError, ValueError):
        minimo_atributos_comunes = MINIMO_ATRIBUTOS_COMUNES

    modelo_django = obtener_modelo_django(modelo)

    if modelo_django is None:
        return {
            "ok": False,
            "modelo": modelo,
            "total_colecciones": 0,
            "colecciones": [],
            "razon": "El modelo no pudo resolverse de forma inequívoca.",
            "llm_invocado": False,
        }

    grupos: dict[str, dict[str, dict[str, dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(dict)
    )

    campos_analizados = 0
    campos_patron = 0

    for campo in modelo_django._meta.get_fields():
        if bool(getattr(campo, "is_relation", False)):
            continue

        if not bool(getattr(campo, "concrete", False)):
            continue

        nombre = _texto(getattr(campo, "name", ""))
        if not nombre:
            continue

        campos_analizados += 1
        coincidencia = PATRON_CAMPO_REPETIDO.match(nombre)

        if coincidencia is None:
            continue

        prefijo = coincidencia.group("prefijo")
        indice = coincidencia.group("indice")
        atributo = coincidencia.group("atributo")

        campos_patron += 1
        grupos[prefijo][indice][atributo] = _describir_campo(campo)

    colecciones = []

    for prefijo, slots_raw in grupos.items():
        indices = sorted(slots_raw.keys(), key=_orden_indice)

        if len(indices) < minimo_slots:
            continue

        conjuntos_atributos = [set(slots_raw[indice].keys()) for indice in indices]
        if not conjuntos_atributos:
            continue

        atributos_comunes = set.intersection(*conjuntos_atributos)
        atributos_union = set.union(*conjuntos_atributos)

        if len(atributos_comunes) < minimo_atributos_comunes:
            continue

        atributos = sorted(atributos_union)
        atributos_comunes_ordenados = sorted(atributos_comunes)

        slots = []
        slots_completos = 0

        for indice in indices:
            campos_slot = slots_raw[indice]
            presentes = sorted(campos_slot.keys())
            faltantes = sorted(set(atributos) - set(presentes))
            completo = not faltantes

            if completo:
                slots_completos += 1

            slots.append(
                {
                    "indice": indice,
                    "indice_numerico": int(indice) if indice.isdigit() else None,
                    "ancho_indice": len(indice),
                    "completo": completo,
                    "atributos_presentes": presentes,
                    "atributos_faltantes": faltantes,
                    "campos": {
                        atributo: campos_slot[atributo]
                        for atributo in presentes
                    },
                }
            )

        total_slots = len(indices)
        total_atributos = len(atributos)
        total_campos_esperados = total_slots * total_atributos
        total_campos_presentes = sum(len(slots_raw[indice]) for indice in indices)
        cobertura = (
            total_campos_presentes / total_campos_esperados
            if total_campos_esperados
            else 0.0
        )

        tipos_por_atributo = {}
        for atributo in atributos:
            tipos_por_atributo[atributo] = sorted(
                {
                    slots_raw[indice][atributo]["tipo_django"]
                    for indice in indices
                    if atributo in slots_raw[indice]
                }
            )

        colecciones.append(
            {
                "prefijo": prefijo,
                "patron": f"{prefijo}_<indice>_<atributo>",
                "tipo_representacion": "coleccion_estructurada_campos_repetidos",
                "cantidad_slots": total_slots,
                "indices": indices,
                "anchos_indices": sorted({len(indice) for indice in indices}),
                "atributos": atributos,
                "atributos_comunes": atributos_comunes_ordenados,
                "cantidad_atributos": total_atributos,
                "slots_completos": slots_completos,
                "slots_incompletos": total_slots - slots_completos,
                "campos_presentes": total_campos_presentes,
                "campos_esperados": total_campos_esperados,
                "cobertura": round(cobertura, 6),
                "estructura_uniforme": slots_completos == total_slots,
                "tipos_por_atributo": tipos_por_atributo,
                "slots": slots,
                "origen": "django_meta",
                "llm_invocado": False,
            }
        )

    colecciones.sort(
        key=lambda item: (
            -item["cantidad_slots"],
            -item["cantidad_atributos"],
            item["prefijo"],
        )
    )

    return {
        "ok": True,
        "modelo": modelo_django._meta.label,
        "tabla": modelo_django._meta.db_table,
        "campos_analizados": campos_analizados,
        "campos_con_patron": campos_patron,
        "total_colecciones": len(colecciones),
        "colecciones": colecciones,
        "origen": "django_meta",
        "llm_invocado": False,
    }


def obtener_coleccion_estructurada(
    *,
    modelo: str,
    prefijo: str,
) -> dict[str, Any]:
    """Recupera una colección estructurada por prefijo exacto."""

    prefijo = _texto(prefijo)
    inventario = descubrir_colecciones_estructuradas(modelo=modelo)

    if not inventario.get("ok"):
        return {
            "ok": False,
            "resuelto": False,
            "modelo": inventario.get("modelo", modelo),
            "prefijo": prefijo,
            "coleccion": None,
            "razon": inventario.get("razon", "No fue posible construir el inventario."),
            "llm_invocado": False,
        }

    coincidencias = [
        coleccion
        for coleccion in inventario.get("colecciones", [])
        if coleccion.get("prefijo") == prefijo
    ]

    if len(coincidencias) != 1:
        return {
            "ok": True,
            "resuelto": False,
            "modelo": inventario.get("modelo"),
            "prefijo": prefijo,
            "coleccion": None,
            "razon": "No existe una colección estructurada inequívoca con ese prefijo.",
            "llm_invocado": False,
        }

    return {
        "ok": True,
        "resuelto": True,
        "modelo": inventario.get("modelo"),
        "prefijo": prefijo,
        "coleccion": coincidencias[0],
        "origen": "django_meta",
        "llm_invocado": False,
    }
