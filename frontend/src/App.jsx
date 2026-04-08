import { useEffect, useRef, useState } from "react";

const SESSION_KEY = "research-agent-session-id";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("multi");
  const [dryRun, setDryRun] = useState(false);
  const [drawerReport, setDrawerReport] = useState(null);
  const [jobsDrawerOpen, setJobsDrawerOpen] = useState(false);
  const [documentsDrawerOpen, setDocumentsDrawerOpen] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [authMode, setAuthMode] = useState("login");
  const [credentials, setCredentials] = useState({ username: "", password: "" });
  const [user, setUser] = useState(null);
  const [authError, setAuthError] = useState("");
  const [docQuestion, setDocQuestion] = useState("");
  const [docAnswer, setDocAnswer] = useState(null);
  const [docError, setDocError] = useState("");
  const [uploadingDocument, setUploadingDocument] = useState(false);
  const [queryingDocuments, setQueryingDocuments] = useState(false);
  const [documentProgressMessages, setDocumentProgressMessages] = useState([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState([]);
  const [jobsFilter, setJobsFilter] = useState("all");
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
    if (!jobsDrawerOpen || !user) return undefined;
    void loadJobs();
    const intervalId = window.setInterval(() => {
      void loadJobs();
    }, 3000);
    return () => window.clearInterval(intervalId);
  }, [jobsDrawerOpen, user]);

  async function bootstrap() {
    const me = await apiFetch("/api/auth/me");
    if (me.authenticated) {
      setUser(me.user);
      await Promise.all([loadSessions(), loadJobs(), loadDocuments()]);
      const stored = window.localStorage.getItem(SESSION_KEY);
      if (stored) {
        await loadSessionMessages(stored);
      }
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

  async function submitAuth(event) {
    event.preventDefault();
    setAuthError("");
    try {
      const path = authMode === "login" ? "/api/auth/login" : "/api/auth/register";
      const data = await apiFetch(path, {
        method: "POST",
        body: JSON.stringify(credentials),
      });
      setUser(data.user);
      setCredentials({ username: "", password: "" });
      await Promise.all([loadSessions(), loadJobs(), loadDocuments()]);
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
    window.localStorage.removeItem(SESSION_KEY);
  }

  async function loadSessions() {
    const data = await apiFetch("/api/sessions");
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
      setDryRun(data.session.dry_run);
      setMessages(
        (data.messages || []).map((message) =>
          message.role === "assistant"
            ? { id: message.id, role: "assistant", payload: message, text: message.text }
            : { id: message.id, role: "user", text: message.text }
        )
      );
      window.localStorage.setItem(SESSION_KEY, sessionId);
    } catch (_err) {
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
    window.localStorage.removeItem(SESSION_KEY);
    await Promise.all([loadSessions(), loadJobs(), loadDocuments()]);
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
      await Promise.all([loadSessions(), loadJobs(), loadDocuments()]);
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
          dry_run: dryRun,
          session_id: currentSessionId,
        }),
      });

      setCurrentSessionId(startData.session_id);
      window.localStorage.setItem(SESSION_KEY, startData.session_id);
      await Promise.all([loadSessions(), loadJobs(), loadDocuments()]);

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
        prev.map((msg) =>
          msg.id === loadingId ? { ...msg, progressMessages: data.progress_messages || [] } : msg
        )
      );

      if (data.state === "completed") {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
        setMessages((prev) =>
          prev.flatMap((msg) =>
            msg.id === loadingId
              ? [{ role: "assistant", payload: data.result, text: data.result.text }]
              : [msg]
          )
        );
        setLoading(false);
        await Promise.all([loadSessions(), loadJobs()]);
      } else if (data.state === "failed") {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
        setMessages((prev) =>
          prev.flatMap((msg) =>
            msg.id === loadingId ? [{ role: "assistant", text: `Error: ${data.error}` }] : [msg]
          )
        );
        setLoading(false);
        await loadJobs();
      } else if (immediate) {
        return;
      }
    } catch (err) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
      setMessages((prev) =>
        prev.flatMap((msg) =>
          msg.id === loadingId ? [{ role: "assistant", text: `Error: ${err.message}` }] : [msg]
        )
      );
      setLoading(false);
      await loadJobs();
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
      const data = await apiFetch("/api/documents", {
        method: "POST",
        body: formData,
      });
      documentPollRef.current = window.setInterval(() => {
        void pollDocumentTask(data.task_id, "ingest");
      }, 1200);
      await pollDocumentTask(data.task_id, "ingest", true);
    } catch (err) {
      setDocError(err.message);
      setDocumentProgressMessages([]);
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
      const payload = {
        question: trimmed,
        session_id: currentSessionId,
        document_ids: selectedDocumentIds,
      };
      const result = await apiFetch("/api/documents/query", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      documentPollRef.current = window.setInterval(() => {
        void pollDocumentTask(result.task_id, "query");
      }, 1200);
      await pollDocumentTask(result.task_id, "query", true);
    } catch (err) {
      setDocError(err.message);
      setDocumentProgressMessages([]);
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
        if (kind === "ingest") {
          if (fileInputRef.current) {
            fileInputRef.current.value = "";
          }
          setDocumentProgressMessages(["Document ingestion complete."]);
          await Promise.all([loadDocuments(), loadJobs()]);
        } else {
          setDocAnswer(data.result);
          await loadJobs();
        }
      } else if (data.state === "failed") {
        window.clearInterval(documentPollRef.current);
        documentPollRef.current = null;
        setDocError(data.error || "Document task failed.");
        await Promise.all([loadDocuments(), loadJobs()]);
      } else if (immediate) {
        return;
      }
    } catch (err) {
      window.clearInterval(documentPollRef.current);
      documentPollRef.current = null;
      setDocError(err.message);
      await loadJobs();
    }
  }

  function toggleDocumentSelection(documentId) {
    setSelectedDocumentIds((prev) =>
      prev.includes(documentId) ? prev.filter((id) => id !== documentId) : [...prev, documentId]
    );
  }

  if (!user) {
    return (
      <div className="auth-shell">
        <form className="auth-card" onSubmit={submitAuth}>
          <h1>AI Research Agent</h1>
          <p className="topline">Sign in to keep your research sessions isolated and persistent.</p>
          <div className="auth-tabs">
            <button type="button" className={authMode === "login" ? "tab active" : "tab"} onClick={() => setAuthMode("login")}>
              Login
            </button>
            <button type="button" className={authMode === "register" ? "tab active" : "tab"} onClick={() => setAuthMode("register")}>
              Register
            </button>
          </div>
          <input
            value={credentials.username}
            onChange={(e) => setCredentials((prev) => ({ ...prev, username: e.target.value }))}
            placeholder="Username"
          />
          <input
            type="password"
            value={credentials.password}
            onChange={(e) => setCredentials((prev) => ({ ...prev, password: e.target.value }))}
            placeholder="Password"
          />
          {authError ? <div className="auth-error">{authError}</div> : null}
          <button type="submit">{authMode === "login" ? "Login" : "Create account"}</button>
        </form>
      </div>
    );
  }

  const filteredJobs = jobsFilter === "all" ? jobs : jobs.filter((job) => job.state === jobsFilter);

  return (
    <div className="app app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div>
            <h2>History</h2>
            <p>{user.username}&apos;s local research sessions.</p>
          </div>
          <div className="sidebar-actions">
            <button className="secondary-button" type="button" onClick={startNewSession}>
              New chat
            </button>
            <button className="secondary-button" type="button" onClick={logoutUser}>
              Logout
            </button>
          </div>
        </div>
        <div className="session-list">
          {sessions.map((session) => (
            <div key={session.id} className={`session-card ${session.id === currentSessionId ? "active" : ""}`}>
              <button type="button" className="session-main" onClick={() => loadSessionMessages(session.id)}>
                {editingSessionId === session.id ? (
                  <input
                    className="session-edit"
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <div className="session-title">{session.title}</div>
                )}
                <div className="session-meta">
                  {new Date(session.updated_at).toLocaleString()} - {session.reports_count ?? 0} reports
                </div>
              </button>
              <div className="session-actions">
                {editingSessionId === session.id ? (
                  <button type="button" className="mini-button" onClick={() => renameSession(session.id)}>
                    Save
                  </button>
                ) : (
                  <button
                    type="button"
                    className="mini-button"
                    onClick={() => {
                      setEditingSessionId(session.id);
                      setEditingTitle(session.title);
                    }}
                  >
                    Rename
                  </button>
                )}
                <button type="button" className="mini-button danger" onClick={() => deleteSession(session.id)}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-header">
            <h3>Document Library</h3>
            <button className="mini-button" type="button" onClick={() => setDocumentsDrawerOpen(true)}>
              Open
            </button>
          </div>
          <p className="sidebar-note">Upload docs into the current workspace and query them alongside your research flow.</p>
          <div className="sidebar-stat-row">
            <span>{documents.length} documents</span>
            <span>{jobs.filter((job) => job.state === "running").length} running jobs</span>
          </div>
        </div>
      </aside>

      <div className="main-pane">
        <header className="topbar">
          <div>
            <h1>AI Research Agent</h1>
            <p className="topline">Django + Celery + Redis research chat with user-isolated session history.</p>
          </div>
          <div className="controls">
            <label>
              Mode
              <select value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="multi">multi</option>
                <option value="single">single</option>
              </select>
            </label>
            <label className="checkbox">
              <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
              Dry run
            </label>
            <button className="secondary-button" type="button" onClick={() => setJobsDrawerOpen(true)}>
              Job status
            </button>
            <button className="secondary-button" type="button" onClick={() => setDocumentsDrawerOpen(true)}>
              Documents
            </button>
          </div>
        </header>

        <main className="chat">
          {messages.length === 0 && <p className="placeholder">Ask a research question to start.</p>}
          {messages.map((msg, index) => (
            <article key={msg.id || index} className={`bubble ${bubbleClass(msg.role)}`}>
              <div className="role">{labelForRole(msg.role)}</div>
              {msg.role === "assistant" && msg.payload ? (
                <AssistantResponse payload={msg.payload} onOpenSources={() => setDrawerReport(msg.payload.report)} />
              ) : msg.role === "assistant-loading" ? (
                <LoadingResponse query={msg.query} progressMessages={msg.progressMessages} />
              ) : (
                <pre>{msg.text}</pre>
              )}
            </article>
          ))}
        </main>

        <form className="composer" onSubmit={sendQuery}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Impact of AI on healthcare startups"
            disabled={loading}
          />
          <button type="submit" disabled={loading || !query.trim()}>
            Send
          </button>
        </form>
      </div>

      <SourcesDrawer report={drawerReport} onClose={() => setDrawerReport(null)} />
      <JobsDrawer
        open={jobsDrawerOpen}
        onClose={() => setJobsDrawerOpen(false)}
        jobs={filteredJobs}
        jobsFilter={jobsFilter}
        onFilterChange={setJobsFilter}
        onRefresh={() => void loadJobs()}
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
        documentProgressMessages={documentProgressMessages}
        selectedDocumentIds={selectedDocumentIds}
        toggleDocumentSelection={toggleDocumentSelection}
        onUpload={uploadDocument}
        onAsk={submitDocumentQuestion}
      />
    </div>
  );
}

function AssistantResponse({ payload, onOpenSources }) {
  const { report, report_markdown: reportMarkdown } = payload;

  return (
    <div className="response">
      <div className="response-header">
        <div>
          <h2>{report?.headline || "Research response"}</h2>
          <pre className="response-text">{report?.response_text || payload.text}</pre>
        </div>
        <div className="action-row">
          <button className="secondary-button" onClick={onOpenSources} type="button">
            View sources
          </button>
        </div>
      </div>
      {reportMarkdown ? <div className="meta-line">Structured report saved for this response.</div> : null}
    </div>
  );
}

function LoadingResponse({ query, progressMessages }) {
  const latest = progressMessages[progressMessages.length - 1] || "Generating response.";

  return (
    <div className="loading-shell">
      <div className="loading-stage">
        <div className="loading-badge">Generating</div>
        <h2>{query}</h2>
        <p>{latest}</p>
      </div>
      <div className="progress-feed">
        {progressMessages.slice(-5).map((message, index) => (
          <div className="progress-item" key={`${message}-${index}`}>
            <span className="progress-dot" />
            <span>{message}</span>
          </div>
        ))}
      </div>
      <div className="loading-bars" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}

function SourcesDrawer({ report, onClose }) {
  return (
    <aside className={`drawer ${report ? "open" : ""}`}>
      <div className="drawer-panel">
        <div className="drawer-header">
          <div>
            <div className="drawer-kicker">Sources</div>
            <h2>{report?.headline || "Research sources"}</h2>
          </div>
          <button className="secondary-button" onClick={onClose} type="button">
            Close
          </button>
        </div>
        <div className="drawer-content">
          {report?.sources?.map((source) => (
            <article className="source-card" key={source.id}>
              <div className="source-topline">
                <span className="citation-chip">[{source.id}]</span>
                <span className="source-type">{source.source_type}</span>
              </div>
              <h3>{source.title}</h3>
              <a href={source.url} target="_blank" rel="noreferrer">
                {source.url}
              </a>
              <div className="source-meta">Credibility {Math.round((source.credibility_score || 0) * 100)}%</div>
              <p>{source.summary || source.snippet}</p>
              {!!source.key_points?.length && (
                <div className="source-points">
                  {source.key_points.map((point, index) => (
                    <div key={`${source.id}-${index}`} className="source-point">
                      {point}
                    </div>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      </div>
      {report && <button className="drawer-backdrop" type="button" onClick={onClose} aria-label="Close drawer" />}
    </aside>
  );
}

function JobsDrawer({ open, onClose, jobs, jobsFilter, onFilterChange, onRefresh }) {
  return (
    <aside className={`drawer ${open ? "open" : ""}`}>
      <div className="drawer-panel drawer-panel-wide">
        <div className="drawer-header">
          <div>
            <div className="drawer-kicker">Operations</div>
            <h2>Job status</h2>
          </div>
          <div className="action-row">
            <button className="secondary-button" type="button" onClick={onRefresh}>
              Refresh
            </button>
            <button className="secondary-button" onClick={onClose} type="button">
              Close
            </button>
          </div>
        </div>
        <div className="drawer-content">
          <div className="filter-row">
            {["all", "queued", "running", "completed", "failed"].map((value) => (
              <button
                key={value}
                type="button"
                className={`mini-button ${jobsFilter === value ? "active" : ""}`}
                onClick={() => onFilterChange(value)}
              >
                {value}
              </button>
            ))}
          </div>
          {jobs.length === 0 ? <p className="placeholder">No jobs yet.</p> : null}
          {jobs.map((job) => (
            <article className="job-card" key={job.id}>
              <div className="job-row">
                <div>
                  <div className="job-query">{job.query}</div>
                  <div className="job-meta">
                    {job.session_title} · {new Date(job.created_at).toLocaleString()}
                  </div>
                </div>
                <span className={`status-pill ${job.state}`}>{job.state}</span>
              </div>
              <div className="job-meta">
                {job.kind === "research" ? `Mode ${job.mode} · ${job.dry_run ? "Dry run" : "Live run"}` : `Type ${job.kind}`}
              </div>
              {job.latest_progress ? <div className="job-progress">{job.latest_progress}</div> : null}
              {job.error ? <div className="job-error">{job.error}</div> : null}
            </article>
          ))}
        </div>
      </div>
      {open && <button className="drawer-backdrop" type="button" onClick={onClose} aria-label="Close drawer" />}
    </aside>
  );
}

function DocumentsDrawer({
  open,
  onClose,
  documents,
  currentSessionId,
  fileInputRef,
  uploadingDocument,
  docQuestion,
  setDocQuestion,
  docAnswer,
  docError,
  queryingDocuments,
  documentProgressMessages,
  selectedDocumentIds,
  toggleDocumentSelection,
  onUpload,
  onAsk,
}) {
  return (
    <aside className={`drawer ${open ? "open" : ""}`}>
      <div className="drawer-panel drawer-panel-wide">
        <div className="drawer-header">
          <div>
            <div className="drawer-kicker">Documents</div>
            <h2>Upload and query files</h2>
          </div>
          <button className="secondary-button" onClick={onClose} type="button">
            Close
          </button>
        </div>
        <div className="drawer-content">
          <section className="panel-card">
            <div className="panel-title-row">
              <div>
                <h3>Upload</h3>
                <p>
                  {currentSessionId
                    ? "New uploads will be attached to the active chat session."
                    : "Uploads will be available across your account until attached to a session."}
                </p>
              </div>
            </div>
            <form className="upload-form" onSubmit={onUpload}>
              <input ref={fileInputRef} type="file" accept=".txt,.md,.csv,.json,.pdf,.docx" />
              <button className="secondary-button" type="submit" disabled={uploadingDocument}>
                {uploadingDocument ? "Uploading..." : "Upload document"}
              </button>
            </form>
            {!!documentProgressMessages.length && (
              <div className="progress-feed compact">
                {documentProgressMessages.slice(-4).map((message, index) => (
                  <div className="progress-item" key={`${message}-${index}`}>
                    <span className="progress-dot" />
                    <span>{message}</span>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="panel-card">
            <div className="panel-title-row">
              <div>
                <h3>Ask documents</h3>
                <p>Select specific files if you want a narrower answer.</p>
              </div>
            </div>
            <form className="doc-query-form" onSubmit={onAsk}>
              <textarea
                value={docQuestion}
                onChange={(event) => setDocQuestion(event.target.value)}
                placeholder="What does the uploaded material say about adoption risk?"
              />
              <button className="secondary-button" type="submit" disabled={queryingDocuments || !docQuestion.trim()}>
                {queryingDocuments ? "Answering..." : "Query documents"}
              </button>
            </form>
            {docError ? <div className="auth-error">{docError}</div> : null}
            {docAnswer ? (
              <article className="doc-answer-card">
                <div className="drawer-kicker">Answer</div>
                <pre>{docAnswer.answer}</pre>
                {!!docAnswer.citations?.length && (
                  <div className="support-list">
                    {docAnswer.citations.map((citation) => (
                      <div className="support-card" key={`${citation.document_id}-${citation.chunk_index}`}>
                        <div className="support-name">{citation.name}</div>
                        <div className="source-meta">
                          {citation.file_type.toUpperCase()} · chunk {citation.chunk_index}
                        </div>
                        <p>{citation.excerpt}</p>
                      </div>
                    ))}
                  </div>
                )}
              </article>
            ) : null}
          </section>

          <section className="panel-card">
            <div className="panel-title-row">
              <div>
                <h3>Library</h3>
                <p>{documents.length} uploaded files.</p>
              </div>
            </div>
            <div className="document-list">
              {documents.map((document) => (
                <label className="document-card" key={document.id}>
                  <input
                    type="checkbox"
                    checked={selectedDocumentIds.includes(document.id)}
                    disabled={document.status !== "processed"}
                    onChange={() => toggleDocumentSelection(document.id)}
                  />
                  <div>
                    <div className="document-name">{document.name}</div>
                    <div className="document-meta">
                      {document.file_type.toUpperCase()} · {document.chunk_count} chunks · {document.status}
                      {document.session_title ? ` · ${document.session_title}` : " · account-wide"}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </section>
        </div>
      </div>
      {open && <button className="drawer-backdrop" type="button" onClick={onClose} aria-label="Close drawer" />}
    </aside>
  );
}

function bubbleClass(role) {
  if (role === "assistant-loading") return "assistant loading";
  if (role === "assistant") return "assistant";
  return "user";
}

function labelForRole(role) {
  if (role === "assistant-loading") return "Agent";
  if (role === "assistant") return "Agent";
  return "You";
}
