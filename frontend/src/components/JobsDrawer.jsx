export default function JobsDrawer({
  open,
  onClose,
  jobs,
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
