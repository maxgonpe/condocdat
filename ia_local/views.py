import io
import json
from datetime import datetime
from html import escape

from django.contrib.admin.views.decorators import staff_member_required
from django.http import (
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


from .models import IAReglaSemantica
from .services.host.router import (
    procesar_pregunta,
)
from .services.host.salida import (
    normalizar_salida,
)
from .services.host.diagnostico import (
    diagnosticar_pregunta,
)
from .services.reglas_semanticas import (
    guardar_regla_exacta,
    guardar_regla_patron,
)


# ============================================================
# MOTOR CENTRAL PORTABLE
# ============================================================

def _ejecutar_consulta_ia(
    pregunta,
    limite=20,
):
    """
    Punto único de entrada para web/API.

    El router HOST conserva toda la lógica interna. Aquí sólo
    construimos una salida pública estable para la interfaz y
    las exportaciones.
    """

    resultado = procesar_pregunta(
        pregunta,
        profundidad=3,
    )

    if not resultado.get(
        "ok"
    ):
        mensaje = (
            resultado.get(
                "respuesta"
            )
            or resultado.get(
                "error"
            )
            or "Error procesando la consulta IA."
        )

        raise RuntimeError(
            str(
                mensaje
            )
        )

    intencion = (
        resultado.get(
            "intencion"
        )
        or {}
    )

    respuesta_estructurada = (
        resultado.get(
            "respuesta_estructurada"
        )
        or {}
    )

    salida_publica = normalizar_salida(
        resultado
    )

    diagnostico = {
        "origen":
            salida_publica.get(
                "origen"
            ),

        "tema":
            salida_publica.get(
                "destino"
            ),

        "modelo":
            salida_publica.get(
                "modelo"
            ),

        "operacion":
            salida_publica.get(
                "operacion"
            ),

        "cantidad":
            None,

        "orden":
            salida_publica.get(
                "orden"
            ),

        "filtros_orm":
            salida_publica.get(
                "filtros"
            ),

        "total":
            salida_publica.get(
                "total"
            ),

        "limite":
            salida_publica.get(
                "limite"
            )
            or limite,

        "destino":
            salida_publica.get(
                "destino"
            ),

        "tipo_intencion":
            intencion.get(
                "tipo"
            ),

        "subtipo_intencion":
            intencion.get(
                "subtipo"
            ),

        "validado":
            intencion.get(
                "validado"
            ),

        "llm_invocado":
            salida_publica.get(
                "llm_invocado"
            ),
    }

    return {
        "motor":
            intencion,

        "diagnostico":
            diagnostico,

        "salida":
            salida_publica,

        # Se conserva para diagnóstico y compatibilidad.
        "respuesta_estructurada":
            respuesta_estructurada,

        "registros":
            salida_publica.get(
                "resultados",
                [],
            ),

        "respuesta_texto":
            salida_publica.get(
                "respuesta",
                "",
            ),

        "router":
            resultado,
    }


# ============================================================
# PANTALLA PRINCIPAL
# ============================================================

@staff_member_required
@require_http_methods(
    [
        "GET",
        "POST",
    ]
)
def consulta_ia(request):

    contexto = {
        "pregunta": "",
        "respuesta": "",
        "respuesta_estructurada": None,
        "plan": None,
        "resultado": None,
        "error": "",
    }

    if request.method == "POST":

        pregunta = (
            request.POST.get(
                "pregunta"
            )
            or ""
        ).strip()

        contexto[
            "pregunta"
        ] = pregunta

        if not pregunta:

            contexto[
                "error"
            ] = "Escribe una pregunta."

        else:

            try:

                salida = (
                    _ejecutar_consulta_ia(
                        pregunta
                    )
                )

                contexto[
                    "plan"
                ] = salida[
                    "diagnostico"
                ]

                contexto[
                    "resultado"
                ] = salida[
                    "diagnostico"
                ]

                contexto[
                    "respuesta_estructurada"
                ] = salida[
                    "respuesta_estructurada"
                ]

                contexto[
                    "respuesta"
                ] = salida[
                    "respuesta_texto"
                ]

            except Exception as exc:

                contexto[
                    "error"
                ] = str(exc)

    return render(
        request,
        "ia_local/index.html",
        contexto,
    )


# ============================================================
# API PRINCIPAL
# ============================================================

@staff_member_required
@require_http_methods(
    [
        "POST",
    ]
)
def consulta_ia_json(request):

    pregunta = (
        request.POST.get(
            "pregunta"
        )
        or ""
    ).strip()

    if not pregunta:

        return JsonResponse(
            {
                "ok": False,
                "error":
                    "La pregunta está vacía.",
            },
            status=400,
            json_dumps_params={
                "ensure_ascii": False
            },
        )

    try:

        salida = (
            _ejecutar_consulta_ia(
                pregunta
            )
        )

        diagnostico = salida[
            "diagnostico"
        ]

        return JsonResponse(
            {
                "ok":
                    True,

                "pregunta":
                    pregunta,

                "origen":
                    diagnostico[
                        "origen"
                    ],

                "tema":
                    diagnostico[
                        "tema"
                    ],

                "modelo":
                    diagnostico[
                        "modelo"
                    ],

                "operacion":
                    diagnostico[
                        "operacion"
                    ],

                "intencion":
                    salida[
                        "motor"
                    ].get(
                        "intencion"
                    ),

                "filtros_orm":
                    diagnostico[
                        "filtros_orm"
                    ],

                "total":
                    diagnostico[
                        "total"
                    ],

                "respuesta":
                    salida[
                        "respuesta_texto"
                    ],

                "salida":
                    salida[
                        "salida"
                    ],

                "respuesta_estructurada":
                    salida[
                        "respuesta_estructurada"
                    ],

                "registros":
                    salida[
                        "registros"
                    ],

                "json_completo":
                    salida[
                        "router"
                    ],
            },
            json_dumps_params={
                "ensure_ascii": False
            },
        )

    except Exception as exc:

        return JsonResponse(
            {
                "ok": False,
                "error": str(exc),
            },
            status=400,
            json_dumps_params={
                "ensure_ascii": False
            },
        )


# ============================================================
# REGLA EXACTA
# ============================================================

@staff_member_required
@require_http_methods(
    [
        "POST",
    ]
)
def guardar_regla_test_json(
    request,
):

    pregunta = (
        request.POST.get(
            "pregunta"
        )
        or ""
    ).strip()

    intencion_json = (
        request.POST.get(
            "intencion"
        )
        or ""
    ).strip()

    if not pregunta:

        return JsonResponse(
            {
                "ok": False,
                "error":
                    "La pregunta está vacía.",
            },
            status=400,
        )

    if not intencion_json:

        return JsonResponse(
            {
                "ok": False,
                "error":
                    "No existe intención "
                    "normalizada para guardar.",
            },
            status=400,
        )

    try:

        intencion = json.loads(
            intencion_json
        )

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "ok": False,
                "error":
                    "La intención recibida "
                    "no es JSON válido.",
            },
            status=400,
        )

    try:

        if not isinstance(
            intencion,
            dict,
        ):

            raise ValueError(
                "La intención debe ser "
                "un objeto JSON."
            )

        if not intencion.get(
            "tema"
        ):

            raise ValueError(
                "La intención no contiene "
                "'tema'."
            )

        regla, creada = (
            guardar_regla_exacta(
                pregunta=pregunta,
                intencion=intencion,
                observacion=(
                    "Regla guardada manualmente "
                    "desde la consola de diagnóstico."
                ),
            )
        )

        return JsonResponse(
            {
                "ok":
                    True,

                "creada":
                    creada,

                "regla":
                    {
                        "id":
                            regla.pk,

                        "pregunta":
                            regla.pregunta,

                        "tema":
                            regla.tema,

                        "operacion":
                            regla.operacion,

                        "filtros":
                            regla.filtros,

                        "cantidad":
                            regla.cantidad,

                        "orden":
                            regla.orden,
                    },

                "mensaje":
                    (
                        "Regla semántica creada "
                        "correctamente."
                        if creada
                        else
                        "Regla semántica actualizada "
                        "correctamente."
                    ),
            },
            json_dumps_params={
                "ensure_ascii": False
            },
        )

    except Exception as exc:

        return JsonResponse(
            {
                "ok": False,
                "error": str(exc),
            },
            status=400,
        )


