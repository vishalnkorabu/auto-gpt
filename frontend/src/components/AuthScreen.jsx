export default function AuthScreen({
  authMode,
  credentials,
  authError,
  onModeChange,
  onCredentialsChange,
  onSubmit,
}) {
  return (
    <div className="auth-shell">
      <form className="auth-card" onSubmit={onSubmit}>
        <h1>AI Research Agent</h1>
        <p className="topline">Sign in to keep your research sessions isolated and persistent.</p>
        <div className="auth-tabs">
          <button type="button" className={authMode === "login" ? "tab active" : "tab"} onClick={() => onModeChange("login")}>
            Login
          </button>
          <button type="button" className={authMode === "register" ? "tab active" : "tab"} onClick={() => onModeChange("register")}>
            Register
          </button>
        </div>
        <input
          value={credentials.username}
          onChange={(e) => onCredentialsChange((prev) => ({ ...prev, username: e.target.value }))}
          placeholder="Username"
        />
        {authMode === "register" ? (
          <>
            <input
              value={credentials.display_name}
              onChange={(e) => onCredentialsChange((prev) => ({ ...prev, display_name: e.target.value }))}
              placeholder="Display name"
            />
            <input
              type="email"
              value={credentials.email}
              onChange={(e) => onCredentialsChange((prev) => ({ ...prev, email: e.target.value }))}
              placeholder="Email"
            />
          </>
        ) : null}
        <input
          type="password"
          value={credentials.password}
          onChange={(e) => onCredentialsChange((prev) => ({ ...prev, password: e.target.value }))}
          placeholder="Password"
        />
        {authError ? <div className="auth-error">{authError}</div> : null}
        <button type="submit">{authMode === "login" ? "Login" : "Create account"}</button>
      </form>
    </div>
  );
}
