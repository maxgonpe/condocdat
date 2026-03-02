# Propuesta: Carpetas, documentos y búsqueda por nombre y contenido

## Objetivo

Poder **almacenar carpetas** (ej. transmittals como `ODATA-ST01-F5-TTAL-PPT-00050`) y, dentro de ellas, **documentos** que sean:

- **Rastreables** por nombre y por **contenido interno** (ej. encontrar “Juan Pérez” dentro de un PDF).
- **Seleccionables** desde una búsqueda única (por código, título, nombre de archivo o texto extraído).

Así se compensa que en SharePoint los nombres de carpeta no sean descriptivos y no se pueda buscar por lo que dice el archivo por dentro.

---

## 1. Modelo de datos propuesto

### 1.1 Carpeta (Transmittal / “Carpeta SharePoint”)

Representa una carpeta o envío (transmittal) que agrupa documentos.

| Campo        | Tipo        | Descripción |
|-------------|-------------|-------------|
| `code`      | CharField   | Código único (ej. `ODATA-ST01-F5-TTAL-PPT-00050`) |
| `title`     | CharField   | Título opcional |
| `description` | TextField | Descripción libre |
| `date`      | DateField   | Fecha del envío/carpeta |
| `created_at` / `updated_at` | DateTimeField | Auditoría |

- **Relación:** una carpeta tiene muchos **documentos** y/o muchos **archivos** (ver más abajo).

### 1.2 Documento (el que ya tienes) + vínculo a carpeta y texto para búsqueda

- Añadir en tu modelo `Document` actual:
  - **`folder`** → `ForeignKey(Folder, null=True, blank=True, related_name='documents')`.  
    Así un documento puede pertenecer a una carpeta (transmittal).
  - **`content_extract`** → `TextField(blank=True)`.  
    Aquí se guarda el **texto extraído** del archivo adjunto (`file`) cuando se sube o se reindexa. Ese texto es el que se usará para buscar “por contenido” (ej. “Juan Pérez”).

