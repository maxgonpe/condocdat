import re
import unicodedata

from django.db.models import F

from ia_local.models import IAReglaSemantica


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalizar_pregunta(texto):
    """
    Normaliza preguntas exactas.

    - minúsculas
    - elimina tildes
    - elimina signos de puntuación
    - normaliza espacios
    """

    texto = (texto or "").strip().lower()

    texto = unicodedata.normalize(
        "NFD",
        texto,
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    texto = re.sub(
        r"[^a-z0-9\s]",
        " ",
        texto,
    )

    texto = " ".join(
        texto.split()
    )

    return texto


def normalizar_patron(texto):
    """
    Normaliza un patrón preservando variables como:

        {REVISION}
        {CODIGO}
        {PROCESO}

    Ejemplo:

        ¿Muéstrame documentos revisión {REVISION}?

    queda:

        muestrame documentos revision {REVISION}
    """

    texto = (texto or "").strip()

    partes = re.split(
        r"(\{[A-Za-z_][A-Za-z0-9_]*\})",
        texto,
    )

    resultado = []

    for parte in partes:

        if not parte:
            continue

        if re.fullmatch(
            r"\{[A-Za-z_][A-Za-z0-9_]*\}",
            parte,
        ):
            resultado.append(
                parte.upper()
            )
        else:

            normalizada = normalizar_pregunta(
                parte
            )

            if normalizada:
                resultado.append(
                    normalizada
                )

    return " ".join(
        resultado
    )


# ============================================================
# REGLAS EXACTAS
# ============================================================

def buscar_regla_exacta(pregunta):
    """
    Busca una regla EXACTA previamente aprendida.
    """

    pregunta_normalizada = normalizar_pregunta(
        pregunta
    )

    regla = (
        IAReglaSemantica.objects
        .filter(
            activa=True,
            tipo=IAReglaSemantica.TIPO_EXACTA,
            pregunta_normalizada=pregunta_normalizada,
        )
        .first()
    )

    if not regla:
        return None

    IAReglaSemantica.objects.filter(
        pk=regla.pk
    ).update(
        veces_usada=F("veces_usada") + 1
    )

    return {
        "tema": regla.tema,
        "operacion": regla.operacion,
        "filtros": regla.filtros or {},
        "cantidad": regla.cantidad,
        "orden": regla.orden,
    }


def buscar_regla_semantica(pregunta):
    """
    Compatibilidad con la versión anterior.

    Por ahora equivale a buscar una regla exacta.
    """

    return buscar_regla_exacta(
        pregunta
    )


def guardar_regla_exacta(
    pregunta,
    intencion,
    observacion="",
):
    """
    Guarda o actualiza una regla exacta.
    """

    pregunta_normalizada = normalizar_pregunta(
        pregunta
    )

    regla, creada = (
        IAReglaSemantica.objects.update_or_create(
            tipo=IAReglaSemantica.TIPO_EXACTA,
            pregunta_normalizada=pregunta_normalizada,
            defaults={
                "pregunta": pregunta.strip(),
                "tema": intencion["tema"],
                "operacion": intencion.get(
                    "operacion",
                    "listar",
                ),
                "filtros": intencion.get(
                    "filtros",
                    {},
                ),
                "cantidad": intencion.get(
                    "cantidad",
                    "varios",
                ),
                "orden": intencion.get(
                    "orden",
                    "ninguno",
                ),
                "activa": True,
                "observacion": observacion,
            },
        )
    )

    return regla, creada


# ============================================================
# MOTOR DE PATRONES
# ============================================================


def _compilar_patron(patron_normalizado):
    """
    Convierte un patrón semántico en regex.

    Variables actualmente soportadas:

        {REVISION}
            Una sola palabra/letra/número.

        {PROCESO}
            Una o varias palabras.

    Ejemplos:

        revision {REVISION}
        proceso {PROCESO}
    """

    partes = re.split(
        r"(\{[A-Z_][A-Z0-9_]*\})",
        patron_normalizado,
    )

    regex = []

    for parte in partes:

        if not parte:
            continue

        variable = re.fullmatch(
            r"\{([A-Z_][A-Z0-9_]*)\}",
            parte,
        )

        if variable:

            nombre = variable.group(1)

            if nombre == "REVISION":

                regex.append(
                    rf"(?P<{nombre}>[a-z0-9]+)"
                )

            elif nombre == "PROCESO":

                regex.append(
                    rf"(?P<{nombre}>[a-z0-9 ]+?)"
                )

            else:

                # Comportamiento conservador para
                # variables aún no definidas.
                regex.append(
                    rf"(?P<{nombre}>[a-z0-9]+)"
                )

        else:

            regex.append(
                re.escape(parte)
            )

    return re.compile(
        "^" + "".join(regex) + "$",
        re.IGNORECASE,
    )


def _valor_variable(nombre, valor):
    """
    Normaliza variables capturadas por reglas patrón.
    """

    valor = str(
        valor or ""
    ).strip()

    valor = " ".join(
        valor.split()
    )

    if nombre == "REVISION":
        return valor.upper()

    if nombre == "PROCESO":
        return valor.upper()

    return valor


def _reemplazar_variables(valor, variables):
    """
    Reemplaza variables dentro de strings,
    diccionarios y listas.

    Ejemplo:

        "CANDIDATO REV {REVISION}"

    con:

        REVISION=B

    produce:

        "CANDIDATO REV B"
    """

    if isinstance(valor, str):

        resultado = valor

        for nombre, contenido in variables.items():

            contenido = _valor_variable(
                nombre,
                contenido,
            )

            resultado = resultado.replace(
                "{" + nombre + "}",
                contenido,
            )

        return resultado

    if isinstance(valor, dict):

        return {
            clave: _reemplazar_variables(
                contenido,
                variables,
            )
            for clave, contenido in valor.items()
        }

    if isinstance(valor, list):

        return [
            _reemplazar_variables(
                elemento,
                variables,
            )
            for elemento in valor
        ]

    return valor


def buscar_regla_patron(pregunta):
    """
    Busca una regla tipo PATRON.

    Retorna la intención ya materializada
    con las variables encontradas.
    """

    pregunta_normalizada = normalizar_pregunta(
        pregunta
    )

    reglas = (
        IAReglaSemantica.objects
        .filter(
            activa=True,
            tipo=IAReglaSemantica.TIPO_PATRON,
        )
        .order_by("-updated_at", "-pk")
    )

    for regla in reglas:

        try:

            patron_regex = _compilar_patron(
                regla.pregunta_normalizada
            )

        except re.error:

            # Una regla dañada no debe romper
            # todo el sistema.
            continue

        coincidencia = patron_regex.fullmatch(
            pregunta_normalizada
        )

        if not coincidencia:
            continue

        variables = coincidencia.groupdict()

        intencion = {
            "tema": regla.tema,
            "operacion": regla.operacion,
            "filtros": regla.filtros or {},
            "cantidad": regla.cantidad,
            "orden": regla.orden,
        }

        intencion = _reemplazar_variables(
            intencion,
            variables,
        )

        IAReglaSemantica.objects.filter(
            pk=regla.pk
        ).update(
            veces_usada=F("veces_usada") + 1
        )

        return intencion

    return None


def guardar_regla_patron(
    patron,
    intencion,
    observacion="",
):
    """
    Guarda o actualiza una regla por patrón.

    Ejemplo:

        patron:
        Muéstrame los documentos candidatos
        a revisión {REVISION}

        filtros:
        {
            "revision":
            "CANDIDATO REV {REVISION}"
        }
    """

    patron_normalizado = normalizar_patron(
        patron
    )

    if not re.search(
        r"\{[A-Z_][A-Z0-9_]*\}",
        patron_normalizado,
    ):
        raise ValueError(
            "El patrón debe contener al menos una variable "
            "como {REVISION}."
        )

    regla, creada = (
        IAReglaSemantica.objects.update_or_create(
            tipo=IAReglaSemantica.TIPO_PATRON,
            pregunta_normalizada=patron_normalizado,
            defaults={
                "pregunta": patron.strip(),
                "tema": intencion["tema"],
                "operacion": intencion.get(
                    "operacion",
                    "listar",
                ),
                "filtros": intencion.get(
                    "filtros",
                    {},
                ),
                "cantidad": intencion.get(
                    "cantidad",
                    "varios",
                ),
                "orden": intencion.get(
                    "orden",
                    "ninguno",
                ),
                "activa": True,
                "observacion": observacion,
            },
        )
    )

    return regla, creada