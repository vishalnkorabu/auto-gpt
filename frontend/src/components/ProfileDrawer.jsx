export default function ProfileDrawer({
  open,
  onClose,
  profile,
  passwordForm,
  error,
  success,
  saving,
  onProfileChange,
  onPasswordChange,
  onSaveProfile,
  onSavePassword,
}) {
  return (
    <aside className={`drawer ${open ? "open" : ""}`}>
      <div className="drawer-panel">
        <div className="drawer-header">
          <div>
            <div className="drawer-kicker">Account</div>
            <h2>Profile and security</h2>
          </div>
          <button className="secondary-button" onClick={onClose} type="button">
            Close
          </button>
        </div>
        <div className="drawer-content">
          <section className="panel-card">
            <div className="panel-title-row">
              <div>
                <h3>Profile</h3>
                <p>Keep your account details distinct across users and sessions.</p>
              </div>
            </div>
            <label className="field-grid">
              <span>Username</span>
              <input value={profile.username} disabled />
            </label>
            <label className="field-grid">
              <span>Display name</span>
              <input value={profile.display_name} onChange={(event) => onProfileChange("display_name", event.target.value)} />
            </label>
            <label className="field-grid">
              <span>Email</span>
              <input type="email" value={profile.email} onChange={(event) => onProfileChange("email", event.target.value)} />
            </label>
            <button className="secondary-button" type="button" onClick={onSaveProfile} disabled={saving}>
              {saving ? "Saving..." : "Save profile"}
            </button>
          </section>

          <section className="panel-card">
            <div className="panel-title-row">
              <div>
                <h3>Password</h3>
                <p>Change the password for this local multi-user account.</p>
              </div>
            </div>
            <label className="field-grid">
              <span>Current password</span>
              <input
                type="password"
                value={passwordForm.current_password}
                onChange={(event) => onPasswordChange("current_password", event.target.value)}
              />
            </label>
            <label className="field-grid">
              <span>New password</span>
              <input
                type="password"
                value={passwordForm.new_password}
                onChange={(event) => onPasswordChange("new_password", event.target.value)}
              />
            </label>
            <button className="secondary-button" type="button" onClick={onSavePassword} disabled={saving}>
              {saving ? "Updating..." : "Update password"}
            </button>
          </section>

          {error ? <div className="auth-error">{error}</div> : null}
          {success ? <div className="success-banner">{success}</div> : null}
        </div>
      </div>
      {open && <button className="drawer-backdrop" type="button" onClick={onClose} aria-label="Close drawer" />}
    </aside>
  );
}