# ============================================================
# PATRONES
# ============================================================

@staff_member_required
@require_http_methods(
    [
        "POST",
    ]
)
def guardar_patron_test_json(
    request,
):

    patron = (
        request.POST.get(
            "patron"
        )
        or ""
    ).strip()

    intencion_json = (
        request.POST.get(
            "intencion"
        )
        or ""
    ).strip()

    if not patron:

        return JsonResponse(
            {
                "ok": False,
                "error":
                    "El patrón está vacío.",
            },
            status=400,
        )

    if not intencion_json:

        return JsonResponse(
            {
                "ok": False,
                "error":
                    "La intención del patrón "
                    "está vacía.",
            },
            status=400,
        )

    try:

        intencion = json.loads(
            intencion_json
        )

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "ok": False,
                "error":
                    "La intención no contiene "
                    "JSON válido.",
            },
            status=400,
        )

    try:

        if not isinstance(
            intencion,
            dict,
        ):

            raise ValueError(
                "La intención debe ser "
                "un objeto JSON."
            )

        if not intencion.get(
            "tema"
        ):

            raise ValueError(
                "La intención debe contener "
                "'tema'."
            )

        regla, creada = (
            guardar_regla_patron(
                patron=patron,
                intencion=intencion,
                observacion=(
                    "Patrón guardado manualmente "
                    "desde la consola de diagnóstico."
                ),
            )
        )

        return JsonResponse(
            {
                "ok":
                    True,

                "creada":
                    creada,

                "regla":
                    {
                        "id":
                            regla.pk,

                        "tipo":
                            regla.tipo,

                        "patron":
                            regla.pregunta,

                        "patron_normalizado":
                            regla.pregunta_normalizada,

                        "tema":
                            regla.tema,

                        "operacion":
                            regla.operacion,

                        "filtros":
                            regla.filtros,

                        "cantidad":
                            regla.cantidad,

                        "orden":
                            regla.orden,
                    },

                "mensaje":
                    (
                        "Patrón semántico creado "
                        "correctamente."
                        if creada
                        else
                        "Patrón semántico actualizado "
                        "correctamente."
                    ),
            },
            json_dumps_params={
                "ensure_ascii": False
            },
        )

    except Exception as exc:

        return JsonResponse(
            {
                "ok": False,
                "error": str(exc),
            },
            status=400,
        )


