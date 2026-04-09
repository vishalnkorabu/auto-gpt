export default function DocumentsDrawer({
  open,
  onClose,
  documents,
  currentSessionId,
  fileInputRef,
  uploadingDocument,
  docQuestion,
  setDocQuestion,
  docAnswer,
  docError,
  queryingDocuments,
  includeResearch,
  setIncludeResearch,
  documentProgressMessages,
  activeDocumentTask,
  selectedDocumentIds,
  toggleDocumentSelection,
  onUpload,
  onAsk,
  onCancelTask,
}) {
  return (
    <aside className={`drawer ${open ? "open" : ""}`}>
      <div className="drawer-panel drawer-panel-wide">
        <div className="drawer-header">
          <div>
            <div className="drawer-kicker">Documents</div>
            <h2>Upload and query files</h2>
          </div>
          <button className="secondary-button" onClick={onClose} type="button">
            Close
          </button>
        </div>
        <div className="drawer-content">
          <section className="panel-card">
            <div className="panel-title-row">
              <div>
                <h3>Upload</h3>
                <p>
                  {currentSessionId
                    ? "New uploads will be attached to the active chat session."
                    : "Uploads will be available across your account until attached to a session."}
                </p>
              </div>
            </div>
            <form className="upload-form" onSubmit={onUpload}>
              <input ref={fileInputRef} type="file" accept=".txt,.md,.csv,.json,.pdf,.docx" />
              <button className="secondary-button" type="submit" disabled={uploadingDocument}>
                {uploadingDocument ? "Uploading..." : "Upload document"}
              </button>
            </form>
            {!!documentProgressMessages.length && (
              <div className="progress-feed compact">
                {documentProgressMessages.slice(-4).map((message, index) => (
                  <div className="progress-item" key={`${message}-${index}`}>
                    <span className="progress-dot" />
                    <span>{message}</span>
                  </div>
                ))}
              </div>
            )}
            {activeDocumentTask?.kind === "ingest" ? (
              <button className="mini-button danger" type="button" onClick={() => onCancelTask(activeDocumentTask.id)}>
                Cancel upload job
              </button>
            ) : null}
          </section>

          <section className="panel-card">
            <div className="panel-title-row">
              <div>
                <h3>Ask documents</h3>
                <p>Select specific files if you want a narrower answer.</p>
              </div>
            </div>
            <form className="doc-query-form" onSubmit={onAsk}>
              <textarea
                value={docQuestion}
                onChange={(event) => setDocQuestion(event.target.value)}
                placeholder="What does the uploaded material say about adoption risk?"
              />
              <label className="checkbox doc-checkbox">
                <input type="checkbox" checked={includeResearch} onChange={(event) => setIncludeResearch(event.target.checked)} />
                Include live web research in the answer
              </label>
              <button className="secondary-button" type="submit" disabled={queryingDocuments || !docQuestion.trim()}>
                {queryingDocuments ? "Answering..." : "Query documents"}
              </button>
            </form>
            {activeDocumentTask?.kind === "query" ? (
              <button className="mini-button danger" type="button" onClick={() => onCancelTask(activeDocumentTask.id)}>
                Cancel query job
              </button>
            ) : null}
            {docError ? <div className="auth-error">{docError}</div> : null}
            {docAnswer ? (
              <article className="doc-answer-card">
                <div className="drawer-kicker">{docAnswer.mode === "hybrid" ? "Hybrid answer" : "Answer"}</div>
                <pre>{docAnswer.answer}</pre>
                {!!docAnswer.citations?.length && (
                  <div className="support-list">
                    {docAnswer.citations.map((citation) => (
                      <div className="support-card" key={`${citation.document_id}-${citation.chunk_index}`}>
                        <div className="support-name">{citation.name}</div>
                        <div className="source-meta">
                          {citation.file_type.toUpperCase()} · chunk {citation.chunk_index}
                        </div>
                        <p>{citation.excerpt}</p>
                      </div>
                    ))}
                  </div>
                )}
                {!!docAnswer.research_sources?.length && (
                  <div className="research-support">
                    <div className="drawer-kicker">Web research used</div>
                    <div className="source-points">
                      {docAnswer.research_sources.slice(0, 4).map((source) => (
                        <a className="source-link-chip" key={`${source.id}-${source.url}`} href={source.url} target="_blank" rel="noreferrer">
                          [{source.id}] {source.title}
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </article>
            ) : null}
          </section>

          <section className="panel-card">
            <div className="panel-title-row">
              <div>
                <h3>Library</h3>
                <p>{documents.length} uploaded files.</p>
              </div>
            </div>
            <div className="document-list">
              {documents.map((document) => (
                <label className="document-card" key={document.id}>
                  <input
                    type="checkbox"
                    checked={selectedDocumentIds.includes(document.id)}
                    disabled={document.status !== "processed"}
                    onChange={() => toggleDocumentSelection(document.id)}
                  />
                  <div>
                    <div className="document-name">{document.name}</div>
                    <div className="document-meta">
                      {document.file_type.toUpperCase()} · {document.chunk_count} chunks · {document.status}
                      {document.session_title ? ` · ${document.session_title}` : " · account-wide"}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </section>
        </div>
      </div>
      {open && <button className="drawer-backdrop" type="button" onClick={onClose} aria-label="Close drawer" />}
    </aside>
  );
}
