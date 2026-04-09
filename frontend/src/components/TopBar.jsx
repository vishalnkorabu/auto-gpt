export default function TopBar({
  mode,
  researchDepth,
  dryRun,
  onModeChange,
  onResearchDepthChange,
  onDryRunChange,
  onOpenJobs,
  onOpenDocuments,
}) {
  return (
    <header className="topbar">
      <div>
        <h1>AI Research Agent</h1>
        <p className="topline">Django + Celery + Redis research chat with user-isolated session history.</p>
      </div>
      <div className="controls">
        <label>
          Mode
          <select value={mode} onChange={(e) => onModeChange(e.target.value)}>
            <option value="multi">multi</option>
            <option value="single">single</option>
          </select>
        </label>
        <label>
          Depth
          <select value={researchDepth} onChange={(e) => onResearchDepthChange(e.target.value)}>
            <option value="quick">quick</option>
            <option value="standard">standard</option>
            <option value="deep">deep</option>
          </select>
        </label>
        <label className="checkbox">
          <input type="checkbox" checked={dryRun} onChange={(e) => onDryRunChange(e.target.checked)} />
          Dry run
        </label>
        <button className="secondary-button" type="button" onClick={onOpenJobs}>
          Job status
        </button>
        <button className="secondary-button" type="button" onClick={onOpenDocuments}>
          Documents
        </button>
      </div>
    </header>
  );
}
