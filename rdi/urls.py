from django.urls import path

from . import views


urlpatterns = [
    path("", views.rdi_list_view, name="rdi_list"),
    path("import/", views.rdi_import_view, name="rdi_import"),
    path("records.json", views.rdi_records_json, name="rdi_records_json"),
    path("export/excel/", views.rdi_export_excel, name="rdi_export_excel"),
    path("export/pdf/", views.rdi_export_pdf, name="rdi_export_pdf"),
]