Sigue siendo un solo tipo de entidad “documento” (con código PROY-EECC-PR-TIP-#####), pero ahora:
- Puede asociarse a una carpeta.
- Tiene un campo indexable con el contenido del PDF/DOCX para búsqueda full‑text.

### 1.3 Archivo dentro de carpeta (opcional pero recomendable)

Para representar **varios archivos dentro de una misma carpeta** que no siempre son un “Document” con código (p. ej. PDFs sueltos en la carpeta del transmittal):

| Campo           | Tipo      | Descripción |
|-----------------|-----------|-------------|
| `folder`        | FK Folder | Carpeta a la que pertenece |
| `name`          | CharField | Nombre del archivo (como se llama en SharePoint o al subir) |
| `file`          | FileField | Archivo subido (PDF, DOCX, etc.) |
| `extracted_text`| TextField | Texto extraído del archivo para búsqueda |
| `document`      | FK Document (null=True) | Opcional: si este archivo es el adjunto de un Document, enlace aquí |
| `created_at`    | DateTimeField | Fecha de carga |

Con esto:

- **Carpeta** = contenedor (ej. `ODATA-ST01-F5-TTAL-PPT-00050`).
- **Document** = documento con código de control (PROY-EECC-PR-TIP-#####), puede tener `folder` y `content_extract`.
- **FolderFile** = cualquier archivo dentro de la carpeta (nombre + contenido extraído), con enlace opcional a `Document`.

La búsqueda podrá mirar:
- En `Document`: código, título, descripción, `content_extract`.
- En `FolderFile`: nombre (`name`), `extracted_text`.

---

## 2. Extracción de texto (para búsqueda por contenido)

Cada vez que se suba (o se reindexe) un archivo:

1. **PDF:** con `PyMuPDF` (fitz) o `pypdf` leer las páginas y concatenar el texto → guardar en `content_extract` (Document) o `extracted_text` (FolderFile).
2. **DOCX:** con `python-docx` leer párrafos y tablas → mismo destino.
3. **Otras extensiones:** opcionalmente solo indexar el nombre del archivo; más adelante se puede añadir soporte para más formatos.

Esto se puede hacer:

- En el **save** del modelo (señal `post_save` o override de `save`) cuando `document.file` o `folder_file.file` cambie.
- O con un **comando de management** `reindex_documents` que recorra documentos/archivos y rellene los campos de texto.

Recomendación: **tarea asíncrona** (Celery o similar) para no bloquear la subida; si no, al menos en background thread o comando periódico.

---

## 3. Búsqueda unificada

Una sola **vista de búsqueda** (y una URL, ej. `/documentos/buscar/`) donde el usuario escribe una palabra o frase (ej. “Juan Pérez”, “ODATA-ST01”, “PPT-00050”):

1. **Por nombre/código:**
   - En `Document`: `code`, `title`, `description`, `revision`, y campos relacionados (project, company, process, doc_type).
   - En `Folder`: `code`, `title`, `description`.
   - En `FolderFile`: `name`.

2. **Por contenido:**
   - En `Document`: `content_extract`.
   - En `FolderFile`: `extracted_text`.

Implementación posible:

- **SQLite:** `filter(Q(content_extract__icontains=term) | Q(title__icontains=term) | ...)`. Funciona bien para volúmenes no enormes.
- **PostgreSQL:** usar `SearchVector` / `SearchRank` para búsqueda full‑text más rápida y relevancia.

El resultado puede mostrarse como:

- **Documentos** que coinciden (con enlace al detalle y a la carpeta si tiene `folder`).
- **Carpetas** que coinciden (por código/título) o que contienen documentos/archivos que coinciden.
- **Archivos en carpeta** (FolderFile) que coinciden por nombre o por `extracted_text`, con enlace a la carpeta y al archivo para abrirlo/descargarlo.

Así, aunque el nombre de la carpeta sea poco descriptivo, el usuario encuentra por “Juan Pérez” y ve en qué carpeta y en qué documento/archivo aparece.

---

## 4. Flujo en la interfaz (condocdat)

1. **Carpetas**
   - Listado de carpetas (código, título, fecha).
   - Al hacer clic en una carpeta → listado de **documentos** de esa carpeta + **archivos** (FolderFile) de esa carpeta (nombre, enlace para abrir, opción “Ver contenido indexado” si se desea).

2. **Búsqueda global**
   - Caja de búsqueda (en el listado de documentos o en la barra principal).
   - Al buscar (por nombre o por contenido):
     - Se muestran **documentos** que coinciden (y en qué carpeta están).
     - Se muestran **archivos en carpeta** que coinciden (nombre o contenido), con enlace a la carpeta y al archivo.
   - Opcional: filtros por carpeta, por proyecto, por tipo de documento, por rango de fechas.

3. **Subida**
   - Al crear/editar un **Document** y adjuntar `file`, se dispara la extracción de texto y se guarda en `content_extract`.
   - Al añadir un **FolderFile** a una carpeta, se sube el archivo y se rellena `extracted_text` con la misma lógica.

Con esto se consigue que **toda la información que está dentro de las carpetas** (nombres y contenido de documentos) sea **rastreable y seleccionable** desde condocdat, sin depender de que el nombre de la carpeta en SharePoint sea descriptivo.

---

## 5. Resumen de pasos técnicos

| Paso | Acción |
|------|--------|
| 1 | Crear modelo **Folder** (code, title, description, date, timestamps). |
| 2 | En **Document** añadir `folder` (FK, null=True) y `content_extract` (TextField, blank=True). |
| 3 | Crear modelo **FolderFile** (folder, name, file, extracted_text, document FK opcional). |
| 4 | Añadir dependencias: `PyMuPDF` o `pypdf`, `python-docx`. |
| 5 | Implementar función **extraer_texto(archivo)** (PDF/DOCX) y llamarla al guardar Document con file o al guardar FolderFile. |
| 6 | Crear vista **búsqueda unificada** (por nombre + content_extract / extracted_text). |
| 7 | UI: listado de carpetas, detalle de carpeta (documentos + archivos), y caja de búsqueda que use la nueva vista. |

Si quieres, el siguiente paso puede ser bajar esto a **cambios concretos** en tu `models.py` (clases `Folder` y `FolderFile`, y campos nuevos en `Document`) y la migración correspondiente.