# ============================================================
# REGLAS SEMANTICAS
# ============================================================

@staff_member_required
@require_http_methods(
    [
        "GET",
    ]
)
def reglas_semanticas(
    request,
):

    reglas = (
        IAReglaSemantica.objects
        .all()
        .order_by(
            "-activa",
            "tipo",
            "-veces_usada",
            "-updated_at",
        )
    )

    return render(
        request,
        "ia_local/reglas_semanticas.html",
        {
            "reglas":
                reglas,
        },
    )


@staff_member_required
@require_http_methods(
    [
        "POST",
    ]
)
def cambiar_estado_regla(
    request,
    pk,
):

    try:

        regla = (
            IAReglaSemantica.objects.get(
                pk=pk
            )
        )

        regla.activa = not regla.activa

        regla.save(
            update_fields=[
                "activa",
                "updated_at",
            ]
        )

        return JsonResponse(
            {
                "ok":
                    True,

                "id":
                    regla.pk,

                "activa":
                    regla.activa,

                "mensaje":
                    (
                        "Regla activada."
                        if regla.activa
                        else
                        "Regla desactivada."
                    ),
            }
        )

    except IAReglaSemantica.DoesNotExist:

        return JsonResponse(
            {
                "ok": False,
                "error":
                    "La regla no existe.",
            },
            status=404,
        )


# ============================================================
# EXPORTACION
# ============================================================

