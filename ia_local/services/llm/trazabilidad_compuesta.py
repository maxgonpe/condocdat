"""Trazabilidad conservadora de una consulta compuesta.

No llama al LLM, no ejecuta ORM y no habilita FINAL.
"""
import re
import unicodedata
from typing import Any

VERSION = "IA-LLM008-F5-06-06-v1"

TIPOS_CONOCIDOS = {
    "filtro",
    "limite",
    "ordenamiento",
    "fecha",
    "negacion_relacional",
    "agrupamiento",
    "agregacion",
}


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.casefold())
    texto = "".join(
        caracter for caracter in texto
        if not unicodedata.combining(caracter)
    )
    return " ".join(re.findall(r"\w+", texto))


def _evidencia_presente(pregunta, evidencia):
    if not isinstance(evidencia, str):
        return False

    texto = _normalizar(pregunta)
    fragmento = _normalizar(evidencia)

    if not fragmento:
        return False

    return f" {fragmento} " in f" {texto} "


def integrar_trazabilidad_compuesta(
    pregunta: str,
    *,
    consolidacion: dict,
    relacion: dict,
) -> dict[str, Any]:

    base = {
        "ok": False,
        "version": VERSION,
        "estado": "contrato_invalido",
        "pregunta_original": pregunta,
        "operacion": None,
        "restricciones": [],
        "relacion": {},
        "pendientes": [],
        "trazabilidad_textual_verificada": False,
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    if (
        not isinstance(pregunta, str)
        or not pregunta.strip()
        or not isinstance(consolidacion, dict)
        or not isinstance(relacion, dict)
    ):
        return base

    if (
        consolidacion.get("ok") is not True
        or consolidacion.get("estado")
            != "consolidacion_diagnostica"
        or consolidacion.get("pregunta") != pregunta
        or consolidacion.get("ejecutado") is not False
        or consolidacion.get("ejecutable") is not False
    ):
        return {
            **base,
            "estado": "consolidacion_no_compatible",
        }

    restricciones = consolidacion.get("restricciones")
    if not isinstance(restricciones, list):
        return {
            **base,
            "estado": "restricciones_invalidas",
        }

    pendientes = []
    trazas = []
    identificadores = set()

    for indice, restriccion in enumerate(restricciones):
        if not isinstance(restriccion, dict):
            return {
                **base,
                "estado": "restriccion_invalida",
            }

        tipo = restriccion.get("tipo")
        evidencia = restriccion.get("evidencia_textual")
        origen = restriccion.get("origen")

        if (
            not isinstance(tipo, str)
            or tipo not in TIPOS_CONOCIDOS
            or not isinstance(evidencia, str)
            or not evidencia.strip()
            or origen not in {
                "extraccion_inicial",
                "auditoria",
            }
        ):
            return {
                **base,
                "estado": "restriccion_invalida",
            }

        identificador = (tipo, _normalizar(evidencia))

        if identificador in identificadores:
            pendientes.append(
                f"restriccion_duplicada_{indice}"
            )

        identificadores.add(identificador)

        presente = _evidencia_presente(
            pregunta, evidencia
        )

        if not presente:
            pendientes.append(
                f"evidencia_no_encontrada_{indice}"
            )

        # Se conserva el valor propuesto como dato
        # no certificado, sin aplicarlo a ningún plan.
        traza = {
            "indice": indice,
            "tipo": tipo,
            "evidencia_textual": evidencia,
            "origen": origen,
            "evidencia_presente": presente,
            "valor_propuesto": restriccion.get(
                "valor_propuesto"
            ),
            "certificada_host": False,
            "ejecutable": False,
        }

        trazas.append(traza)

        pendientes.append(
            f"certificacion_pendiente_{indice}_{tipo}"
        )

    vr = relacion.get("validacion_ruta")

    relacion_valida = (
        relacion.get("ok") is True
        and relacion.get("estado") == "relacion_certificada"
        and relacion.get("componente_certificador")
            in {"QUERY007", "QUERY007/HOST"}
        and relacion.get("ejecutado") is False
        and relacion.get("llm_invocado") is False
        and isinstance(vr, dict)
        and vr.get("ok") is True
        and vr.get("valida") is True
        and vr.get("origen") == "django_meta"
        and vr.get("modelo_origen")
            == relacion.get("modelo_origen")
        and vr.get("modelo_destino")
            == relacion.get("modelo_destino")
        and vr.get("ruta_orm")
            == relacion.get("ruta_orm")
        and vr.get("profundidad")
            == relacion.get("profundidad")
    )

    expresion_parcial = relacion.get("pregunta")

    # La expresión parcial debe permanecer identificada
    # como tal; no se convierte en pregunta original.
    relacion_traza = {
        "expresion_parcial": expresion_parcial,
        "modelo_origen": relacion.get("modelo_origen"),
        "modelo_destino": relacion.get("modelo_destino"),
        "ruta_orm": relacion.get("ruta_orm"),
        "certificada_estructuralmente": relacion_valida,
        "vinculo_semantico_verificado": False,
    }

    if not relacion_valida:
        pendientes.append("relacion_no_certificada")

    pendientes.extend([
        "vinculo_relacional_semantico_pendiente",
        "cobertura_semantica_total_pendiente",
        "certificacion_conjunta_host_pendiente",
    ])

    trazabilidad_textual = all(
        item["evidencia_presente"]
        for item in trazas
    ) and bool(trazas)

    return {
        **base,
        "ok": True,
        "estado": "trazabilidad_parcial_registrada",
        "operacion": consolidacion.get("operacion"),
        "restricciones": trazas,
        "relacion": relacion_traza,
        "pendientes": list(dict.fromkeys(pendientes)),
        "trazabilidad_textual_verificada":
            trazabilidad_textual,
    }



# IA-LLM008-F5-06-08
def integrar_certificaciones_reales(trazabilidad):
    """Actualiza el diagnóstico sin autorizar ejecución."""
    from ia_local.config.cardinalidad import (
        LIMITE_MAXIMO_SOLICITABLE,
    )
    from ia_local.services.llm.cardinalidad_natural import (
        detectar_cardinalidad_natural,
    )
    from ia_local.services.query.ordenamiento_natural import (
        componer_ordenamiento_natural,
    )
    from ia_local.services.host.desambiguacion_filtros import (
        preparar_aclaracion_filtro,
    )

    base = {
        "ok": False,
        "version": "IA-LLM008-F5-06-08-v1",
        "estado": "entrada_invalida",
        "componentes": {},
        "pendientes": [],
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    if not isinstance(trazabilidad, dict):
        return base

    pregunta = trazabilidad.get("pregunta_original")
    restricciones = trazabilidad.get("restricciones")
    relacion = trazabilidad.get("relacion")

    if (
        trazabilidad.get("ok") is not True
        or trazabilidad.get("estado")
            != "trazabilidad_parcial_registrada"
        or trazabilidad.get("ejecutable") is not False
        or trazabilidad.get("ejecutado") is not False
        or not isinstance(pregunta, str)
        or not pregunta.strip()
        or not isinstance(restricciones, list)
        or not isinstance(relacion, dict)
        or relacion.get("certificada_estructuralmente") is not True
        or not isinstance(relacion.get("modelo_destino"), str)
    ):
        return base

    # Conservar la trazabilidad original sin modificarla.
    trazas = []
    for r in restricciones:
        if (
            not isinstance(r, dict)
            or r.get("evidencia_presente") is not True
            or not isinstance(r.get("tipo"), str)
            or not isinstance(r.get("evidencia_textual"), str)
        ):
            return {**base, "estado": "restricciones_invalidas"}
        trazas.append(dict(r))

    tipos = [r["tipo"] for r in trazas]

    # Primera versión: un límite, un filtro y un orden.
    # Los contratos más complejos se bloquean explícitamente.
    if (
        sorted(tipos) !=
        sorted(["limite", "filtro", "ordenamiento"])
    ):
        return {
            **base,
            "estado": "estructura_no_soportada",
            "pendientes": ["composicion_no_soportada"],
        }

    limite_traza = next(
        r for r in trazas if r["tipo"] == "limite"
    )
    filtro_traza = next(
        r for r in trazas if r["tipo"] == "filtro"
    )

    cardinalidad = detectar_cardinalidad_natural(pregunta)

    cantidad = cardinalidad.get("cantidad_solicitada")
    propuesta = limite_traza.get("valor_propuesto")

    cardinalidad_coherente = (
        cardinalidad.get("ok") is True
        and cardinalidad.get("pregunta") == pregunta
        and cardinalidad.get("detectada") is True
        and cardinalidad.get("totalidad_solicitada") is False
        and type(cantidad) is int
        and type(propuesta) is int
        and cantidad == propuesta
        and 1 <= cantidad <= LIMITE_MAXIMO_SOLICITABLE
    )

    filtro = preparar_aclaracion_filtro(
        relacion["modelo_destino"],
        filtro_traza["evidencia_textual"],
    )

    opciones = filtro.get("opciones", [])
    filtro_coherente = (
        filtro.get("ok") is True
        and filtro.get("modelo")
            == relacion["modelo_destino"]
        and filtro.get("evidencia_textual")
            == filtro_traza["evidencia_textual"]
        and isinstance(opciones, list)
        and len(opciones) >= 1
    )

    # QUERY004 sigue siendo el único responsable
    # de certificar el ordenamiento.
    orden = componer_ordenamiento_natural(
        pregunta,
        limite=cantidad if cardinalidad_coherente else 20,
    )

    # IA-LLM008-F5-06-09 — RECONCILIACION
    # Los pendientes se calculan desde el estado vigente.
    # No se copian certificaciones provisionales anteriores.
    if not isinstance(trazabilidad.get("pendientes"), list):
        return base

    pendientes = []

    for r in trazas:
        tipo = r["tipo"]

        if tipo == "limite":
            r["estado_certificacion"] = (
                "validada_localmente"
                if cardinalidad_coherente
                else "pendiente"
            )
            if not cardinalidad_coherente:
                pendientes.append("cardinalidad_inconsistente")

        elif tipo == "filtro":
            if not filtro_coherente:
                r["estado_certificacion"] = "pendiente"
                pendientes.append("filtro_no_certificado")
            elif len(opciones) > 1:
                r["estado_certificacion"] = "requiere_aclaracion"
                pendientes.append("filtro_ambiguo")
            else:
                r["estado_certificacion"] = "pendiente"
                pendientes.append(
                    "filtro_sin_confirmacion_de_intencion"
                )

        elif tipo == "ordenamiento":
            r["estado_certificacion"] = "pendiente"
            if orden.get("ok") is not True:
                pendientes.append("ordenamiento_no_certificado")
            else:
                pendientes.append(
                    "ordenamiento_pendiente_composicion"
                )

        # Ninguna restricción queda certificada dentro de un
        # plan completo en esta fase.
        r["certificada_host"] = False
        r["ejecutable"] = False

    # Barreras que las certificaciones parciales no resuelven.
    if not relacion.get("vinculo_semantico_verificado"):
        pendientes.append(
            "vinculo_relacional_semantico_pendiente"
        )

    pendientes.append("cobertura_semantica_total_pendiente")
    pendientes.append("certificacion_conjunta_host_pendiente")

    componentes = {
        "cardinalidad": {
            "estado": cardinalidad.get("estado"),
            "cantidad_solicitada": cantidad,
            "coincide_con_consolidacion":
                cardinalidad_coherente,
        },
        "filtro": {
            "estado": filtro.get("estado"),
            "modelo": relacion["modelo_destino"],
            "opciones": [
                {
                    "id": o.get("id"),
                    "etiqueta": o.get("etiqueta"),
                }
                for o in opciones
                if isinstance(o, dict)
            ] if filtro_coherente else [],
            "requiere_aclaracion":
                filtro.get("requiere_aclaracion") is True,
        },
        "ordenamiento": {
            "estado": orden.get("estado"),
            "certificado_para_plan_compuesto": False,
        },
    }

    return {
        **base,
        "ok": True,
        "estado": "certificaciones_parciales_integradas",
        "pregunta_original": pregunta,
        "relacion": dict(relacion),
        "restricciones": trazas,
        "componentes": componentes,
        "pendientes": list(dict.fromkeys(pendientes)),
        "requiere_aclaracion": (
            filtro.get("requiere_aclaracion") is True
            or orden.get("ok") is not True
        ),
    }



# IA-LLM008-F5-06-10
def incorporar_eleccion_filtro(plan_compuesto, opcion_id):
    """Recertifica una elección y actualiza su estado diagnóstico.

    El llamador debe haber validado previamente sesión, token
    e identidad mediante sesion_aclaracion_filtros.
    """
    from ia_local.services.host.desambiguacion_filtros import (
        verificar_eleccion_filtro,
    )

    base = {
        "ok": False,
        "version": "IA-LLM008-F5-06-10-v1",
        "estado": "entrada_invalida",
        "ejecutable": False,
        "ejecutado": False,
        "integridad_completa": False,
        "cobertura_verificada": False,
        "llm_invocado": False,
    }

    if (
        not isinstance(plan_compuesto, dict)
        or plan_compuesto.get("ok") is not True
        or plan_compuesto.get("estado")
            != "certificaciones_parciales_integradas"
        or plan_compuesto.get("ejecutable") is not False
        or plan_compuesto.get("ejecutado") is not False
        or plan_compuesto.get("integridad_completa") is not False
        or plan_compuesto.get("cobertura_verificada") is not False
        or not isinstance(opcion_id, str)
        or not opcion_id
    ):
        return base

    pregunta = plan_compuesto.get("pregunta_original")
    relacion = plan_compuesto.get("relacion")
    restricciones = plan_compuesto.get("restricciones")
    componentes = plan_compuesto.get("componentes")
    pendientes = plan_compuesto.get("pendientes")

    if (
        not isinstance(pregunta, str)
        or not pregunta.strip()
        or not isinstance(relacion, dict)
        or relacion.get("certificada_estructuralmente") is not True
        or not isinstance(relacion.get("modelo_destino"), str)
        or not isinstance(restricciones, list)
        or not isinstance(componentes, dict)
        or not isinstance(pendientes, list)
    ):
        return base

    filtros = [
        r for r in restricciones
        if isinstance(r, dict) and r.get("tipo") == "filtro"
    ]

    if len(filtros) != 1:
        return {**base, "estado": "estructura_filtro_no_soportada"}

    traza_filtro = filtros[0]
    evidencia = traza_filtro.get("evidencia_textual")
    modelo = relacion["modelo_destino"]

    if (
        not isinstance(evidencia, str)
        or not evidencia.strip()
        or traza_filtro.get("evidencia_presente") is not True
        or traza_filtro.get("estado_certificacion")
            != "requiere_aclaracion"
    ):
        return {**base, "estado": "filtro_no_pendiente"}

    componente_filtro = componentes.get("filtro")

    if (
        not isinstance(componente_filtro, dict)
        or componente_filtro.get("modelo") != modelo
        or componente_filtro.get("requiere_aclaracion") is not True
        or componente_filtro.get("estado")
            != "requiere_aclaracion_filtro"
    ):
        return {**base, "estado": "contrato_filtro_incompatible"}

    seleccion = verificar_eleccion_filtro(
        modelo, evidencia, opcion_id
    )

    if (
        seleccion.get("ok") is not True
        or seleccion.get("estado")
            != "eleccion_filtro_certificada"
        or seleccion.get("certificada_host") is not True
        or seleccion.get("modelo") != modelo
        or seleccion.get("evidencia_textual") != evidencia
        or seleccion.get("ejecutado") is not False
        or seleccion.get("ejecutable") is not False
        or not isinstance(seleccion.get("seleccion"), dict)
    ):
        return {
            **base,
            "estado": "eleccion_no_certificada",
        }

    opcion = dict(seleccion["seleccion"])

    # La opción debe haber formado parte de las alternativas
    # mostradas en el diagnóstico original.
    opciones_previas = componente_filtro.get("opciones")
    if (
        not isinstance(opciones_previas, list)
        or opcion_id not in {
            o.get("id")
            for o in opciones_previas
            if isinstance(o, dict)
        }
    ):
        return {
            **base,
            "estado": "eleccion_ajena_al_plan",
        }

    nuevas_restricciones = [
        dict(r) for r in restricciones
    ]

    for r in nuevas_restricciones:
        if r.get("tipo") == "filtro":
            r["estado_certificacion"] = (
                "seleccionada_host_aisladamente"
            )
            r["seleccion"] = opcion
            r["certificada_host"] = False
            r["ejecutable"] = False

    nuevos_componentes = {
        k: dict(v) if isinstance(v, dict) else v
        for k, v in componentes.items()
    }

    nuevos_componentes["filtro"] = {
        **componente_filtro,
        "estado": "filtro_seleccionado_pendiente_plan",
        "requiere_aclaracion": False,
        "seleccion": opcion,
        "certificada_plan_completo": False,
    }

    # Los demás pendientes permanecen intactos.
    nuevos_pendientes = [
        p for p in pendientes
        if p not in {
            "filtro_ambiguo",
            "filtro_sin_confirmacion_de_intencion",
        }
    ]
    nuevos_pendientes.append(
        "filtro_seleccionado_pendiente_plan"
    )

    return {
        **base,
        "ok": True,
        "estado": "filtro_integrado_pendiente_plan",
        "pregunta_original": pregunta,
        "relacion": dict(relacion),
        "restricciones": nuevas_restricciones,
        "componentes": nuevos_componentes,
        "pendientes": list(dict.fromkeys(nuevos_pendientes)),
        "requiere_aclaracion": (
            "ordenamiento_no_certificado" in nuevos_pendientes
            or "ordenamiento_pendiente_composicion"
                in nuevos_pendientes
        ),
    }



# IA-LLM008-F5-06-12
def preparar_aclaracion_orden_temporal(modelo, evidencia="últimos"):
    """Descubre campos temporales autorizados, sin ejecutar ORM."""
    import hashlib
    import json

    from django.db import models
    from ia_local.services.host.catalogo_datos import (
        obtener_modelo_django,
        describir_modelo,
    )
    from ia_local.services.host.validador_plan_datos import (
        validar_plan_datos,
    )

    base = {
        "ok": False,
        "version": "IA-LLM008-F5-06-12-v1",
        "estado": "entrada_invalida",
        "opciones": [],
        "requiere_aclaracion": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    if (
        not isinstance(modelo, str)
        or not isinstance(evidencia, str)
        or not modelo.strip()
        or evidencia.casefold().strip()
            not in {"últimos", "ultimos", "últimas", "ultimas"}
    ):
        return base

    django_modelo = obtener_modelo_django(modelo)

    if (
        django_modelo is None
        or django_modelo._meta.label_lower != modelo.casefold()
    ):
        return {**base, "estado": "modelo_no_autorizado"}

    descripcion = describir_modelo(django_modelo)

    if not isinstance(descripcion, dict):
        return {**base, "estado": "catalogo_invalido"}

    consultables = descripcion.get("campos_consultables")

    if not isinstance(consultables, list):
        return {**base, "estado": "catalogo_invalido"}

    permitidos = {
        c for c in consultables if isinstance(c, str)
    }

    opciones = []

    for campo in django_modelo._meta.get_fields():
        if (
            not isinstance(
                campo, (models.DateField, models.DateTimeField)
            )
            or not getattr(campo, "concrete", False)
            or getattr(campo, "is_relation", False)
            or campo.name not in permitidos
        ):
            continue

        propuesta = {
            "modelo": modelo,
            "operacion": "listar",
            "filtros": [],
            "orden": [{
                "campo": campo.name,
                "direccion": "desc",
            }],
            "limite": 5,
            "condiciones_no_resueltas": [],
        }

        certificado = validar_plan_datos(propuesta)

        if (
            certificado.get("ok") is not True
            or certificado.get("plan_validado") is not True
        ):
            continue

        plan = certificado.get("plan")

        if not isinstance(plan, dict):
            continue

        orden = plan.get("orden")

        if (
            not isinstance(orden, list)
            or len(orden) != 1
            or orden[0].get("campo") != campo.name
            or orden[0].get("direccion") != "desc"
            or orden[0].get("expresion") != "-" + campo.name
        ):
            continue

        datos = json.dumps(
            [modelo, campo.name, "desc"],
            ensure_ascii=False,
        )

        ident = hashlib.sha256(
            datos.encode("utf-8")
        ).hexdigest()[:24]

        opciones.append({
            "id": ident,
            "campo": campo.name,
            "etiqueta": str(campo.verbose_name),
            "direccion": "desc",
        })

    opciones.sort(key=lambda o: o["campo"])

    return {
        **base,
        "ok": bool(opciones),
        "estado": (
            "requiere_aclaracion_orden"
            if len(opciones) > 1
            else "candidato_temporal_unico"
            if opciones
            else "sin_campos_temporales_certificados"
        ),
        "modelo": modelo,
        "evidencia_textual": evidencia,
        "opciones": opciones,
        "requiere_aclaracion": len(opciones) > 1,
        "alternativas_validadas_host": len(opciones),
    }


def incorporar_eleccion_orden_temporal(plan_compuesto, opcion_id):
    """Recertifica el campo temporal y conserva los otros bloqueos.

    Solo integración diagnóstica. La sesión HTTP debe validarse
    por separado antes de invocar esta función.
    """
    base = {
        "ok": False,
        "version": "IA-LLM008-F5-06-12-v1",
        "estado": "entrada_invalida",
        "ejecutable": False,
        "ejecutado": False,
        "integridad_completa": False,
        "cobertura_verificada": False,
        "llm_invocado": False,
    }

    if (
        not isinstance(plan_compuesto, dict)
        or plan_compuesto.get("ok") is not True
        or plan_compuesto.get("estado")
            != "filtro_integrado_pendiente_plan"
        or plan_compuesto.get("ejecutable") is not False
        or plan_compuesto.get("ejecutado") is not False
        or not isinstance(opcion_id, str)
        or not opcion_id
    ):
        return base

    relacion = plan_compuesto.get("relacion")
    restricciones = plan_compuesto.get("restricciones")
    componentes = plan_compuesto.get("componentes")
    pendientes = plan_compuesto.get("pendientes")

    if (
        not isinstance(relacion, dict)
        or not isinstance(restricciones, list)
        or not isinstance(componentes, dict)
        or not isinstance(pendientes, list)
        or relacion.get("certificada_estructuralmente") is not True
    ):
        return base

    temporales = [
        r for r in restricciones
        if isinstance(r, dict) and r.get("tipo") == "ordenamiento"
    ]

    if (
        len(temporales) != 1
        or temporales[0].get("evidencia_presente") is not True
        or temporales[0].get("estado_certificacion") != "pendiente"
    ):
        return {**base, "estado": "ordenamiento_no_pendiente"}

    modelo = relacion.get("modelo_destino")
    evidencia = temporales[0].get("evidencia_textual")

    aclaracion = preparar_aclaracion_orden_temporal(
        modelo, evidencia
    )

    opciones = aclaracion.get("opciones", [])

    coincidencias = [
        o for o in opciones
        if o["id"] == opcion_id
    ]

    if len(coincidencias) != 1:
        return {**base, "estado": "eleccion_orden_no_certificada"}

    elegida = dict(coincidencias[0])

    # Verificación adicional contra HOST en el contexto
    # del modelo; no ejecuta ni certifica el plan completo.
    from ia_local.services.host.validador_plan_datos import (
        validar_plan_datos,
    )
    from ia_local.config.cardinalidad import (
        LIMITE_MAXIMO_SOLICITABLE,
    )

    componente_limite = componentes.get("cardinalidad", {})
    cantidad = componente_limite.get("cantidad_solicitada")

    if (
        componente_limite.get("coincide_con_consolidacion") is not True
        or type(cantidad) is not int
        or not 1 <= cantidad <= LIMITE_MAXIMO_SOLICITABLE
    ):
        return {**base, "estado": "cardinalidad_no_conciliada"}

    propuesta = {
        "modelo": modelo,
        "operacion": "listar",
        "filtros": [],
        "orden": [{
            "campo": elegida["campo"],
            "direccion": "desc",
        }],
        "limite": cantidad,
        "condiciones_no_resueltas": [],
    }

    verificacion = validar_plan_datos(propuesta)

    if (
        verificacion.get("ok") is not True
        or verificacion.get("plan_validado") is not True
    ):
        return {**base, "estado": "orden_rechazado_host"}

    certificado = verificacion.get("plan", {})
    orden = certificado.get("orden")

    if (
        not isinstance(orden, list)
        or len(orden) != 1
        or orden[0].get("campo") != elegida["campo"]
        or orden[0].get("direccion") != "desc"
        or orden[0].get("expresion") != "-" + elegida["campo"]
    ):
        return {**base, "estado": "orden_rechazado_host"}

    nuevas_restricciones = [
        dict(r) for r in restricciones
    ]

    for r in nuevas_restricciones:
        if r.get("tipo") == "ordenamiento":
            r["estado_certificacion"] = (
                "seleccionada_host_aisladamente"
            )
            r["seleccion"] = elegida
            r["certificada_host"] = False
            r["ejecutable"] = False

    nuevos_componentes = {
        k: dict(v) if isinstance(v, dict) else v
        for k, v in componentes.items()
    }

    nuevos_componentes["ordenamiento"] = {
        "estado": "orden_seleccionado_pendiente_plan",
        "seleccion": elegida,
        "certificado_para_plan_compuesto": False,
    }

    nuevos_pendientes = [
        p for p in pendientes
        if p not in {
            "ordenamiento_no_certificado",
            "ordenamiento_pendiente_composicion",
        }
    ]

    nuevos_pendientes.append(
        "orden_seleccionado_pendiente_plan"
    )

    return {
        **base,
        "ok": True,
        "estado": "orden_integrado_pendiente_plan",
        "pregunta_original": plan_compuesto.get("pregunta_original"),
        "relacion": dict(relacion),
        "restricciones": nuevas_restricciones,
        "componentes": nuevos_componentes,
        "pendientes": list(dict.fromkeys(nuevos_pendientes)),
        "requiere_aclaracion": False,
    }



# IA-LLM008-F5-07-06
def conciliar_interpretacion_host(plan_compuesto, interpretacion):
    """
    Contrasta una interpretación HOST con elecciones ya certificadas.

    No interpreta relaciones implícitas, no ejecuta consultas y
    no convierte validaciones parciales en autorización FINAL.

    El plan de entrada debe proceder del flujo de certificación;
    esta función NO autentica la procedencia de sus datos.
    """
    from ia_local.services.host.validador_plan_datos import (
        validar_plan_datos,
    )

    base = {
        "ok": False,
        "version": "IA-LLM008-F5-07-06-v1",
        "estado": "entrada_invalida",
        "discrepancias": [],
        "pendientes": [],
        "plan_estructural_validado": False,
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    if (
        not isinstance(plan_compuesto, dict)
        or not isinstance(interpretacion, dict)
        or plan_compuesto.get("ok") is not True
        or plan_compuesto.get("estado")
            != "orden_integrado_pendiente_plan"
        or plan_compuesto.get("ejecutable") is not False
        or plan_compuesto.get("ejecutado") is not False
        or plan_compuesto.get("cobertura_verificada") is not False
        or plan_compuesto.get("integridad_completa") is not False
    ):
        return base

    pregunta = plan_compuesto.get("pregunta_original")
    relacion = plan_compuesto.get("relacion")
    componentes = plan_compuesto.get("componentes")
    restricciones = plan_compuesto.get("restricciones")
    pendientes = plan_compuesto.get("pendientes")

    if (
        not isinstance(pregunta, str)
        or not pregunta.strip()
        or not isinstance(relacion, dict)
        or not isinstance(componentes, dict)
        or not isinstance(restricciones, list)
        or not isinstance(pendientes, list)
        or not all(isinstance(p, str) for p in pendientes)
        or relacion.get("certificada_estructuralmente") is not True
    ):
        return base

    modelo = relacion.get("modelo_destino")
    filtro = componentes.get("filtro")
    ordenamiento = componentes.get("ordenamiento")
    cardinalidad = componentes.get("cardinalidad")

    if (
        not isinstance(modelo, str)
        or not isinstance(filtro, dict)
        or not isinstance(ordenamiento, dict)
        or not isinstance(cardinalidad, dict)
        or filtro.get("estado")
            != "filtro_seleccionado_pendiente_plan"
        or ordenamiento.get("estado")
            != "orden_seleccionado_pendiente_plan"
        or cardinalidad.get("coincide_con_consolidacion") is not True
    ):
        return {**base, "estado": "componentes_incompatibles"}

    seleccion_filtro = filtro.get("seleccion")
    seleccion_orden = ordenamiento.get("seleccion")
    cantidad = cardinalidad.get("cantidad_solicitada")

    if (
        not isinstance(seleccion_filtro, dict)
        or not isinstance(seleccion_orden, dict)
        or type(cantidad) is not int
        or not 1 <= cantidad <= 100
    ):
        return {**base, "estado": "selecciones_incompletas"}

    campo_filtro = seleccion_filtro.get("campo")
    operador = seleccion_filtro.get("operador")
    valor = seleccion_filtro.get("valor")
    campo_orden = seleccion_orden.get("campo")
    direccion = seleccion_orden.get("direccion")

    if (
        not isinstance(campo_filtro, str)
        or not isinstance(operador, str)
        or not isinstance(campo_orden, str)
        or direccion != "desc"
        or not campo_filtro
        or not operador
        or not campo_orden
        or valor is None
    ):
        return {**base, "estado": "selecciones_incompletas"}

    tipos = [
        r.get("tipo")
        for r in restricciones
        if isinstance(r, dict)
    ]

    if (
        len(tipos) != len(restricciones)
        or tipos.count("limite") != 1
        or tipos.count("filtro") != 1
        or tipos.count("ordenamiento") != 1
        or len(restricciones) != 3
    ):
        return {**base, "estado": "restricciones_incompatibles"}

    estados = {
        r["tipo"]: r.get("estado_certificacion")
        for r in restricciones
    }

    if estados != {
        "limite": "validada_localmente",
        "filtro": "seleccionada_host_aisladamente",
        "ordenamiento": "seleccionada_host_aisladamente",
    }:
        return {**base, "estado": "estados_incompatibles"}

    # La interpretación debe corresponder a la pregunta exacta.
    if (
        interpretacion.get("ok") is not True
        or interpretacion.get("pregunta") != pregunta
        or interpretacion.get("modelo") != modelo
    ):
        return {**base, "estado": "interpretacion_no_vinculada"}

    propuesta_host = interpretacion.get("propuesta")

    if not isinstance(propuesta_host, dict):
        return {**base, "estado": "propuesta_host_ausente"}

    if (
        propuesta_host.get("modelo") != modelo
        or propuesta_host.get("operacion") != "listar"
        or type(propuesta_host.get("limite")) is not int
        or propuesta_host["limite"] != cantidad
    ):
        return {**base, "estado": "contradiccion_host_critica"}

    filtros_host = propuesta_host.get("filtros")
    orden_host = propuesta_host.get("orden")
    condiciones = propuesta_host.get("condiciones_no_resueltas")

    if (
        not isinstance(filtros_host, list)
        or not isinstance(orden_host, list)
        or not isinstance(condiciones, list)
        or not all(
            isinstance(c, str) and c.strip()
            for c in condiciones
        )
    ):
        return {**base, "estado": "contrato_host_incompleto"}

    # La propuesta de HOST no modifica las elecciones previas.
    filtro_elegido = {
        "campo": campo_filtro,
        "operador": operador,
        "valor": valor,
    }
    orden_elegido = {
        "campo": campo_orden,
        "direccion": direccion,
    }

    discrepancias = []

    filtros_normalizados = []
    for f in filtros_host:
        if not isinstance(f, dict):
            return {**base, "estado": "contrato_host_incompleto"}
        filtros_normalizados.append({
            "campo": f.get("campo"),
            "operador": f.get("operador"),
            "valor": f.get("valor"),
        })

    ordenes_normalizados = []
    for o in orden_host:
        if not isinstance(o, dict):
            return {**base, "estado": "contrato_host_incompleto"}
        ordenes_normalizados.append({
            "campo": o.get("campo"),
            "direccion": o.get("direccion"),
        })

    if filtros_normalizados != [filtro_elegido]:
        discrepancias.append("filtro_host_distinto_o_omitido")

    if ordenes_normalizados != [orden_elegido]:
        discrepancias.append("orden_host_distinto_o_omitido")

    # Solo certificamos la composición estructural de las
    # elecciones recibidas. La procedencia se verifica fuera.
    propuesta_conjunta = {
        "modelo": modelo,
        "operacion": "listar",
        "filtros": [dict(filtro_elegido)],
        "orden": [dict(orden_elegido)],
        "limite": cantidad,
        "condiciones_no_resueltas": [],
    }

    validacion = validar_plan_datos(propuesta_conjunta)

    if (
        not isinstance(validacion, dict)
        or validacion.get("ok") is not True
        or validacion.get("plan_validado") is not True
        or not isinstance(validacion.get("plan"), dict)
    ):
        return {
            **base,
            "estado": "composicion_rechazada_host",
            "discrepancias": discrepancias,
        }

    plan_validado = validacion["plan"]

    vf = plan_validado.get("filtros")
    vo = plan_validado.get("orden")

    if (
        plan_validado.get("modelo") != modelo
        or plan_validado.get("operacion") != "listar"
        or plan_validado.get("limite") != cantidad
        or not isinstance(vf, list)
        or len(vf) != 1
        or vf[0].get("campo") != campo_filtro
        or vf[0].get("operador") != operador
        or vf[0].get("valor") != valor
        or not isinstance(vo, list)
        or len(vo) != 1
        or vo[0].get("campo") != campo_orden
        or vo[0].get("direccion") != "desc"
        or vo[0].get("expresion") != "-" + campo_orden
    ):
        return {
            **base,
            "estado": "composicion_inconsistente_host",
        }

    nuevos_pendientes = list(pendientes)

    for codigo in discrepancias:
        if codigo not in nuevos_pendientes:
            nuevos_pendientes.append(codigo)

    # Conservamos íntegramente el residuo semántico;
    # no eliminamos "de los proyectos" por elegir filtro.
    if condiciones:
        codigo = "condiciones_host_no_resueltas"
        if codigo not in nuevos_pendientes:
            nuevos_pendientes.append(codigo)

    for codigo in (
        "vinculo_relacional_semantico_pendiente",
        "cobertura_semantica_total_pendiente",
        "certificacion_conjunta_host_pendiente",
    ):
        if codigo not in nuevos_pendientes:
            nuevos_pendientes.append(codigo)

    return {
        **base,
        "ok": True,
        "estado": "conciliacion_host_diagnostica",
        "pregunta_original": pregunta,
        "modelo": modelo,
        "componentes": componentes,
        "restricciones": [dict(r) for r in restricciones],
        "relacion": dict(relacion),
        "discrepancias": discrepancias,
        "condiciones_host_no_resueltas": list(condiciones),
        "propuesta_host": dict(propuesta_host),
        "plan_estructural_validado": True,
        "plan_estructural": plan_validado,
        "pendientes": list(dict.fromkeys(nuevos_pendientes)),
        "llm_invocado": interpretacion.get("llm_invocado") is True,
    }



# IA-LLM008-F5-07-07-R
def preparar_alcance_relacional_certificado(plan_compuesto):
    """
    Recertifica la ruta relacional y prepara una aclaración.

    No interpreta automáticamente el alcance de la relación.
    No ejecuta consultas ni certifica la pregunta completa.
    """
    from ia_local.services.llm.relaciones_controladas import (
        certificar_relacion,
    )

    base = {
        "ok": False,
        "version": "IA-LLM008-F5-07-07-R-v1",
        "estado": "entrada_invalida",
        "opciones": [],
        "requiere_aclaracion": False,
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    if (
        not isinstance(plan_compuesto, dict)
        or plan_compuesto.get("ok") is not True
        or plan_compuesto.get("estado")
            != "conciliacion_host_diagnostica"
        or plan_compuesto.get("plan_estructural_validado")
            is not True
        or plan_compuesto.get("ejecutable") is not False
        or plan_compuesto.get("ejecutado") is not False
        or plan_compuesto.get("cobertura_verificada") is not False
        or plan_compuesto.get("integridad_completa") is not False
    ):
        return base

    relacion = plan_compuesto.get("relacion")
    pendientes = plan_compuesto.get("pendientes")
    residuos = plan_compuesto.get(
        "condiciones_host_no_resueltas"
    )
    pregunta = plan_compuesto.get("pregunta_original")

    if (
        not isinstance(relacion, dict)
        or not isinstance(pendientes, list)
        or not isinstance(residuos, list)
        or not residuos
        or not all(
            isinstance(r, str) and r.strip()
            for r in residuos
        )
        or not isinstance(pregunta, str)
        or not pregunta.strip()
        or "vinculo_relacional_semantico_pendiente"
            not in pendientes
        or relacion.get("certificada_estructuralmente")
            is not True
        or relacion.get("vinculo_semantico_verificado")
            is not False
    ):
        return {
            **base,
            "estado": "evidencia_relacional_incompleta",
        }

    expresion = relacion.get("expresion_parcial")
    origen = relacion.get("modelo_origen")
    destino = relacion.get("modelo_destino")
    ruta = relacion.get("ruta_orm")

    if not all(
        isinstance(v, str) and v.strip()
        for v in (expresion, origen, destino, ruta)
    ):
        return {
            **base,
            "estado": "contrato_relacional_incompleto",
        }

    # Se vuelve a certificar desde el mecanismo existente.
    # No se confía únicamente en los valores del plan.
    certificacion = certificar_relacion(expresion)

    if (
        not isinstance(certificacion, dict)
        or certificacion.get("ok") is not True
        or certificacion.get("estado")
            != "relacion_certificada"
        or certificacion.get("componente_certificador")
            != "QUERY007"
        or certificacion.get("pregunta") != expresion
        or certificacion.get("modelo_origen") != origen
        or certificacion.get("modelo_destino") != destino
        or certificacion.get("ruta_orm") != ruta
        or certificacion.get("ejecutado") is not False
    ):
        return {
            **base,
            "estado": "relacion_no_recertificada",
        }

    validacion = certificacion.get("validacion_ruta")

    if (
        not isinstance(validacion, dict)
        or validacion.get("ok") is not True
        or validacion.get("valida") is not True
        or validacion.get("origen") != "django_meta"
        or validacion.get("modelo_origen") != origen
        or validacion.get("modelo_destino") != destino
        or validacion.get("ruta_orm") != ruta
        or validacion.get("ejecutado") is True
        or not isinstance(validacion.get("pasos"), list)
        or not validacion["pasos"]
    ):
        return {
            **base,
            "estado": "ruta_host_no_certificada",
        }

    # Las opciones describen decisiones posibles, no
    # determinan cuál corresponde a la intención del usuario.
    opciones = [
        {
            "id": "contexto",
            "tipo": "contexto",
            "descripcion": (
                "La entidad relacionada solo aporta contexto. "
                "No deseo agregar condiciones sobre ella."
            ),
        },
        {
            "id": "restriccion",
            "tipo": "restriccion",
            "descripcion": (
                "Deseo restringir los resultados mediante "
                "una condición sobre la entidad relacionada."
            ),
        },
    ]

    evidencia = {
        "certificador": "QUERY007",
        "modelo_origen": origen,
        "modelo_destino": destino,
        "ruta_orm": ruta,
        "profundidad": validacion.get("profundidad"),
        "contiene_relacion_multiple": validacion.get(
            "contiene_relacion_multiple"
        ),
        "pasos": [
            dict(p) for p in validacion["pasos"]
            if isinstance(p, dict)
        ],
        "validacion_host025": True,
        "vinculo_semantico_verificado": False,
    }

    if len(evidencia["pasos"]) != len(validacion["pasos"]):
        return {
            **base,
            "estado": "pasos_relacionales_invalidos",
        }

    return {
        **base,
        "ok": True,
        "estado": "requiere_aclaracion_alcance_relacional",
        "pregunta_original": pregunta,
        "evidencia_relacional": evidencia,
        "residuo_semantico": list(residuos),
        "opciones": opciones,
        "requiere_aclaracion": True,
        "decision_confirmada": False,
        "pendientes": list(pendientes),
    }



# IA-LLM008-F5-07-08-C
# IA-LLM008-F5-07-10-A-v1
def incorporar_decision_relacional(plan, confirmacion):
    """
    Registra una decisión relacional en un plan diagnóstico.

    No autentica una confirmación recibida desde una fuente
    arbitraria. Solo debe utilizarse después del mecanismo
    de sesión y dentro de un flujo servidor confiable.
    No ejecuta ni certifica cobertura completa.
    """
    from copy import deepcopy

    base = {
        "ok": False,
        "version": "IA-LLM008-F5-07-08-C-v1",
        "estado": "entrada_invalida",
        "ejecutable": False,
        "ejecutado": False,
        "cobertura_verificada": False,
        "integridad_completa": False,
        "llm_invocado": False,
    }

    if (
        not isinstance(plan, dict)
        or not isinstance(confirmacion, dict)
        or plan.get("ok") is not True
        or plan.get("estado") != "conciliacion_host_diagnostica"
        or plan.get("plan_estructural_validado") is not True
        or plan.get("ejecutable") is not False
        or plan.get("ejecutado") is not False
        or plan.get("cobertura_verificada") is not False
        or plan.get("integridad_completa") is not False
        or confirmacion.get("ok") is not True
        or confirmacion.get("estado")
            != "alcance_relacional_seleccionado"
        or confirmacion.get("ejecutable") is not False
        or confirmacion.get("ejecutado") is not False
    ):
        return base

    pregunta = plan.get("pregunta_original")
    relacion = plan.get("relacion")
    pendientes = plan.get("pendientes")
    residuos = plan.get("condiciones_host_no_resueltas")

    if (
        not isinstance(pregunta, str)
        or not pregunta.strip()
        or confirmacion.get("pregunta_original") != pregunta
        or not isinstance(relacion, dict)
        or not isinstance(pendientes, list)
        or not isinstance(residuos, list)
        or not residuos
        or not all(
            isinstance(r, str) and r.strip() for r in residuos
        )
        or "vinculo_relacional_semantico_pendiente"
            not in pendientes
    ):
        return {**base, "estado": "plan_no_vinculado"}


    restricciones = plan.get("restricciones")

    if (
        not isinstance(restricciones, list)
        or not all(
            isinstance(r, dict)
            and isinstance(r.get("tipo"), str)
            and r.get("tipo", "").strip()
            and isinstance(r.get("evidencia_textual"), str)
            and r.get("evidencia_textual", "").strip()
            for r in restricciones
        )
    ):
        return {
            **base,
            "estado": "restricciones_no_disponibles",
        }

    evidencia = confirmacion.get("evidencia_relacional")
    residuo_confirmado = confirmacion.get("residuo_semantico")
    decision = confirmacion.get("decision")

    if (
        not isinstance(evidencia, dict)
        or decision not in ("contexto", "restriccion")
        or residuo_confirmado != residuos
        or evidencia.get("certificador") != "QUERY007"
        or evidencia.get("validacion_host025") is not True
        or evidencia.get("vinculo_semantico_verificado") is not False
    ):
        return {**base, "estado": "confirmacion_incompatible"}

    claves = (
        "modelo_origen",
        "modelo_destino",
        "ruta_orm",
    )

    if any(
        evidencia.get(clave) != relacion.get(clave)
        or not isinstance(evidencia.get(clave), str)
        for clave in claves
    ):
        return {**base, "estado": "relacion_no_coincide"}

    # La decisión confirma la intención declarada, pero no
    # resuelve por sí sola la cobertura de la pregunta.
    nuevos_pendientes = list(pendientes)

    if decision == "contexto":
        estado = "relacion_declarada_como_contexto"
        pendientes_adicionales = [
            "verificacion_contexto_semantico_pendiente",
        ]
    else:
        estado = "restriccion_relacional_declarada"
        pendientes_adicionales = [
            "condicion_relacional_concreta_pendiente",
        ]

    for codigo in pendientes_adicionales:
        if codigo not in nuevos_pendientes:
            nuevos_pendientes.append(codigo)

    for codigo in (
        "vinculo_relacional_semantico_pendiente",
        "cobertura_semantica_total_pendiente",
        "certificacion_conjunta_host_pendiente",
    ):
        if codigo not in nuevos_pendientes:
            nuevos_pendientes.append(codigo)

    return {
        **base,
        "ok": True,
        "estado": "decision_relacional_registrada",
        "pregunta_original": pregunta,
        "modelo": plan.get("modelo"),
        "decision": decision,
        "estado_alcance": estado,
        "relacion": dict(relacion),
        "residuo_semantico": list(residuos),
        "evidencia_relacional": dict(evidencia),
        "plan_estructural_validado": True,
        "plan_estructural": dict(plan["plan_estructural"]),
        "restricciones": deepcopy(restricciones),
        "pendientes": list(dict.fromkeys(nuevos_pendientes)),
        "requiere_validacion_plan_completo": True,
    }



# IA-LLM008-F5-07-09
def auditar_cobertura_trazable(
    pregunta, consolidacion, plan
):
    """
    Compara restricciones consolidadas con la trazabilidad.

    Es un control de conservación, NO un detector exhaustivo
    ni una certificación de ejecución.
    """
    base = {
        "ok": False,
        "version": "IA-LLM008-F5-07-09-v1",
        "estado": "entrada_invalida",
        "restricciones_auditadas": [],
        "faltantes": [],
        "conservacion_completa": False,
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    if (
        not isinstance(pregunta, str)
        or not pregunta.strip()
        or not isinstance(consolidacion, dict)
        or not isinstance(plan, dict)
        or consolidacion.get("ok") is not True
        or plan.get("ok") is not True
        or plan.get("pregunta_original") != pregunta
        or consolidacion.get("pregunta") != pregunta
        or plan.get("ejecutable") is not False
        or plan.get("ejecutado") is not False
    ):
        return base

    originales = consolidacion.get("restricciones")
    conservadas = plan.get("restricciones")

    if (
        not isinstance(originales, list)
        or not isinstance(conservadas, list)
        or not originales
        or not all(isinstance(r, dict) for r in originales)
        or not all(isinstance(r, dict) for r in conservadas)
    ):
        return {**base, "estado": "contrato_incompleto"}

    def identidad(r):
        return (
            r.get("tipo"),
            r.get("evidencia_textual"),
            r.get("valor_propuesto"),
        )

    # Conservamos multiplicidad: dos filtros del mismo tipo
    # no deben confundirse con una sola restricción.
    usadas = set()
    auditadas = []
    faltantes = []

    for indice, original in enumerate(originales):
        tipo = original.get("tipo")
        texto = original.get("evidencia_textual")

        if (
            not isinstance(tipo, str)
            or not tipo.strip()
            or not isinstance(texto, str)
            or not texto.strip()
        ):
            faltantes.append({
                "indice": indice,
                "motivo": "evidencia_original_invalida",
            })
            continue

        presente = texto.casefold() in pregunta.casefold()

        coincidencia = None
        for j, candidata in enumerate(conservadas):
            if j in usadas:
                continue
            if identidad(candidata) == identidad(original):
                coincidencia = j
                usadas.add(j)
                break

        traza = (
            conservadas[coincidencia]
            if coincidencia is not None
            else None
        )

        conservada = traza is not None
        estado = (
            traza.get("estado_certificacion", "sin_estado")
            if conservada
            else "ausente"
        )

        valida_localmente = (
            estado == "validada_localmente"
        )
        seleccionada_host = (
            estado == "seleccionada_host_aisladamente"
        )

        auditadas.append({
            "indice": indice,
            "tipo": tipo,
            "evidencia_textual": texto,
            "presente_en_pregunta": presente,
            "conservada_en_plan": conservada,
            "estado_certificacion": estado,
            "validada_localmente": valida_localmente,
            "seleccionada_host_aisladamente": seleccionada_host,
            "certificada_plan_completo": False,
        })

        if not presente or not conservada:
            faltantes.append({
                "indice": indice,
                "tipo": tipo,
                "motivo": (
                    "evidencia_ausente_en_pregunta"
                    if not presente
                    else "restriccion_no_conservada"
                ),
            })

    # Las restricciones adicionales no pueden introducirse
    # silenciosamente como si provinieran del usuario.
    adicionales = [
        j for j in range(len(conservadas))
        if j not in usadas
    ]

    for j in adicionales:
        faltantes.append({
            "indice_plan": j,
            "motivo": "restriccion_adicional_no_conciliada",
        })

    conservacion_completa = (
        not faltantes
        and len(auditadas) == len(originales)
        and len(usadas) == len(conservadas)
    )

    return {
        **base,
        "ok": True,
        "estado": (
            "restricciones_conservadas_sin_cobertura_certificada"
            if conservacion_completa
            else "inconsistencia_de_trazabilidad"
        ),
        "pregunta_original": pregunta,
        "restricciones_auditadas": auditadas,
        "total_originales": len(originales),
        "total_conservadas": len(conservadas),
        "faltantes": faltantes,
        "conservacion_completa": conservacion_completa,
        "pendientes": list(plan.get("pendientes", []))
            if isinstance(plan.get("pendientes"), list)
            else ["pendientes_no_disponibles"],
    }



# IA-LLM008-F5-07-11-A
def preparar_coleccion_restricciones(consolidacion):
    """
    Normaliza una colección variable de restricciones.

    Los identificadores son deterministas dentro de la
    colección y de su pregunta original.

    No interpreta, certifica ni ejecuta consultas.
    """
    from copy import deepcopy
    from hashlib import sha256
    import json

    base = {
        "ok": False,
        "version": "IA-LLM008-F5-07-11-A-v1",
        "estado": "entrada_invalida",
        "pregunta_original": None,
        "identificador_coleccion": None,
        "restricciones": [],
        "total_restricciones": 0,
        "tipos_presentes": [],
        "pendientes": [],
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    if not isinstance(consolidacion, dict):
        return base

    pregunta = consolidacion.get("pregunta")
    originales = consolidacion.get("restricciones")

    if (
        consolidacion.get("ok") is not True
        or consolidacion.get("estado")
            != "consolidacion_diagnostica"
        or consolidacion.get("ejecutable") is not False
        or consolidacion.get("ejecutado") is not False
        or not isinstance(pregunta, str)
        or not pregunta.strip()
        or not isinstance(originales, list)
    ):
        return base

    # Copia independiente del diagnóstico.
    try:
        datos = deepcopy(originales)
    except (TypeError, ValueError, RecursionError):
        return {
            **base,
            "estado": "restricciones_no_copiables",
        }

    # Se exige una estructura de datos JSON, apta para
    # contratos de sesión y trazabilidad.
    try:
        serializado = json.dumps(
            {
                "pregunta": pregunta,
                "restricciones": datos,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError):
        return {
            **base,
            "estado": "restricciones_no_serializables",
        }

    for indice, original in enumerate(datos):
        if not isinstance(original, dict):
            return {
                **base,
                "estado": "restriccion_invalida",
                "indice_error": indice,
            }

        tipo = original.get("tipo")
        evidencia = original.get("evidencia_textual")

        if (
            not isinstance(tipo, str)
            or not tipo.strip()
            or not isinstance(evidencia, str)
            or not evidencia.strip()
            or evidencia.casefold()
                not in pregunta.casefold()
        ):
            return {
                **base,
                "estado": "evidencia_invalida",
                "indice_error": indice,
            }

        # No aceptar una entrada que se proclame ejecutable
        # o ya certificada por HOST.
        if (
            original.get("ejecutable") is True
            or original.get("ejecutado") is True
            or original.get("certificada_host") is True
            or original.get("certificada_plan_completo") is True
        ):
            return {
                **base,
                "estado": "certificacion_prematura",
                "indice_error": indice,
            }

    huella = sha256(
        serializado.encode("utf-8")
    ).hexdigest()

    coleccion = []
    tipos = []
    pendientes = []

    for indice, original in enumerate(datos):
        tipo = original["tipo"]
        evidencia = original["evidencia_textual"]

        # El índice distingue ocurrencias duplicadas.
        # La huella vincula el ID a la entrada completa.
        identificador = (
            "r"
            + str(indice + 1).zfill(4)
            + "-"
            + huella[:16]
        )

        restriccion = {
            "id": identificador,
            "indice_original": indice,
            "tipo": tipo,
            "evidencia_textual": evidencia,
            "origen": original.get("origen"),
            "datos_originales": deepcopy(original),
            "estado_certificacion": "pendiente",
            "seleccion": None,
            "certificada_host": False,
            "certificada_plan_completo": False,
            "ejecutable": False,
        }

        coleccion.append(restriccion)
        pendientes.append(identificador)

        if tipo not in tipos:
            tipos.append(tipo)

    return {
        **base,
        "ok": True,
        "estado": "coleccion_normalizada_pendiente",
        "pregunta_original": pregunta,
        "identificador_coleccion": huella,
        "restricciones": coleccion,
        "total_restricciones": len(coleccion),
        "tipos_presentes": tipos,
        "pendientes": pendientes,
    }



# IA-LLM008-F5-07-11-B-v1
def _verificar_coleccion_identificada(coleccion):
    """Comprueba la coherencia de la colección normalizada."""
    if not isinstance(coleccion, dict):
        return False

    if (
        coleccion.get("ok") is not True
        or coleccion.get("estado") not in {
            "coleccion_normalizada_pendiente",
            "coleccion_con_selecciones_pendientes",
        }
        or coleccion.get("ejecutable") is not False
        or coleccion.get("ejecutado") is not False
        or coleccion.get("cobertura_verificada") is not False
        or coleccion.get("integridad_completa") is not False
    ):
        return False

    restricciones = coleccion.get("restricciones")
    pregunta = coleccion.get("pregunta_original")
    identificador = coleccion.get("identificador_coleccion")

    if (
        not isinstance(restricciones, list)
        or not isinstance(pregunta, str)
        or not isinstance(identificador, str)
        or type(coleccion.get("total_restricciones")) is not int
        or coleccion["total_restricciones"] != len(restricciones)
    ):
        return False

    originales = []

    for indice, r in enumerate(restricciones):
        if not isinstance(r, dict):
            return False

        original = r.get("datos_originales")

        if not isinstance(original, dict):
            return False

        if (
            r.get("indice_original") != indice
            or r.get("tipo") != original.get("tipo")
            or r.get("evidencia_textual")
                != original.get("evidencia_textual")
            or r.get("origen") != original.get("origen")
            or r.get("ejecutable") is not False
            or r.get("certificada_host") is not False
            or r.get("certificada_plan_completo") is not False
            or r.get("estado_certificacion") not in {
                "pendiente",
                "seleccionada_host_aisladamente",
            }
        ):
            return False

        if (
            r["estado_certificacion"] == "pendiente"
            and r.get("seleccion") is not None
        ):
            return False

        if (
            r["estado_certificacion"]
                == "seleccionada_host_aisladamente"
            and not isinstance(r.get("seleccion"), dict)
        ):
            return False

        originales.append(original)

    regenerada = preparar_coleccion_restricciones({
        "ok": True,
        "estado": "consolidacion_diagnostica",
        "pregunta": pregunta,
        "restricciones": originales,
        "ejecutable": False,
        "ejecutado": False,
    })

    if (
        regenerada.get("ok") is not True
        or regenerada.get("identificador_coleccion")
            != identificador
        or [
            r.get("id") for r in restricciones
        ] != [
            r["id"] for r in regenerada["restricciones"]
        ]
    ):
        return False

    esperados = [
        r["id"] for r in restricciones
        if r["estado_certificacion"] == "pendiente"
    ]

    return coleccion.get("pendientes") == esperados


def preparar_opciones_restriccion(
    coleccion, restriccion_id, modelo
):
    """Descubre opciones para una sola restricción."""
    base = {
        "ok": False,
        "version": "IA-LLM008-F5-07-11-B-v1",
        "estado": "entrada_invalida",
        "opciones": [],
        "ejecutable": False,
        "ejecutado": False,
        "cobertura_verificada": False,
        "integridad_completa": False,
    }

    if (
        not _verificar_coleccion_identificada(coleccion)
        or not isinstance(restriccion_id, str)
        or not isinstance(modelo, str)
        or not modelo.strip()
    ):
        return base

    contexto_previo = coleccion.get("modelo_contexto")

    if (
        contexto_previo is not None
        and contexto_previo != modelo
    ):
        return {**base, "estado": "modelo_contexto_distinto"}

    coincidencias = [
        r for r in coleccion["restricciones"]
        if r["id"] == restriccion_id
    ]

    if len(coincidencias) != 1:
        return {**base, "estado": "restriccion_no_encontrada"}

    r = coincidencias[0]

    if r["estado_certificacion"] != "pendiente":
        return {**base, "estado": "restriccion_ya_seleccionada"}

    tipo = r["tipo"]
    evidencia = r["evidencia_textual"]

    if tipo == "filtro":
        from ia_local.services.host.desambiguacion_filtros import (
            preparar_aclaracion_filtro,
        )
        resultado = preparar_aclaracion_filtro(
            modelo, evidencia
        )
    elif tipo == "ordenamiento":
        resultado = preparar_aclaracion_orden_temporal(
            modelo, evidencia
        )
    else:
        return {
            **base,
            "estado": "tipo_sin_certificador_disponible",
        }

    opciones = resultado.get("opciones")

    if (
        resultado.get("ok") is not True
        or resultado.get("modelo") != modelo
        or resultado.get("evidencia_textual") != evidencia
        or not isinstance(opciones, list)
        or not opciones
        or not all(
            isinstance(o, dict)
            and isinstance(o.get("id"), str)
            for o in opciones
        )
        or len({o["id"] for o in opciones}) != len(opciones)
    ):
        return {
            **base,
            "estado": "alternativas_no_certificadas",
        }

    from copy import deepcopy

    return {
        **base,
        "ok": True,
        "estado": "opciones_restriccion_preparadas",
        "identificador_coleccion":
            coleccion["identificador_coleccion"],
        "restriccion_id": restriccion_id,
        "tipo": tipo,
        "modelo": modelo,
        "evidencia_textual": evidencia,
        "opciones": deepcopy(opciones),
        "requiere_aclaracion": len(opciones) > 1,
    }


def incorporar_eleccion_restriccion(
    coleccion, restriccion_id, modelo, opcion_id
):
    """
    Recertifica una elección y modifica únicamente su restricción.

    Contrato diagnóstico: el llamador debe validar previamente
    identidad, token, sesión y vinculación con el plan.
    """
    from copy import deepcopy

    base = {
        "ok": False,
        "version": "IA-LLM008-F5-07-11-B-v1",
        "estado": "entrada_invalida",
        "ejecutable": False,
        "ejecutado": False,
        "cobertura_verificada": False,
        "integridad_completa": False,
    }

    if (
        not isinstance(opcion_id, str)
        or not opcion_id
        or len(opcion_id) > 256
    ):
        return base

    preparacion = preparar_opciones_restriccion(
        coleccion, restriccion_id, modelo
    )

    if preparacion.get("ok") is not True:
        return {
            **base,
            "estado": preparacion.get(
                "estado", "aclaracion_no_disponible"
            ),
        }

    opciones = [
        o for o in preparacion["opciones"]
        if o["id"] == opcion_id
    ]

    if len(opciones) != 1:
        return {**base, "estado": "opcion_ajena_a_restriccion"}

    tipo = preparacion["tipo"]

    if tipo == "filtro":
        from ia_local.services.host.desambiguacion_filtros import (
            verificar_eleccion_filtro,
        )

        certificacion = verificar_eleccion_filtro(
            modelo,
            preparacion["evidencia_textual"],
            opcion_id,
        )

        if (
            certificacion.get("ok") is not True
            or certificacion.get("certificada_host") is not True
            or certificacion.get("estado")
                != "eleccion_filtro_certificada"
            or certificacion.get("modelo") != modelo
            or certificacion.get("evidencia_textual")
                != preparacion["evidencia_textual"]
        ):
            return {**base, "estado": "eleccion_rechazada_host"}

        seleccion = certificacion.get("seleccion")

        if seleccion != opciones[0]:
            return {
                **base,
                "estado": "certificacion_no_coincide",
            }

    elif tipo == "ordenamiento":
        # Cada opción ya pasó por validar_plan_datos()
        # durante el descubrimiento del campo temporal.
        seleccion = opciones[0]

    else:
        return {**base, "estado": "tipo_no_soportado"}

    nuevas = deepcopy(coleccion["restricciones"])

    seleccionadas = 0

    for r in nuevas:
        if r["id"] != restriccion_id:
            continue

        r["estado_certificacion"] = (
            "seleccionada_host_aisladamente"
        )
        r["seleccion"] = deepcopy(seleccion)
        r["certificada_host"] = False
        r["certificada_plan_completo"] = False
        r["ejecutable"] = False
        seleccionadas += 1

    if seleccionadas != 1:
        return {**base, "estado": "identidad_inconsistente"}

    pendientes = [
        r["id"] for r in nuevas
        if r["estado_certificacion"] == "pendiente"
    ]

    actualizado = {
        **deepcopy(coleccion),
        "ok": True,
        "version": "IA-LLM008-F5-07-11-B-v1",
        "estado": "coleccion_con_selecciones_pendientes",
        "modelo_contexto": modelo,
        "restricciones": nuevas,
        "pendientes": pendientes,
        "ultima_restriccion_seleccionada": restriccion_id,
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
    }

    if not _verificar_coleccion_identificada(actualizado):
        return {**base, "estado": "coleccion_resultante_invalida"}

    return actualizado



# IA-LLM008-F5-07-11-C-v1
def componer_coleccion_recertificada(
    coleccion, modelo, operacion, limite
):
    """
    Recertifica selecciones y valida su composición mediante HOST.

    No certifica la intención original, procedencia de sesión,
    cobertura semántica ni autorización de ejecución.
    """
    from copy import deepcopy
    from ia_local.services.host.validador_plan_datos import (
        validar_plan_datos,
    )
    from ia_local.services.host.desambiguacion_filtros import (
        verificar_eleccion_filtro,
    )

    base = {
        "ok": False,
        "version": "IA-LLM008-F5-07-11-C-v1",
        "estado": "entrada_invalida",
        "plan_estructural_validado": False,
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
    }

    if (
        not _verificar_coleccion_identificada(coleccion)
        or not isinstance(modelo, str)
        or not modelo.strip()
        or not isinstance(operacion, str)
        or not operacion.strip()
        or type(limite) is not int
        or coleccion.get("pendientes")
        or coleccion.get("modelo_contexto") not in (None, modelo)
    ):
        return base

    filtros = []
    ordenes = []
    evidencias = []

    for r in coleccion["restricciones"]:
        if (
            r.get("estado_certificacion")
                != "seleccionada_host_aisladamente"
            or not isinstance(r.get("seleccion"), dict)
        ):
            return {**base, "estado": "seleccion_incompleta"}

        tipo = r["tipo"]
        opcion = r["seleccion"]
        opcion_id = opcion.get("id")

        if not isinstance(opcion_id, str) or not opcion_id:
            return {**base, "estado": "opcion_sin_identidad"}

        # Descubrimiento nuevamente desde el modelo real.
        preparacion = preparar_opciones_restriccion_revalidada(
            coleccion, r, modelo
        )

        if preparacion.get("ok") is not True:
            return {
                **base,
                "estado": "recertificacion_no_disponible",
            }

        coincidencias = [
            o for o in preparacion["opciones"]
            if o.get("id") == opcion_id
        ]

        if (
            len(coincidencias) != 1
            or coincidencias[0] != opcion
        ):
            return {
                **base,
                "estado": "seleccion_alterada_o_no_certificada",
            }

        if tipo == "filtro":
            certificado = verificar_eleccion_filtro(
                modelo, r["evidencia_textual"], opcion_id
            )

            if (
                certificado.get("ok") is not True
                or certificado.get("certificada_host") is not True
                or certificado.get("modelo") != modelo
                or certificado.get("evidencia_textual")
                    != r["evidencia_textual"]
                or certificado.get("seleccion") != opcion
            ):
                return {
                    **base,
                    "estado": "filtro_rechazado_host",
                }

            filtros.append({
                "campo": opcion["campo"],
                "operador": opcion["operador"],
                "valor": opcion["valor"],
            })

        elif tipo == "ordenamiento":
            if (
                not isinstance(opcion.get("campo"), str)
                or opcion.get("direccion") != "desc"
            ):
                return {
                    **base,
                    "estado": "ordenamiento_incompatible",
                }

            ordenes.append({
                "campo": opcion["campo"],
                "direccion": opcion["direccion"],
            })

        else:
            return {
                **base,
                "estado": "tipo_sin_compositor_certificado",
            }

        evidencias.append({
            "restriccion_id": r["id"],
            "tipo": tipo,
            "opcion_id": opcion_id,
            "recertificada": True,
        })

    propuesta = {
        "modelo": modelo,
        "operacion": operacion,
        "filtros": filtros,
        "orden": ordenes,
        "limite": limite,
        "condiciones_no_resueltas": [],
    }

    validacion = validar_plan_datos(propuesta)

    if (
        not isinstance(validacion, dict)
        or validacion.get("ok") is not True
        or validacion.get("plan_validado") is not True
        or not isinstance(validacion.get("plan"), dict)
    ):
        return {
            **base,
            "estado": "composicion_rechazada_host",
        }

    validado = validacion["plan"]

    vf = validado.get("filtros")
    vo = validado.get("orden")

    if (
        validado.get("modelo") != modelo
        or validado.get("operacion") != operacion
        or validado.get("limite") != limite
        or not isinstance(vf, list)
        or not isinstance(vo, list)
        or len(vf) != len(filtros)
        or len(vo) != len(ordenes)
        or any(
            not isinstance(a, dict)
            or any(a.get(k) != b.get(k) for k in (
                "campo", "operador", "valor"
            ))
            for a, b in zip(vf, filtros)
        )
        or any(
            not isinstance(a, dict)
            or a.get("campo") != b["campo"]
            or a.get("direccion") != b["direccion"]
            or a.get("expresion") != "-" + b["campo"]
            for a, b in zip(vo, ordenes)
        )
    ):
        return {
            **base,
            "estado": "composicion_inconsistente_host",
        }

    return {
        **base,
        "ok": True,
        "estado": "composicion_estructural_diagnostica",
        "pregunta_original": coleccion["pregunta_original"],
        "identificador_coleccion":
            coleccion["identificador_coleccion"],
        "modelo": modelo,
        "restricciones": deepcopy(coleccion["restricciones"]),
        "evidencias_recertificacion": evidencias,
        "plan_estructural_validado": True,
        "plan_estructural": deepcopy(validado),
        "pendientes": [
            "procedencia_sesion_pendiente",
            "operacion_y_limite_semanticos_pendientes",
            "cobertura_semantica_total_pendiente",
            "certificacion_integral_pendiente",
        ],
    }


def preparar_opciones_restriccion_revalidada(
    coleccion, restriccion, modelo
):
    """
    Reconstruye opciones para una restricción ya seleccionada,
    sin depender del estado pendiente que exige el preparador
    interactivo.
    """
    from ia_local.services.host.desambiguacion_filtros import (
        preparar_aclaracion_filtro,
    )

    tipo = restriccion.get("tipo")
    evidencia = restriccion.get("evidencia_textual")

    if tipo == "filtro":
        resultado = preparar_aclaracion_filtro(modelo, evidencia)
    elif tipo == "ordenamiento":
        resultado = preparar_aclaracion_orden_temporal(
            modelo, evidencia
        )
    else:
        return {"ok": False, "opciones": []}

    if (
        resultado.get("ok") is not True
        or resultado.get("modelo") != modelo
        or resultado.get("evidencia_textual") != evidencia
        or not isinstance(resultado.get("opciones"), list)
    ):
        return {"ok": False, "opciones": []}

    return resultado



# IA-LLM008-F5-07-12-C01
def verificar_equivalencia_logica(
    coleccion, resultado_query, asociaciones
):
    """
    Contrasta hojas QUERY003 con elecciones HOST de LLM008.

    asociaciones:
        {restriccion_id: indice_hoja_query}

    No reconstruye ni ejecuta el árbol.
    No certifica procedencia, intención ni cobertura completa.
    """
    from copy import deepcopy

    from ia_local.services.host.desambiguacion_filtros import (
        verificar_eleccion_filtro,
    )

    base = {
        "ok": False,
        "version": "IA-LLM008-F5-07-12-C01-v1",
        "estado": "entrada_invalida",
        "discrepancias": [],
        "vinculos": [],
        "plan_estructural_validado": False,
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
    }

    if (
        not _verificar_coleccion_identificada(coleccion)
        or not isinstance(resultado_query, dict)
        or not isinstance(asociaciones, dict)
        or resultado_query.get("ok") is not True
        or resultado_query.get("estado")
            != "arbol_logico_validado"
        or resultado_query.get("modo")
            != "agrupacion_logica"
        or resultado_query.get("ejecutado") is not False
    ):
        return base

    contrato = resultado_query.get("contrato_logico")
    resoluciones = resultado_query.get("resoluciones")

    if (
        not isinstance(contrato, dict)
        or not isinstance(resoluciones, list)
        or not isinstance(contrato.get("modelo"), str)
        or not isinstance(contrato.get("operacion"), str)
    ):
        return base

    modelo = contrato["modelo"]

    if coleccion.get("modelo_contexto") != modelo:
        return {
            **base,
            "estado": "modelo_no_vinculado",
        }

    restricciones = coleccion["restricciones"]

    if (
        not restricciones
        or len(restricciones) != len(asociaciones)
        or len(restricciones) != len(resoluciones)
        or set(asociaciones) != {
            r["id"] for r in restricciones
        }
        or any(
            type(indice) is not int
            for indice in asociaciones.values()
        )
        or set(asociaciones.values())
            != set(range(len(restricciones)))
        or resultado_query.get("cantidad_condiciones")
            != len(restricciones)
    ):
        return {
            **base,
            "estado": "asociacion_incompleta_o_ambigua",
        }

    # Inspeccionar todo el árbol y rechazar estructuras
    # desconocidas, ciclos y hojas duplicadas.
    hojas = {}
    operadores = []
    nodos_vistos = set()

    def recorrer(nodo, profundidad=0):
        if (
            profundidad > 64
            or not isinstance(nodo, dict)
            or id(nodo) in nodos_vistos
        ):
            raise ValueError("arbol_invalido")

        nodos_vistos.add(id(nodo))

        if nodo.get("tipo") == "CONDICION":
            indice = nodo.get("indice")

            if (
                type(indice) is not int
                or indice in hojas
            ):
                raise ValueError("hoja_duplicada")

            hojas[indice] = nodo
            return

        if nodo.get("tipo") != "GRUPO":
            raise ValueError("tipo_logico_desconocido")

        operador = nodo.get("operador")
        hijos = nodo.get("hijos")

        if (
            operador not in ("AND", "OR")
            or not isinstance(hijos, list)
            or len(hijos) < 2
        ):
            raise ValueError("grupo_logico_invalido")

        operadores.append(operador)

        for hijo in hijos:
            recorrer(hijo, profundidad + 1)

    try:
        recorrer(contrato.get("arbol_logico"))
    except (ValueError, RecursionError):
        return {
            **base,
            "estado": "arbol_logico_invalido",
        }

    if set(hojas) != set(range(len(restricciones))):
        return {
            **base,
            "estado": "hojas_incompletas",
        }

    resoluciones_por_indice = {}

    for resolucion in resoluciones:
        if not isinstance(resolucion, dict):
            return {
                **base,
                "estado": "resoluciones_invalidas",
            }

        indice = resolucion.get("indice")

        if (
            type(indice) is not int
            or indice in resoluciones_por_indice
            or indice not in hojas
            or resolucion.get("modelo") != modelo
            or resolucion.get("operacion")
                != contrato["operacion"]
        ):
            return {
                **base,
                "estado": "resoluciones_incompatibles",
            }

        resoluciones_por_indice[indice] = resolucion

    discrepancias = []
    vinculos = []

    for r in restricciones:
        restriccion_id = r["id"]
        indice = asociaciones[restriccion_id]

        if (
            r.get("tipo") != "filtro"
            or r.get("estado_certificacion")
                != "seleccionada_host_aisladamente"
            or not isinstance(r.get("seleccion"), dict)
        ):
            return {
                **base,
                "estado": "restriccion_no_preparada",
            }

        seleccion = r["seleccion"]
        opcion_id = seleccion.get("id")
        evidencia = r["evidencia_textual"]

        if not isinstance(opcion_id, str):
            return {
                **base,
                "estado": "opcion_invalida",
            }

        # Revalidar contra HOST; no confiar en el diccionario.
        certificado = verificar_eleccion_filtro(
            modelo, evidencia, opcion_id
        )

        if (
            certificado.get("ok") is not True
            or certificado.get("certificada_host") is not True
            or certificado.get("modelo") != modelo
            or certificado.get("evidencia_textual") != evidencia
            or certificado.get("seleccion") != seleccion
        ):
            return {
                **base,
                "estado": "seleccion_rechazada_host",
            }

        hoja = hojas[indice]
        resolucion = resoluciones_por_indice[indice]
        filtro_query = resolucion.get("filtro")

        if not isinstance(filtro_query, dict):
            return {
                **base,
                "estado": "filtro_query_invalido",
            }

        # Verificar coherencia entre hoja y resolución.
        pares = (
            ("campo", "campo"),
            ("operador", "operador"),
            ("valor", "valor"),
            ("lookup", "lookup"),
            ("tipo_django", "tipo"),
        )

        if any(
            hoja.get(campo_hoja)
                != filtro_query.get(campo_filtro)
            for campo_hoja, campo_filtro in pares
        ):
            return {
                **base,
                "estado": "hoja_resolucion_incompatible",
            }

        filtro_host = {
            "campo": seleccion.get("campo"),
            "operador": seleccion.get("operador"),
            "valor": seleccion.get("valor"),
        }

        filtro_query_comparable = {
            clave: filtro_query.get(clave)
            for clave in ("campo", "operador", "valor")
        }

        coincide = filtro_host == filtro_query_comparable

        vinculos.append({
            "restriccion_id": restriccion_id,
            "indice_query": indice,
            "coincidencia_exacta": coincide,
        })

        if not coincide:
            discrepancias.append({
                "restriccion_id": restriccion_id,
                "indice_query": indice,
                "codigo": "filtro_query_host_distinto",
                "filtro_host": deepcopy(filtro_host),
                "filtro_query": deepcopy(
                    filtro_query_comparable
                ),
            })

    if discrepancias:
        return {
            **base,
            "ok": True,
            "estado": "equivalencia_logica_con_discrepancias",
            "discrepancias": discrepancias,
            "vinculos": vinculos,
            "operadores_detectados": operadores,
        }

    return {
        **base,
        "ok": True,
        "estado": "equivalencia_estructural_diagnostica",
        "vinculos": vinculos,
        "operadores_detectados": operadores,
        "pendientes": [
            "autenticidad_query_y_asociaciones_pendiente",
            "procedencia_sesion_pendiente",
            "cobertura_semantica_total_pendiente",
            "certificacion_integral_pendiente",
        ],
    }



# IA-LLM008-F5-07-12-C02
def reconstruir_arbol_logico_certificado(
    coleccion, resultado_query, asociaciones
):
    """
    Reconstruye hojas QUERY003 desde elecciones HOST.

    Conserva operadores y estructura. No autentica asociaciones,
    no verifica intención completa y nunca autoriza FINAL.
    """
    from copy import deepcopy

    from ia_local.services.host.desambiguacion_filtros import (
        verificar_eleccion_filtro,
    )
    from ia_local.services.host.validador_plan_datos import (
        validar_plan_datos,
    )
    from ia_local.config.cardinalidad import (
        LIMITE_MAXIMO_SOLICITABLE,
    )

    base = {
        "ok": False,
        "version": "IA-LLM008-F5-07-12-C02-v1",
        "estado": "entrada_invalida",
        "arbol_derivado": None,
        "equivalencias": [],
        "arbol_derivado_validado_host": False,
        "plan_estructural_validado": False,
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    # Reutilizamos la auditoría de C01.
    auditoria = verificar_equivalencia_logica(
        coleccion, resultado_query, asociaciones
    )

    if (
        auditoria.get("ok") is not True
        or auditoria.get("estado") not in {
            "equivalencia_logica_con_discrepancias",
            "equivalencia_estructural_diagnostica",
        }
    ):
        return {
            **base,
            "estado": "equivalencia_previa_rechazada",
            "detalle": auditoria.get("estado"),
        }

    contrato = resultado_query["contrato_logico"]
    modelo = contrato["modelo"]
    operacion = contrato["operacion"]
    limite = contrato.get("limite")

    if (
        not isinstance(modelo, str)
        or not modelo.strip()
        or operacion != "listar"
        or type(limite) is not int
        or not 1 <= limite <= LIMITE_MAXIMO_SOLICITABLE
    ):
        return {
            **base,
            "estado": "operacion_o_limite_no_soportado",
        }

    restricciones = {
        r["id"]: r
        for r in coleccion["restricciones"]
    }

    indice_a_id = {
        indice: identificador
        for identificador, indice in asociaciones.items()
    }

    resoluciones = {
        r["indice"]: r
        for r in resultado_query["resoluciones"]
    }

    sustituciones = {}
    equivalencias = []

    for indice in sorted(indice_a_id):
        identificador = indice_a_id[indice]
        restriccion = restricciones[identificador]
        seleccion = restriccion["seleccion"]
        resolucion = resoluciones[indice]
        filtro_query = resolucion["filtro"]

        # En C02 no cambiamos el campo identificado por QUERY.
        # Cambiarlo requiere una conciliación semántica adicional.
        if seleccion.get("campo") != filtro_query.get("campo"):
            return {
                **base,
                "estado": "campo_semantico_distinto",
                "restriccion_id": identificador,
                "indice_query": indice,
            }

        # Recertificación individual; no confiamos en el
        # contenido almacenado de la selección.
        verificada = verificar_eleccion_filtro(
            modelo,
            restriccion["evidencia_textual"],
            seleccion.get("id"),
        )

        if (
            verificada.get("ok") is not True
            or verificada.get("certificada_host") is not True
            or verificada.get("modelo") != modelo
            or verificada.get("evidencia_textual")
                != restriccion["evidencia_textual"]
            or verificada.get("seleccion") != seleccion
        ):
            return {
                **base,
                "estado": "seleccion_rechazada_host",
            }

        filtro = {
            "campo": seleccion.get("campo"),
            "operador": seleccion.get("operador"),
            "valor": seleccion.get("valor"),
        }

        # HOST produce los metadatos ORM de la condición
        # derivada. Nunca fabricamos lookup ni tipo Django.
        propuesta = {
            "modelo": modelo,
            "operacion": operacion,
            "filtros": [filtro],
            "orden": [],
            "limite": limite,
            "condiciones_no_resueltas": [],
        }

        validacion = validar_plan_datos(propuesta)

        if (
            not isinstance(validacion, dict)
            or validacion.get("ok") is not True
            or validacion.get("plan_validado") is not True
            or not isinstance(validacion.get("plan"), dict)
        ):
            return {
                **base,
                "estado": "hoja_rechazada_host",
            }

        plan = validacion["plan"]
        filtros = plan.get("filtros")

        if (
            plan.get("modelo") != modelo
            or plan.get("operacion") != operacion
            or plan.get("limite") != limite
            or not isinstance(filtros, list)
            or len(filtros) != 1
            or not isinstance(filtros[0], dict)
            or any(
                filtros[0].get(k) != filtro[k]
                for k in ("campo", "operador", "valor")
            )
            or not isinstance(filtros[0].get("lookup"), str)
            or not filtros[0]["lookup"]
        ):
            return {
                **base,
                "estado": "hoja_host_inconsistente",
            }

        certificado = filtros[0]

        sustituciones[indice] = {
            "tipo": "CONDICION",
            "indice": indice,
            "campo": certificado["campo"],
            "operador": certificado["operador"],
            "lookup": certificado["lookup"],
            "valor": deepcopy(certificado["valor"]),
            "tipo_django": certificado.get("tipo"),
        }

        equivalencias.append({
            "restriccion_id": identificador,
            "indice_query": indice,
            "campo": certificado["campo"],
            "valor_query": deepcopy(filtro_query.get("valor")),
            "valor_host": deepcopy(certificado["valor"]),
            "operador_query": filtro_query.get("operador"),
            "operador_host": certificado["operador"],
            "recertificada_host": True,
        })

    # El recorrido copia la topología del árbol original.
    # Ningún operador se deduce a partir de la lista de filtros.
    usados = set()
    visitados = set()

    def copiar(nodo, profundidad=0):
        if (
            profundidad > 64
            or not isinstance(nodo, dict)
            or id(nodo) in visitados
        ):
            raise ValueError("nodo_invalido")

        visitados.add(id(nodo))

        if nodo.get("tipo") == "CONDICION":
            indice = nodo.get("indice")

            if indice not in sustituciones or indice in usados:
                raise ValueError("hoja_invalida")

            usados.add(indice)
            return deepcopy(sustituciones[indice])

        if nodo.get("tipo") != "GRUPO":
            raise ValueError("grupo_invalido")

        operador = nodo.get("operador")
        hijos = nodo.get("hijos")

        if (
            operador not in ("AND", "OR")
            or not isinstance(hijos, list)
            or len(hijos) < 2
        ):
            raise ValueError("operador_invalido")

        return {
            "tipo": "GRUPO",
            "operador": operador,
            "hijos": [
                copiar(hijo, profundidad + 1)
                for hijo in hijos
            ],
        }

    try:
        arbol = copiar(contrato["arbol_logico"])
    except (ValueError, KeyError, RecursionError):
        return {
            **base,
            "estado": "reconstruccion_invalida",
        }

    if usados != set(sustituciones):
        return {
            **base,
            "estado": "hojas_no_conservadas",
        }

    return {
        **base,
        "ok": True,
        "estado": "arbol_logico_derivado_diagnostico",
        "pregunta_original": coleccion["pregunta_original"],
        "identificador_coleccion":
            coleccion["identificador_coleccion"],
        "modelo": modelo,
        "operacion": operacion,
        "limite": limite,
        "arbol_derivado": arbol,
        "equivalencias": equivalencias,
        "arbol_derivado_validado_host": True,
        "pendientes": [
            "autenticidad_asociaciones_pendiente",
            "procedencia_sesion_pendiente",
            "equivalencia_intencion_original_pendiente",
            "operacion_y_limite_semanticos_pendientes",
            "cobertura_semantica_total_pendiente",
            "certificacion_logica_integral_pendiente",
        ],
    }
