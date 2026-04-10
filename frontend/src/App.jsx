import { useEffect, useRef, useState } from "react";

import AuthScreen from "./components/AuthScreen";
import ChatMessageList from "./components/ChatMessageList";
import Composer from "./components/Composer";
import DocumentsDrawer from "./components/DocumentsDrawer";
import HistorySidebar from "./components/HistorySidebar";
import JobsDrawer from "./components/JobsDrawer";
import ProfileDrawer from "./components/ProfileDrawer";
import SourcesDrawer from "./components/SourcesDrawer";
import TopBar from "./components/TopBar";

const SESSION_KEY = "research-agent-session-id";
const EMPTY_OBSERVABILITY = {
  requests: { total: 0, errors: 0, avg_duration_ms: 0, top_paths: [] },
  research_jobs: { total: 0, queued: 0, running: 0, completed: 0, failed: 0 },
  document_tasks: { total: 0, queued: 0, running: 0, completed: 0, failed: 0, canceled: 0 },
  usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0, estimated_cost_usd: 0, llm_errors: 0 },
  recent_errors: [],
  queue: { mode: "thread", broker_url: "", queue_name: "research" },
};

export default function App() {
  const [messages, setMessages] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [observability, setObservability] = useState(EMPTY_OBSERVABILITY);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("multi");
  const [researchDepth, setResearchDepth] = useState("standard");
  const [dryRun, setDryRun] = useState(false);
  const [drawerReport, setDrawerReport] = useState(null);
  const [jobsDrawerOpen, setJobsDrawerOpen] = useState(false);
  const [documentsDrawerOpen, setDocumentsDrawerOpen] = useState(false);
  const [profileDrawerOpen, setProfileDrawerOpen] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [sessionSearch, setSessionSearch] = useState("");
  const [authMode, setAuthMode] = useState("login");
  const [credentials, setCredentials] = useState({ username: "", password: "", email: "", display_name: "" });
  const [user, setUser] = useState(null);
  const [profileForm, setProfileForm] = useState({ username: "", email: "", display_name: "" });
  const [passwordForm, setPasswordForm] = useState({ current_password: "", new_password: "" });
  const [authError, setAuthError] = useState("");
  const [profileError, setProfileError] = useState("");
  const [profileSuccess, setProfileSuccess] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);
  const [docQuestion, setDocQuestion] = useState("");
  const [docAnswer, setDocAnswer] = useState(null);
  const [docError, setDocError] = useState("");
  const [uploadingDocument, setUploadingDocument] = useState(false);
  const [queryingDocuments, setQueryingDocuments] = useState(false);
  const [includeResearch, setIncludeResearch] = useState(false);
  const [documentProgressMessages, setDocumentProgressMessages] = useState([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState([]);
  const [editingDocumentId, setEditingDocumentId] = useState(null);
  const [editingDocumentName, setEditingDocumentName] = useState("");
  const [jobsFilter, setJobsFilter] = useState("all");
  const [activeDocumentTask, setActiveDocumentTask] = useState(null);
  const fileInputRef = useRef(null);
  const pollRef = useRef(null);
  const documentPollRef = useRef(null);

  useEffect(() => {
    void bootstrap();
    return () => {
      window.clearInterval(pollRef.current);
      window.clearInterval(documentPollRef.current);
    };
  }, []);

  useEffect(() => {
    if (!user) return undefined;
    if (!jobsDrawerOpen) return undefined;
    void refreshOperationalData();
    const intervalId = window.setInterval(() => {
      void refreshOperationalData();
    }, 3000);
    return () => window.clearInterval(intervalId);
  }, [jobsDrawerOpen, user]);

  useEffect(() => {
    if (!user) return;
    const timeoutId = window.setTimeout(() => {
      void loadSessions(sessionSearch);
    }, 250);
    return () => window.clearTimeout(timeoutId);
  }, [sessionSearch, user]);

  async function bootstrap() {
    const me = await apiFetch("/api/auth/me");
    if (!me.authenticated) return;
    applyUserState(me.user);
    await Promise.all([loadSessions(), refreshOperationalData(), loadDocuments()]);
    const stored = window.localStorage.getItem(SESSION_KEY);
    if (stored) {
      await loadSessionMessages(stored);
    }
  }

  async function apiFetch(url, options = {}) {
    const headers =
      options.body instanceof FormData
        ? options.headers || {}
        : { "Content-Type": "application/json", ...(options.headers || {}) };

    const response = await fetch(url, {
      credentials: "include",
      headers,
      ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Request failed");
    }
    return data;
  }

  function applyUserState(nextUser) {
    setUser(nextUser);
    setProfileForm({
      username: nextUser.username || "",
      email: nextUser.email || "",
      display_name: nextUser.display_name || nextUser.username || "",
    });
  }

  async function refreshOperationalData() {
    const [jobsData, observabilityData] = await Promise.all([apiFetch("/api/jobs"), apiFetch("/api/observability")]);
    setJobs(jobsData.jobs || []);
    setObservability(observabilityData || EMPTY_OBSERVABILITY);
  }

  async function submitAuth(event) {
    event.preventDefault();
    setAuthError("");
    try {
      const path = authMode === "login" ? "/api/auth/login" : "/api/auth/register";
      const data = await apiFetch(path, {
        method: "POST",
        body: JSON.stringify(credentials),
      });
      applyUserState(data.user);
      setCredentials({ username: "", password: "", email: "", display_name: "" });
      await Promise.all([loadSessions(), refreshOperationalData(), loadDocuments()]);
    } catch (err) {
      setAuthError(err.message);
    }
  }

  async function logoutUser() {
    await apiFetch("/api/auth/logout", { method: "POST", body: "{}" });
    setUser(null);
    setSessions([]);
    setJobs([]);
    setDocuments([]);
    setMessages([]);
    setCurrentSessionId(null);
    setDocAnswer(null);
    setDocError("");
    setDocumentProgressMessages([]);
    setSelectedDocumentIds([]);
    setEditingDocumentId(null);
    setEditingDocumentName("");
    setActiveDocumentTask(null);
    setObservability(EMPTY_OBSERVABILITY);
    setProfileDrawerOpen(false);
    setProfileError("");
    setProfileSuccess("");
    window.localStorage.removeItem(SESSION_KEY);
  }

  async function loadSessions(searchTerm = sessionSearch) {
    const queryString = searchTerm ? `?q=${encodeURIComponent(searchTerm)}` : "";
    const data = await apiFetch(`/api/sessions${queryString}`);
    setSessions(data.sessions || []);
  }

  async function loadJobs() {
    const data = await apiFetch("/api/jobs");
    setJobs(data.jobs || []);
  }

  async function loadDocuments() {
    const data = await apiFetch("/api/documents");
    setDocuments(data.documents || []);
  }

  async function loadSessionMessages(sessionId) {
    try {
      const data = await apiFetch(`/api/sessions/${sessionId}/messages`);
      setCurrentSessionId(sessionId);
      setMode(data.session.mode);
      setResearchDepth(data.session.research_depth || "standard");
      setDryRun(data.session.dry_run);
      setMessages(
        (data.messages || []).map((message) =>
          message.role === "assistant"
            ? { id: message.id, role: "assistant", payload: message, text: message.text }
            : { id: message.id, role: "user", text: message.text }
        )
      );
      window.localStorage.setItem(SESSION_KEY, sessionId);
    } catch {
      window.localStorage.removeItem(SESSION_KEY);
      setCurrentSessionId(null);
      setMessages([]);
    }
  }

  async function startNewSession() {
    setCurrentSessionId(null);
    setMessages([]);
    setDocAnswer(null);
    setDocError("");
    setDocumentProgressMessages([]);
    setSelectedDocumentIds([]);
    setEditingDocumentId(null);
    setEditingDocumentName("");
    setActiveDocumentTask(null);
    window.localStorage.removeItem(SESSION_KEY);
    await Promise.all([loadSessions(), refreshOperationalData(), loadDocuments()]);
  }

  async function renameSession(sessionId) {
    const title = editingTitle.trim();
    if (!title) return;
    await apiFetch(`/api/sessions/${sessionId}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    });
    setEditingSessionId(null);
    setEditingTitle("");
    await loadSessions();
  }

  async function deleteSession(sessionId) {
    await apiFetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
    if (sessionId === currentSessionId) {
      await startNewSession();
    } else {
      await Promise.all([loadSessions(), refreshOperationalData(), loadDocuments()]);
    }
  }

  async function saveProfile() {
    setProfileError("");
    setProfileSuccess("");
    setProfileSaving(true);
    try {
      const data = await apiFetch("/api/auth/profile", {
        method: "PATCH",
        body: JSON.stringify({
          email: profileForm.email,
          display_name: profileForm.display_name,
        }),
      });
      applyUserState(data.user);
      setProfileSuccess("Profile updated.");
    } catch (err) {
      setProfileError(err.message);
    } finally {
      setProfileSaving(false);
    }
  }

  async function savePassword() {
    setProfileError("");
    setProfileSuccess("");
    setProfileSaving(true);
    try {
      await apiFetch("/api/auth/password", {
        method: "POST",
        body: JSON.stringify(passwordForm),
      });
      setPasswordForm({ current_password: "", new_password: "" });
      setProfileSuccess("Password updated.");
    } catch (err) {
      setProfileError(err.message);
    } finally {
      setProfileSaving(false);
    }
  }

  async function sendQuery(event) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || loading) return;

    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setQuery("");
    setLoading(true);

    try {
      const startData = await apiFetch("/api/chat/start", {
        method: "POST",
        body: JSON.stringify({
          query: trimmed,
          mode,
          research_depth: researchDepth,
          dry_run: dryRun,
          session_id: currentSessionId,
        }),
      });

      setCurrentSessionId(startData.session_id);
      window.localStorage.setItem(SESSION_KEY, startData.session_id);
      await Promise.all([loadSessions(), refreshOperationalData(), loadDocuments()]);

      const loadingId = `${startData.job_id}-loading`;
      setMessages((prev) => [
        ...prev,
        { id: loadingId, role: "assistant-loading", query: trimmed, progressMessages: ["Queued research job."] },
      ]);

      pollRef.current = window.setInterval(() => {
        void pollJob(startData.job_id, loadingId);
      }, 1200);
      await pollJob(startData.job_id, loadingId, true);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", text: `Error: ${err.message}` }]);
      setLoading(false);
    }
  }

  async function pollJob(jobId, loadingId, immediate = false) {
    try {
      const data = await apiFetch(`/api/chat/status/${jobId}`);
      setMessages((prev) =>
        prev.map((msg) => (msg.id === loadingId ? { ...msg, progressMessages: data.progress_messages || [] } : msg))
      );

      if (data.state === "completed") {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
        setMessages((prev) =>
          prev.flatMap((msg) =>
            msg.id === loadingId ? [{ role: "assistant", payload: data.result, text: data.result.text }] : [msg]
          )
        );
        setLoading(false);
        await Promise.all([loadSessions(), refreshOperationalData()]);
      } else if (data.state === "failed") {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
        setMessages((prev) =>
          prev.flatMap((msg) => (msg.id === loadingId ? [{ role: "assistant", text: `Error: ${data.error}` }] : [msg]))
        );
        setLoading(false);
        await refreshOperationalData();
      } else if (immediate) {
        return;
      }
    } catch (err) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
      setMessages((prev) =>
        prev.flatMap((msg) => (msg.id === loadingId ? [{ role: "assistant", text: `Error: ${err.message}` }] : [msg]))
      );
      setLoading(false);
      await refreshOperationalData();
    }
  }

  async function uploadDocument(event) {
    event.preventDefault();
    const file = fileInputRef.current?.files?.[0];
    if (!file || uploadingDocument) return;

    const formData = new FormData();
    formData.append("file", file);
    if (currentSessionId) {
      formData.append("session_id", currentSessionId);
    }

    setDocError("");
    setDocAnswer(null);
    setDocumentProgressMessages(["Queued document ingestion job."]);
    setUploadingDocument(true);
    try {
      const data = await apiFetch("/api/documents", { method: "POST", body: formData });
      setActiveDocumentTask({ id: data.task_id, kind: "ingest" });
      documentPollRef.current = window.setInterval(() => {
        void pollDocumentTask(data.task_id, "ingest");
      }, 1200);
      await pollDocumentTask(data.task_id, "ingest", true);
    } catch (err) {
      setDocError(err.message);
      setDocumentProgressMessages([]);
      setActiveDocumentTask(null);
    } finally {
      setUploadingDocument(false);
    }
  }

  async function submitDocumentQuestion(event) {
    event.preventDefault();
    const trimmed = docQuestion.trim();
    if (!trimmed || queryingDocuments) return;

    setDocError("");
    setDocAnswer(null);
    setDocumentProgressMessages(["Queued document query job."]);
    setQueryingDocuments(true);
    try {
      const result = await apiFetch("/api/documents/query", {
        method: "POST",
        body: JSON.stringify({
          question: trimmed,
          session_id: currentSessionId,
          document_ids: selectedDocumentIds,
          include_research: includeResearch,
          research_mode: mode,
          research_depth: researchDepth,
          dry_run: dryRun,
        }),
      });
      setActiveDocumentTask({ id: result.task_id, kind: "query" });
      documentPollRef.current = window.setInterval(() => {
        void pollDocumentTask(result.task_id, "query");
      }, 1200);
      await pollDocumentTask(result.task_id, "query", true);
    } catch (err) {
      setDocError(err.message);
      setDocumentProgressMessages([]);
      setActiveDocumentTask(null);
    } finally {
      setQueryingDocuments(false);
    }
  }

  async function pollDocumentTask(taskId, kind, immediate = false) {
    try {
      const data = await apiFetch(`/api/documents/tasks/${taskId}`);
      setDocumentProgressMessages(data.progress_messages || []);

      if (data.state === "completed") {
        window.clearInterval(documentPollRef.current);
        documentPollRef.current = null;
        setActiveDocumentTask(null);
        if (kind === "ingest") {
          if (fileInputRef.current) fileInputRef.current.value = "";
          setDocumentProgressMessages(["Document ingestion complete."]);
          await Promise.all([loadDocuments(), refreshOperationalData()]);
        } else {
          setDocAnswer(data.result);
          await refreshOperationalData();
        }
      } else if (data.state === "failed" || data.state === "canceled") {
        window.clearInterval(documentPollRef.current);
        documentPollRef.current = null;
        setActiveDocumentTask(null);
        setDocError(data.error || "Document task did not complete.");
        await Promise.all([loadDocuments(), refreshOperationalData()]);
      } else if (immediate) {
        return;
      }
    } catch (err) {
      window.clearInterval(documentPollRef.current);
      documentPollRef.current = null;
      setActiveDocumentTask(null);
      setDocError(err.message);
      await refreshOperationalData();
    }
  }

  async function cancelDocumentTask(taskId) {
    await apiFetch(`/api/documents/tasks/${taskId}/cancel`, { method: "POST", body: "{}" });
    window.clearInterval(documentPollRef.current);
    documentPollRef.current = null;
    setActiveDocumentTask(null);
    setDocumentProgressMessages(["Task canceled by user."]);
    await Promise.all([refreshOperationalData(), loadDocuments()]);
  }

  async function retryDocumentTask(taskId) {
    setDocError("");
    setDocumentProgressMessages(["Re-queued document task."]);
    const data = await apiFetch(`/api/documents/tasks/${taskId}/retry`, { method: "POST", body: "{}" });
    const matchingJob = jobs.find((job) => job.id === taskId);
    const kind = matchingJob?.kind === "document-ingest" ? "ingest" : "query";
    setActiveDocumentTask({ id: data.task_id, kind });
    documentPollRef.current = window.setInterval(() => {
      void pollDocumentTask(data.task_id, kind);
    }, 1200);
    await pollDocumentTask(data.task_id, kind, true);
    await refreshOperationalData();
  }

  function startRenameDocument(document) {
    setEditingDocumentId(document.id);
    setEditingDocumentName(document.name);
  }

  function cancelRenameDocument() {
    setEditingDocumentId(null);
    setEditingDocumentName("");
  }

  async function saveDocumentRename(documentId) {
    const trimmed = editingDocumentName.trim();
    if (!trimmed) return;
    await apiFetch(`/api/documents/${documentId}`, {
      method: "PATCH",
      body: JSON.stringify({ name: trimmed }),
    });
    cancelRenameDocument();
    await loadDocuments();
  }

  async function attachDocument(documentId, sessionId) {
    await apiFetch(`/api/documents/${documentId}`, {
      method: "PATCH",
      body: JSON.stringify({ session_id: sessionId }),
    });
    await loadDocuments();
  }

  async function detachDocument(documentId) {
    await apiFetch(`/api/documents/${documentId}`, {
      method: "PATCH",
      body: JSON.stringify({ session_id: null }),
    });
    await loadDocuments();
  }

  async function deleteDocument(documentId) {
    await apiFetch(`/api/documents/${documentId}`, { method: "DELETE" });
    setSelectedDocumentIds((prev) => prev.filter((id) => id !== documentId));
    if (editingDocumentId === documentId) {
      cancelRenameDocument();
    }
    await Promise.all([loadDocuments(), refreshOperationalData()]);
  }

  function toggleDocumentSelection(documentId) {
    setSelectedDocumentIds((prev) =>
      prev.includes(documentId) ? prev.filter((id) => id !== documentId) : [...prev, documentId]
    );
  }

  function exportMessage(messageId, format) {
    window.open(`/api/messages/${messageId}/export?format=${format}`, "_blank", "noopener,noreferrer");
  }

  if (!user) {
    return (
      <AuthScreen
        authMode={authMode}
        credentials={credentials}
        authError={authError}
        onModeChange={setAuthMode}
        onCredentialsChange={setCredentials}
        onSubmit={submitAuth}
      />
    );
  }

  const filteredJobs = jobsFilter === "all" ? jobs : jobs.filter((job) => job.state === jobsFilter);

  return (
    <div className="app app-layout">
      <HistorySidebar
        user={user}
        sessions={sessions}
        currentSessionId={currentSessionId}
        editingSessionId={editingSessionId}
        editingTitle={editingTitle}
        sessionSearch={sessionSearch}
        documentsCount={documents.length}
        runningJobsCount={jobs.filter((job) => job.state === "running").length}
        onStartNewSession={startNewSession}
        onLogout={logoutUser}
        onOpenProfile={() => setProfileDrawerOpen(true)}
        onLoadSession={loadSessionMessages}
        onEditingSessionChange={setEditingSessionId}
        onEditingTitleChange={setEditingTitle}
        onSessionSearchChange={setSessionSearch}
        onRenameSession={renameSession}
        onDeleteSession={deleteSession}
        onOpenDocuments={() => setDocumentsDrawerOpen(true)}
      />

      <div className="main-pane">
        <TopBar
          user={user}
          observability={observability}
          mode={mode}
          researchDepth={researchDepth}
          dryRun={dryRun}
          onModeChange={setMode}
          onResearchDepthChange={setResearchDepth}
          onDryRunChange={setDryRun}
          onOpenJobs={() => setJobsDrawerOpen(true)}
          onOpenDocuments={() => setDocumentsDrawerOpen(true)}
        />
        <ChatMessageList messages={messages} onOpenSources={setDrawerReport} onExport={exportMessage} />
        <Composer query={query} loading={loading} onQueryChange={setQuery} onSubmit={sendQuery} />
      </div>

      <SourcesDrawer report={drawerReport} onClose={() => setDrawerReport(null)} />
      <ProfileDrawer
        open={profileDrawerOpen}
        onClose={() => setProfileDrawerOpen(false)}
        profile={profileForm}
        passwordForm={passwordForm}
        error={profileError}
        success={profileSuccess}
        saving={profileSaving}
        onProfileChange={(field, value) => setProfileForm((prev) => ({ ...prev, [field]: value }))}
        onPasswordChange={(field, value) => setPasswordForm((prev) => ({ ...prev, [field]: value }))}
        onSaveProfile={() => void saveProfile()}
        onSavePassword={() => void savePassword()}
      />
      <JobsDrawer
        open={jobsDrawerOpen}
        onClose={() => setJobsDrawerOpen(false)}
        jobs={filteredJobs}
        observability={observability}
        jobsFilter={jobsFilter}
        onFilterChange={setJobsFilter}
        onRefresh={() => void refreshOperationalData()}
        onCancel={cancelDocumentTask}
        onRetry={retryDocumentTask}
      />
      <DocumentsDrawer
        open={documentsDrawerOpen}
        onClose={() => setDocumentsDrawerOpen(false)}
        documents={documents}
        currentSessionId={currentSessionId}
        fileInputRef={fileInputRef}
        uploadingDocument={uploadingDocument}
        docQuestion={docQuestion}
        setDocQuestion={setDocQuestion}
        docAnswer={docAnswer}
        docError={docError}
        queryingDocuments={queryingDocuments}
        includeResearch={includeResearch}
        setIncludeResearch={setIncludeResearch}
        documentProgressMessages={documentProgressMessages}
        activeDocumentTask={activeDocumentTask}
        selectedDocumentIds={selectedDocumentIds}
        editingDocumentId={editingDocumentId}
        editingDocumentName={editingDocumentName}
        setEditingDocumentName={setEditingDocumentName}
        toggleDocumentSelection={toggleDocumentSelection}
        onStartRenameDocument={startRenameDocument}
        onSaveDocumentRename={saveDocumentRename}
        onCancelRenameDocument={cancelRenameDocument}
        onAttachDocument={attachDocument}
        onDetachDocument={detachDocument}
        onDeleteDocument={deleteDocument}
        onUpload={uploadDocument}
        onAsk={submitDocumentQuestion}
        onCancelTask={cancelDocumentTask}
      />
    </div>
  );
}