def _leer_respuesta_exportacion(
    request,
):
    """
    Lee la respuesta estructurada que ya está visible
    en index.html.

    No vuelve a ejecutar Qwen.
    """

    pregunta = (
        request.POST.get(
            "pregunta"
        )
        or ""
    ).strip()

    respuesta_json = (
        request.POST.get(
            "respuesta_json"
        )
        or ""
    ).strip()

    if not respuesta_json:

        raise ValueError(
            "No existe un resultado "
            "para exportar."
        )

    try:

        respuesta = json.loads(
            respuesta_json
        )

    except json.JSONDecodeError:

        raise ValueError(
            "El resultado recibido "
            "no contiene JSON válido."
        )

    if not isinstance(
        respuesta,
        dict,
    ):

        raise ValueError(
            "La respuesta debe ser "
            "un objeto JSON."
        )

    return (
        pregunta,
        respuesta,
    )


def _valor_exportable(
    valor,
):
    if valor is None:
        return ""

    if isinstance(
        valor,
        (
            dict,
            list,
            tuple,
        ),
    ):

        return json.dumps(
            valor,
            ensure_ascii=False,
            default=str,
        )

    return str(
        valor
    )



def _extraer_resultados(
    respuesta,
):
    """
    Extrae filas del contrato público normalizado.

    Mantiene una compatibilidad mínima con respuestas previas,
    pero la interfaz nueva debe enviar siempre ``salida``.
    """

    if not isinstance(
        respuesta,
        dict,
    ):
        return []

    resultados = respuesta.get(
        "resultados"
    )

    if isinstance(
        resultados,
        list,
    ):
        return resultados

    # Compatibilidad con el contrato HOST previo.
    for clave in (
        "ejecucion",
        "ejecucion_datos",
    ):
        bloque = respuesta.get(
            clave
        )

        if isinstance(
            bloque,
            dict,
        ):
            resultados = bloque.get(
                "resultados"
            )

            if isinstance(
                resultados,
                list,
            ):
                return resultados

    return []


def _resumen_exportacion(
    respuesta,
):
    """
    Construye el resumen desde el contrato público normalizado.
    """

    if not isinstance(
        respuesta,
        dict,
    ):
        return []

    resumen = []

    etiquetas = (
        ("tipo", "Tipo"),
        ("destino", "Destino"),
        ("modelo", "Modelo"),
        ("operacion", "Operación"),
        ("tabla", "Tabla"),
        ("total", "Total"),
        ("limite", "Límite"),
        ("llm_invocado", "LLM invocado"),
        ("respuesta", "Respuesta"),
    )

    for clave, etiqueta in etiquetas:
        valor = respuesta.get(
            clave
        )

        if valor not in (
            None,
            "",
            [],
            {},
        ):
            resumen.append(
                (
                    etiqueta,
                    valor,
                )
            )

    return resumen


def _texto_pdf(
    valor,
):
    """Escapa contenido dinámico antes de entregarlo a ReportLab."""

    return escape(
        _valor_exportable(
            valor
        )
    )


def _campos_resultados(
    resultados,
):
    """
    Unión de las columnas encontradas.
    Mantiene el orden de aparición.
    """

    campos = []

    for fila in resultados:

        if not isinstance(
            fila,
            dict,
        ):
            continue

        for campo in fila.keys():

            if campo not in campos:
                campos.append(
                    campo
                )

    return campos


def _nombre_archivo(
    extension,
):
    ahora = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    return (
        f"consulta_ia_{ahora}."
        f"{extension}"
    )


# ============================================================
# EXCEL
# ============================================================

