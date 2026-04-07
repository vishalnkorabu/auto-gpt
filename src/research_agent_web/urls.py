from __future__ import annotations

from django.urls import path

from . import views


urlpatterns = [
    path("health", views.health, name="health"),
    path("sessions", views.sessions_view, name="sessions"),
    path("sessions/<uuid:session_id>", views.session_detail, name="session-detail"),
    path("sessions/<uuid:session_id>/messages", views.session_messages, name="session-messages"),
    path("sessions/<uuid:session_id>/reports", views.session_reports, name="session-reports"),
    path("chat/start", views.chat_start, name="chat-start"),
    path("chat/status/<uuid:job_id>", views.chat_status, name="chat-status"),
]
