from django.urls import path
from . import views

urlpatterns = [
    path('', views.document_list, name='document_list'),
    path('buscar/', views.search_unified_view, name='search_unified'),
    path('carpetas/', views.folder_list, name='folder_list'),
    path('carpetas/<int:pk>/', views.folder_detail, name='folder_detail'),
    path('carpetas/<int:pk>/archivos/', views.folder_upload_files, name='folder_upload_files'),
    path('<int:pk>/', views.document_detail, name='document_detail'),
    path('<int:pk>/adjuntos/', views.document_upload_attachments, name='document_upload_attachments'),
    path('<int:pk>/eliminar/', views.document_delete, name='document_delete'),
]
