export default function JobsDrawer({
  open,
  onClose,
  jobs,
  observability,
  jobsFilter,
  onFilterChange,
  onRefresh,
  onCancel,
  onRetry,
}) {
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
          {observability ? (
            <section className="panel-card ops-grid">
              <article className="metric-card">
                <div className="drawer-kicker">Queue</div>
                <strong>{observability.queue?.mode || "thread"}</strong>
                <span>{observability.research_jobs?.running || 0} research jobs running</span>
              </article>
              <article className="metric-card">
                <div className="drawer-kicker">Requests</div>
                <strong>{observability.requests?.total || 0}</strong>
                <span>
                  {observability.requests?.errors || 0} API errors · avg {observability.requests?.avg_duration_ms || 0} ms
                </span>
              </article>
              <article className="metric-card">
                <div className="drawer-kicker">Usage</div>
                <strong>{observability.usage?.total_tokens || 0} tokens</strong>
                <span>
                  ${(observability.usage?.estimated_cost_usd || 0).toFixed(4)} estimated cost · avg{" "}
                  {observability.usage?.avg_duration_ms || 0} ms
                </span>
              </article>
              <article className="metric-card">
                <div className="drawer-kicker">Research jobs</div>
                <strong>{observability.research_jobs?.completed || 0} completed</strong>
                <span>avg {observability.research_jobs?.avg_duration_ms || 0} ms</span>
              </article>
              <article className="metric-card">
                <div className="drawer-kicker">Document tasks</div>
                <strong>{observability.document_tasks?.completed || 0} completed</strong>
                <span>avg {observability.document_tasks?.avg_duration_ms || 0} ms</span>
              </article>
              <article className="metric-card">
                <div className="drawer-kicker">Retention</div>
                <strong>{observability.retention?.processed_documents || 0} processed docs</strong>
                <span>
                  {observability.retention?.expired_documents || 0} past {observability.retention?.retention_days || 0} days
                </span>
              </article>
            </section>
          ) : null}
          {observability?.usage?.providers?.length ? (
            <section className="panel-card">
              <div className="panel-title-row">
                <div>
                  <h3>Usage breakdown</h3>
                  <p>Provider and model usage captured from research and document runs.</p>
                </div>
              </div>
              <div className="document-list">
                {observability.usage.providers.map((item) => (
                  <article className="job-card" key={`${item.provider}-${item.model}`}>
                    <div className="job-row">
                      <div className="job-query">
                        {item.provider} · {item.model}
                      </div>
                      <span className={`status-pill ${item.errors ? "failed" : "completed"}`}>
                        {item.calls} calls
                      </span>
                    </div>
                    <div className="job-meta">
                      {item.total_tokens} tokens · ${(item.estimated_cost_usd || 0).toFixed(4)} cost · avg{" "}
                      {item.avg_duration_ms || 0} ms
                    </div>
                    {item.errors ? <div className="job-error">{item.errors} failed calls in the last 7 days.</div> : null}
                  </article>
                ))}
              </div>
            </section>
          ) : null}
          {observability?.recent_errors?.length ? (
            <section className="panel-card">
              <div className="panel-title-row">
                <div>
                  <h3>Recent errors</h3>
                  <p>Latest API and LLM failures captured by the app.</p>
                </div>
              </div>
              <div className="document-list">
                {observability.recent_errors.map((item, index) => (
                  <article className="job-card" key={`${item.kind}-${item.created_at}-${index}`}>
                    <div className="job-row">
                      <div className="job-query">{item.path}</div>
                      <span className="status-pill failed">{item.kind}</span>
                    </div>
                    <div className="job-error">{item.message}</div>
                  </article>
                ))}
              </div>
            </section>
          ) : null}
          <div className="filter-row">
            {["all", "queued", "running", "completed", "failed", "canceled"].map((value) => (
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
              <div className="job-actions">
                {job.kind.startsWith("document-") && ["queued", "running"].includes(job.state) ? (
                  <button className="mini-button danger" type="button" onClick={() => onCancel(job.id)}>
                    Cancel
                  </button>
                ) : null}
                {job.kind.startsWith("document-") && ["failed", "canceled"].includes(job.state) ? (
                  <button className="mini-button" type="button" onClick={() => onRetry(job.id)}>
                    Retry
                  </button>
                ) : null}
              </div>
              {job.error ? <div className="job-error">{job.error}</div> : null}
            </article>
          ))}
        </div>
      </div>
      {open && <button className="drawer-backdrop" type="button" onClick={onClose} aria-label="Close drawer" />}
    </aside>
  );
}
