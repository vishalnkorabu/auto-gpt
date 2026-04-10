from __future__ import annotations

from django.contrib import admin

from .models import (
    ApiRequestLog,
    ConversationMessage,
    ConversationSession,
    DocumentChunk,
    DocumentTask,
    DocumentTaskProgressEvent,
    JobProgressEvent,
    LLMUsageEvent,
    ResearchJob,
    SavedReport,
    UserProfile,
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
    list_display = ("id", "session", "state", "queue_backend", "mode", "dry_run", "updated_at")
    list_filter = ("state", "queue_backend", "mode", "dry_run")
    search_fields = ("query", "error", "celery_task_id")


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
    list_display = ("title", "task_type", "owner", "state", "queue_backend", "updated_at")
    list_filter = ("task_type", "state", "queue_backend")
    search_fields = ("title", "error", "celery_task_id")


@admin.register(DocumentTaskProgressEvent)
class DocumentTaskProgressEventAdmin(admin.ModelAdmin):
    list_display = ("task", "sequence", "message", "created_at")
    search_fields = ("message",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "updated_at")
    search_fields = ("user__username", "user__email", "display_name")


@admin.register(LLMUsageEvent)
class LLMUsageEventAdmin(admin.ModelAdmin):
    list_display = ("provider", "model", "operation", "total_tokens", "estimated_cost_usd", "success", "created_at")
    list_filter = ("provider", "model", "operation", "success")
    search_fields = ("error_message",)


@admin.register(ApiRequestLog)
class ApiRequestLogAdmin(admin.ModelAdmin):
    list_display = ("method", "path", "status_code", "duration_ms", "user", "created_at")
    list_filter = ("method", "status_code")
    search_fields = ("path", "error_message", "user__username")
