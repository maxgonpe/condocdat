"""Únicas entradas HTTP del motor Qwen + HOST."""
from django.urls import path
from . import views, views_desambiguacion
app_name = "ia_local"
urlpatterns = [
    path("", views.consulta_ia, name="consulta_ia_json"),
    path("consultar/", views.consulta_ia_json, name="consultar"),
    path("consultar-contextual/", views_desambiguacion.consultar_con_aclaracion, name="consultar_contextual"),
    path("diagnostico/", views.diagnostico_ia, name="diagnostico"),
]
