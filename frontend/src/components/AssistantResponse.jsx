export default function AssistantResponse({ payload, onOpenSources }) {
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
