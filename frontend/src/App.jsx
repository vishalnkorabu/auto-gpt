import { useState } from "react";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("multi");
  const [dryRun, setDryRun] = useState(false);

  async function sendQuery(event) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || loading) return;

    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setQuery("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed, mode, dry_run: dryRun }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Request failed");
      }

      const text = `${data.answer}\n\nSources: ${data.sources_count}\nOutput: ${data.output_dir}`;
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text, report: data.report_markdown },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1>AI Research Agent</h1>
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
          <article key={index} className={`bubble ${msg.role}`}>
            <div className="role">{msg.role === "user" ? "You" : "Agent"}</div>
            <pre>{msg.text}</pre>
            {msg.report && (
              <details>
                <summary>Full report</summary>
                <pre>{msg.report}</pre>
              </details>
            )}
          </article>
        ))}
        {loading && <div className="bubble assistant"><div className="role">Agent</div><pre>Researching...</pre></div>}
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
  );
}
