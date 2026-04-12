from django.urls import path

from . import views

urlpatterns = [
    path("", views.equipos_hub, name="equipos_hub"),
    path("import/", views.equipos_import_view, name="equipos_import"),
    path("download/xlsx/", views.equipos_download_xlsx, name="equipos_download_xlsx"),
    path("export/pdf/", views.equipos_export_pdf, name="equipos_export_pdf"),
    path("search.json", views.equipos_search_json, name="equipos_search_json"),
    path("cambios/", views.equipos_cambios_list, name="equipos_cambios"),
    path("assets/", views.equipos_asset_list, name="equipos_asset_list"),
    path("assets/records.json", views.equipos_asset_records_json, name="equipos_asset_records_json"),
    path("assets/<int:pk>/edit/", views.equipos_asset_edit, name="equipos_asset_edit"),
    path("locations/", views.equipos_location_list, name="equipos_location_list"),
    path(
        "locations/records.json",
        views.equipos_location_records_json,
        name="equipos_location_records_json",
    ),
    path(
        "locations/<int:pk>/edit/",
        views.equipos_location_edit,
        name="equipos_location_edit",
    ),
    path("otros/", views.equipos_otro_list, name="equipos_otro_list"),
    path("otros/records.json", views.equipos_otro_records_json, name="equipos_otro_records_json"),
    path("otros/<int:pk>/edit/", views.equipos_otro_edit, name="equipos_otro_edit"),
    path("resumen/", views.equipos_resumen_list, name="equipos_resumen_list"),
    path(
        "resumen/<int:pk>/edit/",
        views.equipos_resumen_edit,
        name="equipos_resumen_edit",
    ),
    path("significado/", views.equipos_significado_list, name="equipos_significado_list"),
    path(
        "significado/<int:pk>/edit/",
        views.equipos_significado_edit,
        name="equipos_significado_edit",
    ),
]
