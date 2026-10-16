from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from django.db import DatabaseError
from django.db.models import Count

from .catalogo_datos import obtener_modelo_django
from .validador_plan_datos import validar_plan_datos


TRANSFORMACIONES_PERMITIDAS = {"identidad", "basename", "stem_ruta"}
TIPOS_EVIDENCIA_PERMITIDOS = {
    "campo_transformado_igual_clave",
    "campo_contiene_clave",
}
MAX_EJEMPLOS = 20
ITERATOR_CHUNK_SIZE = 1000


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _transformar(valor: Any, transformacion: str) -> str:
    texto = _texto(valor)
    if not texto:
        return ""
    if transformacion == "identidad":
        return texto
    if transformacion == "basename":
        return Path(texto).name
    if transformacion == "stem_ruta":
        return Path(texto).stem
    return ""


def _error(fase: str, mensaje: str, modelo_origen=None, modelo_destino=None):
    r = {
        "ok": False,
        "validado": False,
        "fase": fase,
        "errores": [mensaje],
        "llm_invocado": False,
    }
    if modelo_origen:
        r["modelo_origen"] = modelo_origen
    if modelo_destino:
        r["modelo_destino"] = modelo_destino
    return r


def _campo_escalar(modelo_django, nombre: str):
    try:
        campo = modelo_django._meta.get_field(nombre)
    except Exception:
        return False, None, f"Django._meta no pudo resolver el campo {nombre!r}."

    if bool(getattr(campo, "is_relation", False)):
        return False, campo, f"El campo {nombre!r} es una relación."
    if not bool(getattr(campo, "concrete", False)):
        return False, campo, f"El campo {nombre!r} no es concreto."
    return True, campo, None


