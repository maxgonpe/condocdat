from django.contrib import admin
from .models import Project, ExecutingCompany, Process, DocumentType, DocumentSequence, Document


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
    list_display = ('code', 'title', 'project', 'company', 'process', 'doc_type', 'status', 'date')
    list_filter = ('project', 'status', 'doc_type')
    search_fields = ('code', 'title', 'description')
    readonly_fields = ('code', 'created_at', 'updated_at')
