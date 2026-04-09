from __future__ import annotations

from django.urls import path

from . import views


urlpatterns = [
    path("health", views.health, name="health"),
    path("auth/me", views.auth_me, name="auth-me"),
    path("auth/register", views.auth_register, name="auth-register"),
    path("auth/login", views.auth_login, name="auth-login"),
    path("auth/logout", views.auth_logout, name="auth-logout"),
    path("sessions", views.sessions_view, name="sessions"),
    path("sessions/<uuid:session_id>", views.session_detail, name="session-detail"),
    path("sessions/<uuid:session_id>/messages", views.session_messages, name="session-messages"),
    path("sessions/<uuid:session_id>/reports", views.session_reports, name="session-reports"),
    path("jobs", views.jobs_view, name="jobs"),
    path("documents", views.documents_view, name="documents"),
    path("documents/query", views.document_query, name="document-query"),
    path("documents/tasks/<uuid:task_id>", views.document_task_status, name="document-task-status"),
    path("documents/tasks/<uuid:task_id>/cancel", views.document_task_cancel, name="document-task-cancel"),
    path("documents/tasks/<uuid:task_id>/retry", views.document_task_retry, name="document-task-retry"),
    path("chat/start", views.chat_start, name="chat-start"),
    path("chat/status/<uuid:job_id>", views.chat_status, name="chat-status"),
]
