export default function LoadingResponse({ query, progressMessages }) {
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
