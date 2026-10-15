from django.urls import path

from . import views

app_name = "ia_local"

urlpatterns = [
    path("", views.consulta_ia, name="consulta_ia_json"),
    path("consultar/", views.consulta_ia_json, name="consultar"),
    path("test-guardar-regla/", views.guardar_regla_test_json, name="guardar_regla_test_json",),
    path("test-guardar-patron/", views.guardar_patron_test_json, name="guardar_patron_test_json",),
    path("reglas/", views.reglas_semanticas, name="reglas_semanticas",),
    path("reglas/<int:pk>/estado/", views.cambiar_estado_regla, name="cambiar_estado_regla",),
    path("test-vocabulario/", views.vocabulario_test_json, name="vocabulario_test_json",),
    path("exportar/excel/",views.exportar_resultado_excel,name="exportar_resultado_excel",),
    path("exportar/pdf/",views.exportar_resultado_pdf,name="exportar_resultado_pdf",),
    path("diagnostico/", views.diagnostico_ia, name="diagnostico"),
]
