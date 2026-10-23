from django.urls import path

from . import views_desambiguacion

from . import (
    views,
    views_bridge,
    views_correcciones,
)


app_name = "ia_local"


urlpatterns = [
    # IA-LLM007-F4-07: endpoint contextual; el endpoint legado sigue igual.
    path(
        "consultar-contextual/",
        views_desambiguacion.consultar_con_aclaracion,
        name="consultar_contextual",
    ),

    # ========================================================
    # INTERFAZ PRINCIPAL
    # ========================================================

    path(
        "",
        views.consulta_ia,
        name="consulta_ia_json",
    ),

    path(
        "consultar/",
        views.consulta_ia_json,
        name="consultar",
    ),

    # ========================================================
    # PIPELINE FINAL
    # ========================================================

    path(
        "bridge/consultar/",
        views_bridge.consulta_bridge_json,
        name="bridge_consultar",
    ),

    # ========================================================
    # IA-FINAL008
    # CORRECCIÓN SEMÁNTICA CONTROLADA
    # ========================================================

    path(
        "correcciones/proponer/",
        views_correcciones.proponer_correccion_json,
        name="proponer_correccion",
    ),

    # ========================================================
    # REGLAS / SEMÁNTICA
    # ========================================================

    path(
        "test-guardar-regla/",
        views.guardar_regla_test_json,
        name="guardar_regla_test_json",
    ),

    path(
        "test-guardar-patron/",
        views.guardar_patron_test_json,
        name="guardar_patron_test_json",
    ),

    path(
        "test-vocabulario/",
        views.vocabulario_test_json,
        name="vocabulario_test_json",
    ),

    path(
        "reglas/",
        views.reglas_semanticas,
        name="reglas_semanticas",
    ),

    path(
        "reglas/<int:pk>/estado/",
        views.cambiar_estado_regla,
        name="cambiar_estado_regla",
    ),

    # ========================================================
    # EXPORTACIÓN
    # ========================================================

    path(
        "exportar/excel/",
        views.exportar_resultado_excel,
        name="exportar_resultado_excel",
    ),

    path(
        "exportar/pdf/",
        views.exportar_resultado_pdf,
        name="exportar_resultado_pdf",
    ),

    # ========================================================
    # DIAGNÓSTICO
    # ========================================================

    path(
        "diagnostico/",
        views.diagnostico_ia,
        name="diagnostico",
    ),
]