from django.contrib import admin
from .models import (
    Project, ExecutingCompany, Process, DocumentType, DocumentSequence,
    Document, Folder, FolderFile, DocumentAttachment, CorreoEnviado, GrupoCorreo,
    UserSessionLog, UserPresence,
)


class DocumentAttachmentInline(admin.TabularInline):
    model = DocumentAttachment
    extra = 3
    fields = ('file', 'extracted_text', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')


@admin.register(ExecutingCompany)
class ExecutingCompanyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')


@admin.register(DocumentSequence)
class DocumentSequenceAdmin(admin.ModelAdmin):
    list_display = ('project', 'company', 'process', 'doc_type', 'last_number')
    list_filter = ('project',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'project', 'company', 'process', 'doc_type', 'folder', 'status', 'informado', 'date')
    list_filter = ('project', 'status', 'informado', 'doc_type', 'folder')
    search_fields = ('code', 'title', 'description', 'content_extract')
    readonly_fields = ('code', 'created_at', 'updated_at')
    inlines = [DocumentAttachmentInline]


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'date', 'created_at')
    search_fields = ('code', 'title', 'description')
    list_filter = ('date',)


@admin.register(FolderFile)
class FolderFileAdmin(admin.ModelAdmin):
    list_display = ('name', 'folder', 'document', 'created_at')
    list_filter = ('folder',)
    search_fields = ('name', 'extracted_text')


@admin.register(CorreoEnviado)
class CorreoEnviadoAdmin(admin.ModelAdmin):
    list_display = ('asunto', 'enviado_ok', 'enviado_at', 'enviado_por')
    list_filter = ('enviado_ok', 'enviado_at')
    search_fields = ('asunto', 'destinatarios', 'copia')
    readonly_fields = ('enviado_at',)


@admin.register(GrupoCorreo)
class GrupoCorreoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'email_count')
    list_filter = ('activo',)
    search_fields = ('nombre', 'descripcion', 'emails')

    def email_count(self, obj):
        return len(obj.lista_emails())
    email_count.short_description = "Correos"


@admin.register(UserSessionLog)
class UserSessionLogAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "user", "action", "ip_address", "session_key")
    list_filter = ("action", "occurred_at")
    search_fields = ("user__username", "user__first_name", "user__last_name", "ip_address", "session_key", "user_agent")
    readonly_fields = ("occurred_at",)


@admin.register(UserPresence)
class UserPresenceAdmin(admin.ModelAdmin):
    list_display = ("user", "last_seen")
    list_filter = ("last_seen",)
    search_fields = ("user__username", "user__first_name", "user__last_name")
