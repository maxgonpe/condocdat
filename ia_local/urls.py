from django.urls import path

from . import views, views_bridge

app_name = "ia_local"

urlpatterns = [
    path("", views.consulta_ia, name="consulta_ia_json"),
    path("consultar/", views.consulta_ia_json, name="consultar"),

    path("test-guardar-regla/", views.guardar_regla_test_json, name="guardar_regla_test_json",),
    path("test-guardar-patron/", views.guardar_patron_test_json, name="guardar_patron_test_json",),
    path("test-vocabulario/", views.vocabulario_test_json, name="vocabulario_test_json",),

    path("reglas/", views.reglas_semanticas, name="reglas_semanticas",),
    path("reglas/<int:pk>/estado/", views.cambiar_estado_regla, name="cambiar_estado_regla",),

    path("bridge/consultar/",views_bridge.consulta_bridge_json, name="bridge_consultar",),
    
    path("exportar/excel/",views.exportar_resultado_excel,name="exportar_resultado_excel",),
    path("exportar/pdf/",views.exportar_resultado_pdf,name="exportar_resultado_pdf",),
    path("diagnostico/", views.diagnostico_ia, name="diagnostico"),
]

'''

from django.urls import path

from . import views
from . import views_bridge


app_name = "ia_local"


urlpatterns = [

    # ========================================================
    # FLUJO ACTUAL
    # ========================================================

    path("", views.consulta_ia,name="consulta_ia_json", ),
    path("consultar/",views.consulta_ia_json,name="consultar",),

    # ========================================================
    # IA-BRIDGE006
    # NUEVO PIPELINE EN PARALELO
    # ========================================================

    path("bridge/consultar/",views_bridge.consulta_bridge_json, name="bridge_consultar",),

    # ========================================================
    # REGLAS / SEMÁNTICA LEGADA
    # ========================================================

    path("test-guardar-regla/", views.guardar_regla_test_json, name="guardar_regla_test_json",),
    path("test-guardar-patron/",views.guardar_patron_test_json, name="guardar_patron_test_json",),

    path("reglas/", views.reglas_semanticas, name="reglas_semanticas",),

    path("reglas/<int:pk>/estado/", views.cambiar_estado_regla, name="cambiar_estado_regla",),

    path( "test-vocabulario/", views.vocabulario_test_json, name="vocabulario_test_json", ),

    # ========================================================
    # EXPORTACIÓN
    # ========================================================

    path("exportar/excel/", views.exportar_resultado_excel, name="exportar_resultado_excel",),

    path("exportar/pdf/",views.exportar_resultado_pdf,name="exportar_resultado_pdf",),
] 
'''