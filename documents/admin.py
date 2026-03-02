from django.contrib import admin
from .models import Project, ExecutingCompany, Process, DocumentType, DocumentSequence, Document, Folder, FolderFile, DocumentAttachment


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
    list_display = ('code', 'title', 'project', 'company', 'process', 'doc_type', 'folder', 'status', 'date')
    list_filter = ('project', 'status', 'doc_type', 'folder')
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