@staff_member_required
@require_http_methods(
    [
        "POST",
    ]
)
def exportar_resultado_excel(
    request,
):
    try:

        pregunta, respuesta = (
            _leer_respuesta_exportacion(
                request
            )
        )

    except ValueError as exc:

        return HttpResponse(
            str(exc),
            status=400,
            content_type=(
                "text/plain; "
                "charset=utf-8"
            ),
        )

    workbook = Workbook()

    # --------------------------------------------------------
    # RESUMEN
    # --------------------------------------------------------

    hoja_resumen = workbook.active
    hoja_resumen.title = "Resumen"

    hoja_resumen[
        "A1"
    ] = "Consulta IA"

    hoja_resumen[
        "A1"
    ].font = Font(
        bold=True,
        size=14,
    )

    hoja_resumen[
        "A3"
    ] = "Pregunta"

    hoja_resumen[
        "B3"
    ] = pregunta

    fila = 5

    for clave, valor in _resumen_exportacion(
        respuesta
    ):

        hoja_resumen.cell(
            row=fila,
            column=1,
            value=str(
                clave
            ),
        )

        hoja_resumen.cell(
            row=fila,
            column=2,
            value=_valor_exportable(
                valor
            ),
        )

        fila += 1

    hoja_resumen.column_dimensions[
        "A"
    ].width = 30

    hoja_resumen.column_dimensions[
        "B"
    ].width = 90

    for row in hoja_resumen.iter_rows():

        for cell in row:

            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True,
            )

    # --------------------------------------------------------
    # RESULTADOS
    # --------------------------------------------------------

    resultados = (
        _extraer_resultados(
            respuesta
        )
    )

    if resultados:

        hoja = workbook.create_sheet(
            "Resultados"
        )

        campos = (
            _campos_resultados(
                resultados
            )
        )

        for columna, campo in enumerate(
            campos,
            start=1,
        ):

            celda = hoja.cell(
                row=1,
                column=columna,
                value=campo,
            )

            celda.font = Font(
                bold=True
            )

            celda.alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True,
            )

        for numero_fila, registro in enumerate(
            resultados,
            start=2,
        ):

            if not isinstance(
                registro,
                dict,
            ):
                registro = {
                    "resultado":
                        registro
                }

            for numero_columna, campo in enumerate(
                campos,
                start=1,
            ):

                valor = (
                    registro.get(
                        campo
                    )
                )

                celda = hoja.cell(
                    row=numero_fila,
                    column=numero_columna,
                    value=_valor_exportable(
                        valor
                    ),
                )

                celda.alignment = Alignment(
                    vertical="top",
                    wrap_text=True,
                )

        hoja.freeze_panes = "A2"

        hoja.auto_filter.ref = (
            hoja.dimensions
        )

        for numero_columna, campo in enumerate(
            campos,
            start=1,
        ):

            ancho = max(
                12,
                min(
                    45,
                    len(
                        str(
                            campo
                        )
                    ) + 5,
                ),
            )

            if campo in {
                "archivo",
                "title",
                "description",
                "texto_fila",
            }:

                ancho = 45

            hoja.column_dimensions[
                get_column_letter(
                    numero_columna
                )
            ].width = ancho

    salida = io.BytesIO()

    workbook.save(
        salida
    )

    salida.seek(
        0
    )

    response = HttpResponse(
        salida.getvalue(),
        content_type=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )

    response[
        "Content-Disposition"
    ] = (
        'attachment; filename="'
        + _nombre_archivo(
            "xlsx"
        )
        + '"'
    )

    return response


# ============================================================
# PDF
# ============================================================

def _columnas_pdf(
    resultados,
    columnas_preferidas=None,
):
    """
    Selecciona columnas de forma portable.

    Respeta primero la proyección informada por el ejecutor ORM
    y nunca contiene nombres de campos propios de un host.
    """

    disponibles = _campos_resultados(
        resultados
    )

    if isinstance(
        columnas_preferidas,
        list,
    ):
        columnas = [
            campo
            for campo in columnas_preferidas
            if campo in disponibles
        ]

        if columnas:
            return columnas[
                :7
            ]

    return disponibles[
        :7
    ]


