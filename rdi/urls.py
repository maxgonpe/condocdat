from django.urls import path

from . import views


urlpatterns = [
    path(
        "planos-actualizados/",
        views.planos_actualizados_view,
        name="planos_actualizados_list",
    ),
    path(
        "planos-actualizados/records.json",
        views.planos_actualizados_json,
        name="planos_actualizados_records_json",
    ),
    path(
        "planos-actualizados/export/excel/",
        views.planos_actualizados_export_excel,
        name="planos_actualizados_export_excel",
    ),
    path(
        "planos-actualizados/export/pdf/",
        views.planos_actualizados_export_pdf,
        name="planos_actualizados_export_pdf",
    ),
    path(
        "planos-iniciales/",
        views.planos_iniciales_list_view,
        name="planos_iniciales_list",
    ),
    path(
        "planos-iniciales/import/",
        views.planos_iniciales_import_view,
        name="planos_iniciales_import",
    ),
    path(
        "planos-iniciales/records.json",
        views.planos_iniciales_records_json,
        name="planos_iniciales_records_json",
    ),
    path(
        "planos-iniciales/export/excel/",
        views.planos_iniciales_export_excel,
        name="planos_iniciales_export_excel",
    ),
    path(
        "planos-iniciales/export/pdf/",
        views.planos_iniciales_export_pdf,
        name="planos_iniciales_export_pdf",
    ),
    path("planos/", views.planos_list_view, name="planos_list"),
    path("planos/import/", views.planos_import_view, name="planos_import"),
    path("planos/records.json", views.planos_records_json, name="planos_records_json"),
    path("planos/export/excel/", views.planos_export_excel, name="planos_export_excel"),
    path("planos/export/pdf/", views.planos_export_pdf, name="planos_export_pdf"),
    path("informar-bim/", views.informar_bim_list_view, name="informar_bim_list"),
    path(
        "aumentos-disminuciones/",
        views.rdi_increments_decrements_view,
        name="rdi_increments_decrements",
    ),
    path("", views.rdi_list_view, name="rdi_list"),
    path("import/", views.rdi_import_view, name="rdi_import"),
    path("records.json", views.rdi_records_json, name="rdi_records_json"),
    path(
        "records-increments-decrements.json",
        views.rdi_increments_decrements_json,
        name="rdi_increments_decrements_json",
    ),
    path(
        "export/aumentos-disminuciones/excel/",
        views.rdi_increments_decrements_export_excel,
        name="rdi_increments_decrements_export_excel",
    ),
    path(
        "export/aumentos-disminuciones/pdf/",
        views.rdi_increments_decrements_export_pdf,
        name="rdi_increments_decrements_export_pdf",
    ),
    path("export/excel/", views.rdi_export_excel, name="rdi_export_excel"),
    path("export/pdf/", views.rdi_export_pdf, name="rdi_export_pdf"),
]

