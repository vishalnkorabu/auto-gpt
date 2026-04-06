from __future__ import annotations

from django.contrib import admin

from .models import ConversationMessage, ConversationSession, JobProgressEvent, ResearchJob


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