@staff_member_required
@require_http_methods(
    [
        "POST",
    ]
)
def exportar_resultado_pdf(
    request,
):
    try:

        pregunta, respuesta = (
            _leer_respuesta_exportacion(
                request
            )
        )

    except ValueError as exc:

        return HttpResponse(
            str(exc),
            status=400,
            content_type=(
                "text/plain; "
                "charset=utf-8"
            ),
        )

    buffer = io.BytesIO()

    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(
            A4
        ),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="Resultado consulta IA",
    )

    estilos = getSampleStyleSheet()

    elementos = []

    elementos.append(
        Paragraph(
            "Resultado de consulta IA",
            estilos[
                "Title"
            ],
        )
    )

    elementos.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    elementos.append(
        Paragraph(
            "<b>Pregunta:</b> "
            + escape(
                pregunta
            ),
            estilos[
                "BodyText"
            ],
        )
    )

    elementos.append(
        Spacer(
            1,
            4 * mm,
        )
    )

    # --------------------------------------------------------
    # Resumen
    # --------------------------------------------------------

    resumen = []

    for clave, valor in _resumen_exportacion(
        respuesta
    ):

        resumen.append(
            [
                Paragraph(
                    f"<b>{escape(str(clave))}</b>",
                    estilos[
                        "BodyText"
                    ],
                ),
                Paragraph(
                    _texto_pdf(
                        valor
                    ),
                    estilos[
                        "BodyText"
                    ],
                ),
            ]
        )

    if resumen:

        tabla_resumen = Table(
            resumen,
            colWidths=[
                45 * mm,
                205 * mm,
            ],
            repeatRows=0,
        )

        tabla_resumen.setStyle(
            TableStyle(
                [
                    (
                        "VALIGN",
                        (
                            0,
                            0,
                        ),
                        (
                            -1,
                            -1,
                        ),
                        "TOP",
                    ),
                    (
                        "GRID",
                        (
                            0,
                            0,
                        ),
                        (
                            -1,
                            -1,
                        ),
                        0.25,
                        colors.grey,
                    ),
                    (
                        "BACKGROUND",
                        (
                            0,
                            0,
                        ),
                        (
                            0,
                            -1,
                        ),
                        colors.whitesmoke,
                    ),
                    (
                        "LEFTPADDING",
                        (
                            0,
                            0,
                        ),
                        (
                            -1,
                            -1,
                        ),
                        4,
                    ),
                    (
                        "RIGHTPADDING",
                        (
                            0,
                            0,
                        ),
                        (
                            -1,
                            -1,
                        ),
                        4,
                    ),
                ]
            )
        )

        elementos.append(
            tabla_resumen
        )

        elementos.append(
            Spacer(
                1,
                6 * mm,
            )
        )

    # --------------------------------------------------------
    # Resultados
    # --------------------------------------------------------

    resultados = (
        _extraer_resultados(
            respuesta
        )
    )

    if resultados:

        columnas = (
            _columnas_pdf(
                resultados,
                respuesta.get(
                    "columnas"
                ),
            )
        )

        datos = [
            [
                Paragraph(
                    f"<b>{campo}</b>",
                    estilos[
                        "BodyText"
                    ],
                )
                for campo in columnas
            ]
        ]

        for registro in resultados:

            if not isinstance(
                registro,
                dict,
            ):

                registro = {
                    "resultado":
                        registro
                }

            fila = []

            for campo in columnas:

                valor = (
                    _valor_exportable(
                        registro.get(
                            campo
                        )
                    )
                )

                valor = escape(
                    valor
                )

                fila.append(
                    Paragraph(
                        valor,
                        estilos[
                            "BodyText"
                        ],
                    )
                )

            datos.append(
                fila
            )

        ancho_total = (
            267 * mm
        )

        ancho_columna = (
            ancho_total
            / max(
                len(
                    columnas
                ),
                1,
            )
        )

        tabla = Table(
            datos,
            colWidths=[
                ancho_columna
                for _ in columnas
            ],
            repeatRows=1,
        )

        tabla.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (
                            0,
                            0,
                        ),
                        (
                            -1,
                            0,
                        ),
                        colors.lightgrey,
                    ),
                    (
                        "GRID",
                        (
                            0,
                            0,
                        ),
                        (
                            -1,
                            -1,
                        ),
                        0.25,
                        colors.grey,
                    ),
                    (
                        "VALIGN",
                        (
                            0,
                            0,
                        ),
                        (
                            -1,
                            -1,
                        ),
                        "TOP",
                    ),
                    (
                        "FONTSIZE",
                        (
                            0,
                            0,
                        ),
                        (
                            -1,
                            -1,
                        ),
                        7,
                    ),
                    (
                        "LEFTPADDING",
                        (
                            0,
                            0,
                        ),
                        (
                            -1,
                            -1,
                        ),
                        3,
                    ),
                    (
                        "RIGHTPADDING",
                        (
                            0,
                            0,
                        ),
                        (
                            -1,
                            -1,
                        ),
                        3,
                    ),
                ]
            )
        )

        elementos.append(
            tabla
        )

    documento.build(
        elementos
    )

    buffer.seek(
        0
    )

    response = HttpResponse(
        buffer.getvalue(),
        content_type=(
            "application/pdf"
        ),
    )

    # INLINE:
    # abre el PDF en el navegador.
    # Desde el visor puede descargarse.
    response[
        "Content-Disposition"
    ] = (
        'inline; filename="'
        + _nombre_archivo(
            "pdf"
        )
        + '"'
    )

    return response


