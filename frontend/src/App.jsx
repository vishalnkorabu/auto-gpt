import { useEffect, useRef, useState } from "react";

const SESSION_KEY = "research-agent-session-id";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("multi");
  const [dryRun, setDryRun] = useState(false);
  const [drawerReport, setDrawerReport] = useState(null);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => {
    void loadSessions();
    const stored = window.localStorage.getItem(SESSION_KEY);
    if (stored) {
      void loadSessionMessages(stored);
    }
    return () => window.clearInterval(pollRef.current);
  }, []);

  async function loadSessions() {
    const res = await fetch("/api/sessions");
    const data = await res.json();
    if (res.ok) {
      setSessions(data.sessions || []);
    }
  }

  async function loadSessionMessages(sessionId) {
    const res = await fetch(`/api/sessions/${sessionId}/messages`);
    const data = await res.json();
    if (!res.ok) {
      window.localStorage.removeItem(SESSION_KEY);
      setCurrentSessionId(null);
      setMessages([]);
      return;
    }

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
  }

  async function startNewSession() {
    setCurrentSessionId(null);
    setMessages([]);
    window.localStorage.removeItem(SESSION_KEY);
    await loadSessions();
  }

  async function sendQuery(event) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || loading) return;

    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setQuery("");
    setLoading(true);

    try {
      const startRes = await fetch("/api/chat/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: trimmed,
          mode,
          dry_run: dryRun,
          session_id: currentSessionId,
        }),
      });
      const startData = await startRes.json();
      if (!startRes.ok) {
        throw new Error(startData.detail || "Unable to start research job");
      }

      setCurrentSessionId(startData.session_id);
      window.localStorage.setItem(SESSION_KEY, startData.session_id);
      await loadSessions();

      const loadingId = `${startData.job_id}-loading`;
      setMessages((prev) => [
        ...prev,
        { id: loadingId, role: "assistant-loading", query: trimmed, progressMessages: ["Queued research job."] },
      ]);

      pollRef.current = window.setInterval(() => {
        pollJob(startData.job_id, loadingId);
      }, 1200);
      await pollJob(startData.job_id, loadingId, true);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", text: `Error: ${err.message}` }]);
      setLoading(false);
    }
  }

  async function pollJob(jobId, loadingId, immediate = false) {
    try {
      const res = await fetch(`/api/chat/status/${jobId}`);
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Unable to fetch job status");
      }

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
        await loadSessions();
      } else if (data.state === "failed") {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
        setMessages((prev) =>
          prev.flatMap((msg) =>
            msg.id === loadingId ? [{ role: "assistant", text: `Error: ${data.error}` }] : [msg]
          )
        );
        setLoading(false);
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
    }
  }

  return (
    <div className="app app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div>
            <h2>History</h2>
            <p>Local conversation sessions saved in SQLite.</p>
          </div>
          <button className="secondary-button" type="button" onClick={startNewSession}>
            New chat
          </button>
        </div>
        <div className="session-list">
          {sessions.map((session) => (
            <button
              key={session.id}
              type="button"
              className={`session-card ${session.id === currentSessionId ? "active" : ""}`}
              onClick={() => loadSessionMessages(session.id)}
            >
              <div className="session-title">{session.title}</div>
              <div className="session-meta">{new Date(session.updated_at).toLocaleString()}</div>
            </button>
          ))}
        </div>
      </aside>

      <div className="main-pane">
        <header className="topbar">
          <div>
            <h1>AI Research Agent</h1>
            <p className="topline">Django-backed research chat with persistent local session history.</p>
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
