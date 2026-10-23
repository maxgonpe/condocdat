"""Descubrimiento conservador de filtros sobre choices.

No interpreta SQL, no consulta registros y no certifica
una elección del usuario.
"""
import re
import unicodedata
from typing import Any

from ia_local.services.host.catalogo_datos import (
    obtener_modelo_django,
    describir_modelo,
)

VERSION = "IA-LLM008-F5-05-04-v1"


def _normalizar(valor):
    texto = unicodedata.normalize("NFKD", str(valor).casefold())
    texto = "".join(
        c for c in texto if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", texto).strip()


def _palabras(valor):
    return re.findall(r"[a-z0-9]+", _normalizar(valor))


def _variantes(palabra):
    resultado = {palabra}
    if palabra.endswith("es") and len(palabra) > 4:
        resultado.add(palabra[:-2])
    if palabra.endswith("s") and len(palabra) > 3:
        resultado.add(palabra[:-1])
    return resultado


def _coincide(evidencia, etiqueta):
    buscadas = _palabras(evidencia)
    existentes = set(_palabras(etiqueta))

    if not buscadas or not existentes:
        return False

    # Coincidencia conservadora de tokens completos,
    # admitiendo flexión plural simple.
    return all(
        bool(_variantes(p) & existentes)
        for p in buscadas
    )


def _campos_consultables(descripcion):
    if not isinstance(descripcion, dict):
        return None

    datos = descripcion.get("campos_consultables")

    if isinstance(datos, dict):
        return set(datos.keys())

    if isinstance(datos, (list, tuple, set)):
        nombres = set()
        for elemento in datos:
            if isinstance(elemento, str):
                nombres.add(elemento)
            elif isinstance(elemento, dict):
                nombre = elemento.get("nombre") or elemento.get("name")
                if isinstance(nombre, str):
                    nombres.add(nombre)
        return nombres

    return None


def descubrir_filtros_choices(
    modelo: str,
    evidencia_textual: str,
) -> dict[str, Any]:

    salida = {
        "ok": False,
        "version": VERSION,
        "estado": "no_resuelto",
        "modelo": modelo,
        "evidencia_textual": evidencia_textual,
        "alternativas": [],
        "requiere_aclaracion": False,
        "certificada_host": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    if (
        not isinstance(modelo, str)
        or not modelo.strip()
        or not isinstance(evidencia_textual, str)
        or not evidencia_textual.strip()
        or len(evidencia_textual) > 100
        or len(_palabras(evidencia_textual)) > 5
    ):
        return {**salida, "estado": "entrada_invalida"}

    try:
        django_modelo = obtener_modelo_django(modelo)
    except Exception:
        return {**salida, "estado": "modelo_no_resuelto"}

    if django_modelo is None:
        return {**salida, "estado": "modelo_no_autorizado"}

    if django_modelo._meta.label_lower != modelo.casefold():
        return {**salida, "estado": "referencia_modelo_no_canonica"}

    try:
        descripcion = describir_modelo(django_modelo)
    except Exception:
        return {**salida, "estado": "catalogo_no_disponible"}

    permitidos = _campos_consultables(descripcion)

    if permitidos is None:
        return {**salida, "estado": "contrato_catalogo_no_reconocido"}

    alternativas = []

    for campo in django_modelo._meta.get_fields():
        if (
            campo.name not in permitidos
            or not getattr(campo, "concrete", False)
            or getattr(campo, "is_relation", False)
        ):
            continue

        for valor, etiqueta in getattr(campo, "choices", []) or []:
            if isinstance(etiqueta, (list, tuple)):
                continue

            if not _coincide(evidencia_textual, etiqueta):
                continue

            alternativas.append({
                "campo": campo.name,
                "operador_propuesto": "exact",
                "valor": valor,
                "etiqueta": str(etiqueta),
            })

    alternativas.sort(
        key=lambda x: (x["campo"], str(x["valor"]))
    )

    if len(alternativas) > 1:
        estado = "filtro_ambiguo"
    elif len(alternativas) == 1:
        estado = "candidato_unico_no_certificado"
    else:
        estado = "sin_candidatos_choices"

    return {
        **salida,
        "ok": True,
        "estado": estado,
        "modelo": django_modelo._meta.label,
        "alternativas": alternativas,
        "requiere_aclaracion": len(alternativas) > 1,
    }
