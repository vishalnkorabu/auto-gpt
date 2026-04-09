export default function AssistantResponse({ payload, onOpenSources, onExport }) {
  const { report, report_markdown: reportMarkdown } = payload;

  return (
    <div className="response">
      <div className="response-header">
        <div>
          <h2>{report?.headline || "Research response"}</h2>
          <pre className="response-text">{report?.response_text || payload.text}</pre>
        </div>
        <div className="action-row">
          {payload?.id ? (
            <>
              <button className="secondary-button" onClick={() => onExport(payload.id, "pdf")} type="button">
                Export PDF
              </button>
              <button className="secondary-button" onClick={() => onExport(payload.id, "docx")} type="button">
                Export DOCX
              </button>
            </>
          ) : null}
          <button className="secondary-button" onClick={onOpenSources} type="button">
            View sources
          </button>
        </div>
      </div>
      {reportMarkdown ? <div className="meta-line">Structured report saved for this response.</div> : null}
    </div>
  );
}
