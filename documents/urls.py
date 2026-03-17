from django.urls import path
from . import views

urlpatterns = [
    path('', views.document_list, name='document_list'),
    path('contrato/', views.contrato_view, name='contrato_view'),
    path('correo/', views.enviar_correo_view, name='enviar_correo'),
    path('correo/extraer-transmittal/', views.extraer_transmittal_ajax, name='extraer_transmittal_ajax'),
    path('buscar/', views.search_unified_view, name='search_unified'),
    path('carpetas/', views.folder_list, name='folder_list'),
    path('carpetas/<int:pk>/', views.folder_detail, name='folder_detail'),
    path('carpetas/<int:pk>/archivos/', views.folder_upload_files, name='folder_upload_files'),
    path('cartas/', views.cartas_status, name='cartas_status'),
    path('logs-propamat-odata/', views.logs_propamat_odata, name='logs_propamat_odata'),
    path('logs-odata-propamat/', views.logs_odata_propamat, name='logs_odata_propamat'),
    path('<int:pk>/', views.document_detail, name='document_detail'),
    path('<int:pk>/adjuntos/', views.document_upload_attachments, name='document_upload_attachments'),
    path('<int:pk>/eliminar/', views.document_delete, name='document_delete'),
]
