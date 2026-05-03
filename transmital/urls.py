from django.urls import path

from . import views

urlpatterns = [
    path("", views.transmital_hub, name="transmital_hub"),
    path("carpetas/", views.transmital_folder_builder, name="transmital_folder_builder"),
    path("crear/", views.transmital_create, name="transmital_create"),
    path("<int:pk>/editar/", views.transmital_edit, name="transmital_edit"),
    path("<int:pk>/descargar.xlsx", views.transmital_download_xlsx, name="transmital_download_xlsx"),
    path("<int:pk>/descargar.pdf", views.transmital_export_pdf, name="transmital_export_pdf"),
]
