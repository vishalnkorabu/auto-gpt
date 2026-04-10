export default function HistorySidebar({
  user,
  sessions,
  currentSessionId,
  editingSessionId,
  editingTitle,
  sessionSearch,
  documentsCount,
  runningJobsCount,
  onStartNewSession,
  onLogout,
  onOpenProfile,
  onLoadSession,
  onEditingSessionChange,
  onEditingTitleChange,
  onSessionSearchChange,
  onRenameSession,
  onDeleteSession,
  onOpenDocuments,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div>
          <h2>History</h2>
          <p>{user.username}&apos;s local research sessions.</p>
        </div>
        <div className="sidebar-actions">
          <button className="secondary-button" type="button" onClick={onStartNewSession}>
            New chat
          </button>
          <button className="secondary-button" type="button" onClick={onOpenProfile}>
            Account
          </button>
          <button className="secondary-button" type="button" onClick={onLogout}>
            Logout
          </button>
        </div>
      </div>
      <input
        className="session-search"
        value={sessionSearch}
        onChange={(e) => onSessionSearchChange(e.target.value)}
        placeholder="Search prior sessions"
      />
      <div className="session-list">
        {sessions.map((session) => (
          <div key={session.id} className={`session-card ${session.id === currentSessionId ? "active" : ""}`}>
            <button type="button" className="session-main" onClick={() => onLoadSession(session.id)}>
              {editingSessionId === session.id ? (
                <input
                  className="session-edit"
                  value={editingTitle}
                  onChange={(e) => onEditingTitleChange(e.target.value)}
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
                <button type="button" className="mini-button" onClick={() => onRenameSession(session.id)}>
                  Save
                </button>
              ) : (
                <button
                  type="button"
                  className="mini-button"
                  onClick={() => {
                    onEditingSessionChange(session.id);
                    onEditingTitleChange(session.title);
                  }}
                >
                  Rename
                </button>
              )}
              <button type="button" className="mini-button danger" onClick={() => onDeleteSession(session.id)}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-header">
          <h3>Document Library</h3>
          <button className="mini-button" type="button" onClick={onOpenDocuments}>
            Open
          </button>
        </div>
        <p className="sidebar-note">Upload docs into the current workspace and query them alongside your research flow.</p>
        <div className="sidebar-stat-row">
          <span>{documentsCount} documents</span>
          <span>{runningJobsCount} running jobs</span>
        </div>
      </div>
    </aside>
  );
}
