from __future__ import annotations

from django.contrib import admin

from .models import (
    ConversationMessage,
    ConversationSession,
    DocumentChunk,
    DocumentTask,
    DocumentTaskProgressEvent,
    JobProgressEvent,
    ResearchJob,
    SavedReport,
    UserDocument,
)


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "mode", "dry_run", "updated_at")
    search_fields = ("title",)


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "role", "created_at", "sources_count")
    search_fields = ("content",)
    list_filter = ("role",)


@admin.register(ResearchJob)
class ResearchJobAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "state", "mode", "dry_run", "updated_at")
    list_filter = ("state", "mode", "dry_run")
    search_fields = ("query", "error")


@admin.register(JobProgressEvent)
class JobProgressEventAdmin(admin.ModelAdmin):
    list_display = ("job", "sequence", "message", "created_at")
    search_fields = ("message",)


@admin.register(SavedReport)
class SavedReportAdmin(admin.ModelAdmin):
    list_display = ("headline", "session", "confidence_score", "sources_count", "created_at")
    search_fields = ("headline",)


@admin.register(UserDocument)
class UserDocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "file_type", "status", "updated_at")
    list_filter = ("file_type", "status")
    search_fields = ("name", "content")


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "chunk_index", "created_at")
    search_fields = ("content",)


@admin.register(DocumentTask)
class DocumentTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "task_type", "owner", "state", "updated_at")
    list_filter = ("task_type", "state")
    search_fields = ("title", "error")


@admin.register(DocumentTaskProgressEvent)
class DocumentTaskProgressEventAdmin(admin.ModelAdmin):
    list_display = ("task", "sequence", "message", "created_at")
    search_fields = ("message",)
