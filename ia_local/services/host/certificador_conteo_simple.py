"""
IA-LLM008-D06-C1

Certificación positiva limitada a conteos simples
cuya pregunta completa coincide con una plantilla
conservadora.

No ejecuta consultas.
No autoriza FINAL.
No contiene nombres de modelos del anfitrión.
"""

import re
import unicodedata

from django.db import transaction

from ia_local.services.host.expediente_consulta import (
    _obtener_bloqueado,
    _vigente,
)

from ia_local.services.host.resolvedor_entidad_datos import (
    resolver_entidad_datos,
)

from ia_local.services.llm.intencion_operacional import (
    detectar_intencion_operacional,
)

from ia_local.services.llm.trazabilidad_compuesta import (
    _verificar_coleccion_identificada,
)


VERSION = "IA-LLM008-D06-C1-v1"


def _normalizar(texto):
    texto = unicodedata.normalize(
        "NFKD", str(texto or "").casefold()
    )
    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )
    texto = re.sub(r"[¿?¡!.,;:]", " ", texto)
    return " ".join(texto.split())


def _respuesta(estado, **datos):
    return {
        "ok": False,
        "version_certificador": VERSION,
        "estado": estado,
        "certificable": False,
        "cobertura_plantilla_verificada": False,
        "ejecutable": False,
        "ejecutado": False,
        **datos,
    }


def certificar_conteo_simple(
    request, identificador, version
):
    if type(version) is not int or version < 1:
        return _respuesta("version_invalida")

    if not identificador:
        return _respuesta("identificador_invalido")

    with transaction.atomic():
        expediente = _obtener_bloqueado(
            request, identificador
        )

        if expediente is None:
            return _respuesta("expediente_no_disponible")

        if not _vigente(expediente):
            return _respuesta("expediente_no_vigente")

        if expediente.version != version:
            return _respuesta("version_obsoleta")

        if expediente.estado != "ABIERTO":
            return _respuesta("estado_no_certificable")

        coleccion = expediente.coleccion

        if (
            not isinstance(coleccion, dict)
            or not _verificar_coleccion_identificada(
                coleccion
            )
            or coleccion.get("ejecutable") is not False
            or coleccion.get("pregunta_original")
                != expediente.pregunta_original
            or coleccion.get("restricciones") != []
            or coleccion.get("pendientes") != []
            or expediente.arbol_logico != {}
            or expediente.asociaciones != {}
        ):
            return _respuesta(
                "estructura_no_certificable"
            )

        pregunta = expediente.pregunta_original

        intencion = detectar_intencion_operacional(
            pregunta
        )
        entidad = resolver_entidad_datos(
            pregunta
        )

        if (
            not isinstance(intencion, dict)
            or intencion.get("ok") is not True
            or intencion.get("detectada") is not True
            or intencion.get("accion_host") != "contar"
            or not isinstance(entidad, dict)
            or entidad.get("ok") is not True
            or entidad.get("resuelto") is not True
            or entidad.get("entidad")
                != expediente.modelo_contexto
        ):
            return _respuesta(
                "operacion_o_entidad_no_certificada"
            )

        evidencia = entidad.get("evidencia")

        if not isinstance(evidencia, dict):
            return _respuesta(
                "evidencia_entidad_no_disponible"
            )

        coincidencias = evidencia.get(
            "coincidencias"
        )

        if not isinstance(coincidencias, list):
            return _respuesta(
                "coincidencias_invalidas"
            )

        texto = _normalizar(pregunta)

        # Coincidencias derivadas del vocabulario HOST.
        # No se permite que un fragmento distinto
        # justifique el modelo del expediente.
        nombres = set()

        for coincidencia in coincidencias:
            if not isinstance(coincidencia, dict):
                continue

            if (
                coincidencia.get("modelo")
                != expediente.modelo_contexto
            ):
                continue

            nombre = _normalizar(
                coincidencia.get("texto")
            )

            if nombre:
                nombres.add(nombre)

        if not nombres:
            return _respuesta(
                "nombre_entidad_no_certificado"
            )

        # La pregunta completa debe corresponder a
        # la plantilla. No se aceptan palabras sobrantes.
        corresponde = any(
            texto == f"cuantos {nombre} hay"
            for nombre in nombres
        )

        if not corresponde:
            return _respuesta(
                "pregunta_fuera_de_plantilla"
            )

        return {
            "ok": True,
            "version_certificador": VERSION,
            "estado": "conteo_simple_certificado",
            "identificador": str(expediente.pk),
            "version_expediente": expediente.version,
            "modelo": expediente.modelo_contexto,
            "operacion": "contar",
            "certificable": True,
            "cobertura_plantilla_verificada": True,
            "alcance_certificacion": "conteo_simple",
            # Certificación positiva de la plantilla,
            # todavía sin autorización FINAL.
            "ejecutable": False,
            "ejecutado": False,
        }