@staff_member_required
@require_http_methods(["POST"])
def vocabulario_test_json(request):

    modelo = (
        request.POST.get("modelo")
        or ""
    ).strip()

    campo = (
        request.POST.get("campo")
        or ""
    ).strip()

    valor_canonico = (
        request.POST.get(
            "valor_canonico"
        )
        or ""
    ).strip()

    aliases_texto = (
        request.POST.get("aliases")
        or ""
    ).strip()

    modo = (
        request.POST.get("modo")
        or "probar"
    ).strip().lower()


    if not modelo:

        return JsonResponse(
            {
                "ok": False,
                "error":
                    "Debes indicar el modelo.",
            },
            status=400,
        )


    if not campo:

        return JsonResponse(
            {
                "ok": False,
                "error":
                    "Debes indicar el campo.",
            },
            status=400,
        )


    if not valor_canonico:

        return JsonResponse(
            {
                "ok": False,
                "error":
                    "Debes indicar el valor canónico.",
            },
            status=400,
        )


    aliases = [
        linea.strip()
        for linea in aliases_texto.splitlines()
        if linea.strip()
    ]


    if not aliases:

        return JsonResponse(
            {
                "ok": False,
                "error":
                    "Debes ingresar al menos un alias.",
            },
            status=400,
        )


    # ========================================================
    # PROBAR
    # ========================================================

    if modo == "probar":

        return JsonResponse(
            {
                "ok": True,

                "guardado":
                    False,

                "modelo":
                    modelo,

                "campo":
                    campo,

                "valor_canonico":
                    valor_canonico,

                "aliases":
                    aliases,

                "mensaje":
                    (
                        "Equivalencia preparada correctamente. "
                        "Todavía no se ha guardado nada."
                    ),
            },
            json_dumps_params={
                "ensure_ascii": False
            },
        )


    # ========================================================
    # GUARDAR
    # ========================================================

    if modo != "guardar":

        return JsonResponse(
            {
                "ok": False,
                "error":
                    "Modo no reconocido.",
            },
            status=400,
        )


    try:

        resultados = (
            guardar_equivalencias(
                modelo=modelo,
                campo=campo,
                valor_canonico=valor_canonico,
                aliases=aliases,
            )
        )

        return JsonResponse(
            {
                "ok": True,

                "guardado":
                    True,

                "total":
                    len(resultados),

                "equivalencias":
                    resultados,

                "mensaje":
                    (
                        f"{len(resultados)} "
                        "equivalencia(s) guardada(s) "
                        "correctamente."
                    ),
            },
            json_dumps_params={
                "ensure_ascii": False
            },
        )

    except Exception as exc:

        return JsonResponse(
            {
                "ok": False,
                "error":
                    str(exc),
            },
            status=400,
            json_dumps_params={
                "ensure_ascii": False
            },
        )

# ============================================================
# HOST016 - CONSOLA DE DIAGNÓSTICO
# ============================================================

@staff_member_required
@require_http_methods(
    [
        "GET",
        "POST",
    ]
)
def diagnostico_ia(request):
    """
    Consola técnica de HOST016.

    Permite observar el pipeline completo de ia_local sin
    introducir decisiones nuevas ni ejecutar etapas adicionales.
    """

    contexto = {
        "pregunta": "",
        "diagnostico": None,
        "error": None,
    }

    if request.method == "POST":

        pregunta = (
            request.POST.get(
                "pregunta"
            )
            or ""
        ).strip()

        contexto[
            "pregunta"
        ] = pregunta

        if not pregunta:

            contexto[
                "error"
            ] = "Escribe una pregunta."

        else:

            try:

                contexto[
                    "diagnostico"
                ] = diagnosticar_pregunta(
                    pregunta,
                    profundidad=3,
                )

            except Exception as exc:

                contexto[
                    "error"
                ] = str(
                    exc
                )

    return render(
        request,
        "ia_local/diagnostico.html",
        contexto,
    )
