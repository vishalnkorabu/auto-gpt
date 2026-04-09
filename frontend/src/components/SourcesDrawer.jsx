export default function SourcesDrawer({ report, onClose }) {
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
