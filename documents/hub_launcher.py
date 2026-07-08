"""
Definición de secciones y enlaces del Centro visual (launcher alternativo).
Las URLs se resuelven en la vista para garantizar que reverse() sea válido.
"""
from __future__ import annotations

from django.urls import NoReverseMatch, reverse


def _item(
    title: str,
    url_name: str,
    icon: str,
    desc: str = "",
    *,
    staff_only: bool = False,
    url_kwargs: dict | None = None,
    external: bool = False,
):
    return {
        "title": title,
        "url_name": url_name,
        "url_kwargs": url_kwargs or {},
        "icon": icon,
        "desc": desc,
        "staff_only": staff_only,
        "external": external,
    }


HUB_SECTIONS_DEF = [
    {
        "id": "inicio",
        "label": "Inicio",
        "icon": "home",
        "items": [
            _item("Pizarra", "pizarra", "board", "Resumen de cartas, logs y RDI."),
            _item("Panel clásico", "dashboard", "panel", "Panel staff con métricas y logs.", staff_only=True),
            _item("Enviar correo", "enviar_correo", "mail", "Correo y plantilla transmittal.", staff_only=True),
            _item("Correos enviado", "correos_enviados_list", "mail-log", "Historial de envíos.", staff_only=True),
            _item("Informar de Odata", "informar_list", "inform", "Carpetas Propamat → informar.", staff_only=True),
            _item("Informar de TRN", "informar_trn_list", "inform", "Carpetas TRN → informar.", staff_only=True),
            _item("Informar desde BIM", "informar_bim_list", "bim", "RDI desde BIM.", staff_only=True),
        ],
    },
    {
        "id": "documentos",
        "label": "Documentos",
        "icon": "folder",
        "items": [
            _item("Carpetas", "folder_list", "folder", "Transmittals y agrupación."),
            _item("Documentos", "document_list", "doc", "Listado codificado."),
            _item("Buscar", "search_unified", "search", "Búsqueda global en contenido."),
            _item("Contrato", "contrato_view", "contract", "Vista restringida a contrato."),
            _item("Trazabilidad", "trazabilidad", "trace", "Recorrido ODATA / TRN."),
        ],
    },
    {
        "id": "transmital",
        "label": "Transmital",
        "icon": "send",
        "items": [
            _item("Gestión de transmital", "transmital_hub", "send", "Crear y editar transmitales."),
            _item("Creador de carpetas", "transmital_folder_builder", "folder-plus", "Secuencias y carpetas locales."),
        ],
    },
    {
        "id": "odata",
        "label": "ODATA ↔ Propamat",
        "icon": "exchange",
        "items": [
            _item("Estatus cartas", "cartas_status", "letter", "Estado de cartas y respuestas."),
            _item("Logs Propamat a Odata", "logs_odata_propamat", "log", "Comunicaciones hacia Odata."),
            _item("Logs Odata a Propamat", "logs_propamat_odata", "log", "Comunicaciones desde Odata."),
        ],
    },
    {
        "id": "rdi",
        "label": "RDI & Planos",
        "icon": "rdi",
        "items": [
            _item("RDI", "rdi_list", "rdi", "Registros de información."),
            _item("Aumentos / disminuciones", "rdi_increments_decrements", "chart", "Variaciones RDI."),
            _item("Planos Colo 7 8 9", "planos_list", "blueprint", "Listado e importación planos."),
            _item("Planos iniciales", "planos_iniciales_list", "blueprint", "Propuesta inicial."),
            _item("Planos actualizados", "planos_actualizados_list", "blueprint", "Diferencias propuesta vs proyecto."),
                _item("Resumen diferencias mensuales", "planos_diferencias_mensuales_list", "blueprint", "Diferencias por mes y descargas Excel/PDF."),
        ],
    },
    {
        "id": "equipos",
        "label": "Equipos",
        "icon": "gear",
        "items": [
            _item("Control de equipos", "equipos_hub", "gear", "Libro Excel maestro."),
            _item("Resumen - TD", "equipos_resumen_list", "table", "Tabla resumen."),
            _item("Significado status", "equipos_significado_list", "tag", "Significados de estado."),
            _item("Locations", "equipos_location_list", "pin", "Ubicaciones."),
            _item("Asset", "equipos_asset_list", "box", "Activos."),
            _item("Otros equipos", "equipos_otro_list", "box", "Otros ítems."),
            _item("Historial de cambios", "equipos_cambios", "history", "Auditoría de ediciones."),
        ],
    },
    {
        "id": "gantt",
        "label": "Gantt",
        "icon": "gantt",
        "items": [
            _item("Control Gantt", "gantt_hub", "gantt", "Importar .mpp y hub."),
            _item("Ruta crítica", "gantt_critical_path", "route", "Análisis de ruta crítica."),
            _item("Ruta crítica gráfica", "gantt_critical_path_graphic", "route", "Vista gráfica."),
            _item("Curva S", "gantt_s_curve", "curve", "Avance acumulado."),
            _item("Estado", "gantt_estado", "status", "Estado del cronograma."),
            _item("Tareas", "gantt_task_list", "tasks", "Edición de tareas."),
            _item("Historial de cambios", "gantt_cambios", "history", "Log de cambios Gantt."),
        ],
    },
    {
        "id": "sistema",
        "label": "Sistema",
        "icon": "settings",
        "items": [
            _item("Administración Django", "admin:index", "admin", "Panel admin.", staff_only=True),
            _item("Proyectos", "admin:documents_project_changelist", "catalog", "Catálogo PROY.", staff_only=True),
            _item("EECC", "admin:documents_executingcompany_changelist", "catalog", "Empresas ejecutoras.", staff_only=True),
            _item("Procesos", "admin:documents_process_changelist", "catalog", "Disciplinas / procesos.", staff_only=True),
            _item("Tipos de documento", "admin:documents_documenttype_changelist", "catalog", "Tipos TIP.", staff_only=True),
        ],
    },
]


def build_hub_sections(user) -> list[dict]:
    """Construye secciones con URLs resueltas, filtrando ítems staff si aplica."""
    is_staff = getattr(user, "is_staff", False)
    sections: list[dict] = []

    for sec in HUB_SECTIONS_DEF:
        items_out = []
        for raw in sec["items"]:
            if raw.get("staff_only") and not is_staff:
                continue
            try:
                url = reverse(raw["url_name"], kwargs=raw.get("url_kwargs") or {})
            except NoReverseMatch:
                continue
            items_out.append(
                {
                    "title": raw["title"],
                    "desc": raw.get("desc") or "",
                    "icon": raw.get("icon") or "doc",
                    "url": url,
                    "external": raw.get("external", False),
                }
            )
        if items_out:
            sections.append(
                {
                    "id": sec["id"],
                    "label": sec["label"],
                    "icon": sec.get("icon") or "folder",
                    "items": items_out,
                }
            )
    return sections