def validar_correspondencia_virtual(
    *,
    plan_origen: dict[str, Any],
    modelo_destino: str,
    campo_clave_destino: str,
    evidencias: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Valida una correspondencia virtual N -> 1 sin ForeignKey.

    Debe existir al menos una evidencia exacta transformada. Esa evidencia
    propone una clave destino real; las evidencias adicionales corroboran
    exactamente esa misma clave.
    """

    validacion_plan = validar_plan_datos(plan_origen)
    if not validacion_plan.get("plan_validado"):
        return {
            "ok": False,
            "validado": False,
            "fase": "validacion_plan",
            "errores": validacion_plan.get("errores", []),
            "validacion_plan": validacion_plan,
            "llm_invocado": False,
        }

    plan_seguro = validacion_plan.get("plan")
    if not isinstance(plan_seguro, dict):
        return _error("validacion_plan", "La validación no produjo un plan seguro.")

    modelo_origen_label = _texto(plan_seguro.get("modelo"))
    modelo_origen_django = obtener_modelo_django(modelo_origen_label)
    if modelo_origen_django is None:
        return _error(
            "modelo_origen",
            "El modelo origen validado ya no puede resolverse en Django.",
            modelo_origen_label,
        )

    modelo_destino_django = obtener_modelo_django(modelo_destino)
    if modelo_destino_django is None:
        return _error(
            "modelo_destino",
            "El modelo destino no pudo resolverse de forma inequívoca.",
            modelo_origen_label,
            modelo_destino,
        )

    modelo_destino_label = modelo_destino_django._meta.label
    campo_clave_destino = _texto(campo_clave_destino)

    ok, campo_destino, err = _campo_escalar(
        modelo_destino_django,
        campo_clave_destino,
    )
    if not ok:
        return _error(
            "clave_destino",
            err or "Clave destino inválida.",
            modelo_origen_label,
            modelo_destino_label,
        )

    es_unique = bool(getattr(campo_destino, "unique", False))
    es_pk = bool(getattr(campo_destino, "primary_key", False))
    if not (es_unique or es_pk):
        return _error(
            "clave_destino",
            "La clave destino no está declarada como primary_key o unique=True.",
            modelo_origen_label,
            modelo_destino_label,
        )

    if not isinstance(evidencias, list) or not evidencias:
        return _error(
            "evidencias",
            "Debe existir al menos una evidencia declarada.",
            modelo_origen_label,
            modelo_destino_label,
        )

    evidencias_validadas = []
    campos_origen = []
    total_exactas = 0

    for i, evidencia in enumerate(evidencias):
        if not isinstance(evidencia, dict):
            return _error(
                "evidencias",
                f"Evidencia {i}: formato inválido.",
                modelo_origen_label,
                modelo_destino_label,
            )

        tipo = _texto(evidencia.get("tipo"))
        campo = _texto(evidencia.get("campo"))

        if tipo not in TIPOS_EVIDENCIA_PERMITIDOS:
            return _error(
                "evidencias",
                f"Evidencia {i}: tipo no permitido {tipo!r}.",
                modelo_origen_label,
                modelo_destino_label,
            )

        ok_o, campo_django, err_o = _campo_escalar(modelo_origen_django, campo)
        if not ok_o:
            return _error(
                "evidencias",
                f"Evidencia {i}: {err_o}",
                modelo_origen_label,
                modelo_destino_label,
            )

        transformacion = None
        if tipo == "campo_transformado_igual_clave":
            total_exactas += 1
            transformacion = _texto(evidencia.get("transformacion", "identidad"))
            if transformacion not in TRANSFORMACIONES_PERMITIDAS:
                return _error(
                    "evidencias",
                    f"Evidencia {i}: transformación no permitida {transformacion!r}.",
                    modelo_origen_label,
                    modelo_destino_label,
                )

        evidencias_validadas.append(
            {
                "tipo": tipo,
                "campo": campo,
                "tipo_django": campo_django.__class__.__name__,
                "transformacion": transformacion,
            }
        )
        campos_origen.append(campo)

    if total_exactas < 1:
        return _error(
            "evidencias",
            "HOST031 exige al menos una evidencia exacta campo_transformado_igual_clave.",
            modelo_origen_label,
            modelo_destino_label,
        )

    campos_origen = list(dict.fromkeys(campos_origen))

    try:
        duplicados_reales = (
            modelo_destino_django.objects
            .values(campo_clave_destino)
            .annotate(n=Count(modelo_destino_django._meta.pk.name))
            .filter(n__gt=1)
            .count()
        )

        if duplicados_reales:
            return _error(
                "clave_destino",
                "La clave destino tiene duplicados reales en la base de datos.",
                modelo_origen_label,
                modelo_destino_label,
            )

        claves_destino = {
            _texto(v)
            for v in modelo_destino_django.objects.values_list(
                campo_clave_destino,
                flat=True,
            )
            if _texto(v)
        }

        filtros_orm = {
            f["lookup"]: f["valor"]
            for f in plan_seguro.get("filtros", [])
        }

        qs = modelo_origen_django.objects.all()
        if filtros_orm:
            qs = qs.filter(**filtros_orm)

        pk_nombre = modelo_origen_django._meta.pk.name
        columnas = [pk_nombre, *campos_origen]
        posiciones = {nombre: pos for pos, nombre in enumerate(columnas)}

        total_origen = total_match = total_sin_match = total_conflicto = 0
        destinos_counter = Counter()
        ejemplos_match = []
        ejemplos_fallo = []

        for fila in qs.values_list(*columnas).iterator(
            chunk_size=ITERATOR_CHUNK_SIZE
        ):
            total_origen += 1
            pk_origen = fila[posiciones[pk_nombre]]
            candidatas = []
            detalle = []

            for evidencia in evidencias_validadas:
                if evidencia["tipo"] != "campo_transformado_igual_clave":
                    continue
                valor = fila[posiciones[evidencia["campo"]]]
                candidata = _transformar(valor, evidencia["transformacion"])
                cumple = bool(candidata) and candidata in claves_destino
                detalle.append(
                    {
                        "tipo": evidencia["tipo"],
                        "campo": evidencia["campo"],
                        "transformacion": evidencia["transformacion"],
                        "valor_transformado": candidata,
                        "cumple": cumple,
                    }
                )
                if cumple:
                    candidatas.append(candidata)

            candidatas_unicas = set(candidatas)
            if len(candidatas_unicas) != 1:
                total_conflicto += 1
                if len(ejemplos_fallo) < MAX_EJEMPLOS:
                    ejemplos_fallo.append(
                        {
                            "pk_origen": pk_origen,
                            "motivo": "evidencia_exacta_no_univoca",
                            "candidatas": sorted(candidatas_unicas),
                            "evidencias": detalle,
                        }
                    )
                continue

            clave = next(iter(candidatas_unicas))
            corroboraciones_ok = True

            for evidencia in evidencias_validadas:
                if evidencia["tipo"] != "campo_contiene_clave":
                    continue
                valor = _texto(fila[posiciones[evidencia["campo"]]])
                cumple = bool(valor) and clave in valor
                detalle.append(
                    {
                        "tipo": evidencia["tipo"],
                        "campo": evidencia["campo"],
                        "clave_candidata": clave,
                        "cumple": cumple,
                    }
                )
                if not cumple:
                    corroboraciones_ok = False

            if not corroboraciones_ok:
                total_sin_match += 1
                if len(ejemplos_fallo) < MAX_EJEMPLOS:
                    ejemplos_fallo.append(
                        {
                            "pk_origen": pk_origen,
                            "motivo": "evidencia_corroborante_fallida",
                            "clave_candidata": clave,
                            "evidencias": detalle,
                        }
                    )
                continue

            total_match += 1
            destinos_counter[clave] += 1

            if len(ejemplos_match) < MAX_EJEMPLOS:
                ejemplos_match.append(
                    {
                        "pk_origen": pk_origen,
                        "clave_destino": clave,
                        "evidencias": detalle,
                    }
                )

        cobertura = total_match / total_origen if total_origen else 0.0
        destinos_unicos = len(destinos_counter)
        asociaciones_duplicadas = sum(
            n - 1 for n in destinos_counter.values() if n > 1
        )

        destinos_con_multiples_origenes = [
            {"clave_destino": k, "cantidad_origenes": n}
            for k, n in sorted(destinos_counter.items())
            if n > 1
        ]

        validado = bool(
            total_origen > 0
            and total_match == total_origen
            and total_conflicto == 0
            and total_sin_match == 0
        )

        return {
            "ok": True,
            "validado": validado,
            "modelo_origen": modelo_origen_label,
            "tabla_origen": modelo_origen_django._meta.db_table,
            "modelo_destino": modelo_destino_label,
            "tabla_destino": modelo_destino_django._meta.db_table,
            "campo_clave_destino": campo_clave_destino,
            "clave_destino_unique_declarada": True,
            "duplicados_reales_destino": duplicados_reales,
            "evidencias": evidencias_validadas,
            "cardinalidad": "N_a_1",
            "total_origen": total_origen,
            "total_matches": total_match,
            "total_no_validados": total_origen - total_match,
            "total_conflictos": total_conflicto,
            "cobertura": round(cobertura, 6),
            "destinos_unicos": destinos_unicos,
            "claves_destino_validadas": sorted(destinos_counter.keys()),
            "asociaciones_duplicadas_sobre_mismo_destino": asociaciones_duplicadas,
            "destinos_con_multiples_origenes": destinos_con_multiples_origenes,
            "ejemplos_match": ejemplos_match,
            "ejemplos_fallo": ejemplos_fallo,
            "filtros_origen": plan_seguro.get("filtros", []),
            "razon": (
                "Todas las filas origen tienen una única clave destino existente "
                "y todas las evidencias declaradas concuerdan."
                if validado
                else
                "La correspondencia no pudo demostrarse para todas las filas origen."
            ),
            "origen": "orm_seguro_correspondencia_virtual",
            "llm_invocado": False,
        }

    except DatabaseError as exc:
        return {
            "ok": False,
            "validado": False,
            "fase": "orm",
            "errores": [str(exc)],
            "modelo_origen": modelo_origen_label,
            "modelo_destino": modelo_destino_label,
            "llm_invocado": False,
        }

    except Exception as exc:
        return {
            "ok": False,
            "validado": False,
            "fase": "general",
            "errores": [str(exc)],
            "modelo_origen": modelo_origen_label,
            "modelo_destino": modelo_destino_label,
            "llm_invocado": False,
        }
