from django.urls import path

from . import views

urlpatterns = [
    path("", views.gantt_hub, name="gantt_hub"),
    path("import/", views.gantt_import_view, name="gantt_import"),
    path("export/excel/", views.gantt_export_excel, name="gantt_export_excel"),
    path("export/csv/", views.gantt_export_csv, name="gantt_export_csv"),
    path("export/project-xml/", views.gantt_export_project_xml, name="gantt_export_project_xml"),
    path("tasks/", views.gantt_task_list, name="gantt_task_list"),
    path("tasks/records.json", views.gantt_task_records_json, name="gantt_task_records_json"),
    path("tasks/<int:pk>/edit/", views.gantt_task_edit, name="gantt_task_edit"),
    path("cambios/", views.gantt_cambios_list, name="gantt_cambios"),
]
