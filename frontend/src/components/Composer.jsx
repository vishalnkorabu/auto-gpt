export default function Composer({ query, loading, onQueryChange, onSubmit }) {
  return (
    <form className="composer" onSubmit={onSubmit}>
      <input
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        placeholder="Impact of AI on healthcare startups"
        disabled={loading}
      />
      <button type="submit" disabled={loading || !query.trim()}>
        Send
      </button>
    </form>
  );
}
